"""
File-based media analysis using ffmpeg
"""
import logging
from pathlib import Path
from typing import Dict, Any, Set

try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False

logger = logging.getLogger(__name__)


class FileAnalyzer:
    """Extract media information directly from files using ffmpeg"""
    
    def __init__(self):
        self.available = FFMPEG_AVAILABLE
    
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a media file and extract technical information"""
        if not self.available:
            return {}
        
        try:
            probe = ffmpeg.probe(str(file_path))
            return self._extract_streams_info(probe)
        except Exception as e:
            logger.debug(f"Failed to analyze {file_path}: {e}")
            return {}
    
    def _extract_streams_info(self, probe: Dict) -> Dict[str, Any]:
        """Extract information from ffmpeg probe data"""
        info = {
            'video_codec': None,
            'audio_codec': None,
            'languages': set(),
            'subtitles': set(),
            'resolution': None,
            'duration': None,
            'bitrate': None
        }
        
        # Extract format info
        format_info = probe.get('format', {})
        info['duration'] = float(format_info.get('duration', 0))
        info['bitrate'] = int(format_info.get('bit_rate', 0))
        
        # Extract stream info
        streams = probe.get('streams', [])
        for stream in streams:
            codec_type = stream.get('codec_type')
            
            if codec_type == 'video':
                info['video_codec'] = self._clean_codec_name(stream.get('codec_name', ''))
                # Extract resolution
                width = stream.get('width')
                height = stream.get('height')
                if width and height:
                    info['resolution'] = f"{height}p"
            
            elif codec_type == 'audio':
                info['audio_codec'] = self._clean_codec_name(stream.get('codec_name', ''))
                # Extract language
                lang = stream.get('tags', {}).get('language')
                if lang:
                    info['languages'].add(lang.lower())
            
            elif codec_type == 'subtitle':
                # Extract subtitle language
                lang = stream.get('tags', {}).get('language')
                if lang:
                    info['subtitles'].add(lang.lower())
        
        return info
    
    def _clean_codec_name(self, codec_name: str) -> str:
        """Clean and normalize codec names"""
        codec_mapping = {
            'h264': 'H264',
            'hevc': 'x265',
            'h265': 'x265',
            'avc': 'H264',
            'aac': 'AAC',
            'ac3': 'AC3',
            'eac3': 'DDP',
            'dts': 'DTS',
            'truehd': 'TrueHD',
            'flac': 'FLAC',
            'opus': 'Opus',
            'vorbis': 'Vorbis',
            'mp3': 'MP3'
        }
        
        codec_lower = codec_name.lower()
        return codec_mapping.get(codec_lower, codec_name.upper())
    
    def analyze_directory(self, directory_path: Path) -> Dict[str, Any]:
        """Analyze all media files in a directory and return combined info"""
        if not self.available or not directory_path.exists():
            return {}
        
        combined_info = {
            'video_codec': None,
            'audio_codec': None,
            'languages': set(),
            'subtitles': set(),
            'resolution': None,
            'duration': 0,
            'bitrate': 0
        }
        
        file_count = 0
        
        for file_path in directory_path.rglob('*'):
            if file_path.is_file() and self._is_media_file(file_path):
                file_info = self.analyze_file(file_path)
                if file_info:
                    self._merge_info(combined_info, file_info)
                    file_count += 1
        
        # Convert sets to lists for JSON serialization
        combined_info['languages'] = list(combined_info['languages'])
        combined_info['subtitles'] = list(combined_info['subtitles'])
        
        # Calculate averages if multiple files
        if file_count > 1:
            combined_info['duration'] = combined_info['duration'] / file_count
            combined_info['bitrate'] = combined_info['bitrate'] // file_count
        
        return combined_info if file_count > 0 else {}
    
    def _is_media_file(self, file_path: Path) -> bool:
        """Check if file is a media file based on extension"""
        media_extensions = {
            '.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
            '.m4v', '.mpg', '.mpeg', '.ts', '.m2ts', '.mts'
        }
        return file_path.suffix.lower() in media_extensions
    
    def _merge_info(self, combined: Dict, file_info: Dict):
        """Merge file info into combined info"""
        # Use first non-None value for codecs and resolution
        if not combined['video_codec'] and file_info.get('video_codec'):
            combined['video_codec'] = file_info['video_codec']
        
        if not combined['audio_codec'] and file_info.get('audio_codec'):
            combined['audio_codec'] = file_info['audio_codec']
        
        if not combined['resolution'] and file_info.get('resolution'):
            combined['resolution'] = file_info['resolution']
        
        # Merge sets
        combined['languages'].update(file_info.get('languages', []))
        combined['subtitles'].update(file_info.get('subtitles', []))
        
        # Sum duration and bitrate for averaging
        combined['duration'] += file_info.get('duration', 0)
        combined['bitrate'] += file_info.get('bitrate', 0)
