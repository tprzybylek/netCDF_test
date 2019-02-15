import time
from datetime import timedelta
import csv
import json
import copy
import geopy.distance

import ogr
import osr


def read_cities_list(filename, max_longitude=None, min_population=None):
    cities = []

    if max_longitude and min_population:
        # cities15000.txt a file from the GeoNames project
        # https://www.geonames.org/
        # http://download.geonames.org/export/dump/
        with open('source/cities15000.txt', encoding='utf-8') as csv_file:
            read_csv = csv.reader(csv_file, delimiter='\t')
            for row in read_csv:
                if row[8] in country_codes.values() and float(row[5]) < max_longitude and int(row[14]) > min_population:
                    cities.append((row[8], row[1], row[2], int(row[14]), float(row[4]), float(row[5])))
    elif max_longitude:
        # cities15000.txt a file from the GeoNames project
        # https://www.geonames.org/
        # http://download.geonames.org/export/dump/
        with open('source/cities15000.txt', encoding='utf-8') as csv_file:
            read_csv = csv.reader(csv_file, delimiter='\t')
            for row in read_csv:
                if row[8] in country_codes.values() and float(row[5]) < max_longitude:
                    cities.append((row[8], row[1], row[2], int(row[14]), float(row[4]), float(row[5])))

    elif min_population:
        # cities15000.txt a file from the GeoNames project
        # https://www.geonames.org/
        # http://download.geonames.org/export/dump/
        with open('source/cities15000.txt', encoding='utf-8') as csv_file:
            read_csv = csv.reader(csv_file, delimiter='\t')
            for row in read_csv:
                if row[8] in country_codes.values() and int(row[14]) > min_population:
                    cities.append((row[8], row[1], row[2], int(row[14]), float(row[4]), float(row[5])))
    else:
        with open('cities.csv', encoding='utf-8') as csv_file:
            read_csv = csv.reader(csv_file, delimiter=',')
            for row in read_csv:
                    cities.append(row)
    return cities


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
        print('\n\033[94mPopulation break:\033[0m', break_value[0], '\033[94mDistance break:\033[0m', break_value[1])
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

        print('\033[94mNumber of cities:\033[0m', len(cities))

    return cities_list


def generate_bounding_boxes(cities_list):
    def transform_point(coordinates, source_crs, target_crs):

        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(coordinates[0], coordinates[1])

        transform = osr.CoordinateTransformation(source_crs, target_crs)
        point.Transform(transform)

        return [point.GetX(), point.GetY()]

    def get_UTM_EPSG_code(longitude):
        if -30.0 <= longitude < -24.0:
            # UTM zone 26
            return 32626
        elif -24.0 <= longitude < -18.0:
            # UTM zone 27
            return 32627
        elif -18.0 <= longitude < -12.0:
            # UTM zone 28
            return 32628
        elif -12.0 <= longitude < -6.0:
            # UTM zone 29
            return 32629
        elif -6.0 <= longitude < 0.0:
            # UTM zone 30
            return 32630
        elif 0.0 <= longitude < 6.0:
            # UTM zone 31
            return 32631
        elif 6.0 <= longitude < 12.0:
            # UTM zone 32
            return 32632
        elif 12.0 <= longitude < 18.0:
            # UTM zone 33
            return 32633
        elif 18.0 <= longitude < 24.0:
            # UTM zone 34
            return 32634
        elif 24.0 <= longitude < 30.0:
            # UTM zone 35
            return 32635
        elif 30.0 <= longitude < 36.0:
            # UTM zone 36
            return 32636
        elif 36.0 <= longitude < 42.0:
            # UTM zone 37
            return 32637
        elif 42.0 <= longitude < 48.0:
            # UTM zone 38
            return 32638
        elif 48.0 <= longitude < 54.0:
            # UTM zone 39
            return 32639
        elif 54.0 <= longitude < 60.0:
            # UTM zone 40
            return 32640
        elif 60.0 <= longitude < 66.0:
            # UTM zone 41
            return 32641
        elif 66.0 <= longitude < 72.0:
            # UTM zone 42
            return 32642
        else:
            return None

    source = osr.SpatialReference()
    source.ImportFromEPSG(4326)

    target = osr.SpatialReference()
    # target.ImportFromEPSG(3035)
    target.ImportFromEPSG(32633)

    cities_json = {
        'type': 'FeatureCollection',
        'features': [],
    }

    for city in cities_list:
        city_coordinates = (city[4], city[5])

        source = osr.SpatialReference()
        source.ImportFromEPSG(4326)

        epsg = get_UTM_EPSG_code(city_coordinates[1])

        target = osr.SpatialReference()

        target.ImportFromEPSG(epsg)

        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(city_coordinates[1], city_coordinates[0])

        transform = osr.CoordinateTransformation(source, target)
        point.Transform(transform)

        city_coordinates_UTM = []

        city_coordinates_UTM.append([point.GetX() - 25000, point.GetY() + 25000])
        city_coordinates_UTM.append([point.GetX() + 25000, point.GetY() + 25000])
        city_coordinates_UTM.append([point.GetX() + 25000, point.GetY() - 25000])
        city_coordinates_UTM.append([point.GetX() - 25000, point.GetY() - 25000])
        city_coordinates_UTM.append(city_coordinates_UTM[0])

        city_coordinates_WGS84 = city_coordinates_UTM
        city_coordinates_UTM[:] = [transform_point(x, target, source) for x in city_coordinates_UTM]
        print(city)

        feature = {
            'type': 'Feature',
            'properties': {
                'country': city[0],
                'name-UTF8': city[1],
                'name-ASCII': city[2],
                'population': city[3],
            },
            'geometry': {
                'type': 'Polygon',
                'coordinates': [
                    city_coordinates_WGS84
                ]
            }
        }
        cities_json['features'].append(feature)

        with open('cities_areas.json', 'w', encoding='utf-8') as json_file:
            json.dump(cities_json, json_file, indent=4, sort_keys=True)

    # for coordinate in coordinates[0]:
    #     point = ogr.Geometry(ogr.wkbPoint)
    #     point.AddPoint(coordinate[0], coordinate[1])
    #     point.Transform(retransform)
    #     print([point.GetX(), point.GetY()])
    #     coordinate = [point.GetX(), point.GetY()]


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
    (1000000, 50.0),
    (750000, 50.0),
    (500000, 50.0),
    (250000, 50.0),
    (100000, 50.0),
    (75000, 50.0),
    (50000, 50.0),
]

cities = []

with open('cities.csv', encoding='utf-8') as csv_file:
    read_csv = csv.reader(csv_file, delimiter=',')
    next(read_csv, None)
    for row in read_csv:
        cities.append((row[0], row[1], row[2], int(row[3]), float(row[4]), float(row[5])))

# cities = aggregate_cities(breaks, cities)
generate_bounding_boxes(cities)

# write_geojson('cities.json', cities)
# write_csv('cities.csv', cities)

elapsed = (time.time() - start)
print('\033[92mElapsed time:\033[0m', str(timedelta(seconds=elapsed)))
