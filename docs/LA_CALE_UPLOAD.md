# La Cale Mass Upload Documentation

## Overview

The La Cale mass upload system automatically uploads all extracted torrents from the output directory using the metadata.json files created during the extract phase. It intelligently maps fields from your extracted data to La Cale API requirements.

## Field Mapping

### Category Mapping
The system maps media types to La Cale categories:

| Media Type | Mapped Category |
|------------|-----------------|
| `movie`    | `movie`         |
| `tvshow`   | `tv_series`     |
| `anime`    | `anime`         |

The actual category IDs are determined by matching these names against La Cale's available categories.

### Tag Mapping
Tags are automatically extracted and mapped from multiple sources:

#### 1. Genre Tags (from TMDB)
- TMDB genres like "Action", "Comedy", "Drama" are mapped to tracker tags
- Common mappings: "Science Fiction" → "sci-fi", etc.

#### 2. Resolution Tags
| Extracted Resolution | Mapped Tag |
|---------------------|------------|
| `480p`, `576p`      | `sd`       |
| `720p`              | `720p`     |
| `1080p`             | `1080p`    |
| `2160p`, `4k`       | `4k`       |

#### 3. Video Codec Tags
| Extracted Codec | Mapped Tag |
|-----------------|------------|
| `x264`, `avc`   | `h264`     |
| `x265`, `hevc`  | `h265`     |
| `vc-1`          | `vc1`      |
| `mpeg2`         | `mpeg2`    |

#### 4. Audio Codec Tags
| Extracted Codec | Mapped Tag |
|-----------------|------------|
| `ac3`           | `ac3`      |
| `dts`           | `dts`      |
| `aac`           | `aac`      |
| `flac`          | `flac`     |
| `truehd`        | `truehd`   |
| `eac3`          | `eac3`     |
| `opus`          | `opus`     |

#### 5. Language Tags
| ISO Code | Mapped Language |
|----------|-----------------|
| `en`     | `english`       |
| `fr`     | `french`        |
| `es`     | `spanish`       |
| `de`     | `german`        |
| `it`     | `italian`       |
| `pt`     | `portuguese`    |
| `ru`     | `russian`       |
| `ja`     | `japanese`      |
| `ko`     | `korean`        |
| `zh`     | `chinese`       |
| `ar`     | `arabic`        |
| `hi`     | `hindi`         |

#### 6. HDR Tags
- HDR formats like `HDR10`, `Dolby Vision` are mapped directly

### Other Fields

#### Title
- Uses `torrent_data.name` from metadata, falls back to `media_info.title`

#### Description
- Uses TMDB overview if available
- Automatically adds technical details section:
  ```
  Technical Details:
  Resolution: 1080p
  Video: x265
  Audio: DTS
  Languages: english, french
  HDR: HDR10
  ```

#### TMDB Information
- **TMDB ID**: Extracted from `media_info.tmdb_id`
- **TMDB Type**: 
  - `movie` → "MOVIE"
  - `tvshow`, `anime` → "TV"

#### Files
- **Torrent file**: Automatically found in the same directory as metadata.json
- **NFO file**: Automatically included if present

## Usage

### 1. Dry Run (Recommended First)
Preview what would be uploaded without actually uploading:

```bash
python -m qbit2track.cli mass-upload-lacle --dry-run
```

This shows:
- How many torrents will be uploaded
- Category mappings
- Tag mappings
- All extracted metadata

### 2. Actual Mass Upload
```bash
python -m qbit2track.cli mass-upload-lacle
```

The system will:
1. Fetch La Cale categories and tags
2. Process each metadata.json file
3. Map fields appropriately
4. Upload each torrent with proper categorization and tagging
5. Show success/failure results

### 3. Custom Output Directory
```bash
python -m qbit2track.cli mass-upload-lacle --output-dir /path/to/output
```

## Example Output

### Dry Run Example
```
=== La Cale Mass Upload ===
Output directory: ./output
🔍 DRY RUN MODE - No actual uploads will be performed
Fetching La Cale metadata...
Found 15 categories and 42 tags
Found 3 torrents to process

=== Dry Run - What would be uploaded ===

📁 Movie.2023.1080p.BluRay.x264-GROUP
   Title: Movie.2023.1080p.BluRay.x264-GROUP
   Type: movie
   Category: Movies/1080p (1)
   Tags: action, adventure, 1080p, h264, english
   TMDB ID: 12345
   Resolution: 1080p
   Video Codec: x264
   Audio Codec: dts
   Languages: english

📁 TV.Show.S01.2023.1080p.WEB-DL.x265-GROUP
   Title: TV.Show.S01.2023.1080p.WEB-DL.x265-GROUP
   Type: tvshow
   Category: TV/HD (2)
   Tags: drama, 1080p, h265, english
   TMDB ID: 67890
   Resolution: 1080p
   Video Codec: x265
   Audio Codec: aac
   Languages: english

Dry run complete. 3 torrents ready for upload.
```

### Actual Upload Example
```
=== La Cale Mass Upload ===
Output directory: ./output
Fetching La Cale metadata...
Found 15 categories and 42 tags
Found 3 torrents to process
Starting mass upload...
INFO: Processing: Movie.2023.1080p.BluRay.x264-GROUP
INFO: ✅ Successfully uploaded: Movie.2023.1080p.BluRay.x264-GROUP
INFO:    Upload ID: abc123
INFO: Processing: TV.Show.S01.2023.1080p.WEB-DL.x265-GROUP
INFO: ✅ Successfully uploaded: TV.Show.S01.2023.1080p.WEB-DL.x265-GROUP
INFO:    Upload ID: def456
INFO: Mass upload complete: 2 success, 1 failed

=== Results ===
Total: 3
✅ Success: 2
❌ Failed: 1
```

## Error Handling

The system handles various error scenarios:

### Mapping Errors
- If category can't be mapped, the upload fails with a clear message
- If tags don't match, they're simply omitted (doesn't cause failure)

### File Errors
- Missing torrent file causes upload failure
- Missing NFO file is ignored (optional)

### API Errors
- Rate limiting: Automatic waiting and retry
- Invalid passkey: Clear error message
- Server errors: Detailed error reporting

## Rate Limiting

- La Cale allows 30 requests per minute
- The system includes automatic rate limiting
- Progress is logged during mass uploads

## Best Practices

1. **Always run dry-run first** to verify mappings
2. **Check the output** to ensure categories and tags map correctly
3. **Monitor logs** for any mapping issues
4. **Set your passkey** as environment variable for convenience:
   ```bash
   export LA_CALE_PASSKEY="your_passkey_here"
   ```

## Troubleshooting

### Category Not Found
If categories don't map correctly:
1. Run dry-run to see available categories
2. Check if your media types match expected values
3. Category names are matched using substring matching

### Tags Not Matching
If tags don't match:
1. Run dry-run to see available tags
2. Check tag mappings in the code
3. Tags use substring matching for flexibility

### Upload Failures
Common causes:
- Invalid passkey
- Missing torrent files
- Network issues
- Rate limiting (automatic retry should handle this)
