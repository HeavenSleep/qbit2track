"""
Debug tools for qbit2track development and troubleshooting
"""

import logging
import sys
from pathlib import Path

from .config import Config
from .extractor import MediaAnalyzer, TMDBMatcher
import torf

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_tmdb():
    """Test TMDB API functionality"""
    print("=== Testing TMDB API ===")
    
    try:
        config = Config.from_env()
        print(f"TMDB API Key: {'***' if config.tmdb.api_key else 'Not set'}")
        
        if not config.tmdb.api_key:
            print("ERROR: TMDB_API_KEY not set")
            return
        
        matcher = TMDBMatcher(config.tmdb.api_key)
        
        # Test movie search
        print("\n--- Testing movie search ---")
        media_info = type('MediaInfo', (), {
            'title': 'Iron Man',
            'year': 2008,
            'type': 'movie'
        })()
        
        result = matcher.match_media(media_info)
        if result:
            print(f"✓ Found movie: {result.get('title')} (TMDB ID: {result.get('tmdb_id')})")
        else:
            print("✗ Movie search failed")
        
        # Test TV show search
        print("\n--- Testing TV show search ---")
        media_info = type('MediaInfo', (), {
            'title': 'Andor',
            'year': 2022,
            'type': 'tvshow'
        })()
        
        result = matcher.match_media(media_info)
        if result:
            print(f"✓ Found TV show: {result.get('title')} (TMDB ID: {result.get('tmdb_id')})")
        else:
            print("✗ TV show search failed")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


def test_torrent():
    """Test torrent creation functionality"""
    print("=== Testing Torrent Creation ===")
    
    try:
        # Create a test torrent
        test_path = Path("./test_torrent_data")
        test_path.mkdir(exist_ok=True)
        
        # Create a test file
        test_file = test_path / "test_video.mkv"
        test_file.write_text("This is test content for torrent creation")
        
        print(f"Creating torrent from: {test_path}")
        
        torrent = torf.Torrent(
            path=test_path,
            name="Test Torrent",
            private=False,
            source="qbit2track test"
        )
        
        # Add a test tracker
        torrent.trackers.add("http://tracker.example.com/announce")
        
        print("Generating torrent...")
        torrent.generate(callback=torf.CLI_CALLBACK(), interval=1)
        
        # Save torrent
        torrent_file = Path("test_output.torrent")
        torrent.write(torrent_file)
        
        print(f"✓ Torrent created: {torrent_file}")
        print(f"  Info hash: {torrent.infohash}")
        print(f"  Size: {torrent.size} bytes")
        
        # Cleanup
        torrent_file.unlink(missing_ok=True)
        test_file.unlink(missing_ok=True)
        test_path.rmdir()
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


def test_analyzer(filename):
    """Test media analyzer functionality"""
    print(f"=== Testing Media Analyzer ===")
    print(f"Analyzing: {filename}")
    
    try:
        analyzer = MediaAnalyzer()
        
        media_info = analyzer.analyze_filename(filename, "tvshows")
        
        print(f"Title: {media_info.title}")
        print(f"Type: {media_info.type}")
        print(f"Year: {media_info.year}")
        print(f"Resolution: {media_info.resolution}")
        print(f"Video Codec: {media_info.video_codec}")
        print(f"Audio Codec: {media_info.audio_codec}")
        print(f"Languages: {media_info.languages}")
        print(f"Season: {media_info.season}")
        print(f"Episode: {media_info.episode}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


def test_connection():
    """Test qBittorrent connection"""
    print("=== Testing qBittorrent Connection ===")
    
    try:
        config = Config.from_env()
        print(f"Connecting to: {config.qbit.url}")
        
        from qbittorrentapi import Client
        client = Client(
            host=config.qbit.url,
            username=config.qbit.username,
            password=config.qbit.password
        )
        
        # Test connection
        client.auth_log_in()
        print("✓ Connection successful")
        
        # Get torrent list
        torrents = client.torrents.info()
        print(f"Found {len(torrents)} torrents")
        
        # Show first few torrents
        for i, torrent in enumerate(torrents[:3]):
            print(f"  {i+1}. {torrent.name} ({torrent.size} bytes)")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_tools.py <command> [args]")
        print("Commands:")
        print("  test_tmdb      - Test TMDB API")
        print("  test_torrent   - Test torrent creation")
        print("  test_analyzer  <filename> - Test media analyzer")
        print("  test_connection - Test qBittorrent connection")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "test_tmdb":
        test_tmdb()
    elif command == "test_torrent":
        test_torrent()
    elif command == "test_analyzer":
        if len(sys.argv) < 3:
            print("Error: test_analyzer requires a filename argument")
            sys.exit(1)
        test_analyzer(sys.argv[2])
    elif command == "test_connection":
        test_connection()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
