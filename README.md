# qbit2track

A powerful Python tool for extracting torrent metadata from qBittorrent and preparing torrents for migration to private trackers.

## Features

- **Torrent Extraction**: Extract torrents from qBittorrent with full metadata
- **Media Analysis**: Automatic detection of resolution, codecs, languages, subtitles
- **TMDB Integration**: Automatic movie/TV show matching with TheMovieDB
- **NFO Generation**: Create NFO files with complete media information
- **Metadata Updates**: Update tracker, comment, tags, and category during extraction
- **Batch Processing**: Process multiple torrents with filtering options
- **Caching**: File-based caching for TMDB lookups to reduce API calls
- **CLI Interface**: Easy-to-use command-line interface

### Prerequisites

- Python 3.8+
- qBittorrent with Web UI enabled
- TheMovieDB API key

### Install from source

```bash
git clone https://github.com/yourusername/qbit2track.git
cd qbit2track
pip install -r requirements.txt
pip install -e .
```

### Dependencies

- `torf` - Torrent file creation
- `tmdbv3api` - TheMovieDB API client
- `qbittorrent-api` - qBittorrent API client
- `pyyaml` - YAML configuration support
- `click` - CLI framework
- `requests` - HTTP requests
- `python-dotenv` - Environment variable management

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# qBittorrent Connection
QBIT_HOST=localhost
QBIT_PORT=8080
QBIT_USERNAME=admin
QBIT_PASSWORD=adminadmin
QBIT_USE_HTTPS=false

# TheMovieDB API
TMDB_API_KEY=your_tmdb_api_key_here
TMDB_LANGUAGE=en

# Output Configuration
OUTPUT_DIR=./output
CREATE_NFO=true
CREATE_TORRENT=true

# Logging
LOG_LEVEL=INFO

# Application Settings
MULTI_LANGUAGE=Multi
CACHE_EXPIRY=86400
```

### qBittorrent Setup

1. Enable Web UI in qBittorrent: **Tools → Options → Web UI**
2. Make sure "Web User Interface" is enabled
3. Note your username and password
4. Ensure the port is accessible (default: 8080)

## Usage

### Basic Commands

#### Show qBittorrent Info
```bash
qbit2track info
```

#### Extract All Torrents (Dry Run)
```bash
qbit2track extract --dry-run
```

#### Extract with Updates
```bash
# Update tracker for all extracted torrents
qbit2track extract --update-tracker "https://private-tracker.com/announce?passkey=xxx"

# Update multiple fields
qbit2track extract \
  --update-tracker "https://tracker.com/announce?passkey=xxx" \
  --update-comment "Prepared for private tracker" \
  --update-tags "movie,1080p,ready" \
  --update-category "movies"
```

#### Filter by Category or Tags
```bash
# Extract only movies
qbit2track extract --filter-category "movies"

# Extract specific tags
qbit2track extract --filter-tags "tv,series"

# Combine filters with updates
qbit2track extract --filter-category "movies" --update-tracker "https://tracker.com"
```

#### Cache Management
```bash
# Show cache statistics
qbit2track cache stats

# Clear cache
qbit2track cache clear
```

### Command Reference

#### `extract`
Extract torrents from qBittorrent with optional updates.

**Options:**
- `--output-dir, -o`: Output directory for extracted files
- `--filter-tags`: Filter torrents by tags (comma-separated)
- `--filter-category`: Filter torrents by category
- `--dry-run`: Show what would be extracted without doing it
- `--update-tracker`: Update tracker for all extracted torrents
- `--update-comment`: Update comment for all extracted torrents
- `--update-tags`: Update tags for all extracted torrents (comma-separated)
- `--update-category`: Update category for all extracted torrents

#### `info`
Display qBittorrent connection and configuration information.

#### `cache`
Manage TMDB cache.
- `cache stats`: Show cache statistics
- `cache clear`: Clear TMDB cache

## Output Structure

For each extracted torrent, the following files are created:

```
output/
├── Torrent Name/
│   ├── Torrent Name.torrent     # New torrent file
│   ├── Torrent Name.nfo         # NFO file with metadata
│   └── metadata.json           # Complete metadata
```

### Metadata JSON Structure

```json
{
  "torrent": {
    "hash": "...",
    "name": "...",
    "private": false,
    "save_path": "...",
    "content_path": "...",
    "size": 1234567890,
    "category": "movies",
    "tags": ["tag1", "tag2"],
    "comment": "...",
    "tracker": ["..."]
  },
  "media_info": {
    "title": "Movie Title",
    "year": 2023,
    "type": "movie",
    "resolution": "2160p",
    "video_codec": "x265",
    "audio_codec": "DDP 5.1",
    "languages": ["en", "fr"],
    "subtitles": ["en", "fr"],
    "tmdb_id": 123456,
    "imdb_id": "tt1234567"
  },
  "tmdb_data": {
    "title": "...",
    "overview": "...",
    "release_date": "...",
    "poster_path": "...",
    "backdrop_path": "..."
  },
  "files": [
    {
      "name": "file.mkv",
      "size": 1234567890,
      "path": "/path/to/file.mkv"
    }
  ]
}
```

## Media Detection

The tool automatically detects:

### Video Information
- **Resolution**: 480p, 720p, 1080p, 2160p (4K)
- **Video Codecs**: H.264, x265 (H.265), AV1, etc.
- **HDR**: HDR10, HDR10+, Dolby Vision
- **Source**: BluRay, WEB-DL, WEBRip, etc.

### Audio Information
- **Audio Codecs**: AC3, DTS, DDP, AAC, etc.
- **Channels**: 2.0, 5.1, 7.1, Atmos

### Languages & Subtitles
- **Languages**: English (en), French (fr), German (de), Spanish (es), etc.
- **Subtitles**: Extracted from filename patterns

### Content Type
- **Movies**: Single files or movie folders
- **TV Shows**: Season/episode detection
- **Anime**: Special anime detection

## Supported Media Types

- **Movies**: Automatically matched with TMDB movie database
- **TV Shows**: Matched with TMDB TV database, supports season/episode detection
- **Anime**: Treated as TV shows with special handling for anime naming patterns

## Detected Technical Information

- **Resolution**: 4K, 2160p, 1080p, 720p, 480p, 360p
- **Video Codecs**: x264, x265, H.264, H.265, HEVC, AV1, VP9, XViD
- **Audio Codecs**: AAC, AC3, DTS, TrueHD, FLAC, MP3, Opus
- **Languages**: Auto-detected from filenames and metadata
- **Subtitles**: Detected from file contents and metadata

## API Configuration Examples

### API Key Authentication
```yaml
auth:
  type: "api_key"
  api_key: "your_api_key_here"
```

### Basic Authentication
```yaml
auth:
  type: "basic"
  username: "your_username"
  password: "your_password"
```

### Bearer Token Authentication
```yaml
auth:
  type: "bearer"
  token: "your_bearer_token"
```

## Rate Limiting

The tool includes built-in rate limiting to respect tracker API limits:
- **Requests per minute**: Configurable limit (default: 30)
- **Burst size**: Maximum requests in short period (default: 5)
- **Automatic waiting**: Tool waits when limits are reached
- **Retry logic**: Exponential backoff for failed requests

## Error Handling

- **Connection errors**: Automatic retry with exponential backoff
- **Rate limiting**: Automatic waiting and retry
- **Invalid data**: Skips problematic files and continues processing
- **Detailed logging**: Comprehensive logging for troubleshooting

## Troubleshooting

### Common Issues

1. **qBittorrent Connection Failed**
   - Check that qBittorrent Web UI is enabled
   - Verify host, port, username, and password
   - Ensure no firewall is blocking the connection

2. **TMDB API Errors**
   - Verify your TMDB API key is valid
   - Check if you've exceeded API rate limits
   - Ensure network connectivity to TMDB servers

3. **Upload Failures**
   - Check tracker API configuration in `api_config.yaml`
   - Verify authentication credentials
   - Review rate limiting settings

### Debug Mode
Enable verbose logging for troubleshooting:

```bash
qbit2track --verbose extract --dry-run
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the Mozilla Public License 2.0 (MPL 2.0).

### What this means:
- ✅ **Free to use**: Anyone can use the software for any purpose
- ✅ **Free to modify**: Source code can be modified and improved
- ✅ **Free to distribute**: Can share original or modified versions
- ✅ **Commercial use allowed**: Can be used in commercial projects
- ❌ **No commercial resale**: Cannot sell the software as a standalone product
- ✅ **Patent protection**: Users are protected from patent claims
- ✅ **Source disclosure**: Modifications must be shared if distributed

### Commercial Restrictions:
- You cannot sell qbit2track as a standalone commercial product
- You must maintain the MPL 2.0 license in derivative works
- If you modify and distribute, you must share the source changes

For full license text, see [LICENSE](LICENSE) file or visit https://www.mozilla.org/en-US/MPL/2.0/

## Disclaimer

This tool is for educational and personal use only. Users are responsible for complying with the terms of service of any trackers they upload to and for respecting copyright laws in their jurisdiction.

## Examples

### Prepare Movies for Private Tracker
```bash
qbit2track extract \
  --filter-category "movies" \
  --update-tracker "https://private-tracker.com/announce?passkey=xxx" \
  --update-comment "Uploaded by qbit2track" \
  --update-tags "movie,2160p,hdr"
```

### Prepare TV Series
```bash
qbit2track extract \
  --filter-tags "tv,series" \
  --update-tracker "https://tv-tracker.com/announce?passkey=xxx" \
  --update-category "tv-series" \
  --update-tags "tv,1080p,complete"
```

### Dry Run Before Actual Extraction
```bash
qbit2track extract --dry-run --filter-category "movies"
```

## Debugging

### VS Code Debug Configuration

The project includes debug configurations in `.vscode/launch.json`:

- **qbit2track info**: Test qBittorrent connection
- **qbit2track extract**: Run extraction with dry run
- **TMDB Test**: Test TMDB API connection
- **Torrent Creation Test**: Test torrent file creation
- **Media Analyzer Test**: Test media analysis

### Debug Tools

Use the debug tools module:

```python
from qbit2track.debug_tools import DebugTools

debug = DebugTools()
debug.test_tmdb_connection()
debug.test_torrent_creation()
debug.test_media_analyzer()
```

### Logging

Set log level in `.env`:
```env
LOG_LEVEL=DEBUG
```

Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## Troubleshooting

### Common Issues

#### Connection Errors
```
InvalidRequest400Error: The plain HTTP request was sent to HTTPS port
```
**Solution**: Set `QBIT_USE_HTTPS=true` if using HTTPS, or ensure port is correct.

#### TMDB API Errors
```
TMDB match failed: API key not found
```
**Solution**: Verify your TMDB API key in `.env`.

#### File Not Found Errors
```
No such file or directory
```
**Solution**: Ensure torrent files exist in the expected paths in qBittorrent.

#### Permission Errors
```
Permission denied
```
**Solution**: Check file permissions and ensure qBittorrent can access the files.

### Cache Issues

If TMDB lookups are failing or returning stale data:

```bash
qbit2track cache clear
```

### Getting Help

1. Check the logs for detailed error messages
2. Use `--dry-run` to test without making changes
3. Verify qBittorrent connection with `qbit2track info`
4. Check TMDB API key and connection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Changelog

### v1.0.0
- Initial release
- Torrent extraction from qBittorrent
- Media analysis and TMDB integration
- NFO and metadata generation
- CLI interface
- Caching system
- Update functionality during extraction

## Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the debug output
