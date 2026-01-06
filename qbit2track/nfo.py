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
        nfo_lines = []
        
        # Header
        nfo_lines.append(f"{'='*60}")
        nfo_lines.append(f"  {torrent_data.media_info.title}")
        nfo_lines.append(f"{'='*60}")
        nfo_lines.append("")
        
        # Basic metadata
        nfo_lines.append("BASIC INFORMATION")
        nfo_lines.append("-" * 20)
        nfo_lines.append(f"Title: {torrent_data.media_info.title}")
        if torrent_data.media_info.year:
            nfo_lines.append(f"Year: {torrent_data.media_info.year}")
        nfo_lines.append(f"Type: {torrent_data.media_info.type}")
        nfo_lines.append(f"Resolution: {torrent_data.media_info.resolution or 'Unknown'}")
        nfo_lines.append(f"Video Codec: {torrent_data.media_info.video_codec or 'Unknown'}")
        nfo_lines.append(f"Audio Codec: {torrent_data.media_info.audio_codec or 'Unknown'}")
        nfo_lines.append(f"Languages: {', '.join(torrent_data.media_info.languages) or 'Unknown'}")
        nfo_lines.append(f"Category: {torrent_data.category}")
        nfo_lines.append(f"Tags: {', '.join(torrent_data.tags)}")
        nfo_lines.append(f"Hash: {torrent_data.hash}")
        nfo_lines.append("")
        
        # TMDB information
        if tmdb_data:
            nfo_lines.append("TMDB INFORMATION")
            nfo_lines.append("-" * 20)
            nfo_lines.append(f"TMDB ID: {tmdb_data.get('tmdb_id', 'Unknown')}")
            if tmdb_data.get('imdb_id'):
                nfo_lines.append(f"IMDB ID: {tmdb_data['imdb_id']}")
            if tmdb_data.get('overview'):
                nfo_lines.append(f"Overview: {tmdb_data['overview']}")
            if tmdb_data.get('genres'):
                nfo_lines.append(f"Genres: {', '.join(tmdb_data['genres'])}")
            if tmdb_data.get('runtime'):
                nfo_lines.append(f"Runtime: {tmdb_data['runtime']} minutes")
            if tmdb_data.get('vote_average'):
                nfo_lines.append(f"Rating: {tmdb_data['vote_average']}/10")
            nfo_lines.append("")
        
        # Detailed technical information using pymediainfo
        nfo_lines.append("TECHNICAL INFORMATION")
        nfo_lines.append("-" * 25)
        
        # Add detailed pymediainfo analysis if available
        if media_file_path and media_file_path.exists() and self.pymediainfo_available:
            try:
                media_info = MediaInfo.parse(str(media_file_path))
                nfo_lines.extend(self._generate_technical_details_text(media_info))
            except Exception as e:
                logger.warning(f"Failed to parse media file with pymediainfo: {e}")
                nfo_lines.append("pymediainfo analysis failed")
        elif not self.pymediainfo_available:
            nfo_lines.append("pymediainfo not available")
        elif not media_file_path:
            nfo_lines.append("No media file path provided")
        
        return "\n".join(nfo_lines)
    
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
    
    def _generate_technical_details_text(self, media_info) -> list:
        """Generate detailed technical information from pymediainfo as text"""
        lines = []
        
        try:
            # General information
            general = media_info.general_tracks[0] if media_info.general_tracks else None
            if general:
                lines.append(f"Container: {general.format or 'Unknown'}")
                if general.file_size:
                    lines.append(f"File Size: {general.file_size}")
                if general.duration:
                    # Convert duration from ms to readable format
                    duration_ms = int(general.duration)
                    hours = duration_ms // 3600000
                    minutes = (duration_ms % 3600000) // 60000
                    seconds = (duration_ms % 60000) // 1000
                    if hours > 0:
                        lines.append(f"Duration: {hours:02d}:{minutes:02d}:{seconds:02d}")
                    else:
                        lines.append(f"Duration: {minutes:02d}:{seconds:02d}")
                if general.overall_bit_rate:
                    lines.append(f"Overall Bitrate: {general.overall_bit_rate}")
                if general.frame_count:
                    lines.append(f"Frame Count: {general.frame_count}")
            lines.append("")
            
            # Video tracks
            for i, video in enumerate(media_info.video_tracks):
                lines.append(f"Video Track {i+1}:")
                lines.append(f"  Codec: {video.codec or 'Unknown'}")
                lines.append(f"  Format: {video.format or 'Unknown'}")
                if video.width and video.height:
                    lines.append(f"  Resolution: {video.width}x{video.height}")
                if video.frame_rate:
                    lines.append(f"  Frame Rate: {video.frame_rate}")
                if video.bit_rate:
                    lines.append(f"  Bitrate: {video.bit_rate}")
                if video.bit_depth:
                    lines.append(f"  Bit Depth: {video.bit_depth}")
                if video.scan_type:
                    lines.append(f"  Scan Type: {video.scan_type}")
                if video.color_space:
                    lines.append(f"  Color Space: {video.color_space}")
                if video.chroma_subsampling:
                    lines.append(f"  Chroma Subsampling: {video.chroma_subsampling}")
                lines.append("")
            
            # Audio tracks
            for i, audio in enumerate(media_info.audio_tracks):
                lines.append(f"Audio Track {i+1}:")
                lines.append(f"  Codec: {audio.codec or 'Unknown'}")
                lines.append(f"  Format: {audio.format or 'Unknown'}")
                if audio.channel_s:
                    lines.append(f"  Channels: {audio.channel_s}")
                if audio.channel_positions:
                    lines.append(f"  Channel Layout: {audio.channel_positions}")
                if audio.sampling_rate:
                    lines.append(f"  Sampling Rate: {audio.sampling_rate}")
                if audio.bit_depth:
                    lines.append(f"  Bit Depth: {audio.bit_depth}")
                if audio.bit_rate:
                    lines.append(f"  Bitrate: {audio.bit_rate}")
                if audio.language:
                    lines.append(f"  Language: {audio.language}")
                if audio.title:
                    lines.append(f"  Title: {audio.title}")
                lines.append("")
            
            # Text tracks (subtitles)
            for i, text in enumerate(media_info.text_tracks):
                lines.append(f"Subtitle Track {i+1}:")
                lines.append(f"  Codec: {text.codec or 'Unknown'}")
                lines.append(f"  Format: {text.format or 'Unknown'}")
                if text.language:
                    lines.append(f"  Language: {text.language}")
                if text.title:
                    lines.append(f"  Title: {text.title}")
                lines.append("")
        
        except Exception as e:
            logger.warning(f"Error generating technical details: {e}")
            lines.append(f"Error generating technical details: {e}")
        
        return lines
