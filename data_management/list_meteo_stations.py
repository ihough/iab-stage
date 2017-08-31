#!/usr/bin/env python3

# Extract a list of stations from the meteo france observation data

import csv
import os
import re

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
                        try:
                            # If the station already exists, update its record
                            record = stations[row['insee']]
                            record['days'] += 1
                            if record['lat'] != row['lat'] or record['lng'] != row['lng']:
                                record['previous_lats'] += '/' + row['lat']
                                record['previous_lngs'] += '/' + row['lng']
                                record['lat'] = row['lat']
                                record['lng'] = row['lng']
                        except KeyError:
                            # If the station does not exist, create a record for it
                            stations[row['insee']] = {
                                'region': dirname,
                                'lat': row['lat'],
                                'lng': row['lng'],
                                'days': 1,
                                'tm': 0,
                                'tn': 0,
                                'tx': 0,
                                'tntxm': 0,
                            }
                            record = stations[row['insee']]

                        # Check for temperature data and update the station's record
                        for var in ['tm', 'tn', 'tx', 'tntxm']:
                            if row[var] != '':
                                record[var] += 1

    return stations

def summarize(root, stations):
    print('Writing station list to ' + os.path.join(root, 'station_list.csv'))
    headers = ['station', 'region', 'latitude', 'longitude', 'previous_lats', 'previous_lngs', 'days']
    with open(os.path.join(root, 'station_list.csv'), 'w') as f:
        writer = csv.DictWriter(f, dialect='excel', fieldnames=headers)
        writer.writeheader()

        for insee, record in stations.items():
            row = {
                'station': insee,
                'region': record['region'],
                'days': record['days'],
            }

            # parse the latitude to decimal format
            row['latitude']  = ddmmss_to_decimal(record['lat'])
            row['longitude'] = ddmmss_to_decimal(record['lng'])

            # record previous lat/lng if any
            if 'previous_lats' in record.keys():
                row['previous_lats'] = record['previous_lats']
                row['previous_lngs'] = record['previous_lngs']

            writer.writerow(row)

if __name__ == "__main__":
    # Assume the data is in subdirs of ~/data/meteo_france/observations
    home = os.path.expanduser('~')
    data_dir = os.path.join(home, 'data', 'meteo_france', 'observations')

    stations = extract_stations(data_dir)
    summarize(data_dir, stations)
