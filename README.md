# Overview
Binance supports historical market data download at https://data.binance.vision/?prefix=data/, go ahead and have a look at the structure. We utilize that link for downloading data.

The basic idea is as follows:
1. You specify a list of paths to download. If the path doesn't point to a file, all files under that path will be checked.
2. You may also specify a list of paths for excluding downloading. Its meaning is the same with that of the ones for downloading.
3. You specify start date and end date to download, only data in the range will be downloaded.
4. You may specify whether to overwrite a file if it is already on the disk. Notice the content of a file on the website could change in theory, and we simply don't check that.
5. You may utilize concurrency for speeding up.

In case links of items could change in the future and don't comply with their paths, we traverse from the root instead of taking a shortcut.

We utilize [selenium](https://www.selenium.dev/) to fetch dynamic pages.

# Example
```python
from downloader import BinanceDownloader

paths = [
    'https://data.binance.vision/?prefix=data/futures/um/monthly/klines/*USDT/1d/',
    # 'futures/um/monthly/klines/*USDT/1d/', # or remove `https://data.binance.vision/?prefix=data/`
]
start_date = '2023-01-01'

bn_downloader = BinanceDownloader(paths=paths, start_date=start_date, output_dir='output',
                                  parallel=10)
bn_downloader.download()
```

