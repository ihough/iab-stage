#!/usr/bin/env python3

# Download MODIS MXD10A1 v6 snow cover data for metropolitan France
#   ~/.netrc must be configured with a NASA Earthdata username and password
#   (see https://nsidc.org/support/faq/what-options-are-available-bulk-downloading-data-https-earthdata-login-enabled)

from datetime import datetime
import os
import re

import requests               # to load pages and download files
from bs4 import BeautifulSoup # to parse pages


datasets = [
    {
        'name': 'MYD10A1.006',
        'description': 'MODIS/Aqua Snow Cover Daily 500m v6',
        'satellite': 'aqua',
        'url': 'https://n5eil01u.ecs.nsidc.org/MOSA/MYD10A1.006/',
        'tilename_format': 'MYD10A1\.A\d{7}\.LOCATION\..+\.hdf',
        'tile_locations': ['h17v04', 'h18v03', 'h18v04'],
    },
    {
        'name': 'MOD10A1.006',
        'description': 'MODIS/Terra Snow Cover Daily 500m v6',
        'satellite': 'terra',
        'url': 'https://n5eil01u.ecs.nsidc.org/MOST/MOD10A1.006/',
        'tilename_format': 'MOD10A1\.A\d{7}\.LOCATION\..+\.hdf',
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
    return BeautifulSoup(request.text, 'html.parser')

# Find dates for which imagery is available
def find_dates(session, url):
    print('  Checking available dates')
    page = get_page(session, url)
    dates = []
    for td in page.find_all('td', class_='indexcolname', string=re.compile('20\d{2}\.\d{2}\.\d{2}')):
        dates.append({
            'date': td.a.text.replace('.', '-').rstrip('/'),
            'url': url + td.a.attrs['href'],
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
        for td in page.find_all('td', class_='indexcolname', string=tile_regexp):
            tiles.append({
                'name': td.a.text,
                'url': url + td.a.attrs['href'],
            })
    return tiles

# Download imagery for the specified date and tile locations
def download(session, url, output):
    print('      ' + output)
    with open(output, 'wb') as f:
        stream = session.get(url, stream=True)
        for chunk in stream.iter_content(chunk_size=1024):
            if chunk: # filter out keep-alive new lines
                f.write(chunk)
        stream.close()

if __name__ == "__main__":
    for dataset in datasets:
        # Search for and download tiles
        print('Acquiring ' + dataset['description'] + ' data (' + dataset['name'] + ')')
        with requests.Session() as session:
            count = 0
            for date in find_dates(session, dataset['url']):
                if count == 2:
                    break
                count += 1
                print('    ' + date['date'])
                for tile in find_tiles(session, date['url'], dataset['tilename_format'], dataset['tile_locations']):
                    output = filename_for(dataset['satellite'], dataset['name'], date['date'], tile['name'])
                    download(session, tile['url'], output)
        print('Done with ' + dataset['description'])
