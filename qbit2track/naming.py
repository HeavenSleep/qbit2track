"""
Tracker naming system for qbit2track
"""
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from pymediainfo import MediaInfo as PyMediaInfo

logger = logging.getLogger(__name__)

# Import pymediainfo if available
try:
    from pymediainfo import MediaInfo
    PYMEDIAINFO_AVAILABLE = True
except ImportError:
    PYMEDIAINFO_AVAILABLE = False
    MediaInfo = None


class PlatformMapper:
    """Maps platform names to shortened codes"""
    
    PLATFORM_MAPPING = {
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
    
    @classmethod
    def get_platform_code(cls, platform_name: str) -> str:
        """Convert platform name to shortened code"""
        # Try exact match first
        if platform_name in cls.PLATFORM_MAPPING:
            return cls.PLATFORM_MAPPING[platform_name]
        
        # Try partial match
        for full_name, code in cls.PLATFORM_MAPPING.items():
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


class MediaAnalyzer:
    """Enhanced media analysis with pymediainfo"""
    
    @staticmethod
    def normalize_resolution(width: int, height: int) -> str:
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
    
    @staticmethod
    def normalize_video_codec(codec: str) -> str:
        """Normalize video codec names"""
        codec = codec.upper()
        if codec in ['AVC', 'H264']:
            return 'x264'
        elif codec in ['HEVC', 'H265']:
            return 'x265'
        elif codec == 'VP9':
            return 'VP9'
        elif codec == 'AV1':
            return 'AV1'
        else:
            return codec.lower()
    
    @staticmethod
    def normalize_audio_codec(codec: str) -> str:
        """Normalize audio codec names"""
        codec = codec.upper()
        if codec in ['AAC']:
            return 'AAC'
        elif codec in ['AC-3', 'AC3', 'DOLBY DIGITAL']:
            return 'AC3'
        elif codec in ['E-AC-3', 'EAC3', 'DD+']:
            return 'EAC3'
        elif codec in ['DTS']:
            return 'DTS'
        elif codec in ['FLAC']:
            return 'FLAC'
        elif codec in ['MP3']:
            return 'MP3'
        elif codec in ['OPUS']:
            return 'OPUS'
        elif codec in ['TRUEHD']:
            return 'TrueHD'
        else:
            return codec.lower()
    
    @staticmethod
    def enhance_with_pymediainfo(media_info, torrent_files, content_path: str) -> None:
        """Enhance media info with pymediainfo technical details"""
        if not PYMEDIAINFO_AVAILABLE:
            logger.warning("pymediainfo not available, skipping technical analysis")
            return
        
        try:
            # Find largest media file
            largest_file = None
            if torrent_files:
                largest_file = max(torrent_files, key=lambda f: f.get('size', 0))
            
            if not largest_file:
                logger.warning("No files found for pymediainfo analysis")
                return
            
            file_path = Path(content_path) / largest_file.get('name', '')
            if not file_path.exists():
                logger.warning(f"Media file not found: {file_path}")
                return
            
            logger.debug(f"Analyzing media file with pymediainfo: {file_path}")
            media_data = MediaInfo.parse(str(file_path))
            
            # Extract video codec information
            if media_data.video_tracks:
                video_track = media_data.video_tracks[0]  # Use first video track
                if video_track.format and not media_info.video_codec:
                    media_info.video_codec = MediaAnalyzer.normalize_video_codec(video_track.format)
                
                # Extract and normalize resolution
                if video_track.width and video_track.height and not media_info.resolution:
                    width, height = video_track.width, video_track.height
                    media_info.resolution = MediaAnalyzer.normalize_resolution(width, height)
                
                logger.debug(f"Video: {media_info.video_codec}, Resolution: {media_info.resolution}")
            
            # Extract audio codec information
            if media_data.audio_tracks and not media_info.audio_codec:
                audio_track = media_data.audio_tracks[0]  # Use first audio track
                if audio_track.format:
                    media_info.audio_codec = MediaAnalyzer.normalize_audio_codec(audio_track.format)
                
                logger.debug(f"Audio: {media_info.audio_codec}")
            
        except Exception as e:
            logger.error(f"Failed to analyze media with pymediainfo: {e}")
    
    @staticmethod
    def enhance_source_with_tmdb(media_info, tmdb_data) -> None:
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
                        platform_code = PlatformMapper.get_platform_code(primary_network)
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
                        platform_code = PlatformMapper.get_platform_code(company_name)
                        if platform_code:
                            media_info.source = f"{media_info.source}.{platform_code}"
                            logger.debug(f"Enhanced source with production company: {media_info.source}")
                            break


class NamingContext:
    """Creates naming context for tracker templates"""
    
    def __init__(self, config):
        self.config = config
        self.default_team = config.app.default_team
    
    def create_context(self, media_info, torrent_data, tmdb_data=None) -> Dict[str, Any]:
        """Create enhanced context for tracker naming templates"""
        return {
            # Basic media info
            'title': media_info.title,
            'year': media_info.year,
            'type': media_info.type,
            'season': media_info.season,
            'episode': media_info.episode,
            
            # Technical details
            'resolution': media_info.resolution,
            'video_codec': media_info.video_codec,
            'audio_codec': media_info.audio_codec,
            'languages': media_info.languages,
            'subtitle_languages': media_info.subtitles,
            'hdr': media_info.hdr,
            'source': media_info.source,
            
            # Team and multi-language
            'team': media_info.team or self.default_team,
            'is_multi': len(media_info.languages) > 1 or getattr(media_info, 'is_multi_language', False),
            
            # TMDB information
            'tmdb_info': tmdb_data if tmdb_data else {},
            
            # Torrent data
            'size': torrent_data.get('size', 0),
            'tags': torrent_data.get('tags', []),
            'files': torrent_data.get('files', []),
            'hash': torrent_data.get('hash', ''),
            'category': torrent_data.get('category', ''),
            
            # File information
            'file_extension': self._get_file_extension(torrent_data.get('files', [])),
        }
    
    def _get_file_extension(self, files: List[Dict]) -> Optional[str]:
        """Get file extension from torrent files"""
        if not files:
            return None
        
        # Get first video file extension
        for file_info in files:
            name = file_info.get('name', '')
            if name.lower().endswith(('.mkv', '.mp4', '.avi', '.mov', '.wmv')):
                return Path(name).suffix.lower().lstrip('.')
        
        return None
