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

# Import pymediainfo if available
try:
    from pymediainfo import MediaInfo
    PYMEDIAINFO_AVAILABLE = True
except ImportError:
    PYMEDIAINFO_AVAILABLE = False
    MediaInfo = None


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
        
        # Default team configuration
        self.default_team = config.app.default_team
    
    def _enhance_media_info_with_pymediainfo(self, media_info, torrent) -> None:
        """Enhance media info with pymediainfo technical details"""
        if not PYMEDIAINFO_AVAILABLE:
            logger.warning("pymediainfo not available, skipping technical analysis")
            return
        
        try:
            # Find the largest media file
            largest_file = None
            if torrent.files:
                largest_file = max(torrent.files, key=lambda f: f.size)
            
            if not largest_file:
                logger.warning("No files found for pymediainfo analysis")
                return
            
            file_path = Path(torrent.content_path) / largest_file.name
            if not file_path.exists():
                logger.warning(f"Media file not found: {file_path}")
                return
            
            logger.debug(f"Analyzing media file with pymediainfo: {file_path}")
            media_data = MediaInfo.parse(str(file_path))
            
            # Extract video codec information
            if media_data.video_tracks:
                video_track = media_data.video_tracks[0]  # Use first video track
                if video_track.format and not media_info.video_codec:
                    # Normalize codec names
                    codec = video_track.format.upper()
                    if codec in ['AVC', 'H264']:
                        media_info.video_codec = 'x264'
                    elif codec in ['HEVC', 'H265']:
                        media_info.video_codec = 'x265'
                    elif codec == 'VP9':
                        media_info.video_codec = 'VP9'
                    elif codec == 'AV1':
                        media_info.video_codec = 'AV1'
                    else:
                        media_info.video_codec = codec.lower()
                
                # Extract and normalize resolution
                if video_track.width and video_track.height and not media_info.resolution:
                    width, height = video_track.width, video_track.height
                    media_info.resolution = self._normalize_resolution(width, height)
                
                logger.debug(f"Video: {media_info.video_codec}, Resolution: {media_info.resolution}")
            
            # Extract audio codec information
            if media_data.audio_tracks and not media_info.audio_codec:
                audio_track = media_data.audio_tracks[0]  # Use first audio track
                if audio_track.format:
                    # Normalize audio codec names
                    codec = audio_track.format.upper()
                    if codec in ['AAC']:
                        media_info.audio_codec = 'AAC'
                    elif codec in ['AC-3', 'AC3', 'DOLBY DIGITAL']:
                        media_info.audio_codec = 'AC3'
                    elif codec in ['E-AC-3', 'EAC3', 'DD+']:
                        media_info.audio_codec = 'EAC3'
                    elif codec in ['DTS']:
                        media_info.audio_codec = 'DTS'
                    elif codec in ['FLAC']:
                        media_info.audio_codec = 'FLAC'
                    elif codec in ['MP3']:
                        media_info.audio_codec = 'MP3'
                    elif codec in ['OPUS']:
                        media_info.audio_codec = 'OPUS'
                    elif codec in ['TRUEHD']:
                        media_info.audio_codec = 'TrueHD'
                    else:
                        media_info.audio_codec = codec.lower()
                
                logger.debug(f"Audio: {media_info.audio_codec}")
            
        except Exception as e:
            logger.error(f"Failed to analyze media with pymediainfo: {e}")
    
    def _normalize_resolution(self, width: int, height: int) -> str:
        """Convert pixel resolution to standard format (e.g., 1920x1080 -> 1080p)"""
        if width >= 3840 or height >= 2160:
            return "2160p"  # 4K
        elif width >= 2560 or height >= 1440:
            return "1440p"  # 2K
        elif width >= 1920 or height >= 1080:
            return "1080p"  # Full HD
        elif width >= 1280 or height >= 720:
            return "720p"   # HD
        elif width >= 854 or height >= 480:
            return "480p"   # SD
        elif width >= 640 or height >= 360:
            return "360p"   # VGA
        else:
            return f"{height}p"  # Fallback to height
    
    def _enhance_source_with_tmdb(self, media_info, tmdb_data) -> None:
        """Enhance source information with TMDB platform/network data"""
        if not media_info.source or media_info.source.lower() in ['web', 'unknown']:
            # Default to WEB-DL if no source specified
            media_info.source = "WEB-DL"
        
        # Try to get platform/network information from TMDB
        if tmdb_data:
            # For TV shows, check network information
            if media_info.type in ['tvshow', 'anime'] and tmdb_data.get('networks'):
                networks = tmdb_data.get('networks', [])
                if networks:
                    primary_network = networks[0].get('name', '')
                    if primary_network:
                        # Get shortened platform code
                        platform_code = self._get_platform_code(primary_network)
                        if platform_code:
                            # Append platform code to source (e.g., "WEB-DL.NF")
                            media_info.source = f"{media_info.source}.{platform_code}"
                            logger.debug(f"Enhanced source with network: {media_info.source}")
            
            # For movies, check production companies
            elif media_info.type == 'movie' and tmdb_data.get('production_companies'):
                companies = tmdb_data.get('production_companies', [])
                # Look for major streaming platforms
                streaming_companies = ['Netflix', 'Amazon', 'Disney', 'HBO', 'Apple', 'Paramount', 'Peacock', 'Hulu']
                for company in companies:
                    company_name = company.get('name', '')
                    if any(stream in company_name for stream in streaming_companies):
                        # Get shortened platform code
                        platform_code = self._get_platform_code(company_name)
                        if platform_code:
                            media_info.source = f"{media_info.source}.{platform_code}"
                            logger.debug(f"Enhanced source with production company: {media_info.source}")
                            break
    
    def _get_platform_code(self, platform_name: str) -> str:
        """Convert platform name to shortened code"""
        platform_mapping = {
            # Streaming Services
            'Netflix': 'NF',
            'Amazon Prime Video': 'AMZ',
            'Amazon': 'AMZ',
            'Prime Video': 'AMZ',
            'Disney+': 'DSN',
            'Disney': 'DSN',
            'Disney Plus': 'DSN',
            'HBO Max': 'HBO',
            'HBO': 'HBO',
            'Apple TV+': 'APTV',
            'Apple TV': 'APTV',
            'Apple': 'APTV',
            'Paramount+': 'PAR',
            'Paramount Plus': 'PAR',
            'Paramount': 'PAR',
            'Peacock': 'PCOK',
            'Hulu': 'HULU',
            'Star+': 'STAR',
            'Star Plus': 'STAR',
            
            # TV Networks
            'HBO': 'HBO',
            'Showtime': 'SHO',
            'CBS': 'CBS',
            'NBC': 'NBC',
            'ABC': 'ABC',
            'FOX': 'FOX',
            'BBC': 'BBC',
            'ITV': 'ITV',
            'Channel 4': 'C4',
            'Sky': 'SKY',
            'FX': 'FX',
            'AMC': 'AMC',
            'USA': 'USA',
            'TNT': 'TNT',
            'TBS': 'TBS',
            'Syfy': 'SYFY',
            'MTV': 'MTV',
            'Comedy Central': 'CC',
            'Cartoon Network': 'CN',
            'Adult Swim': 'AS',
            'Discovery': 'DSC',
            'National Geographic': 'NG',
            'History': 'HIST',
            'A&E': 'AE',
            'Lifetime': 'LIFE',
            
            # International
            'Crunchyroll': 'CR',
            'Funimation': 'FUNI',
            'VRV': 'VRV',
            'Tubi': 'TUBI',
            'Pluto TV': 'PLUTO',
            'Roku': 'ROKU',
            'Vudu': 'VUDU'
        }
        
        # Try exact match first
        if platform_name in platform_mapping:
            return platform_mapping[platform_name]
        
        # Try partial match
        for full_name, code in platform_mapping.items():
            if full_name.lower() in platform_name.lower() or platform_name.lower() in full_name.lower():
                return code
        
        # Fallback: create shortened version
        words = platform_name.split()
        if len(words) >= 2:
            # Take first letter of each word (max 3 chars)
            code = ''.join(word[0].upper() for word in words[:3])
            return code
        elif len(platform_name) >= 3:
            # Take first 3 characters
            return platform_name[:3].upper()
        else:
            # Return uppercase version
            return platform_name.upper()
    
    def _get_default_team(self) -> str:
        """Get default team from configuration or use default"""
        # Use configured default
        return self.default_team
    
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
        self._enhance_media_info_with_pymediainfo(media_info, torrent)
        
        # Enhance source information with TMDB data
        self._enhance_source_with_tmdb(media_info, tmdb_data)
        
        # Ensure team information is set
        if not media_info.team:
            media_info.team = self._get_default_team()
        
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
                    
                    # Prepare enhanced media info dict for template
                    media_info_dict = {
                        'title': media_info.title,
                        'year': media_info.year,
                        'type': media_info.type,
                        'resolution': media_info.resolution,
                        'video_codec': media_info.video_codec,
                        'audio_codec': media_info.audio_codec,
                        'languages': media_info.languages,
                        'hdr': media_info.hdr,
                        'source': media_info.source,
                        'team': media_info.team or self._get_default_team(),
                        'is_multi': len(media_info.languages) > 1,
                        'tmdb_info': tmdb_data if tmdb_data else {}
                    }
                    
                    # Prepare torrent data dict for template
                    torrent_data_dict = {
                        'name': torrent_data.name,
                        'size': torrent_data.size,
                        'tags': torrent_data.tags,
                        'files': torrent_data.files,
                        'hash': torrent_data.hash,
                        'category': torrent_data.category
                    }
                    
                    # Generate tracker-specific name
                    tracker_name = la_cale_uploader.generate_torrent_name(media_info_dict, torrent_data_dict)
                    
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
