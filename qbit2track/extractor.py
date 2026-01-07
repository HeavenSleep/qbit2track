"""
Main torrent extraction and processing logic
"""
import logging
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from qbittorrentapi import Client

from .config import Config
from .models import TorrentData
from .media import FileAnalyzer, FilenameAnalyzer, TMDBMatcher
from .torrent import TorrentManager, MetadataManager
from .nfo import NFOGenerator
from .trackers.lacale import LaCaleUploader
from .naming import MediaAnalyzer, NamingContext


logger = logging.getLogger(__name__)


class TorrentExtractor:
    """Main torrent extraction and processing class"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = Client(
            host=config.qbit.url,
            username=config.qbit.username,
            password=config.qbit.password
        )
        
        # Initialize components
        self.file_analyzer = FileAnalyzer()
        self.filename_analyzer = FilenameAnalyzer(self.file_analyzer)
        self.tmdb_matcher = TMDBMatcher(config, Path(config.output.output_dir))
        self.torrent_manager = TorrentManager()
        self.metadata_manager = MetadataManager()
        self.nfo_generator = NFOGenerator()
        self.naming_context = NamingContext(config)
    
    def extract_all(self, dry_run: bool = False,
                   tags: Optional[List[str]] = None,
                   category: Optional[str] = None,
                   update_tracker: Optional[str] = None,
                   update_comment: Optional[str] = None,
                   update_tags: Optional[str] = None,
                   update_category: Optional[str] = None,
                   tracker_naming: Optional[str] = None) -> Dict[str, int]:
        """Extract all torrents from qBittorrent"""
        results = {'success': 0, 'failed': 0}
        
        try:
            torrents = self.client.torrents.info()
            logger.info(f"Found {len(torrents)} torrents to process")
            
            # Apply filters if specified
            if tags or category:
                filtered_torrents = []
                for torrent in torrents:
                    # Filter by tags
                    if tags:
                        torrent_tags = torrent.tags.lower().split(', ') if torrent.tags else []
                        if not any(tag.lower() in torrent_tags for tag in tags):
                            continue
                    
                    # Filter by category
                    if category and torrent.category.lower() != category.lower():
                        continue
                    
                    filtered_torrents.append(torrent)
                
                torrents = filtered_torrents
                logger.info(f"Filtered to {len(torrents)} torrents")
            
            for torrent in torrents:
                try:
                    logger.info(f"[{results['success'] + 1} / {results['failed']} / {len(torrents)}] Processing: {torrent.name}")
                    self._extract_single_torrent(
                        torrent, dry_run, update_tracker, update_comment, update_tags, update_category, tracker_naming
                    )
                    results['success'] += 1
                    logger.info(f"Processed: {torrent.name}")
                except Exception as e:
                    results['failed'] += 1
                    logger.error(f"Failed to process {torrent.name}: {e}")
                    traceback.print_exc()
        
        except Exception as e:
            logger.error(f"Failed to connect to qBittorrent: {e}")
        
        return results
    
    def _extract_single_torrent(self, torrent, dry_run: bool = False,
                              update_tracker: Optional[str] = None,
                              update_comment: Optional[str] = None,
                              update_tags: Optional[str] = None,
                              update_category: Optional[str] = None,
                              tracker_naming: Optional[str] = None):
        """Extract a single torrent"""
        # Analyze media information
        media_info = self.filename_analyzer.analyze_filename(
            torrent.name, torrent.category, Path(torrent.content_path)
        )
        
        # Match with TMDB
        tmdb_data = self.tmdb_matcher.match_media(media_info)
        
        # Enhance media info with pymediainfo technical details
        MediaAnalyzer.enhance_with_pymediainfo(media_info, torrent.files, torrent.content_path)
        
        # Enhance source information with TMDB data
        MediaAnalyzer.enhance_source_with_tmdb(media_info, tmdb_data)
        
        # Ensure team information is set
        if not media_info.team:
            media_info.team = self.naming_context.default_team
        
        # Create torrent data object
        torrent_data = TorrentData(
            hash=torrent.hash,
            name=torrent.name,
            private=torrent.private,
            save_path=torrent.save_path,
            content_path=torrent.content_path,
            size=torrent.size,
            files=[{
                'name': f.name,
                'size': f.size,
                'path': f"{torrent.content_path}/{f.name}"
            } for f in torrent.files],
            tracker=torrent.trackers,
            tags=torrent.tags.split(', ') if torrent.tags else [],
            category=torrent.category,
            media_info=media_info,
            comment=torrent.comment,
            created_by='qbit2track',
            created_at=datetime.now(),
        )
        
        # Apply updates if specified
        if update_tracker:
            torrent_data.tracker = [update_tracker] if update_tracker else torrent_data.tracker
            logger.info(f"Updating tracker to: {update_tracker}")
        
        if update_comment:
            torrent_data.comment = update_comment
            logger.info(f"Updating comment to: {update_comment}")
        
        if update_tags:
            tag_list = [tag.strip() for tag in update_tags.split(',') if tag.strip()]
            torrent_data.tags = tag_list
            logger.info(f"Updating tags to: {', '.join(tag_list)}")
        
        if update_category:
            torrent_data.category = update_category
            logger.info(f"Updating category to: {update_category}")
        
        # Apply tracker-specific naming if specified
        tracker_name = None
        if tracker_naming:
            try:
                if tracker_naming.lower() == 'lacale':
                    # Initialize La Cale uploader for naming
                    la_cale_uploader = LaCaleUploader('dummy_passkey')
                    
                    # Create enhanced naming context
                    torrent_data_dict = {
                        'name': torrent_data.name,
                        'size': torrent_data.size,
                        'tags': torrent_data.tags,
                        'files': torrent_data.files,
                        'hash': torrent_data.hash,
                        'category': torrent_data.category
                    }
                    
                    naming_context = self.naming_context.create_context(media_info, torrent_data_dict, tmdb_data)
                    
                    # Generate tracker-specific name using the naming context
                    tracker_name = la_cale_uploader.generate_torrent_name(naming_context, torrent_data_dict)
                    
                    # Update torrent data name
                    torrent_data.name = tracker_name
                    logger.info(f"Applied {tracker_naming} naming: {tracker_name}")
                else:
                    logger.warning(f"Unknown tracker: {tracker_naming}")
            except Exception as e:
                logger.error(f"Failed to apply {tracker_naming} naming: {e}")
                logger.info("Using original torrent name")
        
        if dry_run:
            logger.info(f"DRY RUN: Would extract {torrent.name}")
            return
        
        # Create output directory
        output_name = tracker_name if tracker_naming else torrent.name
        output_dir = Path(self.config.output.output_dir) / self._sanitize_filename(output_name)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create NFO file
        if self.config.output.create_nfo:
            # Find the largest media file for pymediainfo analysis
            media_file_path = None
            if torrent.files:
                # Sort files by size and get the largest (likely the main video file)
                largest_file = max(torrent.files, key=lambda f: f.size)
                media_file_path = Path(torrent.content_path) / largest_file.name
            
            self.nfo_generator.create_nfo_file(torrent_data, output_dir, tmdb_data, media_file_path)
        
        # Create torrent file
        if self.config.output.create_torrent:
            self.torrent_manager.create_torrent_file(torrent_data, output_dir)
        
        # Save metadata JSON
        self.metadata_manager.save_metadata(torrent_data, output_dir, tmdb_data)
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove consecutive underscores
        filename = '_'.join(filter(None, filename.split('_')))
        
        return filename
