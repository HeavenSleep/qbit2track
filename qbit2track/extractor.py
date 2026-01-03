"""
Main torrent extraction and processing logic
"""
import logging
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
    
    def extract_all(self, dry_run: bool = False,
                   update_tracker: Optional[str] = None,
                   update_comment: Optional[str] = None,
                   update_tags: Optional[str] = None,
                   update_category: Optional[str] = None) -> Dict[str, int]:
        """Extract all torrents from qBittorrent"""
        results = {'success': 0, 'failed': 0}
        
        try:
            torrents = self.client.torrents.info()
            logger.info(f"Found {len(torrents)} torrents to process")
            
            for torrent in torrents:
                try:
                    self._extract_single_torrent(
                        torrent, dry_run, update_tracker, update_comment, update_tags, update_category
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
                              update_category: Optional[str] = None):
        """Extract a single torrent"""
        # Analyze media information
        media_info = self.filename_analyzer.analyze_filename(
            torrent.name, torrent.category, Path(torrent.content_path)
        )
        
        # Match with TMDB
        tmdb_data = self.tmdb_matcher.match_media(media_info)
        
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
        
        if dry_run:
            logger.info(f"DRY RUN: Would extract {torrent.name}")
            return
        
        # Create output directory
        output_dir = Path(self.config.output.output_dir) / self._sanitize_filename(torrent.name)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create NFO file
        if self.config.output.create_nfo:
            self.nfo_generator.create_nfo_file(torrent_data, output_dir, tmdb_data)
        
        # Create torrent file
        if self.config.output.create_torrent:
            self.torrent_manager.create_torrent_file(torrent_data, output_dir)
        
        # Save metadata JSON
        self.metadata_manager.save_metadata(torrent_data, output_dir, tmdb_data)
        
        # Update torrent in qBittorrent if any updates were applied
        if any([update_tracker, update_comment, update_tags, update_category]):
            self._update_torrent_in_qbittorrent(torrent, torrent_data, update_tracker, update_comment, update_tags, update_category)
    
    def _update_torrent_in_qbittorrent(self, torrent, torrent_data: TorrentData,
                                       update_tracker: Optional[str],
                                       update_comment: Optional[str],
                                       update_tags: Optional[str],
                                       update_category: Optional[str]):
        """Update torrent metadata in qBittorrent"""
        try:
            # Update tracker
            if update_tracker:
                self.client.torrents.set_tracker(hashes=[torrent.hash], urls=[update_tracker])
            
            # Update comment
            if update_comment:
                self.client.torrents.set_comment(hashes=[torrent.hash], comment=update_comment)
            
            # Update tags
            if update_tags:
                self.client.torrents.change_tag(hashes=[torrent.hash], tags=', '.join(torrent_data.tags))
            
            # Update category
            if update_category:
                self.client.torrents.set_category(hashes=[torrent.hash], category=update_category)
            
            logger.info(f"Updated torrent metadata in qBittorrent: {torrent.name}")
            
        except Exception as e:
            logger.error(f"Failed to update torrent {torrent.name}: {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove consecutive underscores
        filename = '_'.join(filter(None, filename.split('_')))
        
        return filename
