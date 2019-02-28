import os
import netCDF4 as nC
import numpy as np
import png
import csv
import json
from osgeo import gdal, osr, ogr
import struct
# from PIL import Image

from operator import itemgetter
from datetime import timedelta
import time

from scipy.misc import imresize

# For code profiling
#
# Add a @profile decorator before function definition
# Run
# python "C:\Users\SR-CleanRoom\AppData\Local\Programs\Python\Python37\Scripts\kernprof.exe" -l -v run.py
#

def regrid(latitudes, longitudes, values, n):
    """
    Resamples input arrays to a (n, n)-sized array.

    :param latitudes:
    :param longitudes:
    :param values:
    :param n:
    :return:
    """

    nrows, ncols = n, n

    # TODO: Remove deprecated methods
    longitudes = imresize(longitudes, (nrows, ncols), interp='bilinear', mode='F')
    latitudes = imresize(latitudes, (nrows, ncols), interp='bilinear', mode='F')
    values = imresize(values, (nrows, ncols), interp='bicubic', mode='F')

    return longitudes, latitudes, values


def select_points(latitudes, longitudes, values, polygon_extent):
    """
    Selects points which are inside of the requested polygon_extent. Returns arrays clipped to the extent.

    :param latitudes:
    :param longitudes:
    :param values:
    :param polygon_extent:
    :return:
    """

    def clip_masked_array(arr):
        """
        Clips array to the unmasked cells. Returns clipped array.

        :param arr:
        :return:
        """
        si, se = np.where(~arr.mask)
        arr = arr[si.min():si.max() + 1, se.min():se.max() + 1]
        return arr

    if type(values) == np.ndarray:
        latitudes = np.ma.MaskedArray(latitudes)
        longitudes = np.ma.MaskedArray(longitudes)
        values = np.ma.MaskedArray(values)

    selected_latitudes = np.logical_and(latitudes > polygon_extent['min_lat'],
                                        latitudes < polygon_extent['max_lat'])
    selected_longitudes = np.logical_and(longitudes > polygon_extent['min_lon'],
                                         longitudes < polygon_extent['max_lon'])

    selected_latitudes_longitudes = np.logical_and(selected_latitudes, selected_longitudes)
    selected_latitudes_longitudes = np.invert(np.asarray(selected_latitudes_longitudes))

    latitudes.mask = selected_latitudes_longitudes
    longitudes.mask = selected_latitudes_longitudes
    values.mask = selected_latitudes_longitudes

    i = np.where(~latitudes.mask)

    if i[0].size > 4:
        latitudes = clip_masked_array(latitudes)
        longitudes = clip_masked_array(longitudes)
        values = clip_masked_array(values)

        latitudes = np.flip(latitudes, axis=0)
        longitudes = np.flip(longitudes, axis=0)
        values = np.flip(values, axis=0)

        return np.ma.copy(latitudes), np.ma.copy(longitudes), np.ma.copy(values)
    else:
        return None, None, None


def write_geotiff(latitudes, longitudes, values, filename):
    """
    Writes input array as a GeoTIFF file to disk. Requires latitudes and longitudes arrays to
    calculate the georeference.

    :param latitudes:
    :param longitudes:
    :param values:
    :param filename:
    :return:
    """

    filename += '.tiff'
    real_bbox = {'max_lon': np.max(longitudes),
                 'min_lon': np.min(longitudes),
                 'max_lat': np.max(latitudes),
                 'min_lat': np.min(latitudes),
                 }

    pixel_width = (real_bbox['max_lon'] - real_bbox['min_lon']) / longitudes.shape[1]
    pixel_height = (real_bbox['max_lat'] - real_bbox['min_lat']) / longitudes.shape[0]

    geo_transform = (real_bbox['min_lon'] - 0.5 * pixel_width,
                     pixel_width,
                     0,
                     real_bbox['max_lat'] + 0.5 * pixel_height,
                     0,
                     -pixel_height
                     )

    driver = gdal.GetDriverByName('GTiff')
    rows, cols = values.shape
    dataset = driver.Create(filename, cols, rows, 1, gdal.GDT_Float32)

    projection = osr.SpatialReference()
    projection.ImportFromEPSG(4326)
    projection_wkt = projection.ExportToWkt()
    dataset.SetProjection(projection_wkt)
    dataset.SetGeoTransform(geo_transform)
    dataset.GetRasterBand(1).WriteArray(values)
    dataset = None


def write_csv(latitudes, longitudes, values, filename):
    """
    Writes the input array as a CSV file to disk.
    :param latitudes:
    :param longitudes:
    :param values:
    :param filename:
    :return:
    """

    filename += '.csv'
    rows = zip(latitudes.ravel(), longitudes.ravel(), values.ravel())

    with open(filename, 'w') as file:
        writer = csv.writer(file)
        for row in rows:
            writer.writerow(row)


def write_png(values, filename):
    """
    Writes the input float32 array as a 16-bit double channel PNG.
    :param values:
    :param filename:
    :return:
    """

    filename += '.png'

    def float_to_split_hex(float_variable):
        hex_variable = hex(struct.unpack('<I', struct.pack('<f', float_variable))[0])
        return hex_variable[2:6], hex_variable[6:10]

    float_to_split_hex = np.vectorize(float_to_split_hex)
    values = np.ma.filled(values, np.nan)
    hex_array = float_to_split_hex(values)
    hex_array = [hex_array[0].tolist(), hex_array[1].tolist()]
    split_hex_array = []

    for row, i in enumerate(hex_array[0]):
        split_hex_array.append([])
        for element, j in enumerate(hex_array[0][row]):
            split_hex_array[row].append(int(hex_array[0][row][element], 16))
            split_hex_array[row].append(int(hex_array[1][row][element], 16))

    with open(filename, 'wb') as file:
        writer = png.Writer(width=values.shape[1],
                            height=values.shape[0],
                            bitdepth=16,
                            greyscale=True,
                            alpha=True, )
        writer.write(file, split_hex_array)


def read_png(filename):
    """
    Reads the input double-channel 16-bit PNG file as a float32 array.
    :param filename:
    :return:
    """
    filename += '.png'
    reader = png.Reader(filename).asDirect()
    values = []

    for row in reader[2]:
        z = list(zip(row[::2], row[1::2]))

        new_row = []
        for j in z:
            unpacked = struct.unpack('>f', struct.pack('>HH', j[0], j[1]))[0]
            new_row.append(unpacked)
        values.append(row)

    values = np.vstack(values)
    return values


def get_product_extent(nc_dataset):
    """
    Calculates the product extent from the NetCDF metadata. Returns a GeoJSON polygon feature.
    :param nc_dataset:
    :return:
    """
    nc_dataset_gml = nc_dataset[
        'METADATA/EOP_METADATA/om:featureOfInterest/eop:multiExtentOf/gml:surfaceMembers/gml:exterior'
    ]

    nc_dataset_gml = getattr(nc_dataset_gml, 'gml:posList')

    nc_dataset_gml = nc_dataset_gml.split(' ')
    nc_dataset_gml = [float(x) for x in nc_dataset_gml]
    nc_dataset_gml = list(zip(nc_dataset_gml[1::2], nc_dataset_gml[::2]))

    nc_dataset_gml[:] = [x for x in nc_dataset_gml if x[1] > 0]

    nc_dataset_geojson = {
        'type': 'Polygon',
        'coordinates': [
            nc_dataset_gml
        ]
    }

    nc_dataset_geojson = json.dumps(nc_dataset_geojson)
    nc_dataset_extent = ogr.CreateGeometryFromJson(nc_dataset_geojson)
    return nc_dataset_extent


def get_polygon_extent(polygon_coordinates):
    """
    Calculates a bounding box from a list of coordinates.

    :param polygon_coordinates:
    :return:
    """

    polygon_bbox = {
        'max_lat': max(polygon_coordinates, key=itemgetter(1))[1],
        'min_lat': min(polygon_coordinates, key=itemgetter(1))[1],
        'max_lon': max(polygon_coordinates, key=itemgetter(0))[0],
        'min_lon': min(polygon_coordinates, key=itemgetter(0))[0],
    }
    return polygon_bbox


def main():
    start = time.time()

    # Use if images are in the 'CURRENT_DIR/data/' directory
    # current_dir = os.path.dirname(os.path.abspath(__file__))
    current_dir = 'D:\\'

    # CURRENT_DIR/data/input/ <- put the input *.nc files here
    input_dir = os.path.join(current_dir, 'data', 'input')

    # CURRENT_DIR/data/output/ <- output files are saved here
    output_dir = os.path.join(current_dir, 'data', 'output')

    filepaths = [os.path.join(input_dir, file) for file in os.listdir(input_dir)]

    with open('cities_areas.json', encoding='utf-8') as f:
        cities_list = json.load(f)

    for filepath in filepaths:
        file = str(filepath.split('\\')[-1])
        input_file_attributes = file.split('_')
        output_file_attributes = {}

        ds = nC.Dataset(filepath, 'r')
        satellite_product_extent = get_product_extent(ds)

        if input_file_attributes[2] == 'L2':
            ds = ds['/PRODUCT']

            output_file_attributes['platform'] = input_file_attributes[0]
            output_file_attributes['level'] = input_file_attributes[2]
            output_file_attributes['product_type'] = input_file_attributes[4]
            output_file_attributes['sensing_date'] = input_file_attributes[7]

            for city in cities_list['features']:
                lons = np.ma.copy(ds.variables['longitude'][0, :, :])
                lats = np.ma.copy(ds.variables['latitude'][0, :, :])

                if output_file_attributes['product_type'] == 'CLOUD':
                    vals = np.ma.copy(ds.variables['cloud_optical_thickness'][0, :, :])
                    # vals_units = ds.variables['cloud_optical_thickness'].units
                    output_file_attributes['sensing_date'] = input_file_attributes[7]
                elif output_file_attributes['product_type'] == 'SO2':
                    vals = np.ma.copy(ds.variables['sulfurdioxide_total_vertical_column'][0, :, :])
                    # vals_units = ds.variables['sulfurdioxide_total_vertical_column'].units
                    output_file_attributes['sensing_date'] = input_file_attributes[9]
                elif output_file_attributes['product_type'] == 'O3':
                    vals = np.ma.copy(ds.variables['ozone_total_vertical_column'][0, :, :])
                    # vals_units = ds.variables['ozone_total_vertical_column'].units
                    output_file_attributes['sensing_date'] = input_file_attributes[10]
                else:
                    vals = None

                requested_small_bbox = get_polygon_extent(city['geometry']['coordinates'][0])
                requested_big_bbox = requested_small_bbox.copy()

                requested_big_bbox['min_lat'] -= 0.5
                requested_big_bbox['max_lat'] += 0.5
                requested_big_bbox['min_lon'] -= 0.5
                requested_big_bbox['max_lon'] += 0.5

                city_geojson = {
                    'type': 'Polygon',
                    'coordinates':
                        city['geometry']['coordinates']
                }
                city_geojson = json.dumps(city_geojson)

                city_extent = ogr.CreateGeometryFromJson(city_geojson)
                intersection = satellite_product_extent.Intersection(city_extent)

                if intersection.IsEmpty():
                    pass
                else:
                    output_file_attributes['city_country_code'] = city['properties']['country']
                    output_file_attributes['city_name'] = city['properties']['name-ASCII']

                    output_filename = str(output_file_attributes['city_country_code']) \
                        + '_' + str(output_file_attributes['city_name']) \
                        + '_' + str(output_file_attributes['platform']) \
                        + '_' + str(output_file_attributes['product_type']) \
                        + '_' + str(output_file_attributes['sensing_date'])

                    print(output_filename)

                    if not os.path.exists(os.path.join(output_dir, output_file_attributes['product_type'])):
                        os.makedirs(os.path.join(output_dir, output_file_attributes['product_type']))

                    output_filename = os.path.join(output_dir, output_file_attributes['product_type'], output_filename)

                    selected_lats, selected_lons, selected_vals = select_points(lats, lons, vals, requested_big_bbox)
                    selected_lats, selected_lons, selected_vals = regrid(selected_lats,
                                                                         selected_lons,
                                                                         selected_vals,
                                                                         100)

                    selected_lats, selected_lons, selected_vals = select_points(selected_lats,
                                                                                selected_lons,
                                                                                selected_vals,
                                                                                requested_small_bbox)
                    if selected_vals is not None:
                        selected_lats, selected_lons, selected_vals = regrid(selected_lats,
                                                                             selected_lons,
                                                                             selected_vals,
                                                                             30)

                        # write_csv(lats, lons, vals, output_filename)
                        write_geotiff(selected_lats, selected_lons, selected_vals, output_filename)
                        # write_png(vals, output_filename)

        elif input_file_attributes[2] == 'L1B':
            output_file_attributes['platform'] = input_file_attributes[0]
            output_file_attributes['level'] = input_file_attributes[2]
            output_file_attributes['product_type'] = input_file_attributes[4]
            output_file_attributes['sensing_date'] = input_file_attributes[10][:-3]

            if output_file_attributes['product_type'] == 'BD1':
                ds_obs = ds['/BAND1_RADIANCE/STANDARD_MODE/OBSERVATIONS']
                ds_geo = ds['/BAND1_RADIANCE/STANDARD_MODE/GEODATA']
            else:
                ds_obs = ds['/BAND2_RADIANCE/STANDARD_MODE/OBSERVATIONS']
                ds_geo = ds['/BAND2_RADIANCE/STANDARD_MODE/GEODATA']

            try:
                bands = ds_obs.variables['radiance'][0, :, :, :]
            except RuntimeError:
                pass
            else:
                cities_in_file = []
                for city in cities_list['features']:
                    city_geojson = {
                        'type': 'Polygon',
                        'coordinates':
                            city['geometry']['coordinates']
                    }
                    city_geojson = json.dumps(city_geojson)

                    city_extent = ogr.CreateGeometryFromJson(city_geojson)
                    intersection = satellite_product_extent.Intersection(city_extent)

                    if intersection.IsEmpty():
                        pass
                    else:
                        cities_in_file.append(city)

                for band in range(bands.shape[2]):
                    output_file_attributes['band'] = band

                    for city in cities_in_file:
                        lats = np.ma.copy(ds_geo.variables['latitude'][0, :, :])
                        lons = np.ma.copy(ds_geo.variables['longitude'][0, :, :])
                        vals = np.ma.copy(bands[:, :, band])

                        requested_small_bbox = get_polygon_extent(city['geometry']['coordinates'][0])
                        requested_big_bbox = requested_small_bbox.copy()

                        requested_big_bbox['min_lat'] -= 0.5
                        requested_big_bbox['max_lat'] += 0.5
                        requested_big_bbox['min_lon'] -= 0.5
                        requested_big_bbox['max_lon'] += 0.5

                        output_file_attributes['city_country_code'] = city['properties']['country']
                        output_file_attributes['city_name'] = city['properties']['name-ASCII']

                        output_filename = str(output_file_attributes['city_country_code']) \
                            + '_' + str(output_file_attributes['city_name']) \
                            + '_' + str(output_file_attributes['platform']) \
                            + '_' + str(output_file_attributes['product_type']) \
                            + '_' + str(output_file_attributes['sensing_date']) \
                            + '_' + str(output_file_attributes['band'])

                        print(output_filename)

                        if not os.path.exists(os.path.join(output_dir, output_file_attributes['product_type'])):
                            os.makedirs(os.path.join(output_dir, output_file_attributes['product_type']))

                        output_filename = os.path.join(output_dir,
                                                       output_file_attributes['product_type'],
                                                       output_filename)

                        selected_lats, selected_lons, selected_vals = select_points(lats,
                                                                                    lons,
                                                                                    vals,
                                                                                    requested_big_bbox)

                        selected_lats, selected_lons, selected_vals = regrid(selected_lats,
                                                                             selected_lons,
                                                                             selected_vals,
                                                                             100)

                        selected_lats, selected_lons, selected_vals = select_points(selected_lats,
                                                                                    selected_lons,
                                                                                    selected_vals,
                                                                                    requested_small_bbox)

                        if selected_vals is not None:
                            selected_lats, selected_lons, selected_vals = regrid(selected_lats,
                                                                                 selected_lons,
                                                                                 selected_vals,
                                                                                 30)

                            # write_csv(selected_lats, selected_lons, selected_vals, output_filename)
                            write_geotiff(selected_lats, selected_lons, selected_vals, output_filename)
                            # write_png(vals, output_filename)

                    partial_elapsed = (time.time() - start)
                    print('Band:', band)
                    print('Partial elapsed time:', str(timedelta(seconds=partial_elapsed)))
                    # print('\033[92mPartial elapsed time:\033[0m', str(timedelta(seconds=partial_elapsed)))

        partial_elapsed = (time.time() - start)
        print('File:', file)
        print('\033[92mPartial elapsed time:\033[0m', str(timedelta(seconds=partial_elapsed)))
        # print('\033[92mPartial elapsed time:\033[0m', str(timedelta(seconds=partial_elapsed)))

    total_elapsed = (time.time() - start)
    print('\033[92mElapsed time:\033[0m', str(timedelta(seconds=total_elapsed)))
    # print('\033[92mElapsed time:\033[0m', str(timedelta(seconds=total_elapsed)))


if __name__ == "__main__":
    main()
