"""
Test data management for downloading test videos
"""
import logging
import requests
import zipfile
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
import hashlib

logger = logging.getLogger(__name__)


class TestDataManager:
    """Manage test video downloads for testing purposes"""
    
    # Big Buck Bunny test videos from Blender Foundation
    BIG_BUCK_BUNNY_VIDEOS = {
        "4K": {
            "url": "https://download.blender.org/demo/movies/BBB/bbb_sunflower_2160p_30fps_normal.mp4.zip",
            "filename": "BigBuckBunny_4K.mp4",
            "expected_size": 1073741824,  # ~1GB (ZIP compressed)
            "resolution": "3840x2160",
            "codec": "H264",
            "is_zip": True
        },
        "1080p": {
            "url": "https://download.blender.org/demo/movies/BBB/bbb_sunflower_1080p_30fps_normal.mp4.zip",
            "filename": "BigBuckBunny_1080p.mp4", 
            "expected_size": 536870912,  # ~512MB (ZIP compressed)
            "resolution": "1920x1080",
            "codec": "H264",
            "is_zip": True
        },
        "720p": {
            "url": "https://download.blender.org/peach/bigbuckbunny_movies/big_buck_bunny_720p_stereo.avi",
            "filename": "BigBuckBunny_720p.avi",
            "expected_size": 268435456,  # ~256MB
            "resolution": "1280x720", 
            "codec": "XVID",
            "is_zip": False
        },
        "480p": {
            "url": "https://download.blender.org/peach/bigbuckbunny_movies/big_buck_bunny_480p_stereo.avi",
            "filename": "BigBuckBunny_480p.avi",
            "expected_size": 134217728,  # ~128MB
            "resolution": "854x480",
            "codec": "XVID",
            "is_zip": False
        }
    }
    
    def __init__(self, test_data_dir: Path = None):
        self.test_data_dir = test_data_dir or Path("test_data")
        self.test_data_dir.mkdir(exist_ok=True)
    
    def download_test_videos(self, resolutions: List[str] = None) -> dict:
        """Download Big Buck Bunny test videos in specified resolutions"""
        if resolutions is None:
            resolutions = ["4K", "1080p", "720p", "480p"]
        
        downloaded_files = {}
        
        for resolution in resolutions:
            if resolution not in self.BIG_BUCK_BUNNY_VIDEOS:
                logger.warning(f"Unknown resolution: {resolution}")
                continue
            
            video_info = self.BIG_BUCK_BUNNY_VIDEOS[resolution]
            file_path = self.test_data_dir / video_info["filename"]
            
            if file_path.exists():
                # Verify file integrity
                if self._verify_file_integrity(file_path, video_info):
                    logger.info(f"Test video already exists and verified: {file_path}")
                    downloaded_files[resolution] = file_path
                    continue
                else:
                    logger.warning(f"Test video exists but failed integrity check, re-downloading: {file_path}")
                    file_path.unlink()
            
            logger.info(f"Downloading {resolution} test video...")
            downloaded_file = self._download_file(video_info["url"], file_path, video_info.get("is_zip", False))
            
            if downloaded_file:
                downloaded_files[resolution] = downloaded_file
            else:
                logger.error(f"Failed to download {resolution} test video")
        
        return downloaded_files
    
    def _download_file(self, url: str, file_path: Path, is_zip: bool = False) -> Optional[Path]:
        """Download a file with progress tracking and ZIP extraction"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # Download to temporary file first
            temp_file = file_path.with_suffix('.tmp')
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log progress every 10MB
                        if downloaded % (10 * 1024 * 1024) == 0:
                            progress = (downloaded / total_size * 100) if total_size > 0 else 0
                            logger.info(f"Downloaded {downloaded / (1024*1024):.1f}MB ({progress:.1f}%)")
            
            # Handle ZIP extraction
            if is_zip:
                logger.info(f"Extracting ZIP file: {temp_file}")
                with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                    # Find the MP4 file inside the ZIP
                    mp4_files = [f for f in zip_ref.namelist() if f.endswith('.mp4')]
                    if mp4_files:
                        zip_ref.extract(mp4_files[0], self.test_data_dir)
                        extracted_file = self.test_data_dir / mp4_files[0]
                        # Rename to expected filename
                        extracted_file.rename(file_path)
                        temp_file.unlink()
                        logger.info(f"Successfully extracted: {file_path}")
                        return file_path
                    else:
                        logger.error("No MP4 file found in ZIP archive")
                        temp_file.unlink()
                        return None
            else:
                # Move temp file to final location
                temp_file.rename(file_path)
                logger.info(f"Successfully downloaded: {file_path}")
                return file_path
            
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            # Clean up temp file if it exists
            temp_file = file_path.with_suffix('.tmp')
            if temp_file.exists():
                temp_file.unlink()
            return None
    
    def _verify_file_integrity(self, file_path: Path, video_info: dict) -> bool:
        """Verify downloaded file integrity"""
        try:
            actual_size = file_path.stat().st_size
            expected_size = video_info["expected_size"]
            
            # Allow 10% size variance (different actual file sizes)
            size_variance = abs(actual_size - expected_size) / expected_size
            
            if size_variance > 0.10:  # 10% variance threshold
                logger.warning(f"File size variance too high: {size_variance:.2%}")
                return False
            
            # Basic file header check (MP4 or AVI)
            with open(file_path, 'rb') as f:
                header = f.read(12)
                if video_info["filename"].endswith('.mp4'):
                    if not header.startswith(b'\x00\x00\x00\x18ftypmp4'):
                        logger.warning("File does not appear to be a valid MP4 file")
                        return False
                elif video_info["filename"].endswith('.avi'):
                    if not header.startswith(b'RIFF') or b'AVI ' not in header[:12]:
                        logger.warning("File does not appear to be a valid AVI file")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying file integrity: {e}")
            return False
    
    def get_test_video_info(self, resolution: str) -> Optional[dict]:
        """Get test video information for a specific resolution"""
        return self.BIG_BUCK_BUNNY_VIDEOS.get(resolution)
    
    def list_downloaded_videos(self) -> dict:
        """List all downloaded test videos"""
        downloaded = {}
        
        for resolution, video_info in self.BIG_BUCK_BUNNY_VIDEOS.items():
            file_path = self.test_data_dir / video_info["filename"]
            if file_path.exists():
                downloaded[resolution] = {
                    "path": file_path,
                    "size": file_path.stat().st_size,
                    "info": video_info
                }
        
        return downloaded
    
    def cleanup_test_data(self):
        """Clean up all test data"""
        for file_path in self.test_data_dir.glob("*.mp4"):
            try:
                file_path.unlink()
                logger.info(f"Cleaned up: {file_path}")
            except Exception as e:
                logger.error(f"Failed to cleanup {file_path}: {e}")


def create_test_torrent_data(resolution: str, video_path: Path) -> dict:
    """Create test torrent data for a specific resolution"""
    video_info = TestDataManager.BIG_BUCK_BUNNY_VIDEOS.get(resolution, {})
    
    return {
        "name": f"Big Buck Bunny {resolution} - Test Video",
        "resolution": resolution,
        "video_codec": video_info.get("codec", "H264"),
        "audio_codec": "AAC",  # Default assumption
        "languages": ["English"],
        "year": 2008,
        "type": "movie",
        "file_path": video_path,
        "category": "Movies/HD",
        "tags": [resolution.lower(), "test", "bigbuckbunny"]
    }
