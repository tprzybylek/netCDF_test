import csv
import json
import copy
import geopy.distance

population = []
location = []

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
}

with open('cities_population.csv', encoding='utf-8') as csv_file:
    read_csv = csv.reader(csv_file, delimiter=',')
    for row in read_csv:
        population.append(row)

for big_city in population:
    if int(big_city[3]) > 750000:
        big_city_coordinates = (big_city[4], big_city[5])
        big_city_name = big_city[1]

        population_copy = copy.copy(population)

        for city in population_copy:
            city_coordinates = (city[4], city[5])
            city_name = city[1]
            distance = geopy.distance.geodesic(big_city_coordinates, city_coordinates).km

            if distance < 40.0 and city_name != big_city_name:
                print(big_city[0], big_city[1], city[1], distance)
                population.remove(city)

print('### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###')

for big_city in population:
    if int(big_city[3]) > 500000:
        big_city_coordinates = (big_city[4], big_city[5])
        big_city_name = big_city[1]

        population_copy = copy.copy(population)

        for city in population_copy:
            city_coordinates = (city[4], city[5])
            city_name = city[1]
            distance = geopy.distance.geodesic(big_city_coordinates, city_coordinates).km

            if distance < 35.0 and city_name != big_city_name:
                print(big_city[0], big_city[1], city[1], distance)
                population.remove(city)

print('### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###')

for big_city in population:
    if int(big_city[3]) > 250000:
        big_city_coordinates = (big_city[4], big_city[5])
        big_city_name = big_city[1]

        population_copy = copy.copy(population)

        for city in population_copy:
            city_coordinates = (city[4], city[5])
            city_name = city[1]
            distance = geopy.distance.geodesic(big_city_coordinates, city_coordinates).km

            if distance < 30.0 and city_name != big_city_name:
                print(big_city[0], big_city[1], city[1], distance)
                population.remove(city)

print('### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###')

for big_city in population:
    if int(big_city[3]) > 100000:
        big_city_coordinates = (big_city[4], big_city[5])
        big_city_name = big_city[1]

        population_copy = copy.copy(population)

        for city in population_copy:
            city_coordinates = (city[4], city[5])
            city_name = city[1]
            distance = geopy.distance.geodesic(big_city_coordinates, city_coordinates).km

            if distance < 25.0 and city_name != big_city_name:
                print(big_city[0], big_city[1], city[1], distance)
                population.remove(city)

for big_city in population:
    if int(big_city[3]) > 75000:
        big_city_coordinates = (big_city[4], big_city[5])
        big_city_name = big_city[1]

        population_copy = copy.copy(population)

        for city in population_copy:
            city_coordinates = (city[4], city[5])
            city_name = city[1]
            distance = geopy.distance.geodesic(big_city_coordinates, city_coordinates).km

            if distance < 20.0 and city_name != big_city_name:
                print(big_city[0], big_city[1], city[1], distance)
                population.remove(city)

population_json = {
    'type': 'FeatureCollection',
    'features': [],
}

for row in population:
    feature = {
        'type': 'Feature',
        'properties': {
            'country': row[0],
            'name': row[1],
            'population': row[3],
        },
        'geometry': {
            'type': 'Point',
            'coordinates': [
                float(row[5]),
                float(row[4])
            ]
        }
    }
    population_json['features'].append(feature)

with open('cities.json', 'w', encoding='utf-8') as json_file:
    json.dump(population_json, json_file)

with open('cities.csv', 'w', newline='', encoding='utf-8') as csv_file:
    write_csv = csv.writer(csv_file, delimiter=',')
    write_csv.writerow(['Country', 'City-UTF8', 'City-ASCII', 'Population', 'Latitude', 'Longitude'])
    write_csv.writerows(population)


