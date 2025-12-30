import os
import numpy as np
from datetime import (
        datetime,
        timedelta,
        timezone
    )
from ..util import *
import BioModRadar as bmod
from .zarr_bioclass import (
        create_zarr_bioclass_dataset,
        update_zarr_bioclass_dataset
    )

def production_rwanda_bio(
        bioradar_dir, radar_id=1
    ):
    info = _get_info_bioclass(bioradar_dir, radar_id)
    if info is None:
        return None

    cursor, conn = bioDBRadar(bioradar_dir)
    t_end = queryDB_json(cursor,
            """
            SELECT end_time
            FROM bioclass_timerange
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

    data_files = _get_polar_files(
        info, start_time, end_time
    )
    if data_files is None:
        return None

    wrapper_rwanda_bios(
        bioradar_dir,
        data_files,
        radar_id,
        info
    )

def process_rwanda_bio(
        bioradar_dir, time, radar_id=1
    ):
    info = _get_info_bioclass(bioradar_dir, radar_id)
    if info is None:
        return None

    frmt = '%Y-%m-%d %H:%M:%S'
    time = datetime.strptime(time, frmt)
    dtime = timedelta(minutes=2)
    start_time = time - dtime
    start_time = start_time.strftime(frmt)
    end_time = time + dtime
    end_time = end_time.strftime(frmt)

    data_files = _get_polar_files(
        info, start_time, end_time
    )
    if data_files is None:
        return None

    wrapper_rwanda_bios(
        bioradar_dir,
        data_files,
        radar_id,
        info
    )

def process_rwanda_bios(
        bioradar_dir, start_time,
        end_time, radar_id=1
    ):
    info = _get_info_bioclass(bioradar_dir, radar_id)
    if info is None:
        return None
    data_files = _get_polar_files(
        info, start_time, end_time
    )
    if data_files is None:
        return None

    wrapper_rwanda_bios(
        bioradar_dir,
        data_files,
        radar_id,
        info
    )

def wrapper_rwanda_bios(
        bioradar_dir, data_files,
        radar_id, info
    ):
    fields_dict = {'ref': 'DBZH', 'zdr': 'ZDR',
                   'rho': 'RHOHV', 'phi': 'PHIDP',
                   'vel': 'VRADH', 'sw': 'WRADH'}
    volume_type = 'rwanda-odim-h5'
    sweeps = np.arange(0, 11)
    texture_fields = False
    features = ['DBZH', 'PHIDP', 'RHOHV', 'ZDR', 'VRADH', 'WRADH']
    # texture_fields = True
    # features = ['DBZH_MED', 'PHIDP_MED', 'RHOHV_MED', 'ZDR_MED', 'VRADH_MED', 'WRADH_MED']
    file_model = os.path.join(info['model']['dir'], info['model']['job'])
    fields_class = ['DR_CLASS', 'BIO_CLASS']

    ds_new = False
    if not os.path.isdir(info['class']['dir']):
        os.makedirs(info['class']['dir'])
        ds_new = True

    zarr_dirfile = info['class']['file'] % (radar_id)
    zarr_path = os.path.join(
        info['class']['dir'], zarr_dirfile
    )
    if not os.path.exists(zarr_path):
        ds_new = True

    for file_path in data_files:
        try:
            radar_mod, fields = bmod.build_features_predict(
                                        file_path,
                                        volume_type,
                                        sweeps,
                                        fields_dict,
                                        spatial_stat_fields=False,
                                        # spatial_stat_fields=True,
                                        texture_fields=texture_fields,
                                        dr_thres=-12,
                                        rho_thres=0.9,
                                        ref_thres=30
                                    )
            radar_mod = bmod.predict_ML_models(radar_mod, features, file_model)
            grid = bmod.grid_radar_data(radar_mod, fields_class, vertical_res=250.)
        except:
            continue

        if ds_new:
            create_zarr_bioclass_dataset(
                grid, zarr_path,
                info['class']['chunck']
            )
        else:
            update_zarr_bioclass_dataset(
                grid, zarr_path,
                info['class']['chunck']
            )

        _update_bioclass_timerange(
            bioradar_dir, zarr_path, radar_id
        )

    return 0

def _get_polar_files(info, start_time, end_time):
    data_files = get_data_files_list(
            info['polar'], start_time, end_time
        )
    if data_files is None:
        msg = 'No data found.'
        format_out_msg(msg, info['log_file'])
        return None

    path_files = []
    for d in data_files:
        data_dir = os.path.join(info['polar']['dir'], d['dir'])
        for f in d['files']:
            path_files += [os.path.join(data_dir, f)]
    return path_files

def _get_info_bioclass(bioradar_dir, radar_id):
    config_dir = os.path.join(
        bioradar_dir, 'BioConfigRadar'
    )
    dir_config = os.path.join(
        config_dir, 'config'
    )
    log_file = get_log_file(
        bioradar_dir, 'logs_bioclass', 'bio_zarr'
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
        'class': data_info['class'],
        'model': data_info['models'],
        'log_file': log_file
    }
