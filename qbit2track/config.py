"""
Configuration management for qbit2track
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class QBitConfig:
    """qBittorrent connection configuration"""
    host: str = field(default_factory=lambda: os.getenv("QBIT_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("QBIT_PORT", "8080")))
    username: str = field(default_factory=lambda: os.getenv("QBIT_USERNAME", "admin"))
    password: str = field(default_factory=lambda: os.getenv("QBIT_PASSWORD", "adminadmin"))
    use_https: bool = field(default_factory=lambda: os.getenv("QBIT_USE_HTTPS", "false").lower() == "true")
    
    @property
    def url(self) -> str:
        scheme = "https" if self.use_https or self.port == 443 else "http"
        return f"{scheme}://{self.host}:{self.port}"


@dataclass
class TMDBConfig:
    """TheMovieDB API configuration"""
    api_key: str = field(default_factory=lambda: os.getenv("TMDB_API_KEY", ""))
    language: str = field(default_factory=lambda: os.getenv("TMDB_LANGUAGE", "en"))
    
    def __post_init__(self):
        if not self.api_key:
            raise ValueError("TMDB_API_KEY environment variable is required")


@dataclass
class OutputConfig:
    """Output configuration"""
    output_dir: str = field(default_factory=lambda: os.getenv("OUTPUT_DIR", "./output"))
    create_nfo: bool = field(default_factory=lambda: os.getenv("CREATE_NFO", "true").lower() == "true")
    create_torrent: bool = field(default_factory=lambda: os.getenv("CREATE_TORRENT", "true").lower() == "true")
    
    def __post_init__(self):
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

@dataclass
class AppConfig:
    """Application configuration"""
    multi_language: str = field(default_factory=lambda: os.getenv("MULTI_LANGUAGE", "Multi"))
    cache_expiry: int = field(default_factory=lambda: int(os.getenv("CACHE_EXPIRY", "86400")))
    default_team: str = field(default_factory=lambda: os.getenv("Q2T_DEFAULT_TEAM", "Q2TBHV"))


@dataclass
class Config:
    """Main configuration class"""
    qbit: QBitConfig = field(default_factory=QBitConfig)
    tmdb: TMDBConfig = field(default_factory=TMDBConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    app: AppConfig = field(default_factory=AppConfig)
    
    @classmethod
    def load_api_config(cls, config_path: str = "config/api_config.yaml") -> Dict[str, Any]:
        """Load API configuration from YAML file"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"API config file not found: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Create configuration from environment variables"""
        return cls()
