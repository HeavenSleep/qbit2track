"""
Command line interface for qbit2track
"""

import click
import logging
from pathlib import Path
from typing import Optional

from .config import Config
from .extractor import TorrentExtractor
from .uploader import MassUploader


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
        
        click.echo(f"Extraction complete. Processed {results['total']} torrents.")
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
    
    click.echo("=== qbit2track Configuration ===")
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


@cache.command()
@click.pass_context
def stats(ctx):
    """Show cache statistics"""
    config = ctx.obj['config']
    
    try:
        from .extractor import TMDBMatcher
        matcher = TMDBMatcher(config.tmdb.api_key, config.output.output_dir)
        stats = matcher.get_cache_stats()
        
        click.echo("=== TMDB Cache Statistics ===")
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
