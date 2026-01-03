"""
TMDB (The Movie Database) matching and caching
"""
import json
import logging
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from tmdbv3api import TMDb, Movie, TV, Search, Season, Episode
from ..config import Config
from ..models import MediaInfo
from ..utils import CustomJSONEncoder, custom_json_decoder

logger = logging.getLogger(__name__)


class TMDBMatcher:
    """Match media with TMDB and cache results"""
    
    def __init__(self, config: Config, cache_dir: Optional[Path] = None):
        self.config = config
        self.tmdb = TMDb()
        self.tmdb.api_key = config.tmdb.api_key
        self.tmdb.language = config.tmdb.language
        
        self.movie = Movie()
        self.tv = TV()
        self.search = Search()
        self.season = Season()
        self.episode = Episode()
        
        # Cache setup
        self.cache_dir = cache_dir or Path(config.output.output_dir)
        self.cache_file = self.cache_dir / "tmdb_cache.json"
        self.cache = self._load_cache()
    
    def match_media(self, media_info: MediaInfo) -> Optional[Dict]:
        """Match media with TMDB and return metadata"""
        cache_key = self._get_cache_key(media_info)
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            logger.debug(f"TMDB cache hit for: {media_info.title}")
            return cached_data
        
        # Perform search
        if media_info.type == "movie":
            result, score = self._match_movie(media_info)
        elif media_info.type in ["tvshow", "anime"]:
            result, score = self._match_tvshow(media_info)
        else:
            logger.warning(f"Unknown media type: {media_info.type}")
            return None
        
        if result:
            self._set_cache(cache_key, result)
            
            if score < 50:
                logger.warning(f"TMDB match score is low: {media_info.title} -> {result.get('title', 'Unknown')} (id: {result.get('tmdb_id')}, score: {score})")
            else:
                logger.info(f"TMDB match found: {media_info.title} -> {result.get('title', 'Unknown')} (id: {result.get('tmdb_id')}, score: {score})")
        else:
            logger.warning(f"TMDB match failed for: {media_info.title}")
        
        return result
    
    def _match_movie(self, media_info: MediaInfo) -> Tuple[Optional[Dict], int]:
        """Match movie with TMDB"""
        try:
            # Search with title
            if media_info.year:
                search_results = self.search.movies(
                    media_info.title,
                    year=media_info.year
                )
            else:
                search_results = self.search.movies(
                    media_info.title
                )
            
            if not search_results or len(search_results.results) < 1:
                # Try broader search without year
                search_results = self.search.movies(
                    media_info.title
                )

            best_match = None
            best_score = 0
            
            for result in search_results.results:
                details = self.movie.details(result.id)
                current_match = {
                    'tmdb_id': result.id,
                    'title': result.title,
                    'original_title': result.original_title,
                    'overview': result.overview,
                    'release_date': result.release_date,
                    'genres': [genre.name for genre in details.genres],
                    'imdb_id': details.imdb_id,
                    'runtime': details.runtime,
                    'vote_average': result.vote_average,
                    'poster_path': result.poster_path,
                    'backdrop_path': result.backdrop_path
                }
                
                # Calculate match score
                score = 0
                media_title_lower = media_info.title.lower()
                result_title_lower = result.title.lower()
                result_original_lower = result.original_title.lower()
                
                # Exact title match (highest priority)
                if media_title_lower == result_title_lower:
                    score += 100
                elif media_title_lower == result_original_lower:
                    score += 90
                    
                # Substring matches
                elif media_title_lower in result_title_lower:
                    score += 70
                elif media_title_lower in result_original_lower:
                    score += 60
                elif result_title_lower in media_title_lower:
                    score += 50
                elif result_original_lower in media_title_lower:
                    score += 40
                
                # Fuzzy matching using Levenshtein distance
                else:
                    import difflib
                    similarity = difflib.SequenceMatcher(None, media_title_lower, result_title_lower).ratio()
                    similarity_orig = difflib.SequenceMatcher(None, media_title_lower, result_original_lower).ratio()
                    score += max(similarity, similarity_orig) * 30
                
                # Year bonus (if year is available)
                if media_info.year and result.release_date:
                    result_year = result.release_date.split('-')[0]
                    if str(media_info.year) == result_year:
                        score += 20
                    elif abs(int(result_year) - media_info.year) <= 2:
                        score += 10

                # Length penalty for very different lengths
                length_diff = abs(len(media_title_lower) - len(result_title_lower))
                if length_diff > 10:
                    score -= length_diff
                
                if score > best_score:
                    best_score = score
                    best_match = current_match
                    
                # Early exit for perfect match
                if score >= 100:  # Exact match + year + language bonus
                    break
            
            return best_match, best_score
        
        except Exception as e:
            logger.error(f"TMDB match failed for {media_info.title}: {e}")
        
        return None, 0
    
    def _match_tvshow(self, media_info: MediaInfo) -> Tuple[Optional[Dict], int]:
        """Match TV show with TMDB"""
        try:
            # Search with title
            if media_info.year:
                search_results = self.search.tv_shows(
                    media_info.title,
                    release_year=media_info.year
                )
            else:
                search_results = self.search.tv_shows(
                    media_info.title
                )
            
            if not search_results or len(search_results.results) < 1:
                # Try broader search without year
                search_results = self.search.tv_shows(
                    media_info.title
                )
            
            # Improved matching system for TV shows
            best_match = None
            best_score = 0
            
            for result in search_results.results:
                details = self.tv.details(result.id)
                
                # If we have season/episode info, get episode details
                episode_data = None
                season_data = None
                if media_info.season:
                    try:
                        if media_info.episode:
                            episode_data = self.episode.details(
                                result.id, 
                                media_info.season, 
                                media_info.episode
                            )

                        if media_info.season:
                            season_data = self.season.details(result.id, media_info.season)
                    except Exception as ex:
                        logger.error(f"TMDB TV show match failed for {media_info.title}: {ex}")
                        pass  # Episode/season details not available
                
                current_match = {
                    'tmdb_id': result.id,
                    'title': result.name,
                    'original_title': result.original_name,
                    'overview': result.overview,
                    'first_air_date': result.first_air_date,
                    'genres': [genre.name for genre in details.genres],
                    'episode_data': episode_data,
                    'season_data': season_data,
                    'season': media_info.season,
                    'episode': media_info.episode,
                    'vote_average': result.vote_average,
                    'poster_path': result.poster_path,
                    'backdrop_path': result.backdrop_path
                }
                
                # Calculate match score (similar to movie matching)
                score = 0
                media_title_lower = media_info.title.lower()
                result_title_lower = result.name.lower()
                result_original_lower = result.original_name.lower()
                
                # Exact title match (highest priority)
                if media_title_lower == result_title_lower:
                    score += 100
                elif media_title_lower == result_original_lower:
                    score += 90
                    
                # Substring matches
                elif media_title_lower in result_title_lower:
                    score += 70
                elif media_title_lower in result_original_lower:
                    score += 60
                elif result_title_lower in media_title_lower:
                    score += 50
                elif result_original_lower in media_title_lower:
                    score += 40
                
                # Fuzzy matching
                else:
                    import difflib
                    similarity = difflib.SequenceMatcher(None, media_title_lower, result_title_lower).ratio()
                    similarity_orig = difflib.SequenceMatcher(None, media_title_lower, result_original_lower).ratio()
                    score += max(similarity, similarity_orig) * 30
                
                # Year bonus (if year is available)
                if media_info.year and result.first_air_date:
                    result_year = result.first_air_date.split('-')[0]
                    if str(media_info.year) == result_year:
                        score += 20
                    elif abs(int(result_year) - media_info.year) <= 2:
                        score += 10
                
                # Length penalty
                length_diff = abs(len(media_title_lower) - len(result_title_lower))
                if length_diff > 10:
                    score -= length_diff
                
                if score > best_score:
                    best_score = score
                    best_match = current_match
                    
                # Early exit for perfect match
                if score >= 100:
                    break
            
            return best_match, best_score
        
        except Exception as e:
            logger.error(f"TMDB TV show match failed for {media_info.title}: {e}")
        
        return None, 0
    
    def _get_cache_key(self, media_info: MediaInfo) -> str:
        """Generate cache key for media info"""
        key_data = f"{media_info.title}_{media_info.year}_{media_info.type}_{media_info.season}_{media_info.episode}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _load_cache(self) -> Dict:
        """Load cache from file"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f, object_hook=custom_json_decoder)
                    # Remove expired entries
                    current_time = time.time()
                    expired_keys = [
                        key for key, value in cache_data.items()
                        if current_time - value.get('timestamp', 0) > self.config.app.cache_expiry
                    ]
                    for key in expired_keys:
                        del cache_data[key]
                    return cache_data
            except Exception as e:
                logger.error(f"Failed to load TMDB cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save cache to file"""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, cls=CustomJSONEncoder)
        except Exception as e:
            logger.error(f"Failed to save TMDB cache: {e}")
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get data from cache if valid"""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if time.time() - entry.get('timestamp', 0) <= self.config.app.cache_expiry:
                return entry.get('data')
            else:
                # Remove expired entry
                del self.cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Dict):
        """Set data in cache"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def clear_cache(self):
        """Clear all cache entries"""
        self.cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("TMDB cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        total_entries = len(self.cache)
        current_time = time.time()
        valid_entries = sum(
            1 for entry in self.cache.values()
            if current_time - entry.get('timestamp', 0) <= self.config.app.cache_expiry
        )
        expired_entries = total_entries - valid_entries
        
        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'cache_file': str(self.cache_file)
        }
    
    def __del__(self):
        """Save cache when object is destroyed"""
        self._save_cache()
