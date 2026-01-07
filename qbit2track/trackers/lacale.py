"""
La Cale tracker uploader implementation
"""
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests
import yaml
from jinja2 import Environment, FileSystemLoader, Template

from ..config import Config
from ..models import TorrentData
from ..naming import NamingContext
from ..uploader import RateLimiter, UploadResult


logger = logging.getLogger(__name__)

@dataclass
class LaCaleMeta:
    """La Cale metadata from /api/external/meta"""
    categories: List[Dict[str, Any]]
    tag_groups: List[Dict[str, Any]]
    ungrouped_tags: List[Dict[str, Any]]

class LaCaleUploader:
    """Specialized uploader for La Cale tracker"""
    
    def __init__(self, passkey: str, config_path: Optional[str] = None):
        self.passkey = passkey
        self.config = self._load_config(config_path)
        self.templates = self._load_templates()
        self.session = requests.Session()
        self.rate_limiter = RateLimiter(
            requests_per_minute=self.config.get('retry', {}).get('max_attempts', 3),
            burst_size=5
        )
        
        # Initialize naming context
        app_config = Config()
        self.naming_context = NamingContext(app_config)
        self._meta_cache_duration = 3600  # Cache for 1 hour
        
        # La Cale specific category mappings based on actual API
        self._category_mapping = {
            "movie": "cmjoyv2cd00027eryreyk39gz",      # Films
            "tvshow": "cmjoyv2dg00067ery8m6c3q8h",     # Séries TV
            "anime": "cmjoyv2d900057eryz5xw65xc"        # Animation (sub-category of Films)
        }
        
        # Resolution mappings based on La Cale tags
        self._resolution_mapping = {
            "480p": "480p",
            "576p": "576p", 
            "720p": "720p",
            "1080p": "1080p",
            "2160p": "2160p",
            "4k": "2160p",
            "sd": "sd"
        }
        
        # Video codec mappings based on La Cale ungrouped tags
        self._video_codec_mapping = {
            "x264": "d5cl1va7302s73ah0hbg",  # H264
            "x265": "d5cl21a7302s73ah0hf0",  # H265
            "hevc": "d5cl22i7302s73ah0hh0",  # HEVC
            "h264": "d5cl1va7302s73ah0hbg",
            "h265": "d5cl21a7302s73ah0hf0",
            "avc": "d5cl1va7302s73ah0hbg",
            "vc-1": "vc1",
            "mpeg2": "mpeg2"
        }
        
        # Audio codec mappings (common codec names)
        self._audio_codec_mapping = {
            "ac3": "ac3",
            "dts": "dts",
            "aac": "aac",
            "flac": "flac",
            "truehd": "truehd",
            "eac3": "eac3",
            "opus": "opus",
            "mp3": "mp3",
            "m4a": "m4a"
        }
        
        # Language mappings (French tracker, so French language names)
        self._language_mapping = {
            "en": "VO",           # Version Originale (English)
            "fr": "VF",           # Version Française
            "es": "espagnol", 
            "de": "allemand",
            "it": "italien",
            "pt": "portugais",
            "ru": "russe",
            "ja": "japonais",
            "ko": "coréen",
            "zh": "chinois",
            "ar": "arabe",
            "hi": "hindi",
            "la": "latin",
            "sv": "suédois",
            "no": "norvégien",
            "da": "danois",
            "nl": "néerlandais",
            "fi": "finnois"
        }
        
        # Genre mappings from TMDB to common tracker genres (French)
        self._genre_mapping = {
            "Action": "action",
            "Adventure": "aventure", 
            "Animation": "animation",
            "Comedy": "comedie",
            "Crime": "polar",
            "Documentary": "documentaire",
            "Drama": "drame",
            "Family": "famille",
            "Fantasy": "fantastique",
            "Horror": "horreur",
            "Mystery": "polar",
            "Romance": "romance",
            "Science Fiction": "science-fiction",
            "Thriller": "thriller",
            "War": "guerre",
            "Western": "western",
            "History": "historique",
            "Music": "musique",
            "TV Movie": "telefilm"
        }
        
        # Content type mappings
        self._content_type_mapping = {
            "movie": "cmjudwpgn0016uyruja14d0fu",     # Film
            "tvshow": "cmjoyv2dg00067ery8m6c3q8h",  # TV shows don't have a specific content type tag
            "anime": "cmjudwprl0017uyrusdiye36d",     # Film d'animation
            "documentary": "documentaire",
            "spectacle": "cmjudwq2v0018uyruhuylsy3q"   # Spectacle
        }
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load La Cale configuration from YAML file"""
        if config_path:
            config_file = Path(config_path)
        else:
            # Default to new config location in trackers/config
            config_file = Path(__file__).parent / "config" / "lacale.yaml"
        
        if not config_file.exists():
            logger.warning(f"La Cale config file not found: {config_file}")
            return {}
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Get La Cale specific configuration
            api_configs = config.get('api_configs', {})
            la_cale_config = api_configs.get('la_cale', {})
            
            logger.info(f"Loaded La Cale configuration from {config_file}")
            return la_cale_config
            
        except Exception as e:
            logger.error(f"Failed to load La Cale config: {e}")
            return {}
    
    def _load_templates(self) -> Dict[str, Template]:
        """Load Jinja2 templates for La Cale"""
        templates = {}
        
        try:
            # Get templates directory - new location in trackers/templates
            templates_dir = Path(__file__).parent / "templates" / "lacale"
            
            if not templates_dir.exists():
                logger.warning(f"Templates directory not found: {templates_dir}")
                return templates
            
            # Setup Jinja2 environment
            env = Environment(
                loader=FileSystemLoader(str(templates_dir)),
                autoescape=True
            )
            
            # Add custom filters
            env.filters['filesizeformat'] = self._filesizeformat
            
            # Load description template
            try:
                templates['description'] = env.get_template('description.j2')
                logger.info("Loaded description template")
            except Exception as e:
                logger.warning(f"Failed to load description template: {e}")
            
            return templates
            
        except Exception as e:
            logger.error(f"Failed to setup templates: {e}")
            return {}
    
    def _filesizeformat(self, size_bytes: Any) -> str:
        """Format file size in human readable format"""
        try:
            if not size_bytes:
                return "Unknown"
            
            size = int(size_bytes)
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} PB"
        except (ValueError, TypeError):
            return "Unknown"
    
    def generate_torrent_name(self, naming_context: Dict[str, Any], torrent_data: Dict[str, Any]) -> str:
        """Generate torrent name using Jinja2 template"""
        try:
            # Get template for media type
            media_type = naming_context.get('type', 'movie')
            torrent_names = self.config.get('torrent_names', {})
            
            template_str = torrent_names.get(media_type)
            if not template_str:
                # Fallback to simple naming
                return naming_context.get('title', 'Unknown')
            
            # Render template
            template = Template(template_str)
            torrent_name = template.render(**naming_context)
            
            logger.info(f"Generated torrent name: {torrent_name}")
            return torrent_name
            
        except Exception as e:
            logger.error(f"Failed to generate torrent name: {e}")
            return naming_context.get('title', 'Unknown')
    
    def generate_description(self, naming_context: Dict[str, Any], torrent_data: Dict[str, Any]) -> str:
        """Generate description using Jinja2 template"""
        try:
            template = self.templates.get('description')
            if not template:
                # Fallback to basic description
                return self._generate_basic_description(naming_context, torrent_data)
            
            # Render template
            description = template.render(**naming_context)
            
            logger.info(f"Generated description: {len(description)} characters")
            return description
            
        except Exception as e:
            logger.error(f"Failed to generate description: {e}")
            return self._generate_basic_description(naming_context, torrent_data)
    
    def _generate_basic_description(self, naming_context: Dict[str, Any], torrent_data: Dict[str, Any]) -> str:
        """Generate basic description without templates"""
        description_parts = []
        
        # Add TMDB overview
        tmdb_info = naming_context.get('tmdb_info', {})
        if tmdb_info.get('overview'):
            description_parts.append(tmdb_info['overview'])
        
        # Add technical details
        tech_details = []
        if naming_context.get('resolution'):
            tech_details.append(f"Resolution: {naming_context['resolution']}")
        if naming_context.get('video_codec'):
            tech_details.append(f"Video: {naming_context['video_codec']}")
        if naming_context.get('audio_codec'):
            tech_details.append(f"Audio: {naming_context['audio_codec']}")
        if naming_context.get('languages'):
            tech_details.append(f"Languages: {', '.join(naming_context['languages'])}")
        if naming_context.get('hdr'):
            tech_details.append(f"HDR: {naming_context['hdr']}")
        
        if tech_details:
            description_parts.append("\n\nTechnical Details:\n" + "\n".join(tech_details))
        
        return "\n".join(description_parts)
    
    def fetch_meta(self) -> LaCaleMeta:
        """Fetch metadata from La Cale API"""
        # Check cache first
        now = time.time()
        if (self._meta_cache and 
            now - self._meta_cache_time < self._meta_cache_duration):
            return self._meta_cache
        
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.base_url}/api/external/meta"
        params = {"passkey": self.passkey}
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self._meta_cache = LaCaleMeta(
                categories=data.get('categories', []),
                tag_groups=data.get('tagGroups', []),
                ungrouped_tags=data.get('ungroupedTags', [])
            )
            self._meta_cache_time = now
            
            logger.info("Successfully fetched La Cale metadata")
            return self._meta_cache
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch La Cale metadata: {e}")
            raise ValueError(f"Meta fetch failed: {e}")
    
    def get_categories(self) -> Dict[str, str]:
        """Get categories as id->name mapping"""
        meta = self.fetch_meta()
        categories = {}
        
        def add_category_with_children(category):
            """Recursively add category and its children"""
            categories[category['id']] = category['name']
            if 'children' in category and category['children']:
                for child in category['children']:
                    add_category_with_children(child)
        
        for category in meta.categories:
            add_category_with_children(category)
        
        return categories
    
    def get_tags(self) -> Dict[str, str]:
        """Get tags as id->name mapping"""
        meta = self.fetch_meta()
        tags = {}
        
        # Add grouped tags
        for group in meta.tag_groups:
            if group.get('tags'):  # Check if tags exist and are not None
                for tag in group['tags']:
                    tags[tag['id']] = tag['name']
        
        # Add ungrouped tags
        for tag in meta.ungrouped_tags:
            tags[tag['id']] = tag['name']
        
        return tags
    
    def _find_matching_tag_id(self, tag_value: str, available_tags: Dict[str, str]) -> Optional[str]:
        """Find the best matching tag ID for a given value"""
        # Direct match
        for tag_id, tag_name in available_tags.items():
            if tag_name.lower() == tag_value.lower():
                return tag_id
        
        # Partial match
        for tag_id, tag_name in available_tags.items():
            if tag_value.lower() in tag_name.lower() or tag_name.lower() in tag_value.lower():
                return tag_id
        
        return None
    
    def _map_category_id(self, media_type: str, available_categories: Dict[str, str]) -> Optional[str]:
        """Map media type to La Cale category ID using actual API categories"""
        # Use direct mapping to La Cale category IDs first
        direct_mapping = self._category_mapping.get(media_type.lower())
        if direct_mapping and direct_mapping in available_categories:
            return direct_mapping
        
        # Special handling for anime - it's a subcategory of Films
        if media_type.lower() == 'anime':
            # Look for Animation subcategory
            for cat_id, cat_name in available_categories.items():
                if 'animation' in cat_name.lower():
                    return cat_id
        
        # Fallback to name-based matching
        category_keywords = {
            'movie': ['film', 'films'],
            'tvshow': ['série', 'series', 'tv'],
            'anime': ['animation', 'anime']
        }
        
        keywords = category_keywords.get(media_type.lower(), [media_type.lower()])
        for cat_id, cat_name in available_categories.items():
            for keyword in keywords:
                if keyword in cat_name.lower() or cat_name.lower() in keyword:
                    return cat_id
        
        return None
    
    def _extract_tags_from_media_info(self, media_info: Dict[str, Any], available_tags: Dict[str, str]) -> List[str]:
        """Extract and map tags from media info using La Cale's actual tags"""
        tags = []
        
        # Add content type tag (Film, Film d'animation, etc.)
        media_type = media_info.get('type', 'movie')
        content_type_tag = self._content_type_mapping.get(media_type)
        if content_type_tag and content_type_tag in available_tags:
            tags.append(content_type_tag)
        
        # Add genre tags from TMDB
        if 'tmdb_info' in media_info and 'genres' in media_info['tmdb_info']:
            for genre in media_info['tmdb_info']['genres']:
                mapped_genre = self._genre_mapping.get(genre, genre.lower())
                tag_id = self._find_matching_tag_id(mapped_genre, available_tags)
                if tag_id:
                    tags.append(tag_id)
        
        # Add resolution tag
        if media_info.get('resolution'):
            mapped_resolution = self._resolution_mapping.get(media_info['resolution'], media_info['resolution'].lower())
            tag_id = self._find_matching_tag_id(mapped_resolution, available_tags)
            if tag_id:
                tags.append(tag_id)
        
        # Add video codec tag (use La Cale specific IDs)
        if media_info.get('video_codec'):
            mapped_codec = self._video_codec_mapping.get(media_info['video_codec'].lower())
            if mapped_codec and mapped_codec in available_tags:
                tags.append(mapped_codec)
            else:
                # Fallback to name matching
                tag_id = self._find_matching_tag_id(media_info['video_codec'].lower(), available_tags)
                if tag_id:
                    tags.append(tag_id)
        
        # Add audio codec tag
        if media_info.get('audio_codec'):
            mapped_codec = self._audio_codec_mapping.get(media_info['audio_codec'].lower())
            tag_id = self._find_matching_tag_id(mapped_codec, available_tags)
            if tag_id:
                tags.append(tag_id)
        
        # Add language tags
        for lang in media_info.get('languages', []):
            mapped_lang = self._language_mapping.get(lang.lower(), lang.lower())
            tag_id = self._find_matching_tag_id(mapped_lang, available_tags)
            if tag_id:
                tags.append(tag_id)
        
        # Add HDR tag if present
        if media_info.get('hdr'):
            hdr_variants = [
                media_info['hdr'].lower(),
                media_info['hdr'].upper(),
                f"HDR{media_info['hdr'][2:]}" if media_info['hdr'].lower().startswith('hdr') else media_info['hdr']
            ]
            for hdr_variant in hdr_variants:
                tag_id = self._find_matching_tag_id(hdr_variant, available_tags)
                if tag_id:
                    tags.append(tag_id)
                    break
        
        # Add source tag if available
        if media_info.get('source'):
            tag_id = self._find_matching_tag_id(media_info['source'].lower(), available_tags)
            if tag_id:
                tags.append(tag_id)
        
        return list(set(tags))  # Remove duplicates
    
    def upload_from_metadata(self, metadata_path: str) -> UploadResult:
        """Upload torrent using metadata.json file from extract phase"""
        try:
            # Load metadata
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            media_info = metadata.get('media_info', {})
            torrent_data = metadata.get('torrent_data', {})
            
            # Get La Cale metadata for mapping
            available_categories = self.get_categories()
            available_tags = self.get_tags()
            
            # Map category ID
            category_id = self._map_category_id(media_info.get('type', 'movie'), available_categories)
            if not category_id:
                return UploadResult(
                    torrent_name=torrent_data.get('name', 'Unknown'),
                    success=False,
                    message=f"Could not map category for media type: {media_info.get('type')}"
                )
            
            # Extract tags
            tags = self._extract_tags_from_media_info(media_info, available_tags)
            
            # Find torrent and NFO files
            metadata_dir = Path(metadata_path).parent
            torrent_file = None
            nfo_file = None
            
            for file_path in metadata_dir.iterdir():
                if file_path.suffix == '.torrent':
                    torrent_file = str(file_path)
                elif file_path.suffix == '.nfo':
                    nfo_file = str(file_path)
            
            if not torrent_file:
                return UploadResult(
                    torrent_name=torrent_data.get('name', 'Unknown'),
                    success=False,
                    message="No torrent file found in metadata directory"
                )
            
            # Determine TMDB type
            tmdb_type = None
            if media_info.get('type') == 'movie':
                tmdb_type = "MOVIE"
            elif media_info.get('type') in ['tvshow', 'anime']:
                tmdb_type = "TV"
            
            # Get TMDB ID
            tmdb_id = None
            if media_info.get('tmdb_id'):
                tmdb_id = str(media_info['tmdb_id'])
            
            # Perform upload
            # Generate naming context
            naming_context = self.naming_context.create_context(media_info, torrent_data)
            
            # Generate torrent name using template
            torrent_name = self.generate_torrent_name(naming_context, torrent_data)
            
            # Generate description using template
            description = self.generate_description(naming_context, torrent_data)
            
            return self.upload_torrent(
                title=torrent_name,
                category_id=category_id,
                torrent_file_path=torrent_file,
                description=description if description.strip() else None,
                tmdb_id=tmdb_id,
                tmdb_type=tmdb_type,
                tags=tags if tags else None,
                nfo_file_path=nfo_file
            )
            
        except Exception as e:
            logger.error(f"Failed to upload from metadata {metadata_path}: {e}")
            return UploadResult(
                torrent_name="Unknown",
                success=False,
                message=f"Metadata processing failed: {str(e)}"
            )
    
    def mass_upload_from_directory(self, output_dir: str) -> Dict[str, int]:
        """Mass upload all torrents from output directory using metadata.json files"""
        output_path = Path(output_dir)
        
        if not output_path.exists():
            raise FileNotFoundError(f"Output directory not found: {output_dir}")
        
        # Find all directories with metadata.json
        metadata_dirs = []
        for item in output_path.iterdir():
            if item.is_dir() and (item / "metadata.json").exists():
                metadata_dirs.append(item)
        
        if not metadata_dirs:
            logger.warning("No metadata.json files found")
            return {'total': 0, 'success': 0, 'failed': 0}
        
        results = {'total': len(metadata_dirs), 'success': 0, 'failed': 0}
        
        logger.info(f"Starting mass upload of {len(metadata_dirs)} torrents")
        
        for metadata_dir in sorted(metadata_dirs):
            metadata_path = metadata_dir / "metadata.json"
            logger.info(f"Processing: {metadata_dir.name}")
            
            try:
                result = self.upload_from_metadata(str(metadata_path))
                
                if result.success:
                    results['success'] += 1
                    logger.info(f"✅ Successfully uploaded: {result.torrent_name}")
                    if result.upload_id:
                        logger.info(f"   Upload ID: {result.upload_id}")
                else:
                    results['failed'] += 1
                    logger.error(f"❌ Failed to upload {metadata_dir.name}: {result.message}")
                    
            except Exception as e:
                results['failed'] += 1
                logger.error(f"❌ Error processing {metadata_dir.name}: {e}")
        
        logger.info(f"Mass upload complete: {results['success']} success, {results['failed']} failed")
        return results
    
    def upload_torrent(self, 
                       title: str,
                       category_id: str,
                       torrent_file_path: str,
                       description: Optional[str] = None,
                       tmdb_id: Optional[str] = None,
                       tmdb_type: Optional[str] = None,
                       cover_url: Optional[str] = None,
                       tags: Optional[List[str]] = None,
                       nfo_file_path: Optional[str] = None) -> UploadResult:
        """Upload torrent to La Cale"""
        
        self.rate_limiter.wait_if_needed()
        
        # Validate inputs
        if not self.passkey:
            return UploadResult(
                torrent_name=title,
                success=False,
                message="Passkey is required"
            )
        
        if not title:
            return UploadResult(
                torrent_name=title,
                success=False,
                message="Title is required"
            )
        
        if not category_id:
            return UploadResult(
                torrent_name=title,
                success=False,
                message="Category ID is required"
            )
        
        torrent_path = Path(torrent_file_path)
        if not torrent_path.exists():
            return UploadResult(
                torrent_name=title,
                success=False,
                message=f"Torrent file not found: {torrent_file_path}"
            )
        
        # Validate TMDB type
        if tmdb_type and tmdb_type not in ["MOVIE", "TV"]:
            return UploadResult(
                torrent_name=title,
                success=False,
                message="tmdb_type must be 'MOVIE' or 'TV'"
            )
        
        # Validate cover URL
        if cover_url and not cover_url.startswith("https://"):
            return UploadResult(
                torrent_name=title,
                success=False,
                message="Cover URL must use HTTPS"
            )
        
        # Prepare form data
        form_data = {
            "passkey": self.passkey,
            "title": title,
            "categoryId": category_id
        }
        
        # Add optional fields
        if description and description.strip():
            form_data["description"] = description.strip()
        
        if tmdb_id and tmdb_id.strip():
            form_data["tmdbId"] = tmdb_id.strip()
        
        if tmdb_type in ["MOVIE", "TV"]:
            form_data["tmdbType"] = tmdb_type
        
        if cover_url and cover_url.strip():
            form_data["coverUrl"] = cover_url.strip()
        
        # Add tags as list (requests handles repeated fields)
        if tags and isinstance(tags, list):
            form_data["tags"] = tags
        
        # Prepare files
        files = {}
        try:
            # Add torrent file
            files["file"] = (torrent_path.name, open(torrent_path, "rb"))
            
            # Add NFO file if provided
            if nfo_file_path:
                nfo_path = Path(nfo_file_path)
                if nfo_path.exists():
                    files["nfoFile"] = (nfo_path.name, open(nfo_path, "rb"))
                else:
                    logger.warning(f"NFO file not found: {nfo_file_path}")
            
            # Make upload request
            url = f"{self.base_url}/api/external/upload"
            
            try:
                response = requests.post(url, data=form_data, files=files, timeout=60)
                
                # Process response
                if response.status_code == 200:
                    result_data = response.json()
                    if result_data.get('success'):
                        return UploadResult(
                            torrent_name=title,
                            success=True,
                            message="Upload successful",
                            upload_id=result_data.get('id'),
                            status_url=result_data.get('link')
                        )
                    else:
                        return UploadResult(
                            torrent_name=title,
                            success=False,
                            message=result_data.get('message', 'Upload failed')
                        )
                elif response.status_code == 400:
                    error_msg = f"Invalid request: {response.text}"
                    logger.error(f"La Cale upload failed (400): {error_msg}")
                    return UploadResult(torrent_name=title, success=False, message=error_msg)
                elif response.status_code == 403:
                    return UploadResult(
                        torrent_name=title,
                        success=False,
                        message="Invalid passkey"
                    )
                elif response.status_code == 409:
                    return UploadResult(
                        torrent_name=title,
                        success=False,
                        message="Duplicate torrent (same infoHash)"
                    )
                elif response.status_code == 429:
                    return UploadResult(
                        torrent_name=title,
                        success=False,
                        message="Rate limit exceeded - please wait and retry"
                    )
                elif response.status_code >= 500:
                    return UploadResult(
                        torrent_name=title,
                        success=False,
                        message=f"Server error: {response.status_code}"
                    )
                else:
                    return UploadResult(
                        torrent_name=title,
                        success=False,
                        message=f"Unexpected error: {response.status_code} - {response.text}"
                    )
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"La Cale upload request failed: {e}")
                return UploadResult(
                    torrent_name=title,
                    success=False,
                    message=f"Request failed: {str(e)}"
                )
                
        finally:
            # Always close file handles
            for file_obj in files.values():
                file_obj[1].close()
    
    def validate_torrent_source(self, torrent_file_path: str) -> bool:
        """Check if torrent contains 'LacaLe' source flag (basic check)"""
        try:
            # This is a basic implementation - in a full implementation,
            # you'd parse the torrent file with bencode library
            torrent_path = Path(torrent_file_path)
            if not torrent_path.exists():
                return False
            
            # For now, just check if filename suggests it's from La Cale
            # In production, you'd parse the torrent and check source field
            return "lacle" in torrent_path.name.lower() or "la-cale" in torrent_path.name.lower()
            
        except Exception as e:
            logger.warning(f"Could not validate torrent source: {e}")
            return True  # Assume valid if we can't check
