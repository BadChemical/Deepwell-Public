import requests
import os
import hashlib
import random
import time
import database
from tqdm import tqdm
from logger import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIRMWARE_BASE = os.path.join(BASE_DIR, 'data', 'firmware')
MAX_DOWNLOADS_PER_RUN = 50
MAX_GB_PER_RUN = 20

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

def build_file_path(vendor, model, version, url):
    vendor_dir = os.path.join(FIRMWARE_BASE, vendor)
    os.makedirs(vendor_dir, exist_ok=True)
    original_filename = url.split('/')[-1]
    versioned_filename = f"{model}_{version}_{original_filename}"
    return os.path.join(vendor_dir, versioned_filename)

def verify_checksum(file_path, expected_sha256):
    if not expected_sha256:
        return True
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    actual = sha256.hexdigest()
    return actual.lower() == expected_sha256.lower()

def validate_record(item):
    required = ['vendor', 'model', 'version', 'url']
    for field in required:
        if not item.get(field):
            return False
    if not item['url'].startswith('http'):
        return False
    return True

def download_firmware(record, session):
    firmware_id = record[0]
    vendor      = record[1]
    model       = record[2]
    version     = record[3]
    url         = record[4]
    sha256      = record[5]

    file_path = build_file_path(vendor, model, version, url)

    if os.path.exists(file_path):
        logger.info(f'Already have {os.path.basename(file_path)}, skipping')
        return 0

    logger.info(f'Downloading {vendor} {model} {version}...')

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = session.get(url, stream=True, timeout=60)
            response.raise_for_status()

            total = int(response.headers.get('content-length', 0))

            with open(file_path, 'wb') as f, tqdm(
                desc=os.path.basename(file_path),
                total=total,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))
            break

        except requests.RequestException as e:
            logger.error(f'Attempt {attempt + 1} failed for {model} {version}: {e}')
            if os.path.exists(file_path):
                os.remove(file_path)
            if attempt < max_retries - 1:
                backoff = (2 ** attempt) + random.uniform(0, 1)
                logger.info(f'Retrying in {backoff:.1f}s...')
                time.sleep(backoff)
            else:
                logger.error(f'All retries failed for {model} {version}')
                return 0

    if not verify_checksum(file_path, sha256):
        logger.error(f'Checksum mismatch on {model} {version}, discarding')
        os.remove(file_path)
        return 0

    database.update_file_path(firmware_id, file_path)
    file_size = os.path.getsize(file_path)
    logger.info(f'Saved {os.path.basename(file_path)} ({file_size / (1024**2):.1f} MB)')
    return file_size

def run_downloader(cookies=None):
    logger.info('[Downloader] Checking for undownloaded firmware...')

    session = requests.Session()
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Referer': 'https://downloadstore.boschsecurity.com/index.php',
        'Accept': 'application/octet-stream,*/*',
    })

    if cookies:
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])

    records = database.get_undownloaded()

    if not records:
        logger.info('[Downloader] Nothing new to download.')
        return {'downloads': 0, 'failures': 0, 'bytes_downloaded': 0}

    logger.info(f'[Downloader] {len(records)} records queued')

    download_count = 0
    failure_count = 0
    bytes_downloaded = 0
    max_bytes = MAX_GB_PER_RUN * 1024 ** 3

    for record in records:
        if download_count >= MAX_DOWNLOADS_PER_RUN:
            logger.warning(f'[Downloader] Download cap of {MAX_DOWNLOADS_PER_RUN} reached.')
            break
        if bytes_downloaded >= max_bytes:
            logger.warning(f'[Downloader] GB cap of {MAX_GB_PER_RUN}GB reached.')
            break

        result = download_firmware(record, session)
        if result > 0:
            download_count += 1
            bytes_downloaded += result
        else:
            if not os.path.exists(build_file_path(record[1], record[2], record[3], record[4])):
                failure_count += 1

        delay = random.uniform(3, 8)
        logger.debug(f'Waiting {delay:.1f}s before next download...')
        time.sleep(delay)

    logger.info(f'[Downloader] Queue complete. Downloaded: {download_count}, Failed: {failure_count}, Total: {bytes_downloaded / (1024**2):.1f} MB')
    return {
        'downloads': download_count,
        'failures': failure_count,
        'bytes_downloaded': bytes_downloaded
    }