"""
Mass upload functionality for qbit2track
"""

import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import Config


logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    """Result of an upload attempt"""
    torrent_name: str
    success: bool
    message: str
    upload_id: Optional[str] = None
    status_url: Optional[str] = None


class RateLimiter:
    """Simple rate limiter for API requests"""
    
    def __init__(self, requests_per_minute: int = 30, burst_size: int = 5):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.requests = []
        self.lock = False
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        
        # Remove old requests (older than 1 minute)
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]
        
        # Check if we would exceed the limit
        if len(self.requests) >= self.requests_per_minute:
            sleep_time = 60 - (now - self.requests[0])
            if sleep_time > 0:
                logger.info(f"Rate limit reached, waiting {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
        
        # Check burst limit
        recent_requests = [req_time for req_time in self.requests if now - req_time < 5]
        if len(recent_requests) >= self.burst_size:
            sleep_time = 5 - (now - recent_requests[0])
            if sleep_time > 0:
                logger.info(f"Burst limit reached, waiting {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
        
        self.requests.append(now)


class APIClient:
    """Generic API client for tracker uploads"""
    
    def __init__(self, config: Dict[str, Any], tracker_name: str):
        self.tracker_name = tracker_name
        self.config = config
        self.session = self._create_session()
        self.rate_limiter = RateLimiter(
            requests_per_minute=config.get('rate_limit', {}).get('requests_per_minute', 30),
            burst_size=config.get('rate_limit', {}).get('burst_size', 5)
        )
    
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.get('retry', {}).get('max_attempts', 3),
            backoff_factor=self.config.get('retry', {}).get('backoff_factor', 2),
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        headers = self.config.get('headers', {})
        for key, value in headers.items():
            session.headers[key] = value
        
        # Configure authentication
        auth_config = self.config.get('auth', {})
        auth_type = auth_config.get('type', 'none')
        
        if auth_type == 'api_key':
            api_key = auth_config.get('api_key')
            if api_key:
                session.headers['Authorization'] = f'Bearer {api_key}'
        elif auth_type == 'basic':
            session.auth = (
                auth_config.get('username', ''),
                auth_config.get('password', '')
            )
        
        return session
    
    def upload_torrent(self, torrent_data: Dict[str, Any], files: Dict[str, Any]) -> UploadResult:
        """Upload torrent to tracker"""
        self.rate_limiter.wait_if_needed()
        
        upload_url = self.config['base_url'] + self.config['endpoints']['upload']
        
        try:
            # Prepare files for upload
            files_to_upload = {}
            
            # Add torrent file
            torrent_file_path = files.get('torrent_file')
            if torrent_file_path and Path(torrent_file_path).exists():
                files_to_upload['torrent'] = open(torrent_file_path, 'rb')
            
            # Add NFO file if exists
            nfo_file_path = files.get('nfo_file')
            if nfo_file_path and Path(nfo_file_path).exists():
                files_to_upload['nfo'] = open(nfo_file_path, 'rb')
            
            # Prepare data
            data = self._prepare_upload_data(torrent_data)
            
            # Make request
            timeout = self.config.get('timeout', 30)
            response = self.session.post(
                upload_url,
                files=files_to_upload,
                data=data,
                timeout=timeout
            )
            
            # Close files
            for file_obj in files_to_upload.values():
                file_obj.close()
            
            # Process response
            if response.status_code in [200, 201]:
                result_data = response.json() if response.content else {}
                return UploadResult(
                    torrent_name=torrent_data['media_info']['title'],
                    success=True,
                    message="Upload successful",
                    upload_id=result_data.get('id'),
                    status_url=self._get_status_url(result_data.get('id'))
                )
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return UploadResult(
                    torrent_name=torrent_data['media_info']['title'],
                    success=False,
                    message=error_msg
                )
        
        except requests.exceptions.Timeout:
            return UploadResult(
                torrent_name=torrent_data['media_info']['title'],
                success=False,
                message="Upload timeout"
            )
        except Exception as e:
            return UploadResult(
                torrent_name=torrent_data['media_info']['title'],
                success=False,
                message=f"Upload error: {str(e)}"
            )
    
    def _prepare_upload_data(self, torrent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for upload request"""
        media_info = torrent_data['media_info']
        tmdb_data = torrent_data.get('tmdb_data', {})
        
        data = {
            'name': media_info['title'],
            'type': media_info['type'],
            'description': self._generate_description(torrent_data),
            'category': torrent_data['torrent']['category'],
            'tags': ','.join(torrent_data['torrent']['tags']),
            'size': torrent_data['torrent']['size']
        }
        
        # Add media-specific fields
        if media_info.get('year'):
            data['year'] = media_info['year']
        
        if media_info.get('resolution'):
            data['resolution'] = media_info['resolution']
        
        if media_info.get('video_codec'):
            data['video_codec'] = media_info['video_codec']
        
        if media_info.get('audio_codec'):
            data['audio_codec'] = media_info['audio_codec']
        
        if media_info.get('tmdb_id'):
            data['tmdb_id'] = media_info['tmdb_id']
        
        if media_info.get('imdb_id'):
            data['imdb_id'] = media_info['imdb_id']
        
        # TV show specific
        if media_info.get('season'):
            data['season'] = media_info['season']
        
        if media_info.get('episode'):
            data['episode'] = media_info['episode']
        
        # TMDB data
        if tmdb_data:
            data['tmdb_data'] = json.dumps(tmdb_data)
        
        return data
    
    def _generate_description(self, torrent_data: Dict[str, Any]) -> str:
        """Generate upload description"""
        media_info = torrent_data['media_info']
        tmdb_data = torrent_data.get('tmdb_data', {})
        
        description = f"**{media_info['title']}**\n\n"
        
        # Add basic info
        if media_info.get('year'):
            description += f"**Year:** {media_info['year']}\n"
        
        description += f"**Type:** {media_info['type']}\n"
        
        # Add technical details
        if media_info.get('resolution'):
            description += f"**Resolution:** {media_info['resolution']}\n"
        
        if media_info.get('video_codec'):
            description += f"**Video Codec:** {media_info['video_codec']}\n"
        
        if media_info.get('audio_codec'):
            description += f"**Audio Codec:** {media_info['audio_codec']}\n"
        
        if media_info.get('languages'):
            description += f"**Languages:** {', '.join(media_info['languages'])}\n"
        
        # Add TMDB info
        if tmdb_data and tmdb_data.get('overview'):
            description += f"\n**Overview:**\n{tmdb_data['overview']}\n"
        
        # Add genres
        if tmdb_data and tmdb_data.get('genres'):
            description += f"\n**Genres:** {', '.join(tmdb_data['genres'])}\n"
        
        # Add original info
        description += f"\n*Original source: qBittorrent ({torrent_data['torrent']['hash'][:8]})*"
        
        return description
    
    def _get_status_url(self, upload_id: Optional[str]) -> Optional[str]:
        """Get status check URL for upload"""
        if not upload_id:
            return None
        
        status_endpoint = self.config['endpoints'].get('status', '/status/{upload_id}')
        return self.config['base_url'] + status_endpoint.format(upload_id=upload_id)
    
    def check_upload_status(self, upload_id: str) -> Dict[str, Any]:
        """Check upload status"""
        if 'status' not in self.config['endpoints']:
            return {'status': 'unknown', 'message': 'Status endpoint not configured'}
        
        status_url = self._get_status_url(upload_id)
        if not status_url:
            return {'status': 'error', 'message': 'Could not create status URL'}
        
        try:
            response = self.session.get(status_url, timeout=self.config.get('timeout', 30))
            if response.status_code == 200:
                return response.json()
            else:
                return {'status': 'error', 'message': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


class MassUploader:
    """Main mass upload coordinator"""
    
    def __init__(self, config: Config, api_configs: Dict[str, Any]):
        self.config = config
        self.api_configs = api_configs
        self.clients = {}
        
        # Initialize API clients
        for tracker_name, tracker_config in api_configs.get('api_configs', {}).items():
            self.clients[tracker_name] = APIClient(tracker_config, tracker_name)
    
    def upload_all(self, tracker_name: Optional[str] = None, dry_run: bool = False) -> Dict[str, int]:
        """Upload all extracted torrents"""
        output_dir = Path(self.config.output.output_dir)
        
        if not output_dir.exists():
            raise FileNotFoundError(f"Output directory not found: {output_dir}")
        
        # Find all torrent directories
        torrent_dirs = [d for d in output_dir.iterdir() if d.is_dir() and (d / "metadata.json").exists()]
        
        if not torrent_dirs:
            logger.warning("No extracted torrents found")
            return {'total': 0, 'success': 0, 'failed': 0}
        
        results = {'total': len(torrent_dirs), 'success': 0, 'failed': 0}
        
        for torrent_dir in torrent_dirs:
            try:
                if self._upload_single_torrent(torrent_dir, tracker_name, dry_run):
                    results['success'] += 1
                else:
                    results['failed'] += 1
            except Exception as e:
                results['failed'] += 1
                logger.error(f"Failed to upload {torrent_dir.name}: {e}")
        
        return results
    
    def _upload_single_torrent(self, torrent_dir: Path, tracker_name: Optional[str], dry_run: bool) -> bool:
        """Upload a single torrent"""
        # Load metadata
        metadata_file = torrent_dir / "metadata.json"
        with open(metadata_file, 'r', encoding='utf-8') as f:
            torrent_data = json.load(f)
        
        # Find files
        files = {
            'torrent_file': None,
            'nfo_file': None
        }
        
        for file_path in torrent_dir.iterdir():
            if file_path.suffix == '.torrent':
                files['torrent_file'] = str(file_path)
            elif file_path.suffix == '.nfo':
                files['nfo_file'] = str(file_path)
        
        if not files['torrent_file']:
            logger.warning(f"No torrent file found in {torrent_dir}")
            return False
        
        # Determine which trackers to upload to
        if tracker_name:
            if tracker_name not in self.clients:
                logger.error(f"Tracker '{tracker_name}' not configured")
                return False
            clients_to_use = {tracker_name: self.clients[tracker_name]}
        else:
            clients_to_use = self.clients
        
        # Upload to each tracker
        success = True
        for name, client in clients_to_use.items():
            if dry_run:
                logger.info(f"DRY RUN: Would upload {torrent_data['media_info']['title']} to {name}")
                continue
            
            result = client.upload_torrent(torrent_data, files)
            
            if result.success:
                logger.info(f"Successfully uploaded {torrent_data['media_info']['title']} to {name}")
                if result.upload_id:
                    logger.info(f"Upload ID: {result.upload_id}")
            else:
                logger.error(f"Failed to upload to {name}: {result.message}")
                success = False
        
        return success
    
    def get_available_trackers(self) -> List[str]:
        """Get list of configured trackers"""
        return list(self.clients.keys())
    
    def check_upload_status(self, tracker_name: str, upload_id: str) -> Dict[str, Any]:
        """Check upload status for a specific tracker"""
        if tracker_name not in self.clients:
            raise ValueError(f"Tracker '{tracker_name}' not configured")
        
        return self.clients[tracker_name].check_upload_status(upload_id)
