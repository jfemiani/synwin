"""
This scrapes on online free website for PBR textures.

** IMPORTANT **:  sudo apt-get install chromium-chromedriver
"""
import os
import shutil
import time
from glob import glob

import tqdm as tq
from bs4 import BeautifulSoup
# This site uses jacascript for pagination -- access needs to be done through
# an actual browser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

BASE_URL = "https://www.cgbookcase.com"


def download(url, filename, tqparams=None):
    import functools
    import pathlib
    import shutil

    import requests
    from tqdm.auto import tqdm

    if tqparams is None:
        tqparams = dict(leave=False)

    r = requests.get(url, stream=True, allow_redirects=True)
    if r.status_code != 200:
        r.raise_for_status()  # Will only raise for 4xx codes, so...
        raise RuntimeError(f"Request to {url} returned status code {r.status_code}")
    file_size = int(r.headers.get('Content-Length', 0))

    path = pathlib.Path(filename).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    desc = "(Unknown total file size)" if file_size == 0 else ""
    r.raw.read = functools.partial(r.raw.read, decode_content=True)  # Decompress if needed
    with tqdm.wrapattr(r.raw, "read", total=file_size, desc=desc, **tqparams) as r_raw:
        with path.open("wb") as f:
            shutil.copyfileobj(r_raw, f)

    return path


def get_driver():
    # Not using requests -- we need to use an actual browser
    # to load the page and run javascript
    options = Options()
    options.headless = True
    driver = webdriver.Chrome('/usr/lib/chromium-browser/chromedriver', options=options)
    return driver


def get_content(url, driver=None, timeout=2):
    if driver is None:
        driver = get_driver()
    driver.get(url)
    time.sleep(5)  # Give any scripts time to execute as the page loads
    content = driver.page_source
    return content


def get_texture_pages(query):
    max_pages = 10
    driver = get_driver()
    for page in range(1, max_pages+1):
        url = f'{BASE_URL}/textures/?search={query}&page={page}'
        content = get_content(url, driver)
        soup = BeautifulSoup(content, 'html.parser')
        links = soup.find_all('a', {'class': 'results-itemWrapper'})

        if len(links) == 0:
            break

        for link in links:
            image_url = f"{BASE_URL}{link['href']}"
            yield image_url


def get_zip_links(texture_page):
    drv = get_driver()
    drv.get(texture_page)
    download_button = drv.find_element_by_class_name('btn-red')
    zip_url = download_button.get_property('href')
    return zip_url


def iter_download_walls(outdir):
    for wall in get_texture_pages('wall'):
        zip_url = get_zip_links(wall)
        zip_path = os.path.join(outdir, os.path.basename(zip_url))
        tq.tqdm.write(f'Downloading {wall} to {zip_path}')
        download(zip_url, zip_path)
        yield zip_path


def download_walls(outdir='data/PBRS/walls'):
    return list(iter_download_walls(outdir))


def extract_materials(outdir='data/PBRS/walls', tqargs=None):
    if tqargs is None:
        tqargs = dict(leave=False)

    zips = glob(f'{outdir}/*.zip')
    for zip in tq.tqdm(zips, desc='Extracting zrchives', **tqargs):
        shutil.unpack_archive(zip, extract_dir=outdir)
