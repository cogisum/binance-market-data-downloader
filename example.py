#!/usr/bin/env python

import logging
import sys

from downloader import BinanceDownloader


logging.basicConfig(format=('%(asctime)s %(levelname)s %(message)s'), level=logging.INFO,
                    stream=sys.stdout)

paths = [
    'https://data.binance.vision/?prefix=data/futures/um/monthly/klines/BT*USDT/*[wo]/',
    'https://data.binance.vision/?prefix=data/futures/um/monthly/klines/ETHUSDT/1mo/',
]
xpaths = [
    'https://data.binance.vision/?prefix=data/futures/um/monthly/klines/BTSUSDT/*[wo]/',
]
start_date = '2023-01-01'

bn_downloader = BinanceDownloader(paths=paths, xpaths=xpaths, start_date=start_date,
                                  output_dir='output', parallel=10)
bn_downloader.download()

