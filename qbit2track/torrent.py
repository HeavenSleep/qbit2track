"""
Torrent file creation and management
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import torf

from .models import TorrentData
from .utils import CustomJSONEncoder


logger = logging.getLogger(__name__)


class TorrentManager:
    """Handle torrent file creation and management"""
    
    def __init__(self):
        pass
    
    def create_torrent_file(self, torrent_data: TorrentData, output_dir: Path):
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
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove consecutive underscores
        filename = '_'.join(filter(None, filename.split('_')))
        
        return filename


class MetadataManager:
    """Handle metadata JSON files"""
    
    def __init__(self):
        pass
    
    def save_metadata(self, torrent_data: TorrentData, output_dir: Path, tmdb_data: Optional[Dict]):
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
            json.dump(metadata, f, indent=2, cls=CustomJSONEncoder, ensure_ascii=False)
        
        logger.debug(f"Saved metadata: {metadata_file}")
    
    def load_metadata(self, metadata_file: Path) -> Dict:
        """Load metadata from JSON file with datetime decoding"""
        from .utils import custom_json_decoder
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            # Use object_hook to decode datetime strings
            return json.load(f, object_hook=custom_json_decoder)
