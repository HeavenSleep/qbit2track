"""
Command-line interface for qbit2track
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

import click

from .config import Config
from .extractor import TorrentExtractor
from .uploader import MassUploader
from .utils import line_separator


@click.group()
@click.option('--config', '-c', help='Path to configuration file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config: Optional[str], verbose: bool):
    """qbit2track - Extract torrents from qBittorrent and prepare for private tracker upload"""
    ctx.ensure_object(dict)
    
    # Setup logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    ctx.obj['config'] = Config.from_env()


@cli.command()
@click.option('--output-dir', '-o', help='Output directory for extracted files')
@click.option('--filter-tags', help='Filter torrents by tags (comma-separated)')
@click.option('--filter-category', help='Filter torrents by category')
@click.option('--dry-run', is_flag=True, help='Show what would be extracted without doing it')
@click.option('--update-tracker', help='Update tracker for all extracted torrents')
@click.option('--update-comment', help='Update comment for all extracted torrents')
@click.option('--update-tags', help='Update tags for all extracted torrents (comma-separated)')
@click.option('--update-category', help='Update category for all extracted torrents')
@click.pass_context
def extract(ctx, output_dir: Optional[str], filter_tags: Optional[str], filter_category: Optional[str], 
           dry_run: bool, update_tracker: Optional[str], update_comment: Optional[str], 
           update_tags: Optional[str], update_category: Optional[str]):
    """Extract torrents from qBittorrent"""
    config = ctx.obj['config']
    
    if output_dir:
        config.output.output_dir = output_dir
    
    extractor = TorrentExtractor(config)
    
    click.echo("Starting torrent extraction...")
    
    if dry_run:
        click.echo("DRY RUN MODE - No files will be created")
    
    try:
        results = extractor.extract_all(
            tags=filter_tags.split(',') if filter_tags else None,
            category=filter_category,
            dry_run=dry_run,
            update_tracker=update_tracker,
            update_comment=update_comment,
            update_tags=update_tags.split(',') if update_tags else None,
            update_category=update_category
        )
        
        # Insert full width separator line without wrapping
        click.echo(line_separator("Results"))
        click.echo(f"Extraction complete. Processed {results['success'] + results['failed']} torrents.")
        click.echo(f"Success: {results['success']}, Failed: {results['failed']}")
        
        # Show update summary if any updates were applied
        if any([update_tracker, update_comment, update_tags, update_category]):
            click.echo("\nUpdate Summary:")
            if update_tracker:
                click.echo(f"  Tracker updated to: {update_tracker}")
            if update_comment:
                click.echo(f"  Comment updated to: {update_comment}")
            if update_tags:
                click.echo(f"  Tags updated to: {update_tags}")
            if update_category:
                click.echo(f"  Category updated to: {update_category}")
        
    except Exception as e:
        click.echo(f"Error during extraction: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--api-config', '-a', default='config/api_config.yaml', 
              help='Path to API configuration file')
@click.option('--tracker', '-t', help='Specific tracker to upload to')
@click.option('--input-dir', '-i', help='Input directory with extracted files')
@click.option('--dry-run', is_flag=True, help='Show what would be uploaded without doing it')
@click.pass_context
def upload(ctx, api_config: str, tracker: Optional[str], 
          input_dir: Optional[str], dry_run: bool):
    """Mass upload extracted torrents to private tracker API"""
    config = ctx.obj['config']
    
    if input_dir:
        config.output.output_dir = input_dir
    
    try:
        api_configs = Config.load_api_config(api_config)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    
    uploader = MassUploader(config, api_configs)
    
    click.echo("Starting mass upload...")
    
    if dry_run:
        click.echo("DRY RUN MODE - No uploads will be performed")
    
    try:
        results = uploader.upload_all(
            tracker_name=tracker,
            dry_run=dry_run
        )
        
        click.echo(line_separator("Results"))
        click.echo(f"Upload complete. Processed {results['total']} torrents.")
        click.echo(f"Success: {results['success']}, Failed: {results['failed']}")
        
    except Exception as e:
        click.echo(f"Error during upload: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.pass_context
def info(ctx):
    """Show configuration and connection information"""
    config = ctx.obj['config']
    
    click.echo(line_separator("qbit2track Configuration"))
    click.echo(f"qBittorrent URL: {config.qbit.url}")
    click.echo(f"Username: {config.qbit.username}")
    click.echo(f"Output Directory: {config.output.output_dir}")
    click.echo(f"Create NFO: {config.output.create_nfo}")
    click.echo(f"Create Torrent: {config.output.create_torrent}")
    click.echo(f"TMDB API Key: {'***' if config.tmdb.api_key else 'Not set'}")
    click.echo(f"Multi Language: {config.app.multi_language}")
    click.echo(f"Log Level: {config.logging.level}")


@cli.group()
def cache():
    """Cache management commands"""
    pass


@cli.command()
@click.option('--passkey', prompt=True, hide_input=True, help='La Cale API passkey')
@click.option('--title', help='Torrent title')
@click.option('--category-id', help='Category ID')
@click.option('--torrent-file', type=click.Path(exists=True), help='Path to .torrent file')
@click.option('--description', help='Torrent description')
@click.option('--tmdb-id', help='TMDB ID')
@click.option('--tmdb-type', type=click.Choice(['MOVIE', 'TV']), help='TMDB type (MOVIE or TV)')
@click.option('--cover-url', help='Cover image URL (HTTPS only)')
@click.option('--tags', help='Comma-separated list of tag IDs')
@click.option('--nfo-file', type=click.Path(exists=True), help='Path to .nfo file')
def test_lacle(passkey, title, category_id, torrent_file, description, tmdb_id, tmdb_type, cover_url, tags, nfo_file):
    """Test La Cale upload functionality"""
    from .uploader import LaCaleUploader
    
    uploader = LaCaleUploader(passkey)
    
    try:
        # Show available metadata
        click.echo(line_separator("La Cale Metadata"))
        
        categories = uploader.get_categories()
        click.echo("Available Categories:")
        for cat_id, cat_name in list(categories.items())[:10]:  # Show first 10
            click.echo(f"  {cat_id}: {cat_name}")
        if len(categories) > 10:
            click.echo(f"  ... and {len(categories) - 10} more")
        
        tags_dict = uploader.get_tags()
        click.echo(f"\nAvailable Tags: {len(tags_dict)} total")
        
        # If not uploading, just show metadata
        if not all([title, category_id, torrent_file]):
            click.echo(line_separator("Upload Test"))
            click.echo("Provide --title, --category-id, and --torrent-file to test upload")
            return
        
        # Parse tags
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
        
        # Perform upload
        click.echo(line_separator(f"Uploading {title}"))
        result = uploader.upload_torrent(
            title=title,
            category_id=category_id,
            torrent_file_path=torrent_file,
            description=description,
            tmdb_id=tmdb_id,
            tmdb_type=tmdb_type,
            cover_url=cover_url,
            tags=tag_list,
            nfo_file_path=nfo_file
        )
        
        if result.success:
            click.echo(f"✅ Upload successful!")
            click.echo(f"Upload ID: {result.upload_id}")
            click.echo(f"Status URL: {result.status_url}")
        else:
            click.echo(f"❌ Upload failed: {result.message}")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--passkey', prompt=True, hide_input=True, help='La Cale API passkey')
@click.option('--output-dir', default='./output', help='Output directory containing extracted torrents')
@click.option('--dry-run', is_flag=True, help='Show what would be uploaded without actually uploading')
def mass_upload_lacale(passkey, output_dir, dry_run):
    """Mass upload all extracted torrents to La Cale using metadata.json"""
    from qbit2track.trackers.lacale import LaCaleUploader
    
    uploader = LaCaleUploader(passkey)
    
    try:
        click.echo(line_separator("La Cale Mass Upload"))
        click.echo(f"Output directory: {output_dir}")
        
        if dry_run:
            click.echo("🔍 DRY RUN MODE - No actual uploads will be performed")
        
        # Get available metadata for mapping
        click.echo("Fetching La Cale metadata...")
        categories = uploader.get_categories()
        tags = uploader.get_tags()
        click.echo(f"Found {len(categories)} categories and {len(tags)} tags")
        
        # Find metadata files
        output_path = Path(output_dir)
        if not output_path.exists():
            click.echo(f"❌ Output directory not found: {output_dir}")
            return
        
        metadata_dirs = []
        for item in output_path.iterdir():
            if item.is_dir() and (item / "metadata.json").exists():
                metadata_dirs.append(item)
        
        if not metadata_dirs:
            click.echo("❌ No metadata.json files found")
            return
        
        click.echo(f"Found {len(metadata_dirs)} torrents to process")
        
        if not dry_run:
            click.echo("Starting mass upload...")
            results = uploader.mass_upload_from_directory(output_dir)
            
            click.echo(line_separator("Results"))
            click.echo(f"Total: {results['total']}")
            click.echo(f"✅ Success: {results['success']}")
            click.echo(f"❌ Failed: {results['failed']}")
        else:
            # Dry run - show what would be uploaded
            click.echo(line_separator("Dry Run - What would be uploaded"))
            for metadata_dir in sorted(metadata_dirs):
                metadata_path = metadata_dir / "metadata.json"
                
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    media_info = metadata.get('media_info', {})
                    torrent_data = metadata.get('torrent_data', {})
                    
                    # Map category
                    category_id = uploader._map_category_id(media_info.get('type', 'movie'), categories)
                    category_name = categories.get(category_id, 'Unknown') if category_id else 'Not found'
                    
                    # Extract tags
                    extracted_tags = uploader._extract_tags_from_media_info(media_info, tags)
                    tag_names = [tags.get(tag_id, 'Unknown') for tag_id in extracted_tags]
                    
                    click.echo(f"\n📁 {metadata_dir.name}")
                    click.echo(f"   Title: {torrent_data.get('name', media_info.get('title', 'Unknown'))}")
                    click.echo(f"   Type: {media_info.get('type', 'Unknown')}")
                    click.echo(f"   Category: {category_name} ({category_id})")
                    click.echo(f"   Tags: {', '.join(tag_names) if tag_names else 'None'}")
                    click.echo(f"   TMDB ID: {media_info.get('tmdb_id', 'None')}")
                    click.echo(f"   Resolution: {media_info.get('resolution', 'Unknown')}")
                    click.echo(f"   Video Codec: {media_info.get('video_codec', 'Unknown')}")
                    click.echo(f"   Audio Codec: {media_info.get('audio_codec', 'Unknown')}")
                    click.echo(f"   Languages: {', '.join(media_info.get('languages', []))}")
                    
                except Exception as e:
                    click.echo(f"\n❌ {metadata_dir.name}: Error reading metadata - {e}")
            
            click.echo(f"\nDry run complete. {len(metadata_dirs)} torrents ready for upload.")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cache.command()
@click.pass_context
def stats(ctx):
    """Show cache statistics"""
    config = ctx.obj['config']
    
    try:
        from .extractor import TMDBMatcher
        matcher = TMDBMatcher(config)
        stats = matcher.get_cache_stats()
        
        click.echo(line_separator("TMDB Cache Statistics"))
        click.echo(f"Total entries: {stats['total_entries']}")
        click.echo(f"Valid entries: {stats['valid_entries']}")
        click.echo(f"Expired entries: {stats['expired_entries']}")
        click.echo(f"Cache file: {stats['cache_file']}")
        
    except Exception as e:
        click.echo(f"Error getting cache stats: {e}", err=True)


@cache.command()
@click.pass_context
@click.confirmation_option(prompt='Are you sure you want to clear the cache?')
def clear(ctx):
    """Clear all cached data"""
    config = ctx.obj['config']
    
    try:
        from .extractor import TMDBMatcher
        matcher = TMDBMatcher(config.tmdb.api_key, config.output.output_dir)
        matcher.clear_cache()
        click.echo("Cache cleared successfully")
        
    except Exception as e:
        click.echo(f"Error clearing cache: {e}", err=True)


if __name__ == '__main__':
    cli()
