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
        r'(10bit|12bit|HDR10Plus|HDR10\+|HDR10|HDR2100|HDR|Dolby\W?Vision|DV\+|DV|HLG)'
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
        r'\W(\w{2,8})\W\(\w+\W*\)\.\w{3}$',  # Team name before year, limit to 2-8 chars
        r'\W(\w{2,8})\W\(\w+\W*\)$',  # Team name before year, no extension
        r'\W(\w{2,8})\.\w{3}$',  # Team name at end, limit to 2-8 chars
        r'\W(\w{2,8})$',  # Team name at end, no extension
        r'\((\w{2,8})\)\.\w{3}$',  # Team name in parentheses
        r'\[(\w{2,8})\]$',  # Team name in brackets
        r'(Tsundere-Raws) \(CR\)',  # Specific known team
        r'(Tsundere-Raws)',  # Specific known team
    ]

    PLATFORM_PATTERNS = [
        r'\W(HMAX|Netflix|NF|Amazon|Disney\+|Apple TV\+|Apple TV|YouTube|Orange|Vimeo|Crunchyroll|Funimation|HBO Max|Disney Plus|Hulu Plus|HBO GO|HBO|Hulu|Disney)\W'
    ]

    SPECIAL_VERSION_PATTERNS = [
        r'\W(Extended|Extended Version|Extended Edition|Directors Cut|Final|Proper|Internal|Fansub|Hybrid|DC|Director\'s Cut|Custom|Unrated|Unrated Version|\w{3,5}logie|Complet|Repack|Reapck|Remux|Integrale|Collection|Saga)'
    ]

    TRASH_PATTERNS = [
        r'\WREADNFO\W',
        r'\WSUBFORCED\W'
    ]
    
    # Language patterns - organized by language for better control
    LANGUAGE_PATTERNS = {
        "French": [
            r'\Wtruefrench\W',
            r'\Wfrench\W',
            r'\Wvff\W',
            r'\Wvfi\W',
            r'\Wvfq\W',
            r'\Wvf2\W',
            r'\Wvf\W',
            r'\Wvof\W',
            r'\Wvo\W',
            r'\Wvostfr\W',
            r'\Wfr\W'
        ],
        "English": [
            r'\Wen\W',
            r'\Weng\W',
        ],
        "Spanish": [
            r'\Wes\W',
        ],
        "German": [
            r'\Wde\W',
            r'\Wgerman\W',
            r'\Wdeu\W',
            r'\Wger\W',
        ],
        "Italian": [
            r'\Wit\W',
            r'\Wita\W',
        ],
        "Portuguese": [
            r'\Wpt\W',
        ],
        "Russian": [
            r'\Wru\W',
        ],
        "Japanese": [
            r'\Wja\W',
        ],
        "Chinese": [
            r'\Wzh\W',
        ],
        "Korean": [
            r'\Wko\W',
        ],
    }

    LANGUAGES = {
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
        
        # Extract year (before cleaning so we don't lose it)
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
        # Pattern for episodes
        episode_patterns = [
            r'[Ss](\d{1,2})[Ee](\d{1,2})',
            r'[Ss](\d{1,2})[Ee](\d{1,2})',
            r'(\d{1,2})x(\d{1,2})',
            r'S(\d{1,2})-(\d{1,2})',
        ]
        for pattern in episode_patterns:
            match = re.search(pattern, filename)
            if match:
                return int(match.group(1)), int(match.group(2))

        episode_range_pattern = r'\b(\d{1,3})-(\d{1,3})\b'
        match = re.search(episode_range_pattern, filename)
        if match:
            return 1, int(match.group(2))

        # Pattern for full season
        full_season_patterns = [
            r'[Ss]aison\s*(\d{1,2})',
            r'[Ss]eason\s*(\d{1,2})',
            r'[Ss](\d{1,2})'
        ]
        for pattern in full_season_patterns:
            match = re.search(pattern, filename)
            if match:
                return int(match.group(1)), None
        
        return None, None
    
    def _extract_languages(self, filename: str) -> Tuple[List[str], bool]:
        """Extract languages from filename"""
        languages = []
        
        # Check language patterns
        for language_name, patterns in self.LANGUAGE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, filename, flags=re.IGNORECASE):
                    if language_name not in languages:
                        languages.append(language_name)
        
        # Check legacy patterns for other languages
        for pattern, lang in self.LANGUAGES.items():
            if pattern == r'\Wmulti\W':
                continue  # Skip multi, handled separately
            if re.search(pattern, filename, flags=re.IGNORECASE):
                if lang not in languages:
                    languages.append(lang)
        
        # Check for multi-language
        is_multi = bool(re.search(r'\W(multi|mult[i|í])\W', filename, flags=re.IGNORECASE))
        
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

        # Handle no extension case
        if len(title) + 4 < len(filename):
            title = filename

        # Remove year brackets
        if media_info.year:
            title = re.sub(r'\(\d{4}\)', str(media_info.year), title)

        # Remove patterns
        patterns_to_remove = [
            r'\[.*?\]',  # Remove brackets
            r'\(.*?\)',  # Remove parentheses
            r'\{.*?\}',  # Remove braces
        ]

        for pattern in patterns_to_remove:
            title = re.sub(pattern, '', title)

        #Split title on year
        if media_info.year:
            title = title.split(str(media_info.year))[0]

        # Remove common patterns that were working - but only for detected languages
        common_patterns = [
            r'\b(multi|mult[i|í])\b',
            r'\b(1080p|720p|2160p|4klight|4k|480p|uhd|hdlight|fhd|mhd|hd)\b',
            r'\b(web|webrip|web-dl|bdrip|bluray)\b',
            r'\b(x264|x265|h264|h265|hevc)\b',
            r'\b(aac|ac3|ddp|dts|mp3|flac)\b',
            r'\b(5\.1|7\.1|2\.0|atmos|truehd)\b',
            r'\b(hdr10|hdr|dv|dolby\s*vision)\b',
            r'\b(10bit)\b',
        ]
        
        for pattern in common_patterns:
            match = re.search(pattern, title, flags=re.IGNORECASE)
            if match:
                title = title[:match.start()]

        # Remove all defined patterns - but only remove language patterns if detected
        all_patterns = self.AUDIO_CODEC_PATTERNS + self.FILE_SOURCE_PATTERNS + self.HDR_PATTERNS + self.PLATFORM_PATTERNS + self.SPECIAL_VERSION_PATTERNS + self.TEAM_PATTERNS + self.TRASH_PATTERNS
        
        # Add language patterns only if languages are detected
        detected_languages_lower = [lang.lower() for lang in media_info.languages]
        for language_name, patterns in self.LANGUAGE_PATTERNS.items():
            if language_name.lower() in detected_languages_lower:
                all_patterns.extend(patterns)
        
        # Add legacy language patterns if detected
        for pattern, lang in self.LANGUAGES.items():
            if pattern == r'\Wmulti\W':
                continue  # Skip multi, handled separately
            if lang.lower() in detected_languages_lower:
                all_patterns.append(pattern)

        for pattern in all_patterns:
            match = re.search(pattern, title, flags=re.IGNORECASE)
            if match:
                title = title[:match.start()]
        
        # For TV shows, remove season/episode
        tvshow_patterns = [
            r'\bS\d{1,2}E\d{1,2}\b',
            r'\bS\d{1,2}\b',
            r'\bE\d{1,2}\b',
            r'\bE\d{1,2}-\d{1,2}\b', # Handle double episodes
            r'\bS\d{1,3}-\d{1,3}\b', # Handle ranges like S1-2
            r'\b\d{1,3}-\d{1,3}\b', # Handle ranges like 71-78
            r'[Ss]aison\s*\d{1,2}'
        ]
        if media_info.type in ["tvshow", "anime"]:
            for pattern in tvshow_patterns:
                title = re.sub(pattern, '', title, flags=re.IGNORECASE)

        # Remove separators and clean up
        title = re.sub(r'[._\-\+]', ' ', title)
        title = re.sub(r'\s+', ' ', title)

        clean_title = title.strip().title()
        
        return clean_title
    
    def _extract_subtitles(self, filename: str) -> List[str]:
        """Extract subtitle languages from filename"""
        subtitles = []
        
        for sub_pattern, lang in self.SUBTITLE_LANGUAGES.items():
            if sub_pattern.lower() in filename:
                subtitles.append(lang)
        
        return subtitles
