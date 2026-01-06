"""
NFO file generation for media files using pymediainfo
"""
import logging
from pathlib import Path
from typing import Dict, Optional

try:
    from pymediainfo import MediaInfo
    PYMEDIAINFO_AVAILABLE = True
except ImportError:
    MediaInfo = None
    PYMEDIAINFO_AVAILABLE = False

from .models import TorrentData


logger = logging.getLogger(__name__)


class NFOGenerator:
    """Generate NFO files for media using pymediainfo"""
    
    def __init__(self):
        self.pymediainfo_available = PYMEDIAINFO_AVAILABLE
        logger.info(f"pymediainfo available: {self.pymediainfo_available}")
    
    def create_nfo_file(self, torrent_data: TorrentData, output_dir: Path, tmdb_data: Optional[Dict], media_file_path: Optional[Path] = None):
        """Create NFO file content and save to file"""
        nfo_content = self.generate_nfo_content(torrent_data, tmdb_data, media_file_path)
        
        nfo_file = output_dir / f"{self._sanitize_filename(torrent_data.name)}.nfo"
        with open(nfo_file, 'w', encoding='utf-8') as f:
            f.write(nfo_content)
        
        logger.debug(f"Created NFO file: {nfo_file}")
    
    def generate_nfo_content(self, torrent_data: TorrentData, tmdb_data: Optional[Dict], media_file_path: Optional[Path] = None) -> str:
        """Generate NFO file content with pymediainfo technical details"""
        nfo = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
        
        if torrent_data.media_info.type == "movie":
            nfo += self._generate_movie_nfo(torrent_data, tmdb_data)
        elif torrent_data.media_info.type in ["tvshow", "anime"]:
            nfo += self._generate_episode_nfo(torrent_data, tmdb_data)
        
        # Add detailed technical information using pymediainfo
        nfo += "\n<!-- Technical Information -->\n"
        
        # Basic metadata from filename analysis
        nfo += f"<!-- Resolution: {torrent_data.media_info.resolution or 'Unknown'} -->\n"
        nfo += f"<!-- Video Codec: {torrent_data.media_info.video_codec or 'Unknown'} -->\n"
        nfo += f"<!-- Audio Codec: {torrent_data.media_info.audio_codec or 'Unknown'} -->\n"
        nfo += f"<!-- Languages: {', '.join(torrent_data.media_info.languages) or 'Unknown'} -->\n"
        nfo += f"<!-- Original Hash: {torrent_data.hash} -->\n"
        nfo += f"<!-- Category: {torrent_data.category} -->\n"
        nfo += f"<!-- Tags: {', '.join(torrent_data.tags)} -->\n"
        
        # Add detailed pymediainfo analysis if available
        if media_file_path and media_file_path.exists() and self.pymediainfo_available:
            try:
                media_info = MediaInfo.parse(str(media_file_path))
                nfo += self._generate_technical_details(media_info)
            except Exception as e:
                logger.warning(f"Failed to parse media file with pymediainfo: {e}")
                nfo += "<!-- pymediainfo analysis failed -->\n"
        elif not self.pymediainfo_available:
            nfo += "<!-- pymediainfo not available -->\n"
        elif not media_file_path:
            nfo += "<!-- No media file path provided -->\n"
        
        return nfo
    
    def _generate_movie_nfo(self, torrent_data: TorrentData, tmdb_data: Optional[Dict]) -> str:
        """Generate movie NFO content"""
        nfo = "<movie>\n"
        nfo += f"  <title>{torrent_data.media_info.title}</title>\n"
        
        if torrent_data.media_info.year:
            nfo += f"  <year>{torrent_data.media_info.year}</year>\n"
        
        if tmdb_data:
            nfo += f"  <plot>{tmdb_data.get('overview', '')}</plot>\n"
            nfo += f"  <tmdbid>{tmdb_data.get('tmdb_id', '')}</tmdbid>\n"
            
            if tmdb_data.get('imdb_id'):
                nfo += f"  <imdbid>{tmdb_data['imdb_id']}</imdbid>\n"
            
            for genre in tmdb_data.get('genres', []):
                nfo += f"  <genre>{genre}</genre>\n"
            
            if tmdb_data.get('runtime'):
                nfo += f"  <runtime>{tmdb_data['runtime']}</runtime>\n"
            
            if tmdb_data.get('vote_average'):
                nfo += f"  <rating>{tmdb_data['vote_average']}</rating>\n"
        
        nfo += "</movie>\n"
        return nfo
    
    def _generate_episode_nfo(self, torrent_data: TorrentData, tmdb_data: Optional[Dict]) -> str:
        """Generate TV episode NFO content"""
        nfo = "<episodedetails>\n"
        nfo += f"  <title>{torrent_data.media_info.title}</title>\n"
        
        if torrent_data.media_info.season:
            nfo += f"  <season>{torrent_data.media_info.season}</season>\n"
        
        if torrent_data.media_info.episode:
            nfo += f"  <episode>{torrent_data.media_info.episode}</episode>\n"
        
        if tmdb_data:
            nfo += f"  <plot>{tmdb_data.get('overview', '')}</plot>\n"
            nfo += f"  <tmdbid>{tmdb_data.get('tmdb_id', '')}</tmdbid>\n"
            
            for genre in tmdb_data.get('genres', []):
                nfo += f"  <genre>{genre}</genre>\n"
            
            if tmdb_data.get('episode_name'):
                nfo += f"  <episodetitle>{tmdb_data['episode_name']}</episodetitle>\n"
            
            if tmdb_data.get('vote_average'):
                nfo += f"  <rating>{tmdb_data['vote_average']}</rating>\n"
        
        nfo += "</episodedetails>\n"
        return nfo
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove consecutive underscores
        filename = '_'.join(filter(None, filename.split('_')))
        
        return filename
    
    def _generate_technical_details(self, media_info) -> str:
        """Generate detailed technical information from pymediainfo"""
        nfo = "\n<!-- pymediainfo Technical Details -->\n"
        
        try:
            # General information
            general = media_info.general_tracks[0] if media_info.general_tracks else None
            if general:
                nfo += f"<!-- Container: {general.format or 'Unknown'} -->\n"
                nfo += f"<!-- File Size: {general.file_size or 'Unknown'} -->\n"
                nfo += f"<!-- Duration: {general.duration or 'Unknown'} -->\n"
                nfo += f"<!-- Overall Bitrate: {general.overall_bit_rate or 'Unknown'} -->\n"
                if general.frame_count:
                    nfo += f"<!-- Frame Count: {general.frame_count} -->\n"
            
            # Video tracks
            for i, video in enumerate(media_info.video_tracks):
                nfo += f"\n<!-- Video Track {i+1} -->\n"
                nfo += f"<!-- Codec: {video.codec or 'Unknown'} -->\n"
                nfo += f"<!-- Format: {video.format or 'Unknown'} -->\n"
                nfo += f"<!-- Width: {video.width or 'Unknown'} -->\n"
                nfo += f"<!-- Height: {video.height or 'Unknown'} -->\n"
                nfo += f"<!-- Resolution: {video.width}x{video.height} -->\n" if video.width and video.height else f"<!-- Resolution: Unknown -->\n"
                nfo += f"<!-- Frame Rate: {video.frame_rate or 'Unknown'} -->\n"
                nfo += f"<!-- Bitrate: {video.bit_rate or 'Unknown'} -->\n"
                nfo += f"<!-- Bit Depth: {video.bit_depth or 'Unknown'} -->\n"
                if video.scan_type:
                    nfo += f"<!-- Scan Type: {video.scan_type} -->\n"
                if video.color_space:
                    nfo += f"<!-- Color Space: {video.color_space} -->\n"
                if video.chroma_subsampling:
                    nfo += f"<!-- Chroma Subsampling: {video.chroma_subsampling} -->\n"
            
            # Audio tracks
            for i, audio in enumerate(media_info.audio_tracks):
                nfo += f"\n<!-- Audio Track {i+1} -->\n"
                nfo += f"<!-- Codec: {audio.codec or 'Unknown'} -->\n"
                nfo += f"<!-- Format: {audio.format or 'Unknown'} -->\n"
                nfo += f"<!-- Channels: {audio.channel_s or 'Unknown'} -->\n"
                nfo += f"<!-- Channel Layout: {audio.channel_positions or 'Unknown'} -->\n"
                nfo += f"<!-- Sampling Rate: {audio.sampling_rate or 'Unknown'} -->\n"
                nfo += f"<!-- Bit Depth: {audio.bit_depth or 'Unknown'} -->\n"
                nfo += f"<!-- Bitrate: {audio.bit_rate or 'Unknown'} -->\n"
                if audio.language:
                    nfo += f"<!-- Language: {audio.language} -->\n"
                if audio.title:
                    nfo += f"<!-- Title: {audio.title} -->\n"
            
            # Text tracks (subtitles)
            for i, text in enumerate(media_info.text_tracks):
                nfo += f"\n<!-- Subtitle Track {i+1} -->\n"
                nfo += f"<!-- Codec: {text.codec or 'Unknown'} -->\n"
                nfo += f"<!-- Format: {text.format or 'Unknown'} -->\n"
                if text.language:
                    nfo += f"<!-- Language: {text.language} -->\n"
                if text.title:
                    nfo += f"<!-- Title: {text.title} -->\n"
            
            # Menu tracks (chapters, etc.)
            for i, menu in enumerate(media_info.menu_tracks):
                nfo += f"\n<!-- Menu Track {i+1} -->\n"
                nfo += f"<!-- Codec: {menu.codec or 'Unknown'} -->\n"
                if menu.duration:
                    nfo += f"<!-- Duration: {menu.duration} -->\n"
                if menu.language:
                    nfo += f"<!-- Language: {menu.language} -->\n"
        
        except Exception as e:
            logger.warning(f"Error generating technical details: {e}")
            nfo += f"<!-- Error generating technical details: {e} -->\n"
        
        return nfo
