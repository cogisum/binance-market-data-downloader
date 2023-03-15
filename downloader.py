import concurrent.futures
import datetime
import enum
import fnmatch
import logging
import os.path
import pathlib
import re
import urllib.request

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait


class OverwriteOption(enum.Enum):
    OVERWRITE_NEVER = 0
    OVERWRITE_ALWAYS = 1


class Path:
    def __init__(self, path):
        self.components = path.strip('/').split('/')

    def match(self, component, level):
        return level >= len(self.components) or fnmatch.fnmatch(component, self.components[level])

    def is_exhausted(self, level):
        return level >= len(self.components)


class PageType(enum.Enum):
    PAGE_FILE = 0
    PAGE_DIR = 1


class Item:
    @property
    def item_type(self):
        return self.ITEM_TYPE

    def is_file(self):
        return self.item_type == PageType.PAGE_FILE


class FileItem(Item):
    ITEM_TYPE = PageType.PAGE_FILE
    date_pat = re.compile(r'(\d{4}-\d{2}(?:-\d{2})?)')

    def __init__(self, name, url, modify_date):
        self.name = name
        self.url = url
        self.date = self.date_pat.search(name).group()
        self.modify_date = modify_date


class DirItem(Item):
    ITEM_TYPE = PageType.PAGE_DIR

    def __init__(self, name, url):
        self.name = name
        self.url = url


class BinanceDownloader:
    BINANCE_DATA_URL = 'https://data.binance.vision/?prefix=data/'
    DEFAULT_RETRY = 3

    def __init__(self, paths, xpaths=None, start_date=None, end_date=None,
                 overwrite=OverwriteOption.OVERWRITE_NEVER, output_dir='.',
                 need_checksum=False, retry=None, parallel=1):
        assert isinstance(overwrite, OverwriteOption)

        dt_format = '%Y-%m-%d'
        if start_date:
            datetime.datetime.strptime(start_date, dt_format)
        if end_date:
            datetime.datetime.strptime(end_date, dt_format)
        self.start_date = start_date
        self.end_date = end_date

        self.paths = [Path(path.removeprefix(self.BINANCE_DATA_URL)) for path in paths]
        self.xpaths = ([Path(path.removeprefix(self.BINANCE_DATA_URL)) for path in xpaths]
                       if xpaths else [])
        self.overwrite = overwrite
        self.output_dir = output_dir
        self.need_checksum = need_checksum
        self.retry = retry if retry is not None else self.DEFAULT_RETRY
        self.executor = (concurrent.futures.ThreadPoolExecutor(max_workers=parallel)
                         if parallel else None)
        self.taskno = 0
        self._init_selenium()

    def _init_selenium(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=chrome_options)

    def download(self):
        self._download(self.BINANCE_DATA_URL, [], 0, self.paths, self.xpaths)
        if self.executor:
            self.executor.shutdown()

    def _download(self, url, components, level, paths, xpaths):
        items = self._fetch(url)
        for item in items:
            cur_paths = [path for path in paths if path.match(item.name, level)]
            if not cur_paths:
                continue
            cur_xpaths = [xpath for xpath in xpaths if xpath.match(item.name, level)]
            if any(xpath.is_exhausted(level) for xpath in cur_xpaths):
                continue
            if item.is_file():
                self._submit_download_file_task(item, components)
            else:
                components.append(item.name)
                self._download(item.url, components, level + 1, cur_paths, cur_xpaths)
                components.pop()

    def _fetch(self, url):
        logging.info(f'Fetching {url}')
        self.driver.get(url)
        WebDriverWait(self.driver, timeout=10).until(
                lambda d: d.find_element(By.CSS_SELECTOR, "#listing tr td"))
        tds = self.driver.find_elements(By.CSS_SELECTOR, '#listing tr td')
        assert len(tds) % 3 == 0
        items = []
        for start in range(0, len(tds), 3):
            e_item = tds[start]
            e_modify_date = tds[start + 2]
            e_a = e_item.find_element(By.TAG_NAME, 'a')
            name = e_a.get_attribute('innerHTML').rstrip('/')
            if name[0] == '.':
                continue
            href = e_a.get_attribute('href')
            modify_date = e_modify_date.get_attribute('innerHTML').strip()
            if modify_date:
                item = FileItem(name, href, modify_date)
            else:
                item = DirItem(name, href)
            items.append(item)
        return items

    def _submit_download_file_task(self, item, components):
        if ((self.start_date and item.date < self.start_date[:len(item.date)]) or
            (self.end_date and item.date > self.end_date[:len(item.date)])):
            return
        if not self.need_checksum and item.name.endswith('.CHECKSUM'):
            return
        dir_path = os.path.join(self.output_dir, *components)
        file_path = os.path.join(dir_path, item.name)
        if self.overwrite == OverwriteOption.OVERWRITE_NEVER and os.path.exists(file_path):
            return
        pathlib.Path(dir_path).mkdir(parents=True, exist_ok=True)
        self.taskno = self.taskno + 1
        if not self.executor:
            self._download_file(item, file_path, self.taskno)
            return
        self.executor.submit(self._download_file, item, file_path, self.taskno)

    def _download_file(self, item, file_path, taskno):
        for i in range(self.retry + 1):
            if i == 0:
                logging.info(f'[{taskno}.{i}] Downloading {item.name}')
            else:
                logging.info(f'[{taskno}.{i}] Retry Downloading {item.name}')
            try:
                urllib.request.urlretrieve(item.url, file_path)
            except Exception as e:
                logging.warn(f'[{taskno}] Got exception {e} when downloading {item.name}')
            else:
                break
        else:
            logging.error(f'[{taskno}] Failed to download {item.name} {item.url}')


