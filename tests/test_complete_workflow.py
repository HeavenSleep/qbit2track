#!/usr/bin/env python3
"""
Complete workflow test for torrent creation, TMDB info, and NFO generation
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_data import TestDataManager, create_test_torrent_data
from qbit2track.nfo import NFOGenerator
from qbit2track.media.filename_analyzer import FilenameAnalyzer
from qbit2track.media.tmdb_matcher import TMDBMatcher
from qbit2track.torrent import TorrentManager
from qbit2track.models import TorrentData, MediaInfo
from qbit2track.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkflowTester:
    """Test the complete qbit2track workflow"""
    
    def __init__(self):
        self.test_data_manager = TestDataManager()
        self.test_output_dir = Path("test_output")
        self.test_output_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.nfo_generator = NFOGenerator()
        self.filename_analyzer = FilenameAnalyzer()
        self.torrent_manager = TorrentManager()
        
        # Try to initialize TMDB matcher (may fail without API key)
        try:
            config = Config.from_env()
            self.tmdb_matcher = TMDBMatcher(config)
            self.tmdb_available = True
        except Exception as e:
            logger.warning(f"TMDB not available: {e}")
            self.tmdb_matcher = None
            self.tmdb_available = False
    
    def run_complete_test(self):
        """Run complete workflow test"""
        logger.info("Starting complete workflow test...")
        logger.info("=" * 60)
        
        # Step 1: Download test videos
        logger.info("Step 1: Downloading test videos...")
        downloaded_videos = self.test_data_manager.download_test_videos(["4K", "1080p", "720p", "480p"])
        
        if not downloaded_videos:
            logger.error("No test videos downloaded. Cannot continue.")
            return False
        
        logger.info(f"Downloaded {len(downloaded_videos)} test videos")
        for resolution, path in downloaded_videos.items():
            logger.info(f"  {resolution}: {path}")
        
        # Step 2: Test filename analysis
        logger.info("\nStep 2: Testing filename analysis...")
        self._test_filename_analysis(downloaded_videos)
        
        # Step 3: Test TMDB matching (if available)
        if self.tmdb_available:
            logger.info("\nStep 3: Testing TMDB matching...")
            self._test_tmdb_matching(downloaded_videos)
        else:
            logger.info("\nStep 3: Skipping TMDB matching (not available)")
        
        # Step 4: Test NFO generation
        logger.info("\nStep 4: Testing NFO generation...")
        self._test_nfo_generation(downloaded_videos)
        
        # Step 5: Test torrent creation
        logger.info("\nStep 5: Testing torrent creation...")
        self._test_torrent_creation(downloaded_videos)
        
        logger.info("\n" + "=" * 60)
        logger.info("Complete workflow test finished successfully!")
        return True
    
    def _test_filename_analysis(self, downloaded_videos):
        """Test filename analysis on test videos"""
        for resolution, video_path in downloaded_videos.items():
            test_data = create_test_torrent_data(resolution, video_path)
            
            # Test filename analysis
            media_info = self.filename_analyzer.analyze_filename(
                test_data["name"], 
                test_data["category"],
                video_path
            )
            
            logger.info(f"Filename Analysis - {resolution}:")
            logger.info(f"  Title: {media_info.title}")
            logger.info(f"  Type: {media_info.type}")
            logger.info(f"  Resolution: {media_info.resolution}")
            logger.info(f"  Video Codec: {media_info.video_codec}")
            logger.info(f"  Audio Codec: {media_info.audio_codec}")
            logger.info(f"  Languages: {media_info.languages}")
    
    def _test_tmdb_matching(self, downloaded_videos):
        """Test TMDB matching"""
        for resolution, video_path in downloaded_videos.items():
            test_data = create_test_torrent_data(resolution, video_path)
            
            # Create media info for TMDB matching
            media_info = MediaInfo(
                title="Big Buck Bunny",
                type="movie",
                year=2008,
                resolution=test_data["resolution"],
                video_codec=test_data["video_codec"],
                audio_codec=test_data["audio_codec"],
                languages=test_data["languages"]
            )
            
            # Test TMDB matching
            tmdb_result = self.tmdb_matcher.match_media(media_info)
            
            logger.info(f"TMDB Matching - {resolution}:")
            if tmdb_result:
                logger.info(f"  Match: {tmdb_result.get('title', 'Unknown')}")
                logger.info(f"  TMDB ID: {tmdb_result.get('tmdb_id', 'Unknown')}")
                logger.info(f"  Year: {tmdb_result.get('release_date', 'Unknown')[:4] if tmdb_result.get('release_date') else 'Unknown'}")
                logger.info(f"  Overview: {tmdb_result.get('overview', 'No overview')[:100]}...")
            else:
                logger.info(f"  No match found")
    
    def _test_nfo_generation(self, downloaded_videos):
        """Test NFO generation"""
        for resolution, video_path in downloaded_videos.items():
            test_data = create_test_torrent_data(resolution, video_path)
            
            # Create torrent data
            media_info = MediaInfo(
                title=test_data["name"],
                type=test_data["type"],
                year=test_data["year"],
                resolution=test_data["resolution"],
                video_codec=test_data["video_codec"],
                audio_codec=test_data["audio_codec"],
                languages=test_data["languages"]
            )
            
            torrent_data = TorrentData(
                hash=f"test_{resolution.lower()}",
                name=test_data["name"],
                private=True,
                save_path=str(self.test_output_dir),
                content_path=str(video_path.parent),
                size=video_path.stat().st_size,
                files=[{'name': video_path.name, 'size': video_path.stat().st_size, 'path': str(video_path)}],
                tracker=['http://tracker.example.com/announce'],
                tags=test_data["tags"],
                category=test_data["category"],
                created_by='qbit2track-test',
                created_at=datetime.now(),
                media_info=media_info
            )
            
            # Generate NFO content
            nfo_content = self.nfo_generator.generate_nfo_content(
                torrent_data, 
                None,  # No TMDB data for this test
                video_path
            )
            
            # Save NFO file
            nfo_file = self.test_output_dir / f"BigBuckBunny_{resolution}.nfo"
            with open(nfo_file, 'w', encoding='utf-8') as f:
                f.write(nfo_content)
            
            logger.info(f"NFO Generation - {resolution}:")
            logger.info(f"  File: {nfo_file}")
            logger.info(f"  Size: {len(nfo_content)} characters")
            
            # Show a preview
            lines = nfo_content.split('\n')[:10]
            logger.info(f"  Preview:")
            for line in lines:
                if line.strip():
                    logger.info(f"    {line}")
    
    def _test_torrent_creation(self, downloaded_videos):
        """Test torrent creation"""
        for resolution, video_path in downloaded_videos.items():
            test_data = create_test_torrent_data(resolution, video_path)
            
            # Create torrent data
            media_info = MediaInfo(
                title=test_data["name"],
                type=test_data["type"],
                year=test_data["year"],
                resolution=test_data["resolution"],
                video_codec=test_data["video_codec"],
                audio_codec=test_data["audio_codec"],
                languages=test_data["languages"]
            )
            
            torrent_data = TorrentData(
                hash=f"test_{resolution.lower()}",
                name=test_data["name"],
                private=True,
                save_path=str(self.test_output_dir),
                content_path=str(video_path),
                size=video_path.stat().st_size,
                files=[{'name': video_path.name, 'size': video_path.stat().st_size, 'path': str(video_path)}],
                tracker=['http://tracker.example.com/announce'],
                tags=test_data["tags"],
                category=test_data["category"],
                created_by='qbit2track-test',
                created_at=datetime.now(),
                media_info=media_info
            )
            
            # Create torrent file
            try:
                torrent_file = self.torrent_manager.create_torrent_file(torrent_data, self.test_output_dir)
                logger.info(f"Torrent Creation - {resolution}:")
                logger.info(f"  File: {torrent_file}")
                logger.info(f"  Size: {torrent_file.stat().st_size} bytes")
            except Exception as e:
                logger.error(f"Failed to create torrent for {resolution}: {e}")
    
    def cleanup(self):
        """Clean up test files"""
        logger.info("Cleaning up test files...")
        
        # Clean up test data
        self.test_data_manager.cleanup_test_data()
        
        # Clean up test output
        for file_path in self.test_output_dir.glob("*"):
            try:
                if file_path.is_file():
                    file_path.unlink()
                    logger.info(f"Cleaned up: {file_path}")
            except Exception as e:
                logger.error(f"Failed to cleanup {file_path}: {e}")


def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test complete qbit2track workflow")
    parser.add_argument("--cleanup", action="store_true", help="Clean up test files only")
    parser.add_argument("--keep", action="store_true", help="Keep test files after testing")
    
    args = parser.parse_args()
    
    tester = WorkflowTester()
    
    if args.cleanup:
        tester.cleanup()
        return
    
    try:
        success = tester.run_complete_test()
        
        if not args.keep:
            tester.cleanup()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        if not args.keep:
            tester.cleanup()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        if not args.keep:
            tester.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
