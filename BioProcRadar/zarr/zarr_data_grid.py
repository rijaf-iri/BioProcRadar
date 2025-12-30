import copy
import numpy as np
import xarray as xr
import netCDF4 as nc
from psycopg2 import sql
from datetime import datetime
from ..util import *

def create_zarr_data_grid(
        grid, zarr_path, zarr_chunk
    ):
    ds = data_grid_convert_ds(grid)
    ds = ds.chunk(zarr_chunk)
    ds.to_zarr(
        zarr_path,
        mode='w',
        consolidated=False,
        zarr_format=3
    )

def update_zarr_data_grid(
        grid, zarr_path, zarr_chunk
    ):
    ds = xr.open_zarr(
        zarr_path, consolidated=False
    )
    ds_g = data_grid_convert_ds(grid)
    new_ds = data_grid_append_ds(
        ds.time.values, ds_g.time.values
    )
    ds_g = ds_g.chunk(zarr_chunk)
    if new_ds:
        ds_g.to_zarr(
            zarr_path,
            append_dim='time',
            consolidated=False,
            zarr_format=3
        )
    else:
        t_idx = np.where(np.in1d(
            ds.time.values,
            ds_g.time.values
        ))[0]
        t_idx = int(t_idx[0])
        ds_g.to_zarr(
            zarr_path,
            mode='r+',
            region={
                'time': slice(t_idx, t_idx + 1),
                'z': slice(0, ds.sizes['z']),
                'y': slice(0, ds.sizes['y']),
                'x': slice(0, ds.sizes['x']),
                'nradar': slice(0, ds.sizes['nradar'])
            },
            consolidated=False,
            zarr_format=3
        )

def data_grid_convert_ds(grid):
    time_encoding = data_grid_time_encoding()
    grd = copy.deepcopy(grid)
    grd.time['data'] = np.array([0])
    time_cf = nc.num2date(
        grd.time['data'][0],
        units=grd.time['units'],
        calendar=grd.time['calendar']
    )
    time_num = nc.date2num(
        time_cf,
        units=time_encoding['units'],
        calendar=time_encoding['calendar']
    )
    grd.time['data'] = np.array([time_num])
    grd.time['units'] = time_encoding['units']
    grd.time['calendar'] = time_encoding['calendar']
    ds_tmp = grd.to_xarray()
    ds_tmp = ds_tmp.drop_vars('ROI', errors='raise')
    ds_tmp = ds_tmp.drop_vars(
        ['ProjectionCoordinateSystem', 'projection']
    )
    for v in list(ds_tmp.data_vars.keys()):
        del ds_tmp[v].attrs['_FillValue']

    ds_tmp['time'] = ds_tmp['time'].astype('datetime64[s]')
    ds_tmp['time'] = ds_tmp['time'].astype(time_encoding['dtype'])
    return ds_tmp

def data_grid_append_ds(ds_time, grid_time):
    gd_dt = grid_time[0]
    return not gd_dt in ds_time

def data_grid_time_encoding():
    return {
        'units': 'seconds since 1970-01-01T00:00:00Z',
        'calendar': 'standard',
        'dtype': 'int64'
    }

def update_timerange_data_grid(
        bioradar_dir, zarr_path,
        table_name, radar_id
    ):
    time_encoding = data_grid_time_encoding()
    ds = xr.open_zarr(
        zarr_path, consolidated=False
    )
    t_max = nc.num2date(
        ds.time.max().values,
        units=time_encoding['units'],
        calendar=time_encoding['calendar']
    )
    end_time = cftime2datetime(t_max)
    t_min = nc.num2date(
        ds.time.min().values,
        units=time_encoding['units'],
        calendar=time_encoding['calendar']
    )
    start_time = cftime2datetime(t_min)

    cursor, conn = bioDBRadar(bioradar_dir)

    tab_name = sql.Identifier(table_name)

    query = sql.SQL(
        """
        SELECT start_time, end_time
        FROM {}
        WHERE radar_id=%s;
        """
    ).format(tab_name)
    trg = queryDB_json(
        cursor, query, (radar_id,)
    )

    if len(trg) == 0:
        sqlCmd = sql.SQL(
            """
            INSERT INTO {} 
              (radar_id, start_time, end_time)
            VALUES 
              (%s, %s, %s);
            """
        ).format(tab_name)
        executeSQLCmd(
            cursor, sqlCmd,
            (radar_id, start_time, end_time)
        )
    else:
        if start_time < trg[0]['start_time']:
            sqlCmd = sql.SQL(
                """
                UPDATE {}
                SET start_time = %s
                WHERE radar_id = %s;
                """
            ).format(tab_name)
            executeSQLCmd(
                cursor, sqlCmd,
                (start_time, radar_id)
            )

        if end_time > trg[0]['end_time']:
            sqlCmd = sql.SQL(
                """
                UPDATE {}
                SET end_time = %s
                WHERE radar_id = %s;
                """
            ).format(tab_name)
            executeSQLCmd(
                cursor, sqlCmd,
                (end_time, radar_id)
            )

    cursor.close()
    conn.close()
    return 0
