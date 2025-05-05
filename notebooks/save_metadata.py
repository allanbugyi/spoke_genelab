"""
This is a modification of the original project: https://github.com/asaravia-butler/KnowHax2025_NASA-SPOKE
"""

from urllib.parse import quote_plus
from itertools import combinations
import requests
import csv
import sys
import os


OSDR_API = 'https://visualization.osdr.nasa.gov/biodata/api/v2/'
DATASET_ENDPOINT = OSDR_API + 'dataset/'
METADATA_ENDPOINT = OSDR_API + 'query/metadata/'

METADATA_DIR = "../data/metadata"


def sampleToGroupMappingAndGroupToGroupMetadata(osd_num):

    os.makedirs(METADATA_DIR, exist_ok=True)
    
    # Get factors
    factors = get_factors(osd_num)

    # Get sample table
    data = get_samples(osd_num, factors)

    # Save samples table
    with open(f'{METADATA_DIR}/{osd_num}_SampleTable.csv', mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Sample Name', 'Treatment Group'])

        rows = []

        for row in data[1:]:  # skip header
            sample = row[2]
            group = ' & '.join(row[3:]).replace('{', '').replace('}', '')

            rows.append([sample, group])
            
        writer.writerows(sorted(set(tuple(row) for row in rows)))  # write unique rows

    # Save contrasts table
    groups = set(sorted([g for s, g in rows]))
    combos = list(combinations(groups, 2))
    print(f'{len(groups)} unique groups = {len(combos)} pairwise combinations')

    with open(f'{METADATA_DIR}/{osd_num}_contrasts.csv', mode='w', newline='') as f:
        writer = csv.writer(f)

        writer.writerow([''] + [f'({a})v({b})' for a, b in combos])
        writer.writerow(['1'] + [a for a, b in combos])
        writer.writerow(['2'] + [b for a, b in combos])


def get_factors(osd_num):
    r = requests.get(DATASET_ENDPOINT + osd_num)
    print(f'Requested metadata from: {r.url}')

    factors = r.json()[osd_num]['metadata']['study factor name']

    return factors if isinstance(factors, list) else [factors]


def get_samples(osd_num, factors):
    query_string = f'?id.accession={osd_num}&' + '&'.join([quote_plus(f'study.factor value.{factor}') for factor in factors])

    r = requests.get(METADATA_ENDPOINT + query_string)
    print(f'Requested sample table from: {r.url}')

    return list(csv.reader(r.text.strip().split('\n')))

