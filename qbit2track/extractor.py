"""
Torrent extraction functionality for qbit2track
"""

import logging
import re
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import time
from datetime import datetime

import torf
from qbittorrentapi import Client
from tmdbv3api import TMDb, Movie, TV, Search

from .config import Config


logger = logging.getLogger(__name__)


@dataclass
class MediaInfo:
    """Extracted media information"""
    title: str
    year: Optional[int] = None
    type: str = "movie"  # movie, tvshow, anime
    source: Optional[str] = None
    version: Optional[str] = None
    team: Optional[str] = None
    resolution: Optional[str] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    hdr: Optional[str] = None
    languages: List[str] = None
    platform: Optional[str] = None
    is_multi_language: bool = False
    subtitles: List[str] = None
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    season: Optional[int] = None
    full_season: Optional[bool] = None
    episode: Optional[int] = None
    
    def __post_init__(self):
        if self.languages is None:
            self.languages = []
        if self.subtitles is None:
            self.subtitles = []
    
    @property
    def is_4k(self) -> bool:
        if self.resolution:
            return self.resolution.upper() in ["2160P", "4KLIGHT", "4KSDR", "4K"]
        else:
            return False

    @property
    def is_hdr(self) -> bool:
        if self.hdr:
            return self.hdr in ["HDR", "HDR10", "HDR10+", "DOLBY VISION", "DV", "DV+", "HLG", "HDR2100", "10BIT", "12BIT"]
        else:
            return False

    @property
    def full_resolution(self) -> Optional[str]:
        resolution = ""
        if self.is_4k:
            resolution = "4K"
        else:
            resolution = self.resolution

        if self.is_hdr:
            resolution += " HDR"

        return resolution


@dataclass
class TorrentData:
    """Complete torrent data for extraction"""
    hash: str
    name: str
    private: bool
    save_path: str
    content_path: str
    size: int
    files: List[Dict]
    tracker: List[str]
    tags: List[str]
    category: str
    media_info: MediaInfo
    comment: Optional[str] = None


class MediaAnalyzer:
    """Analyze filenames and paths to extract media information"""
    
    # Common patterns
    RESOLUTION_PATTERNS = [
        r'(2160p|4KLight|4K\WSDR|4K|SDR)', r'(1080p|FHD|FullHD|HDLight|mHD|miniHD)', r'(720p|HD)', r'(480p|SD)', r'(360p|VGA|VCD|PAL|NTSC)'
    ]

    HDR_PATTERNS = [
        r'(10bit|12bit|HDR10Plus|HDR10\+|HDR10|HDR2100|HDR|Dolby Vision|DV\+|DV|HLG)'
    ]
    
    VIDEO_CODEC_PATTERNS = [
        r'(x264|x265|H\.?264|H\.?265|HEVC|AV1|VP9|XViD|REMUX)'
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
        r'\Wvf2\W': 'French', 
        r'\Wvfr\W': 'French',
        r'\Wfr\W': 'French',
        r'\Wgerman\W': 'German',  # More specific for German
        r'\Wdeutsch\W': 'German',  # Alternative German
        r'\Wit\W': 'Italian', 
        r'\Wpt\W': 'Portuguese', 
        r'\Wru\W': 'Russian', 
        r'\Wja\W': 'Japanese',
        r'\Wzh\W': 'Chinese', 
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
        'vostfr': 'French', 'subfr': 'French', 'subit': 'Italian', 'subes': 'Spanish', 'subpt': 'Portuguese', 'subru': 'Russian', 'subja': 'Japanese', 'subzh': 'Chinese', 'subko': 'Korean', 'subar': 'Arabic', 'subhi': 'Hindi'
    }
    
    def analyze_filename(self, filename: str, category: str = "") -> MediaInfo:
        """Extract media information from filename"""
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
        
        return media_info
    
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
        
        return "movie"  # Default
    
    def _extract_season_episode(self, filename: str) -> Optional[Tuple[int, int]]:
        """Extract season and episode numbers"""
        patterns = [
            r'\Ws(\d+)e(\d+)\W',  # S01E01
            r'\W(\d+)x(\d+)\W',   # 1x01
            r'season\s*(\d+).*episode\s*(\d+)',  # Season 1 Episode 1
        ]

        full_season_pattern = [ 
            r'\Wseason\s*(\d+)\W', 
            r'\Ws(\d+)\W' 
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return int(match.group(1)), int(match.group(2))

        for pattern in full_season_pattern:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return int(match.group(1)), None
        
        return None, None
    
    def _extract_languages(self, filename: str) -> Tuple[List[str], bool]:
        """Extract languages from filename"""
        languages = []
        filename_lower = filename.lower()
        is_multi_language = False
        
        # Check for explicit language indicators first
        for pattern, name in self.LANGUAGES.items():
            match = re.search(pattern, filename_lower, re.IGNORECASE)
            if match:
                # Additional check for German to avoid false positives
                if name == 'German':
                    # Only match German if it's not part of a French title pattern
                    # Look for patterns like "de" at word boundaries, not in "Le monde de Nathan"
                    if re.search(r'\bde\b(?!\s+nathan|\s+monde|\s+la|\s+le|\s+les|\s+des)', filename_lower):
                        languages.append(name)
                else:
                    languages.append(name)

                if 'multi' in pattern.lower():
                    is_multi_language = True

        # Also check for full language names
        full_language_patterns = {
            'english': 'English',
            'spanish': 'Spanish', 
            'french': 'French',
            'german': 'German',
            'italian': 'Italian',
            'portuguese': 'Portuguese',
            'russian': 'Russian',
            'japanese': 'Japanese',
            'chinese': 'Chinese',
            'korean': 'Korean',
            'arabic': 'Arabic',
            'hindi': 'Hindi',
            'norwegian': 'Norwegian'
        }
        
        for lang_name, lang_full in full_language_patterns.items():
            if lang_name in filename_lower and lang_full not in languages:
                # Additional context check for German
                if lang_name == 'german':
                    # Avoid matching "german" in contexts that might be false positives
                    if re.search(r'\bgerman\b', filename_lower):
                        languages.append(lang_full)
                else:
                    languages.append(lang_full)

        # Remove duplicates
        languages = list(set(languages))

        if len(languages) > 1:
            is_multi_language = True

        return languages, is_multi_language

    def _extract_subtitles(self, filename: str) -> List[str]:
        """Extract subtitles from filename"""
        languages = []
        filename_lower = filename.lower()
        
        for code, name in self.SUBTITLE_LANGUAGES.items():
            if code.lower() in filename_lower or name.lower() in filename_lower:
                languages.append(name)
        
        return languages
    
    def _clean_title(self, filename: str, media_info: MediaInfo) -> str:
        """Clean title by removing technical information"""
        title = Path(filename).stem

        # Manage files without extension
        if len(title) + 4 < len(filename):
            title = filename

        # If title is too short, return it
        if len(title.split(' ')) < 3 and len(title.split('.')) < 3:
            return title

        # Remove HDR info
        for pattern in self.HDR_PATTERNS:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)

        # Remove Platform
        for pattern in self.PLATFORM_PATTERNS:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # Remove year
        if media_info.year:
            title = title.split(str(media_info.year))[0].rstrip()

        # Remove subtitles
        if media_info.subtitles:
            for pattern in self.SUBTITLE_LANGUAGES.keys():
                title = re.sub(rf'\b{pattern}', '', title, flags=re.IGNORECASE)

        # Remove multi language
        if media_info.is_multi_language:
            title = title.split('multi')[0].rstrip()

        # Remove languages
        if media_info.languages:
            for pattern in self.LANGUAGES.keys():
                title = re.sub(pattern, ' ', title, flags=re.IGNORECASE)

        # Remove source
        if media_info.source:
            for pattern in self.FILE_SOURCE_PATTERNS:
                title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # Remove resolution
        if media_info.resolution:
            for pattern in self.RESOLUTION_PATTERNS:
                title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # Remove video codecs
        if media_info.video_codec:
            for pattern in self.VIDEO_CODEC_PATTERNS:
                title = re.sub(pattern, '', title, flags=re.IGNORECASE)
            
        # Remove audio codec
        if media_info.audio_codec:
            for pattern in self.AUDIO_CODEC_PATTERNS:
                title = re.sub(pattern, '', title, flags=re.IGNORECASE)

        # Remove team
        if media_info.team:
            for pattern in self.TEAM_PATTERNS:
                title = re.sub(pattern, '', title, flags=re.IGNORECASE)

        # Remove version
        if media_info.version:
            for pattern in self.SPECIAL_VERSION_PATTERNS:
                title = re.sub(pattern, ' ', title, flags=re.IGNORECASE)

        # Remove trash
        for pattern in self.TRASH_PATTERNS:
            title = re.sub(pattern, ' ', title, flags=re.IGNORECASE)
        
        # Remove season/episode info
        if media_info.type in ["tvshow", "anime"] and media_info.season:
            title = re.sub(rf'\bs0*{media_info.season}e\d+\b', '', title, flags=re.IGNORECASE)
            if media_info.season >= 10:
                title = re.sub(rf'\bs*{media_info.season}e\d+\b', '', title, flags=re.IGNORECASE)
            title = re.sub(rf'\b{media_info.season}x\d+\b', '', title, flags=re.IGNORECASE)

            if media_info.full_season:
                if media_info.season < 10:
                    title = re.sub(rf'\bs0*{media_info.season}\b', '', title, flags=re.IGNORECASE)
                else:
                    title = re.sub(rf'\bs*{media_info.season}\b', '', title, flags=re.IGNORECASE)
        
        # Clean up separators and extra spaces
        title = re.sub(r'[._\-\[\]\(\)]+', ' ', title)
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title.capitalize()


class TMDBMatcher:
    """Match media with TMDB database with caching support"""
    
    def __init__(self, api_key: str, cache_dir: Optional[str] = None):
        self.tmdb = TMDb()
        self.tmdb.api_key = api_key
        self.movie = Movie()
        self.tv = TV()
        self.search = Search()
        
        # Setup cache
        if cache_dir is None:
            cache_dir = Path.home() / ".qbit2track" / "cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "tmdb_cache.json"
        
        # Load existing cache
        self.cache = self._load_cache()
        
        # Cache expiry (24 hours)
        self.cache_expiry = Config.from_env().app.cache_expiry
        
        logger.info(f"TMDB cache initialized at {self.cache_dir}")
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from disk"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                logger.debug(f"Loaded {len(cache_data)} cached entries")
                return cache_data
            except Exception as e:
                logger.warning(f"Failed to load TMDB cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save cache to disk"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2)
            logger.debug(f"Saved {len(self.cache)} cached entries")
        except Exception as e:
            logger.warning(f"Failed to save TMDB cache: {e}")
    
    def _get_cache_key(self, media_info: MediaInfo) -> str:
        """Generate cache key for media info"""
        # Create a normalized key based on title, year, and type
        key_data = f"{media_info.title.lower()}|{media_info.year or ''}|{media_info.type}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache entry is still valid"""
        return (time.time() - timestamp) < self.cache_expiry
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache if valid"""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if self._is_cache_valid(entry.get('timestamp', 0)):
                logger.debug(f"Cache hit for key: {cache_key}")
                return entry.get('data')
            else:
                # Remove expired entry
                del self.cache[cache_key]
                logger.debug(f"Cache expired for key: {cache_key}")
        return None
    
    def _set_cache(self, cache_key: str, data: Dict[str, Any]):
        """Set data in cache"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
        # Save cache periodically
        if len(self.cache) % 10 == 0:
            self._save_cache()
    
    def match_media(self, media_info: MediaInfo) -> Optional[Dict[str, Any]]:
        """Match media with TMDB and return details (with caching)"""
        cache_key = self._get_cache_key(media_info)
        
        # Try cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            # Update media_info with cached TMDB ID
            if cached_data.get('tmdb_id'):
                media_info.tmdb_id = cached_data['tmdb_id']
            return cached_data
        
        # Not in cache, perform TMDB lookup
        try:
            result = None
            if media_info.type == "movie":
                result = self._match_movie(media_info)
            elif media_info.type == "tvshow":
                result = self._match_tvshow(media_info)
            elif media_info.type == "anime":
                result = self._match_anime(media_info)
            
            # Cache the result
            if result:
                self._set_cache(cache_key, result)
                logger.debug(f"Cached result for {media_info.title}")
            
            return result
            
        except Exception as e:
            logger.warning(f"TMDB match failed for {media_info.title}: {e}")
            return None
    
    def _match_movie(self, media_info: MediaInfo) -> Optional[Dict[str, Any]]:
        """Match movie with TMDB"""
        result = None
        search_results = self.search.movies(media_info.title, year=media_info.year)
        
        if search_results and len(search_results.results) > 0:
            result = search_results.results[0]
            media_info.tmdb_id = result.id
        else:
            search_results = self.search.movies(media_info.title)
            if search_results and len(search_results.results) > 0:
                result = search_results.results[0]
                media_info.tmdb_id = result.id
        
        if result:
            # Get detailed info
            details = self.movie.details(result.id)
            return {
                'tmdb_id': result.id,
                'title': details.title,
                'overview': details.overview,
                'release_date': details.release_date,
                'imdb_id': details.imdb_id,
                'genres': [g.name for g in details.genres],
                'poster_path': details.poster_path,
                'backdrop_path': details.backdrop_path
            }
        
        return None
    
    def _match_tvshow(self, media_info: MediaInfo) -> Optional[Dict[str, Any]]:
        """Match TV show with TMDB"""

        result = None
        search_results = self.search.tv_shows(media_info.title, release_year=media_info.year)       
        if search_results and len(search_results.results) > 0:
            result = search_results.results[0]
            media_info.tmdb_id = result.id
        else:
            search_results = self.search.tv_shows(media_info.title)
            if search_results and len(search_results.results) > 0:
                result = search_results.results[0]
                media_info.tmdb_id = result.id
        

        if result:
            # Get detailed info
            details = self.tv.details(result.id)
            return {
                'tmdb_id': result.id,
                'title': details.name,
                'overview': details.overview,
                'first_air_date': details.first_air_date,
                'genres': [g.name for g in details.genres],
                'poster_path': details.poster_path,
                'backdrop_path': details.backdrop_path,
                'number_of_seasons': details.number_of_seasons,
                'number_of_episodes': details.number_of_episodes
            }
        
        return None
    
    def _match_anime(self, media_info: MediaInfo) -> Optional[Dict[str, Any]]:
        """Match anime (treated as TV show in TMDB)"""
        return self._match_tvshow(media_info)
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("TMDB cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = len(self.cache)
        valid_entries = sum(1 for entry in self.cache.values() 
                          if self._is_cache_valid(entry.get('timestamp', 0)))
        
        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': total_entries - valid_entries,
            'cache_file': str(self.cache_file)
        }
    
    def __del__(self):
        """Save cache when object is destroyed"""
        if hasattr(self, 'cache'):
            self._save_cache()


class TorrentExtractor:
    """Main torrent extraction class"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = Client(
            host=config.qbit.url,
            username=config.qbit.username,
            password=config.qbit.password
        )
        self.analyzer = MediaAnalyzer()
        self.tmdb_matcher = TMDBMatcher(config.tmdb.api_key, cache_dir=config.output.output_dir)
        
        # Test connection
        try:
            self.client.auth_log_in()
            logger.info("Connected to qBittorrent successfully")
        except Exception as e:
            logger.error(f"Failed to connect to qBittorrent: {e}")
            raise
    
    def extract_all(self, tags: Optional[List[str]] = None, 
                   category: Optional[str] = None, 
                   dry_run: bool = False,
                   update_tracker: Optional[str] = None,
                   update_comment: Optional[str] = None,
                   update_tags: Optional[str] = None,
                   update_category: Optional[str] = None) -> Dict[str, int]:
        """Extract all torrents matching filters"""
        torrents = self.client.torrents.info()
        
        # Apply filters
        if tags:
            torrents = [t for t in torrents if any(tag in t.tags for tag in tags)]
        if category:
            torrents = [t for t in torrents if t.category == category]
        
        results = {'total': len(torrents), 'success': 0, 'failed': 0}
        
        for torrent in torrents:
            try:
                logger.info(f"[{results['success'] + 1}/{results['failed']}/{results['total']}] Processing: {torrent.name}")
                self._extract_single_torrent(
                    torrent, 
                    dry_run=dry_run,
                    update_tracker=update_tracker,
                    update_comment=update_comment,
                    update_tags=update_tags,
                    update_category=update_category
                )
                results['success'] += 1
                logger.info(f"Processed: {torrent.name}")
            except Exception as e:
                results['failed'] += 1
                logger.error(f"Failed to process {torrent.name}: {e}")
        
        return results

    def _extract_single_torrent(self, torrent, dry_run: bool = False,
                                update_tracker: Optional[str] = None,
                                update_comment: Optional[str] = None,
                                update_tags: Optional[str] = None,
                                update_category: Optional[str] = None):
        
        """Extract a single torrent"""
        # Analyze media information
        media_info = self.analyzer.analyze_filename(torrent.name, torrent.category)
        
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
            comment=torrent.comment
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
            self._create_nfo_file(torrent_data, output_dir, tmdb_data)
        
        # Create torrent file
        if self.config.output.create_torrent:
            self._create_torrent_file(torrent_data, output_dir)
        
        # Save metadata JSON
        self._save_metadata(torrent_data, output_dir, tmdb_data)
    
    def _create_nfo_file(self, torrent_data: TorrentData, output_dir: Path, tmdb_data: Optional[Dict]):
        """Create NFO file with media information"""
        nfo_content = self._generate_nfo_content(torrent_data, tmdb_data)
        
        nfo_file = output_dir / f"{self._sanitize_filename(torrent_data.name)}.nfo"
        with open(nfo_file, 'w', encoding='utf-8') as f:
            f.write(nfo_content)
        
        logger.debug(f"Created NFO: {nfo_file}")
    
    def _create_torrent_file(self, torrent_data: TorrentData, output_dir: Path):
        """Create new torrent file from existing data"""
        torrent_path = Path(torrent_data.content_path)
        
        def progress_callback(torrent, filepath, pieces_done, pieces_total):
            """Callback to show torrent generation progress"""
            progress = (pieces_done / pieces_total) * 100
            logger.info(f"Generating torrent: {progress:.1f}% - {pieces_done}/{pieces_total} pieces")
        
        # Create new torrent
        torrent = torf.Torrent(
            path=torrent_path,
            name=torrent_data.name,
            private=torrent_data.private if torrent_data.private else False,
            source=f"qbit2track - {torrent_data.hash[:8]}",
            created_by="qbit2track",
            creation_date=datetime.now()
        )
        
        # Add trackers
        if type(torrent_data.tracker) == list:
            torrent.trackers = torrent_data.tracker
        elif type(torrent_data.tracker) == str:
            torrent.trackers = [torrent_data.tracker]
                
        torrent_file = output_dir / f"{self._sanitize_filename(torrent_data.name)}.torrent"
        logger.info(f"Creating torrent file: {torrent_file}")
        torrent.generate(callback=progress_callback, interval=1)
        torrent.write(torrent_file)
        
        logger.info(f"Created torrent: {torrent_file}")
    
    def _save_metadata(self, torrent_data: TorrentData, output_dir: Path, tmdb_data: Optional[Dict]):
        """Save complete metadata as JSON"""
        metadata = {
            'torrent': {
                'hash': torrent_data.hash,
                'name': torrent_data.name,
                'size': torrent_data.size,
                'category': torrent_data.category,
                'tags': torrent_data.tags,
                'comment': torrent_data.comment,
                'private': torrent_data.private,
                'tracker': torrent_data.tracker,
                'created_by': torrent_data.created_by,
                'created_at': torrent_data.created_at,
            },
            'media_info': torrent_data.media_info,
            'tmdb_data': tmdb_data,
            'files': torrent_data.files
        }
        
        metadata_file = output_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Saved metadata: {metadata_file}")
    
    def _generate_nfo_content(self, torrent_data: TorrentData, tmdb_data: Optional[Dict]) -> str:
        """Generate NFO file content"""
        nfo = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
        
        if torrent_data.media_info.type == "movie":
            nfo += "<movie>\n"
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
            nfo += "</movie>\n"
        
        elif torrent_data.media_info.type in ["tvshow", "anime"]:
            nfo += "<episodedetails>\n"
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
            nfo += "</episodedetails>\n"
        
        # Add technical info
        nfo += "\n<!-- Technical Information -->\n"
        nfo += f"<!-- Resolution: {torrent_data.media_info.resolution or 'Unknown'} -->\n"
        nfo += f"<!-- Video Codec: {torrent_data.media_info.video_codec or 'Unknown'} -->\n"
        nfo += f"<!-- Audio Codec: {torrent_data.media_info.audio_codec or 'Unknown'} -->\n"
        nfo += f"<!-- Languages: {', '.join(torrent_data.media_info.languages) or 'Unknown'} -->\n"
        nfo += f"<!-- Original Hash: {torrent_data.hash} -->\n"
        nfo += f"<!-- Category: {torrent_data.category} -->\n"
        nfo += f"<!-- Tags: {', '.join(torrent_data.tags)} -->\n"
        
        return nfo
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename.strip()
