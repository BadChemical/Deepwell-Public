import json
import random
import time
import sys
import signal
import os
import discovery
import database
import downloader
from logger import logger

# graceful shutdown flag
shutdown_requested = False

def handle_shutdown(signum, frame):
    global shutdown_requested
    logger.warning('Shutdown signal received. Finishing current task then exiting...')
    shutdown_requested = True

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

def health_check():
    # Create the data directory if it doesn't exist
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)

    test_file = os.path.join(data_dir, '.healthcheck')
    try:
        with open(test_file, 'w') as f:
            f.write('ok')
        os.remove(test_file)
    except Exception as e:
        logger.error(f'[Health] Data directory is not writable: {e}')
        return False

    logger.info('[Health] Local environment is writable and ready.')
    return True

def check_robots(vendor_data):
    import urllib.robotparser
    import urllib.parse
    base_url = vendor_data.get('base_url', '')
    parsed = urllib.parse.urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
        allowed = rp.can_fetch('*', base_url)
        if not allowed:
            logger.warning(f"[Robots] {vendor_data['vendor_name']} disallows scraping per robots.txt")
        else:
            logger.info(f"[Robots] {vendor_data['vendor_name']} is clear to scrape.")
        return allowed
    except Exception as e:
        logger.warning(f"[Robots] Could not read robots.txt for {vendor_data['vendor_name']}: {e}")
        return True  # proceed if robots.txt unreachable

def main():
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        logger.info('DRY RUN MODE — scraping only, no downloads.')

    logger.info('Waking up Deepwell....')

    if not health_check():
        logger.error('Health check failed. Aborting.')
        return

    database.init_db()
    #database.audit_file_paths()

    try:
        with open('targets.json', 'r') as t:
            targets = json.load(t)
    except FileNotFoundError:
        logger.error('targets.json not found!')
        return

    enabled_targets = []
    for vendor_name, vendor_data in targets['vendors'].items():
        if vendor_data.get('enabled') == True:
            vendor_data['vendor_name'] = vendor_name
            enabled_targets.append(vendor_data)

    if not enabled_targets:
        logger.warning('No enabled targets. Going to sleep.')
        return

    random.shuffle(enabled_targets)
    logger.info(f'Found {len(enabled_targets)} targets')

    run_stats = {
        'vendors_scraped': 0,
        'downloads': 0,
        'failures': 0,
        'bytes_downloaded': 0
    }

    for vendor_data in enabled_targets:
        if shutdown_requested:
            logger.warning('Shutdown requested. Stopping vendor loop.')
            break

        logger.info(f"==================================================")
        logger.info(f"Initiating scrape for: {vendor_data['vendor_name']}")
        logger.info(f"==================================================")

        if not check_robots(vendor_data):
            if vendor_data.get('ignore_robots'):
                logger.info(f"[Robots] Ignoring robots.txt for {vendor_data['vendor_name']} due to config override.")
            else:
                logger.warning(f"Skipping {vendor_data['vendor_name']} per robots.txt")
                continue

        cookies = discovery.run_discovery(vendor_data)
        run_stats['vendors_scraped'] += 1

        if not dry_run:
            stats = downloader.run_downloader(cookies)
            run_stats['downloads'] += stats['downloads']
            run_stats['failures'] += stats['failures']
            run_stats['bytes_downloaded'] += stats['bytes_downloaded']

        delay = random.uniform(30, 90)
        logger.info(f'Waiting {delay:.1f}s before next vendor...')
        time.sleep(delay)

    gb_downloaded = run_stats['bytes_downloaded'] / (1024 ** 3)
    logger.info('==================================================')
    logger.info('Run Summary:')
    logger.info(f"  Vendors scraped : {run_stats['vendors_scraped']}")
    logger.info(f"  Downloads       : {run_stats['downloads']}")
    logger.info(f"  Failures        : {run_stats['failures']}")
    logger.info(f"  Data downloaded : {gb_downloaded:.2f} GB")
    logger.info('==================================================')
    logger.info('Daily sweep done. Going back to sleep.')

if __name__ == '__main__':
    main()