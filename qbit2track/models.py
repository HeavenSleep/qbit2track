"""
Data models for qbit2track
"""
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional


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
    languages: List[str] = field(default_factory=list)
    subtitles: List[str] = field(default_factory=list)
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    hdr: Optional[str] = None
    platform: Optional[str] = None
    is_multi_language: bool = False
    full_season: bool = False
    
    @property
    def is_4k(self) -> bool:
        """Check if resolution is 4K"""
        return self.resolution in ['2160p', '4K'] if self.resolution else False
    
    @property
    def is_hdr(self) -> bool:
        """Check if content has HDR"""
        return bool(self.hdr)
    
    @property
    def full_resolution(self) -> str:
        """Get full resolution string"""
        if not self.resolution:
            return "Unknown"
        if self.is_hdr and self.hdr:
            return f"{self.resolution} {self.hdr}"
        return self.resolution


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
    created_by: str
    created_at: datetime
    media_info: MediaInfo
    comment: Optional[str] = None
