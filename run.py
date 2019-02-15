import os
import netCDF4 as nC
import numpy as np
import png
import csv
from osgeo import gdal, osr
import struct

# METADATA/EOP_METADATA/om:featureOfInterest/eop:multiExtentOf/gml:surfaceMembers/gml:exterior/:gml:posList

def clip_masked_array(arr):
    si, se = np.where(~arr.mask)
    arr = arr[si.min():si.max() + 1, se.min():se.max() + 1]
    return arr


def write_geotiff(latitudes, longitudes, values, filename):
    filename += '.tiff'
    # Use when clipping raw data to level 1
    real_bbox = {'max_lon': np.max(longitudes),
                 'min_lon': np.min(longitudes),
                 'max_lat': np.max(latitudes),
                 'min_lat': np.min(latitudes),
                 }

    pixel_width = (real_bbox['max_lon'] - real_bbox['min_lon']) / lons.shape[1]
    pixel_height = (real_bbox['max_lat'] - real_bbox['min_lat']) / lons.shape[0]

    geo_transform = (real_bbox['min_lon'] - 0.5 * pixel_width,
                     pixel_width,
                     0,
                     real_bbox['max_lat'] + 0.5 * pixel_height,
                     0,
                     -pixel_height
                     )

    # Use when clipping raw data to level 2
    # gcp_list = [
    #     gdal.GCP(float(longitudes[0][0]), float(latitudes[0][0]), 0.0, 1, 1),
    #     gdal.GCP(float(longitudes[0][-1]), float(latitudes[0][-1]), 0.0, 9, 1),
    #     gdal.GCP(float(longitudes[-1][-1]), float(latitudes[-1][-1]), 0.0, 9, 7),
    #     gdal.GCP(float(longitudes[-1][0]), float(latitudes[-1][0]), 0.0, 1, 7),
    # ]

    driver = gdal.GetDriverByName('GTiff')
    rows, cols = values.shape
    dataset = driver.Create(filename, cols, rows, 1, gdal.GDT_Float32)

    projection = osr.SpatialReference()
    projection.ImportFromEPSG(4326)
    projection_wkt = projection.ExportToWkt()
    dataset.SetProjection(projection_wkt)
    # geo_transform = gdal.GCPsToGeoTransform(gcp_list)
    dataset.SetGeoTransform(geo_transform)
    dataset.GetRasterBand(1).WriteArray(vals)
    dataset = None


def write_csv(latitudes, longitudes, values, filename):
    filename += '.csv'
    rows = zip(latitudes.ravel(), longitudes.ravel(), values.ravel())

    with open(filename, 'w') as file:
        writer = csv.writer(file)
        for row in rows:
            writer.writerow(row)


def write_png(values, filename):
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


# requested_bbox = {'max_lon': 17.22,
#                   'min_lon': 16.80,
#                   'max_lat': 51.22,
#                   'min_lat': 51.01}   # Output geographical extent

requested_bbox = {'max_lon': 17.50,
                  'min_lon': 16.50,
                  'max_lat': 51.50,
                  'min_lat': 50.50}

current_dir = 'D:\\'
# current_dir = os.path.dirname(os.path.abspath(__file__))  # Use if images are in the 'data' directory in the local dir
input_dir = os.path.join(current_dir, 'data', 'input')
output_dir = os.path.join(current_dir, 'data', 'output')

output_archive = {}

filepaths = [os.path.join(input_dir, file) for file in os.listdir(input_dir)]

for filepath in filepaths:

    file = filepath.split('\\')[-1]
    file_attributes = file.split('_')

    ds = nC.Dataset(filepath, "r")

    if file_attributes[2] == 'L2':

        attributes = {attribute: ds.getncattr(attribute) for attribute in ds.ncattrs()}
        variables = [variable for variable in ds['/PRODUCT'].variables.keys()]
        dimensions = [dimension for dimension in ds['/PRODUCT'].dimensions.keys()]

        output_attributes = {
            'platform': file_attributes[0],
            'level': file_attributes[2],
            'product_type': file_attributes[4],
            'sensing_date': file_attributes[7],
        }

        ds = ds['/PRODUCT']

        lons = ds.variables['longitude'][0, :, :]
        lats = ds.variables['latitude'][0, :, :]

        if output_attributes['product_type'] == 'CLOUD':
            vals = ds.variables['cloud_optical_thickness'][0, :, :]
            vals_units = ds.variables['cloud_optical_thickness'].units
            output_attributes['sensing_date'] = file_attributes[7]
        elif output_attributes['product_type'] == 'SO2':
            vals = ds.variables['sulfurdioxide_total_vertical_column'][0, :, :]
            vals_units = ds.variables['sulfurdioxide_total_vertical_column'].units
            output_attributes['sensing_date'] = file_attributes[9]
        elif output_attributes['product_type'] == 'O3':
            vals = ds.variables['ozone_total_vertical_column'][0, :, :]
            vals_units = ds.variables['ozone_total_vertical_column'].units
            output_attributes['sensing_date'] = file_attributes[10]

        # TODO: Change to os.path
        new_filename = output_dir + '\\' \
            + output_attributes['platform'] \
            + '_' + output_attributes['product_type'] \
            + '_' + output_attributes['sensing_date']

        array_name = output_attributes['platform'] \
            + '_' + output_attributes['product_type'] \
            + '_' + output_attributes['sensing_date'] \

        stacked_file = np.stack((lats, lons, vals))

        lat_select = np.logical_and(lats > requested_bbox['min_lat'], lats < requested_bbox['max_lat'])
        lon_select = np.logical_and(lons > requested_bbox['min_lon'], lons < requested_bbox['max_lon'])

        lonlat_select = np.logical_and(lon_select, lat_select)
        lonlat_select = np.invert(np.asarray(lonlat_select))

        lats.mask = lonlat_select
        lons.mask = lonlat_select
        vals.mask = lonlat_select

        lats = clip_masked_array(lats)
        lons = clip_masked_array(lons)
        vals = clip_masked_array(vals)

        lats = np.flip(lats, axis=0)
        lons = np.flip(lons, axis=0)
        vals = np.flip(vals, axis=0)

        # fig, axs = plt.subplots(nrows=3, ncols=1)
        # axs[0].imshow(lats)
        # axs[1].imshow(lons)
        # axs[2].imshow(vals)
        # plt.show()

        # for i, v in np.ndenumerate(lats):
        #     lat = lats[i[0]][i[1]]
        #     lon = lons[i[0]][i[1]]
        #     val = vals[i[0]][i[1]]
        #
        #     if lat < 51.265 and lon > 16.745:
        #         new_bbox = {'tl': i}
        #         print(new_bbox)
        #         break
        #
        # row = lats[new_bbox['tl'][0]]
        # for i, v in np.ndenumerate(row):
        #     lat = lats[new_bbox['tl'][0]][i]
        #     lon = lons[new_bbox['tl'][0]][i]
        #     val = vals[new_bbox['tl'][0]][i]
        #
        #     print(lat, lon, val)
        #
        #     if lat < 51.388 and lon > 17.210:
        #         new_bbox['tr'] = (new_bbox['tl'][0], i[0])
        #         print(new_bbox)
        #         break
        #
        # col = lats.T[new_bbox['tl'][1]]
        # for i, v in np.ndenumerate(col):
        #     lat = lats.T[new_bbox['tl'][1]][i]
        #     lon = lons.T[new_bbox['tl'][1]][i]
        #     val = vals.T[new_bbox['tl'][1]][i]
        #
        #     if lat < 50.861:
        #         new_bbox['dl'] = (i[0], new_bbox['tl'][1])
        #         print(new_bbox)
        #         break
        #
        # new_bbox['dr'] = (new_bbox['dl'][0], new_bbox['tr'][1])
        # print(new_bbox)

        # write_csv(lats[new_bbox['tl'][0]:new_bbox['dl'][0], new_bbox['dl'][1]:new_bbox['dr'][1]],
        #           lons[new_bbox['tl'][0]:new_bbox['dl'][0], new_bbox['dl'][1]:new_bbox['dr'][1]],
        #           vals[new_bbox['tl'][0]:new_bbox['dl'][0], new_bbox['dl'][1]:new_bbox['dr'][1]],
        #           new_filename)
        #
        # write_geotiff(lats[new_bbox['tl'][0]:new_bbox['dl'][0], new_bbox['dl'][1]:new_bbox['dr'][1]],
        #               lons[new_bbox['tl'][0]:new_bbox['dl'][0], new_bbox['dl'][1]:new_bbox['dr'][1]],
        #               vals[new_bbox['tl'][0]:new_bbox['dl'][0], new_bbox['dl'][1]:new_bbox['dr'][1]],
        #               new_filename)

        write_csv(lats, lons, vals, new_filename)
        # write_geotiff(lats, lons, vals, new_filename)
        # write_png(vals, new_filename)

        print(array_name)
        ds = None

    elif file_attributes[2] == 'L1B':
        if file_attributes[4] == 'BD1' or file_attributes[4] == 'BD2':
            output_attributes = {
                'platform': file_attributes[0],
                'level': file_attributes[2],
                'product_type': file_attributes[4],
                'sensing_date': file_attributes[10][:-3],
            }

            if file_attributes[4] == 'BD1':
                ds_obs = ds['/BAND1_RADIANCE/STANDARD_MODE/OBSERVATIONS']
                ds_geo = ds['/BAND1_RADIANCE/STANDARD_MODE/GEODATA']

                output_bbox = requested_bbox.copy()
                output_bbox['max_lon'] += 0.32
                output_bbox['min_lon'] -= 0.10
                output_bbox['max_lat'] += 0.10
                output_bbox['min_lat'] -= 0.10
            else:
                ds_obs = ds['/BAND2_RADIANCE/STANDARD_MODE/OBSERVATIONS']
                ds_geo = ds['/BAND2_RADIANCE/STANDARD_MODE/GEODATA']

                output_bbox = requested_bbox.copy()

            slices = ds_obs.variables['radiance'][0, :, :, :]

            for band in range(slices.shape[2]):
                lons = ds_geo.variables['longitude'][0, :, :]
                lats = ds_geo.variables['latitude'][0, :, :]
                vals = slices[:, :, band]

                output_attributes['band'] = band

                new_filename = output_dir + '\\' \
                    + output_attributes['platform'] \
                    + '_' + output_attributes['product_type'] \
                    + '_' + output_attributes['sensing_date'] \
                    + '_' + str(output_attributes['band'])

                array_name = output_attributes['platform'] \
                    + '_' + output_attributes['product_type'] \
                    + '_' + output_attributes['sensing_date'] \
                    + '_' + str(output_attributes['band']) \

                stacked_file = np.stack((lats, lons, vals))

                lat_select = np.logical_and(lats > output_bbox['min_lat'], lats < output_bbox['max_lat'])
                lon_select = np.logical_and(lons > output_bbox['min_lon'], lons < output_bbox['max_lon'])

                lonlat_select = np.logical_and(lon_select, lat_select)
                lonlat_select = np.invert(np.asarray(lonlat_select))

                lats.mask = lonlat_select
                lons.mask = lonlat_select
                vals.mask = lonlat_select

                lats = clip_masked_array(lats)
                lons = clip_masked_array(lons)
                vals = clip_masked_array(vals)

                lats = np.flip(lats, axis=0)
                lons = np.flip(lons, axis=0)
                vals = np.flip(vals, axis=0)

                write_csv(lats, lons, vals, new_filename)
                # write_geotiff(lats, lons, vals, new_filename)
                # write_png(vals, new_filename)

                print(array_name)
                ds = None
