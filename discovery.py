from patchright.sync_api import sync_playwright
from patchright._impl._errors import TimeoutError as PlaywrightTimeoutError
import handlers
import database
import random
import time
from logger import logger

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

def run_discovery(vendor_data):
    handler_name = vendor_data.get('handler')

    if not handler_name:
        logger.error(f"No handler for {vendor_data.get('vendor_name')}")
        return None

    max_retries = 3
    for attempt in range(max_retries):
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=random.choice(USER_AGENTS)
                )
                page = context.new_page()

                # random human-like delay before interacting
                time.sleep(random.uniform(1.5, 4.0))

                if hasattr(handlers, handler_name):
                    scrape_function = getattr(handlers, handler_name)
                    results = scrape_function(page, vendor_data)
                    cookies = context.cookies()
                    logger.info(f'Handing {len(results)} records to database...')
                    database.save_firmware_data(results)
                    return cookies
                else:
                    logger.error(f"'{handler_name}' is missing in handlers.py!")
                    return None

        except Exception as e:
            logger.error(f'Attempt {attempt + 1} failed for {vendor_data["vendor_name"]}: {e}')
            if attempt < max_retries - 1:
                backoff = (2 ** attempt) + random.uniform(0, 2)
                logger.info(f'Retrying in {backoff:.1f}s...')
                time.sleep(backoff)
            else:
                logger.error(f'All retries failed for {vendor_data["vendor_name"]}')
                return None