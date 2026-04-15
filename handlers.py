from bs4 import BeautifulSoup
from patchright._impl._errors import TimeoutError as PlaywrightTimeoutError
import random
import time
from logger import logger

def bosch_security(page, vendor_data):
    target_url = vendor_data['base_url']
    page.goto(target_url, wait_until='domcontentloaded')

    try:
        page.get_by_role('button', name='OK, understood').click(timeout=3000)
        logger.debug('[Bosch] Cookie dialog dismissed.')
    except PlaywrightTimeoutError:
        logger.debug('[Bosch] No cookie dialog appeared.')

    
    time.sleep(random.uniform(1.0, 2.5))
    page.get_by_text('Firmware', exact=True).click()
    page.wait_for_timeout(random.randint(800, 1500))      #<----------- These timers are required, when useing network_idle or domcontentloaded a race condition exists in main
    page.get_by_role('button', name='Select').click()
    page.wait_for_timeout(random.randint(3000, 5000))

    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr', class_='M-Table__row')

    targeted_models = vendor_data.get('models', [])
    extracted_data = []

    for row in rows:
        cells = row.find_all('td', class_='M-Table__cell')

        if len(cells) >= 4:
            try:
                platform = cells[0].find('div', class_='A-Text-RichText').text.strip()

                if not any(platform.startswith(target) for target in targeted_models):
                    continue

                version = cells[1].find('div', class_='A-Text-RichText').text.strip()
                link_tag = cells[2].find('a', href=True)
                download_url = link_tag['href'] if link_tag else None

                checksum_btn = cells[3].find('button', class_='checksum')
                checksum = checksum_btn['data-clipboard-text'] if checksum_btn else None

                if not download_url:
                    continue
                if not (download_url.endswith('.fw') or download_url.endswith('.zip')):
                    continue
                if not download_url.startswith('http'):
                    download_url = f"https://downloadstore.boschsecurity.com/{download_url}"

                # input validation
                if not platform or not version or not download_url:
                    logger.warning(f'[Bosch] Skipping incomplete record: {platform}')
                    continue

                extracted_data.append({
                    'vendor': vendor_data['vendor_name'],
                    'model': platform,
                    'version': version,
                    'url': download_url,
                    'sha256': checksum
                })

            except Exception as e:
                logger.error(f'[Bosch] Error parsing row: {e}')
                continue

    logger.info(f'[Bosch] Extracted {len(extracted_data)} records.')
    return extracted_data
