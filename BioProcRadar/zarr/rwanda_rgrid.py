import os
import numpy as np
from datetime import (
        datetime,
        timedelta,
        timezone
    )
import BioModRadar as bmod
from ..util import *
from .zarr_data_grid import (
        create_zarr_data_grid,
        update_zarr_data_grid,
        update_timerange_data_grid
    )

def production_rwanda_rgrid(
        bioradar_dir, radar_id=1
    ):
    info = _get_info_rgrid(bioradar_dir, radar_id)
    if info is None:
        return None

    cursor, conn = bioDBRadar(bioradar_dir)
    t_end = queryDB_json(cursor,
            """
            SELECT end_time
            FROM rgrid_timerange
            WHERE radar_id=%s;
            """,
            (radar_id,)
        )
    cursor.close()
    conn.close()

    frmt = '%Y-%m-%d %H:%M:%S'
    t_end = t_end[0]['end_time']
    start_time = t_end + timedelta(seconds=1)
    start_time = start_time.strftime(frmt)
    end_time = datetime.now(timezone.utc)
    end_time = end_time.strftime(frmt)

    data_files = get_polar_path_files(
        info['polar'], start_time, end_time
    )
    if data_files is None:
        msg = 'No data found.'
        format_out_msg(msg, info['log_file'])
        return None

    wrapper_rwanda_rgrids(
        bioradar_dir,
        data_files,
        radar_id,
        info
    )

def process_rwanda_rgrid(
        bioradar_dir, time, radar_id=1
    ):
    info = _get_info_rgrid(bioradar_dir, radar_id)
    if info is None:
        return None

    frmt = '%Y-%m-%d %H:%M:%S'
    time = datetime.strptime(time, frmt)
    dtime = timedelta(minutes=2)
    start_time = time - dtime
    start_time = start_time.strftime(frmt)
    end_time = time + dtime
    end_time = end_time.strftime(frmt)

    data_files = get_polar_path_files(
        info['polar'], start_time, end_time
    )
    if data_files is None:
        msg = 'No data found.'
        format_out_msg(msg, info['log_file'])
        return None

    wrapper_rwanda_rgrids(
        bioradar_dir,
        data_files,
        radar_id,
        info
    )

def process_rwanda_rgrids(
        bioradar_dir, start_time,
        end_time, radar_id=1
    ):
    info = _get_info_rgrid(bioradar_dir, radar_id)
    if info is None:
        return None

    data_files = get_polar_path_files(
        info['polar'], start_time, end_time
    )
    if data_files is None:
        msg = 'No data found.'
        format_out_msg(msg, info['log_file'])
        return None

    wrapper_rwanda_rgrids(
        bioradar_dir,
        data_files,
        radar_id,
        info
    )

def wrapper_rwanda_rgrids(
        bioradar_dir, data_files,
        radar_id, info
    ):
    fields_dict = {'ref': 'DBZH', 'zdr': 'ZDR',
                   'rho': 'RHOHV', 'phi': 'PHIDP',
                   'vel': 'VRADH', 'sw': 'WRADH'}
    volume_type = 'rwanda-odim-h5'
    sweeps = np.arange(0, 11)

    ds_new = False
    if not os.path.isdir(info['grid']['dir']):
        os.makedirs(info['grid']['dir'])
        ds_new = True

    zarr_dirfile = info['grid']['file'] % (radar_id)
    zarr_path = os.path.join(
        info['grid']['dir'], zarr_dirfile
    )
    if not os.path.exists(zarr_path):
        ds_new = True

    for file_path in data_files:
        try:
            radar = bmod.read_radar_data(
                file_path, sweeps,
                volume_type, fields_dict
            )
            grid = bmod.grid_radar_data(
                radar,
                list(radar.fields),
                vertical_res=250.
            )
        except:
            continue

        if ds_new:
            create_zarr_data_grid(
                grid, zarr_path,
                info['grid']['chunck']
            )
        else:
            update_zarr_data_grid(
                grid, zarr_path,
                info['grid']['chunck']
            )

        update_timerange_data_grid(
            bioradar_dir, zarr_path,
            'rgrid_timerange', radar_id
        )

    return 0

def _get_info_rgrid(bioradar_dir, radar_id):
    config_dir = os.path.join(
        bioradar_dir, 'BioConfigRadar'
    )
    dir_config = os.path.join(
        config_dir, 'config'
    )
    log_file = get_log_file(
        bioradar_dir, 'logs_grid', 'grid_zarr'
    )

    yaml_file = os.path.join(
        dir_config, 'config_datasets.yaml'
    )
    if not os.path.exists(yaml_file):
        msg = f'File does not exist: {yaml_file}'
        format_out_msg(msg, log_file)
        return None

    data_info = load_yaml_file(yaml_file)
    polar_info = data_info['radar'][f'polar_{radar_id}']
    return {
        'polar': polar_info,
        'grid': data_info['grid'],
        'log_file': log_file
    }
