#!/usr/bin/env python3

# Extract a list of stations from the meteo france observation data

import csv
from datetime import datetime
import os
import re

# list variables to count records of
count_vars = [
    'tm',
    'tn',
    'tx',
    'tntxm',
]

# convert lat or lng stored as (d)dmmss to decimal degrees
def ddmmss_to_decimal(ddmmss):
    # strip any negative sign and add a leading zero to values < 10 degrees
    # e.g. '-51234' -> '051234'
    clean = ddmmss.lstrip('-').zfill(6)

    # convert to decimal degrees
    degrees = float(clean[0:2])
    minutes = float(clean[2:4])
    seconds = float(clean[4:6])
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)

    # make negative if needed
    if ddmmss.startswith('-'):
        decimal = -decimal

    # round to 6 decimal places
    return round(decimal, 6)

# convert date as DDYYMMMM to Date
def ddmmyyyy_to_date(ddmmyyyy):
    return datetime.strptime(ddmmyyyy, '%d%m%Y')

# compile a list of unique stations from all data files in regional subdirs of root
def extract_stations(root):
    stations = {}
    fields = [
        'insee',
        'lat',
        'lng',
        'date',
        'tm',
        'tn',
        'tx',
        'tntxm',
        'ffm',
        'rr',
        'um',
        'un',
        'ux',
        'visx',
        'visn',
        'blank'
    ]

    # iterate over all data files in subdirs
    for base, dirs, files in os.walk(root):
        dirname = os.path.basename(base)
        if re.compile('^region\d$').match(dirname):
            print('Reading files for ' + dirname)
            for file in files:
                # skip non-data files
                if not re.compile('^donnees_region\d').match(file):
                    print('  Skipping non-data file ' + file)
                    continue

                print('  Reading ' + file)
                with open(os.path.join(base, file), 'r') as f:
                    reader = csv.DictReader(f, dialect='excel', delimiter=';', fieldnames=fields)
                    for row in reader:
                        # If the station does not exist, create a record for it
                        if row['insee'] not in stations:
                            stations[row['insee']] = {
                                'regions': [dirname],
                                'lats': [ddmmss_to_decimal(row['lat'])],
                                'lngs': [ddmmss_to_decimal(row['lng'])],
                                'days': 1,
                            }
                            record = stations[row['insee']]

                            # Set first and last date
                            d = ddmmyyyy_to_date(row['date'])
                            record['dates'] = [d, d]

                            # Set counts for all temperature data to zero
                            for var in count_vars:
                                record[var] = 0

                        # Otherwise update its record
                        else:
                            record = stations[row['insee']]
                            record['days'] += 1

                            # Check if region has changed
                            if dirname not in record['regions']:
                                record['regions'] += [dirname]

                            # Parse lat and lng and check if they have changed
                            for var in ['lat', 'lng']:
                                val = ddmmss_to_decimal(row[var])
                                pluralized = var + 's'
                                if val not in record[pluralized]:
                                    record[pluralized] += [val]

                            # Check for new first or last date
                            d = ddmmyyyy_to_date(row['date'])
                            if d < record['dates'][0]:
                                record['dates'][0] = d
                            elif d > record['dates'][1]:
                                record['dates'][1] = d

                        # For all records - new or extant
                        # Check for temperature data and update the station's record
                        for var in count_vars:
                            if row[var] != '':
                                record[var] += 1

    return stations

def summarize(root, stations):
    outpath = os.path.join(root, 'station_list.csv')
    print('Writing station list to ' + outpath)
    headers = [
        'insee_id',
        'region',
        'lat',
        'lng',
        'days',
    ]
    headers += count_vars
    headers += [
        'first_date',
        'last_date',
        'period_days',
        'region_count',
        'lat_count',
        'lng_count',
        'regions',
        'lats',
        'lngs',
    ]
    with open(outpath, 'w') as f:
        writer = csv.DictWriter(f, dialect='excel', fieldnames=headers)
        writer.writeheader()

        for insee, record in stations.items():
            row = {
                'insee_id': insee,
                'region': record['regions'][-1],
                'lat': record['lats'][-1],
                'lng': record['lngs'][-1],
                'days': record['days'],
            }

            for var in count_vars:
                row[var] = record[var]

            row['first_date'] = record['dates'][0].strftime('%Y-%m-%d')
            row['last_date'] = record['dates'][1].strftime('%Y-%m-%d')
            row['period_days'] = (record['dates'][1] - record['dates'][0]).days + 1
            row['region_count'] = len(record['regions'])
            row['lat_count'] = len(record['lats'])
            row['lng_count'] = len(record['lngs'])
            row['regions'] = record['regions']
            row['lats'] = record['lats']
            row['lngs'] = record['lngs']

            writer.writerow(row)

if __name__ == "__main__":
    # Assume the data is in subdirs of ~/data/meteo_france/observations
    home = os.path.expanduser('~')
    data_dir = os.path.join(home, 'data', 'meteo_france', 'observations')

    stations = extract_stations(data_dir)
    summarize(data_dir, stations)
