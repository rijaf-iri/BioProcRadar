import os
import re
import numpy as np
import xarray as xr
from datetime import (
        datetime,
        timedelta,
        timezone
    )
from ..util import *
from .zarr_vids import (
        create_zarr_vid_dataset,
        update_zarr_vid_dataset
    )

def production_rwanda_vid(
        bioradar_dir, radar_id=1
    ):
    info = _get_info_vids(bioradar_dir)
    if info is None:
        return None

    cursor, conn = bioDBRadar(bioradar_dir)
    t_end = queryDB_json(cursor,
            """
            SELECT end_time
            FROM vid_timerange
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

    date_times = split_start_end_time(
        start_time, end_time, 1
    )
    for times in date_times:
        info1 = info.copy()
        wrapper_rwanda_vids(
            bioradar_dir,
            times['start'],
            times['end'],
            radar_id,
            info1['vid_info'],
            info1['zarr_info'],
            info1['log_file']
        )
    return 0

def process_rwanda_vid(
        bioradar_dir, time, radar_id=1
    ):
    info = _get_info_vids(bioradar_dir)
    if info is None:
        return None

    frmt = '%Y-%m-%d %H:%M:%S'
    time = datetime.strptime(time, frmt)
    dtime = timedelta(minutes=2)
    start_time = time - dtime
    start_time = start_time.strftime(frmt)
    end_time = time + dtime
    end_time = end_time.strftime(frmt)

    wrapper_rwanda_vids(
        bioradar_dir,
        start_time,
        end_time,
        radar_id,
        info['vid_info'],
        info['zarr_info'],
        info['log_file']
    )

def process_rwanda_vids(
        bioradar_dir, start_time,
        end_time, radar_id=1
    ):
    info = _get_info_vids(bioradar_dir)
    if info is None:
        return None

    date_times = split_start_end_time(
        start_time, end_time, 1
    )
    for times in date_times:
        info1 = info.copy()
        wrapper_rwanda_vids(
            bioradar_dir,
            times['start'],
            times['end'],
            radar_id,
            info1['vid_info'],
            info1['zarr_info'],
            info1['log_file']
        )
    return 0

def wrapper_rwanda_vids(
        bioradar_dir, start_time,
        end_time, radar_id,
        vid_info, zarr_info,
        log_file
    ):
    vid_bird = get_vid_species_files(
        'bird', vid_info, start_time,
        end_time, radar_id
    )
    if vid_bird is None:
        msg = 'No bird VID netCDF file found for time'
        msg = f'{msg} from {start_time} to {end_time}'
        format_out_msg(msg, log_file)
        return None

    vid_insect = get_vid_species_files(
        'insect', vid_info, start_time,
        end_time, radar_id
    )
    if vid_insect is None:
        msg = 'No insect VID netCDF file found for time'
        msg = f'{msg} from {start_time} to {end_time}'
        format_out_msg(msg, log_file)
        return None

    ds_new = False
    if not os.path.isdir(zarr_info['dir']):
        os.makedirs(zarr_info['dir'])
        ds_new = True

    zarr_dirfile = zarr_info['file'] % (radar_id)
    zarr_path = os.path.join(
        zarr_info['dir'], zarr_dirfile
    )
    if not os.path.exists(zarr_path):
        ds_new = True

    if ds_new:
        create_zarr_vid_dataset(
            vid_insect['files'],
            vid_bird['files'],
            zarr_path,
            zarr_info['chunck']
        )
    else:
        update_zarr_vid_dataset(
            vid_insect,
            vid_bird,
            zarr_path,
            zarr_info['chunck']
        )

    _update_vid_timerange(
        bioradar_dir, zarr_path, radar_id
    )

    _clean_vids_nc(
        vid_insect['files'],
        vid_bird['files']
    )
    return 0

def _get_info_vids(bioradar_dir):
    config_dir = os.path.join(
        bioradar_dir, 'BioConfigRadar'
    )
    dir_config = os.path.join(
        config_dir, 'config'
    )
    log_file = get_log_file(
        bioradar_dir, 'logs_vid', 'vid_zarr'
    )

    yaml_file = os.path.join(
        dir_config, 'config_datasets.yaml'
    )
    if not os.path.exists(yaml_file):
        msg = f'File does not exist: {yaml_file}'
        format_out_msg(msg, log_file)
        return None

    data_info = load_yaml_file(yaml_file)
    vid_info = data_info['vertical']['sevip']
    zarr_info = data_info['vertical']['zarr']
    return {
        'vid_info': vid_info,
        'zarr_info': zarr_info,
        'log_file': log_file
    }

def get_vid_species_files(
        species, vid_info, start_time,
        end_time, radar_id
    ):
    vid_species = vid_info.copy()
    vid_species['dir'] = os.path.join(
        vid_species['dir'], f'radar_{radar_id}'
    )
    vid_species['pattern'] = vid_species['pattern'] % (species)
    vid_species['pattern1'] = vid_species['pattern']
    vid_species['format_file'] = re.sub(
        r'\*', species, vid_species['format_file']
    )
    species_files = get_data_files_list(
        vid_species, start_time, end_time
    )
    if species_files is None:
        return None

    path_files = []
    for d in species_files:
        radar_dir = f'radar_{radar_id}'
        data_dir = os.path.join(
            vid_info['dir'], radar_dir, d['dir']
        )
        for f in d['files']:
            path_files += [os.path.join(data_dir, f)]

    file_names = [
        os.path.basename(f) for f in path_files
    ]
    #### 
    # dates = extract_filename_dates(
    #     file_names, vid_species['format_file']
    # )
    # dates = datetime.strptime(dates, '%Y%m%d%H%M%S')
    #### 
    dates = [
        datetime.strptime(
            f, vid_species['format_file']
        ) for f in file_names
    ]
    return {'files': path_files, 'dates': dates}

def _clean_vids_nc(insect_files, bird_files):
    for f in insect_files:
        os.remove(f)
    for f in bird_files:
        os.remove(f)
    insect_dir = [
        os.path.dirname(f)
        for f in insect_files
    ]
    bird_dir = [
        os.path.dirname(f)
        for f in bird_files
    ]
    species_dir = insect_dir + bird_dir
    species_dir = list(set(species_dir))
    for d in species_dir:
        if not os.listdir(d):
            os.rmdir(d)

def _update_vid_timerange(
        bioradar_dir, zarr_path, radar_id
    ):
    ds = xr.open_zarr(
        zarr_path, consolidated=False
    )
    t_max = ds.time.max().values
    t_max = t_max.astype('datetime64[s]')
    end_time = t_max.astype(datetime)
    t_min = ds.time.min().values
    t_min = t_min.astype('datetime64[s]')
    start_time = t_min.astype(datetime)

    cursor, conn = bioDBRadar(bioradar_dir)

    trg = queryDB_json(cursor,
            """
            SELECT start_time, end_time
            FROM vid_timerange
            WHERE radar_id=%s;
            """,
            (radar_id,)
        )

    if len(trg) == 0:
        executeSQLCmd(cursor,
            """
            INSERT INTO vid_timerange 
              (radar_id, start_time, end_time)
            VALUES 
              (%s, %s, %s);
            """,
            (radar_id, start_time, end_time)
        )
    else:
        if start_time < trg[0]['start_time']:
            executeSQLCmd(cursor,
                """
                UPDATE vid_timerange
                SET start_time = %s
                WHERE radar_id = %s;
                """,
                (start_time, radar_id)
            )

        if end_time > trg[0]['end_time']:
            executeSQLCmd(cursor,
                """
                UPDATE vid_timerange
                SET end_time = %s
                WHERE radar_id = %s;
                """,
                (end_time, radar_id)
            )

    cursor.close()
    conn.close()
    return 0

