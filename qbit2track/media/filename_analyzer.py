"""
Filename-based media information extraction
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..config import Config
from ..models import MediaInfo


class FilenameAnalyzer:
    """Analyze filenames and paths to extract media information"""
    
    # Common patterns
    RESOLUTION_PATTERNS = [
        r'(2160p|4KLight|4K\WSDR|4K|SDR)', 
        r'(1080p|FHD|FullHD|HDLight|mHD|miniHD)', 
        r'(720p|HD)', 
        r'(480p|SD)', 
        r'(360p|VGA|VCD|PAL|NTSC)'
    ]

    HDR_PATTERNS = [
        r'(10bit|12bit|HDR10Plus|HDR10\+|HDR10|HDR2100|HDR|Dolby Vision|DV\+|DV|HLG)'
    ]
    
    VIDEO_CODEC_PATTERNS = [
        r'(x264|x265|H264|H265|HEVC|AVC|VC-1|VP9|AV1)'
    ]

    AUDIO_CODEC_PATTERNS = [
        r'(AAC\W?\d\.\d|AAC|AC3\W?\d\.\d|AC3|DTS\W?\d\.\d|DTS\W?\d\.\d|DTS-HDMA\W?\d\.\d|DTS-HD\W?\d\.\d|DTS|DTS-HDMA|DTS-HD|FLAC|MP3|Opus|DDP\W?\d\.\d|DDP|DPP\W?\d\.\d|DPP|E-AC3|DD+|Atmos\W?\d\.\d|Atmos|TrueHD|8CH|6CH)'
    ]

    FILE_SOURCE_PATTERNS = [
        r'(webdl|web-dl|webrip|dvdrip|bdrip|bd|dvd5|dvd9|bluray5|bluray9|bluray|web.ad|web|dvd|XviD|brrip)'
    ]

    TEAM_PATTERNS = [
        r'\W(\w+)\.\w{3}$',
        r'\W(\w+)$',
        r'\((\w+)\)\.\w{3}$',
        r'\[(\w+)\]$',
        r'(Tsundere-Raws) \(CR\)'
    ]

    PLATFORM_PATTERNS = [
        r'\W(HMAX|Netflix|Amazon|Disney\+|Apple TV\+|Apple TV|YouTube|Orange|Vimeo|Crunchyroll|Funimation|HBO Max|Disney Plus|Hulu Plus|HBO GO|HBO|Hulu|Disney)\W'
    ]

    SPECIAL_VERSION_PATTERNS = [
        r'\W(Extended|Extended Version|Extended Edition|Directors Cut|Final|Proper|Internal|Fansub|Hybrid|DC|Director\'s Cut|Custom|Unrated|Unrated Version|\w{3-5}logie|Complet)'
    ]

    TRASH_PATTERNS = [
        r'\WREADNFO\W',
        r'\WSUBFORCED\W'
    ]
    
    # Language codes - more specific patterns to avoid false positives
    LANGUAGES = {
        r'\Wen\W': 'English', 
        r'\Weng\W': 'English', 
        r'\Wes\W': 'Spanish', 
        r'\Wtruefrench\W': 'French', 
        r'\Wfrench\W': 'French', 
        r'\Wvff\W': 'French', 
        r'\Wvfi\W': 'French', 
        r'\Wvfq\W': 'French', 
        r'\Wvf\W': 'French', 
        r'\Wfr\W': 'French',
        r'\Wde\W': 'German',
        r'\Wgerman\W': 'German',
        r'\Wdeu\W': 'German',
        r'\Wger\W': 'German',
        r'\Wit\W': 'Italian',
        r'\Wita\W': 'Italian',
        r'\Wpt\W': 'Portuguese',
        r'\Wpor\W': 'Portuguese',
        r'\Wru\W': 'Russian',
        r'\Wrus\W': 'Russian',
        r'\Wja\W': 'Japanese',
        r'\Wjpn\W': 'Japanese',
        r'\Wzh\W': 'Chinese',
        r'\Wchi\W': 'Chinese',
        r'\Wko\W': 'Korean', 
        r'\War\W': 'Arabic', 
        r'\Whi\W': 'Hindi', 
        r'\Wno\W': 'Norwegian',
        r'\Wnor\W': 'Norwegian',
        r'\Wnorwegian\W': 'Norwegian',
        r'\Wvo\w{2-4}': 'Original', 
        r'\Wmulti\W': Config.from_env().app.multi_language
    }

    SUBTITLE_LANGUAGES = {
        'vostfr': 'French', 'subfr': 'French', 'subit': 'Italian', 'subes': 'Spanish', 
        'subpt': 'Portuguese', 'subru': 'Russian', 'subja': 'Japanese', 'subzh': 'Chinese', 
        'subko': 'Korean', 'subar': 'Arabic', 'subhi': 'Hindi'
    }
    
    def __init__(self, file_analyzer=None):
        self.file_analyzer = file_analyzer
    
    def analyze_filename(self, filename: str, category: str = "", file_path: Optional[Path] = None) -> MediaInfo:
        """Extract media information from filename and optionally from file analysis"""
        filename = filename.lower()
        
        media_info = MediaInfo(title=Path(filename).stem)
        
        # Determine type from category or filename patterns
        media_info.type = self._determine_type(filename, category)
        
        # Extract resolution
        for pattern in self.RESOLUTION_PATTERNS:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                media_info.resolution = match.group(1).upper().rstrip()
                break
        
        # Extract video codec
        for pattern in self.VIDEO_CODEC_PATTERNS:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                media_info.video_codec = match.group(1).upper().rstrip()
                break
        
        # Extract HDR information
        for pattern in self.HDR_PATTERNS:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                media_info.hdr = match.group(1).upper().rstrip()
                break
        
        # Extract Platform
        for pattern in self.PLATFORM_PATTERNS:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                media_info.platform = match.group(1).upper().rstrip()
                break
        
        # Extract Special version
        for pattern in self.SPECIAL_VERSION_PATTERNS:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                media_info.version = match.group(1).upper().rstrip()
                break
        
        if not media_info.version:
            media_info.version = "Original"
        
        # Extract audio codec
        for pattern in self.AUDIO_CODEC_PATTERNS:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                media_info.audio_codec = match.group(1).upper().rstrip()
                break
        
        # Extract file source
        for pattern in self.FILE_SOURCE_PATTERNS:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                media_info.source = match.group(1).upper().rstrip()
                break
        
        # Extract year
        year_match = re.search(r'\b(19|20)\d{2}\b', filename)
        if year_match:
            media_info.year = int(year_match.group())
        
        # Extract team
        for pattern in self.TEAM_PATTERNS:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                media_info.team = match.group(1).upper().rstrip()
                break
        
        # Extract season/episode for TV shows
        if media_info.type in ["tvshow", "anime"]:
            season, episode = self._extract_season_episode(filename)
            if season:
                media_info.season = season

                if episode:
                    media_info.episode = episode
                else:
                    media_info.full_season = True
        
        # Extract languages
        media_info.languages, media_info.is_multi_language = self._extract_languages(filename)
        
        # Extract subtitles
        media_info.subtitles = self._extract_subtitles(filename)
        
        # Extract title (clean version)
        media_info.title = self._clean_title(filename, media_info)
        
        # If file path is provided, analyze actual file content for more accurate info
        if file_path and self.file_analyzer and self.file_analyzer.available:
            self._enhance_with_file_analysis(media_info, file_path)
        
        return media_info
    
    def _enhance_with_file_analysis(self, media_info: MediaInfo, file_path: Path):
        """Enhance media info with actual file analysis"""
        try:
            if file_path.is_file():
                file_info = self.file_analyzer.analyze_file(file_path)
            elif file_path.is_dir():
                file_info = self.file_analyzer.analyze_directory(file_path)
            else:
                return
            
            # Override filename-based info with file-based info if available
            if file_info.get('video_codec'):
                media_info.video_codec = file_info['video_codec']
            
            if file_info.get('audio_codec'):
                media_info.audio_codec = file_info['audio_codec']
            
            if file_info.get('resolution'):
                media_info.resolution = file_info['resolution']
            
            # Merge languages (combine filename and file-detected languages)
            file_languages = set(file_info.get('languages', []))
            filename_languages = set(media_info.languages)
            media_info.languages = list(filename_languages.union(file_languages))
            
            # Merge subtitles
            file_subtitles = set(file_info.get('subtitles', []))
            filename_subtitles = set(media_info.subtitles)
            media_info.subtitles = list(filename_subtitles.union(file_subtitles))
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Failed to enhance with file analysis: {e}")
    
    def _determine_type(self, filename: str, category: str) -> str:
        """Determine media type from filename and category"""
        filename_lower = filename.lower()
        category_lower = category.lower()
        
        # Check category first
        if 'tv' in category_lower or 'series' in category_lower:
            return "tvshow"
        elif 'anime' in category_lower or 'manga' in category_lower:
            return "anime"
        elif 'movie' in category_lower or 'film' in category_lower:
            return "movie"
        
        # Check filename patterns
        if any(pattern in filename_lower for pattern in ['s0', 'season', 'episode']):
            return "tvshow"
        elif any(pattern in filename_lower for pattern in ['anime', 'manga']):
            return "anime"
        
        return "movie"
    
    def _extract_season_episode(self, filename: str) -> Tuple[Optional[int], Optional[int]]:
        """Extract season and episode numbers from filename"""
        # Pattern for S01E01 format
        match = re.search(r'[Ss](\d{1,2})[Ee](\d{1,2})', filename)
        if match:
            return int(match.group(1)), int(match.group(2))
        
        # Pattern for 1x01 format
        match = re.search(r'(\d{1,2})x(\d{1,2})', filename)
        if match:
            return int(match.group(1)), int(match.group(2))
        
        # Pattern for full season
        match = re.search(r'[Ss]eason\s*(\d{1,2})', filename)
        if match:
            return int(match.group(1)), None
        
        return None, None
    
    def _extract_languages(self, filename: str) -> Tuple[List[str], bool]:
        """Extract languages from filename"""
        languages = []
        is_multi = False
        
        # Check subtitle languages first
        for sub_pattern, lang in self.SUBTITLE_LANGUAGES.items():
            if sub_pattern.lower() in filename:
                languages.append(lang)
        
        # Check audio languages
        for pattern, lang in self.LANGUAGES.items():
            if re.search(pattern, filename, re.IGNORECASE):
                if lang not in languages:
                    languages.append(lang)
        
        # Check for multi-language
        if Config.from_env().app.multi_language.lower() in filename.lower():
            is_multi = True
        
        return languages, is_multi
    
    def _extract_subtitles(self, filename: str) -> List[str]:
        """Extract subtitle languages from filename"""
        subtitles = []
        
        for sub_pattern, lang in self.SUBTITLE_LANGUAGES.items():
            if sub_pattern.lower() in filename:
                subtitles.append(lang)
        
        return subtitles
    
    def _clean_title(self, filename: str, media_info: MediaInfo) -> str:
        """Clean title by removing technical information"""
        title = Path(filename).stem
        
        # Remove patterns
        patterns_to_remove = [
            r'\[.*?\]',  # Remove brackets
            r'\(.*?\)',  # Remove parentheses
            r'\{.*?\}',  # Remove braces
        ]
        
        for pattern in patterns_to_remove:
            title = re.sub(pattern, '', title)
        
        # Remove technical terms
        technical_terms = [
            media_info.resolution or '',
            media_info.video_codec or '',
            media_info.audio_codec or '',
            media_info.hdr or '',
            media_info.source or '',
            media_info.platform or '',
            media_info.version or '',
            media_info.team or '',
        ]
        
        for term in technical_terms:
            if term:
                title = title.replace(term.lower(), '')
        
        # Remove separators and clean up
        title = re.sub(r'[._\-\+]', ' ', title)
        title = re.sub(r'\s+', ' ', title)
        
        return title.strip().title()
