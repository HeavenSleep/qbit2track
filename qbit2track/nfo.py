"""
NFO file generation for media files
"""
import logging
from pathlib import Path
from typing import Dict, Optional

from .models import TorrentData


logger = logging.getLogger(__name__)


class NFOGenerator:
    """Generate NFO files for media"""
    
    def __init__(self):
        pass
    
    def create_nfo_file(self, torrent_data: TorrentData, output_dir: Path, tmdb_data: Optional[Dict]):
        """Create NFO file content and save to file"""
        nfo_content = self.generate_nfo_content(torrent_data, tmdb_data)
        
        nfo_file = output_dir / f"{self._sanitize_filename(torrent_data.name)}.nfo"
        with open(nfo_file, 'w', encoding='utf-8') as f:
            f.write(nfo_content)
        
        logger.debug(f"Created NFO file: {nfo_file}")
    
    def generate_nfo_content(self, torrent_data: TorrentData, tmdb_data: Optional[Dict]) -> str:
        """Generate NFO file content"""
        nfo = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
        
        if torrent_data.media_info.type == "movie":
            nfo += self._generate_movie_nfo(torrent_data, tmdb_data)
        elif torrent_data.media_info.type in ["tvshow", "anime"]:
            nfo += self._generate_episode_nfo(torrent_data, tmdb_data)
        
        # Add technical info as comments
        nfo += "\n<!-- Technical Information -->\n"
        nfo += f"<!-- Resolution: {torrent_data.media_info.resolution or 'Unknown'} -->\n"
        nfo += f"<!-- Video Codec: {torrent_data.media_info.video_codec or 'Unknown'} -->\n"
        nfo += f"<!-- Audio Codec: {torrent_data.media_info.audio_codec or 'Unknown'} -->\n"
        nfo += f"<!-- Languages: {', '.join(torrent_data.media_info.languages) or 'Unknown'} -->\n"
        nfo += f"<!-- Original Hash: {torrent_data.hash} -->\n"
        nfo += f"<!-- Category: {torrent_data.category} -->\n"
        nfo += f"<!-- Tags: {', '.join(torrent_data.tags)} -->\n"
        
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
