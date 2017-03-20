#!/usr/bin/env python3

# Download MODIS MXD13A3 v6 vegetation indices for metropolitan France
#   ~/.netrc must be configured with a NASA Earthdata username and password
#   (see https://wiki.earthdata.nasa.gov/display/EL/How+To+Access+Data+With+cURL+And+Wget)

from datetime import datetime
import os
import re

import requests               # to load pages and download files
from bs4 import BeautifulSoup # to parse pages

datasets = [
    {
        'name': 'MYD13A3.006',
        'description': 'MODIS/Aqua Vegetation Indices Monthly L3 Global 1km Grid SIN V006',
        'satellite': 'aqua',
        'url': 'https://e4ftl01.cr.usgs.gov/MOLA/MYD13A3.006/',
        'tilename_format': 'MYD13A3\.A\d{7}\.LOCATION\..+\.hdf',
        'tile_locations': ['h17v04', 'h18v03', 'h18v04'],
    },
    {
        'name': 'MOD13A3.006',
        'description': 'MODIS/Terra Vegetation Indices Monthly L3 Global 1km Grid SIN V006',
        'satellite': 'terra',
        'url': 'https://e4ftl01.cr.usgs.gov/MOLT/MOD13A3.006/',
        'tilename_format': 'MOD13A3\.A\d{7}\.LOCATION\..+\.hdf',
        'tile_locations': ['h17v04', 'h18v03', 'h18v04'],
    },
]

# Determine the output filename for a specific tile
def filename_for(satellite, dataset, date, tile):
    base_dir = os.path.dirname(os.path.realpath(__file__))
    data_dir = os.path.join(base_dir, satellite, dataset, date)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return os.path.join(data_dir, tile)

# Request a page and parse it with BeautifulSoup
def get_page(session, url):
    request = session.get(url)
    request.raise_for_status() # raises if bad request status code
    request.close()
    return BeautifulSoup(request.text, 'lxml-xml')

# Find dates for which imagery is available
def find_dates(session, url):
    print('  Checking available dates')
    page = get_page(session, url)
    dates = []
    for tag in page.find_all('a', string=re.compile('20\d{2}\.\d{2}\.\d{2}')):
        dates.append({
            'date': tag.text.replace('.', '-').rstrip('/'),
            'url': url + tag.attrs['href'],
        })
    if len(dates) > 0:
        print('  Downloading ' + str(len(dates)) + ' tilesets from ' + dates[0]['date'] + ' to ' + dates[-1]['date'])
    else:
        print('  No dates found!')
    return dates

def find_tiles(session, url, tilename_format, tile_locations):
    page = get_page(session, url)
    tiles = []
    for location in tile_locations:
        tile_regexp = re.compile(tilename_format.replace('LOCATION', location))
        for tag in page.find_all('a', string=tile_regexp):
            tiles.append({
                'name': tag.text,
                'url': url + tag.attrs['href'],
            })
    return tiles

# Download imagery for the specified date and tile locations
def download(session, url, output):
    print('      ' + os.path.basename(output) + ' ... ', end='', flush=True)
    with open(output, 'wb') as f:
        stream = session.get(url, stream=True)
        for chunk in stream.iter_content(chunk_size=1024):
            if chunk: # filter out keep-alive new lines
                f.write(chunk)
        stream.close()
    print('done')

if __name__ == "__main__":
    for dataset in datasets:
        # Search for and download tiles
        print('Acquiring ' + dataset['description'] + ' data (' + dataset['name'] + ')')
        with requests.Session() as session:
            for date in find_dates(session, dataset['url']):
                print('    ' + date['date'])
                for tile in find_tiles(session, date['url'], dataset['tilename_format'], dataset['tile_locations']):
                    output = filename_for(dataset['satellite'], dataset['name'], date['date'], tile['name'])
                    download(session, tile['url'], output)
        print('Done with ' + dataset['description'])
