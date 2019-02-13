import time
from datetime import timedelta
import csv
import json
import copy
import geopy.distance


def write_csv(filename, cities_list):
    """
    Saves a list of cities in [country code, city name in UTF-8, city name in ASCII,
    city population, latitude, longitude] format as a CSV file.

    :param filename: Path to the destination .csv file.
    :param cities_list: List of lists or tuples in format mentioned above.
    :return: None
    """

    with open(filename, 'w', newline='', encoding='utf-8') as csv_file:
        write_csv = csv.writer(csv_file, delimiter=',')
        write_csv.writerow(['Country', 'City-UTF8', 'City-ASCII', 'Population', 'Latitude', 'Longitude'])
        write_csv.writerows(cities_list)


def write_geojson(filename, cities_list):
    """
    Saves a list of cities in [country code, city name in UTF-8, city name in ASCII,
    city population, latitude, longitude] format as a GEOJSON file.

    :param filename: Path to the destination .json file.
    :param cities_list: List of lists or tuples in format mentioned above.
    :return: None
    """

    cities_json = {
        'type': 'FeatureCollection',
        'features': [],
    }

    for city in cities_list:
        feature = {
            'type': 'Feature',
            'properties': {
                'country': city[0],
                'name-UTF8': city[1],
                'name-ASCII': city[2],
                'population': city[3],
            },
            'geometry': {
                'type': 'Point',
                'coordinates': [
                    city[5],
                    city[4]
                ]
            }
        }
        cities_json['features'].append(feature)

    with open(filename, 'w', encoding='utf-8') as json_file:
        json.dump(cities_json, json_file)


def aggregate_cities(break_values, cities_list):
    """
    Deletes smaller cities around bigger cities. It takes break values from a list of lists or tuples in
    [population limit, distance limit] format.

    :param break_values:
    :param cities_list:
    :return:
    """

    cities_list.sort(key=lambda tup: tup[3], reverse=True)

    for break_value in break_values:
        print('\nPopulation break:', break_value[0], 'Distance break:', break_value[1])
        for bigger_city in cities_list:
            if bigger_city[3] > break_value[0]:
                bigger_city_coordinates = (bigger_city[4], bigger_city[5])
                bigger_city_name = bigger_city[1]
                cities_list_copy = copy.copy(cities_list)

                for city in cities_list_copy:
                    city_coordinates = (city[4], city[5])
                    city_name = city[1]
                    distance = geopy.distance.geodesic(bigger_city_coordinates, city_coordinates).km

                    if distance < break_value[1] and city_name != bigger_city_name:
                        print(bigger_city[0], bigger_city[1], city[1], distance)
                        cities_list.remove(city)

        print('### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###')

    return cities_list


start = time.time()

country_codes = {
    'Portugal': 'PT',
    'Spain': 'ES',
    'Ireland': 'IE',
    'United Kingdom': 'GB',
    'France': 'FR',
    'Belgium': 'BE',
    'Netherlands': 'NL',
    'Luxembourg': 'LU',
    'Switzerland': 'CH',
    'Italy': 'IT',
    'Germany': 'DE',
    'Denmark': 'DK',
    'Austria': 'AT',
    'Czechia': 'CZ',
    'Poland': 'PL',
    'Slovenia': 'SI',
    'Croatia': 'HR',
    'Hungary': 'HU',
    'Slovakia': 'SK',
    'Norway': 'NO',
    'Sweden': 'SE',
    'Finland': 'FI',
    'Estonia': 'EE',
    'Latvia': 'LV',
    'Lithuania': 'LT',
    'Belarus': 'BY',
    'Ukraine': 'UA',
    'Romania': 'RO',
    'Moldova': 'MD',
    'Iceland': 'IS',
    'Bosnia and Herzegovina': 'BA',
    'Kosovo': 'XK',
    'Macedonia': 'MK',
    'Bulgaria': 'BG',
    'Albania': 'AL',
    'Greece': 'GR',
    'Turkey': 'TR',
    'Russia': 'RU',
}
breaks = [
    (750000, 100.0),
    (500000, 75.0),
    (250000, 50.0),
    (100000, 50.0),
    (75000, 50.0),
]

cities = []

# cities15000.txt file from the GeoNames project
# https://www.geonames.org/
# http://download.geonames.org/export/dump/
with open('source/cities15000.txt', encoding='utf-8') as csv_file:
    read_csv = csv.reader(csv_file, delimiter='\t')
    for row in read_csv:
        if row[8] in country_codes.values() and float(row[5]) < 60.5 and int(row[14]) > 75000:
            cities.append((row[8], row[1], row[2], int(row[14]), float(row[4]), float(row[5])))

cities = aggregate_cities(breaks, cities)

write_geojson('cities.json', cities)
write_csv('cities.csv', cities)

elapsed = (time.time() - start)
print('\nElapsed time:', str(timedelta(seconds=elapsed)))
