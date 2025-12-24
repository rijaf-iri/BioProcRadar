import os
import numpy as np
from datetime import datetime
from .misc import (
        load_yaml_file,
        format_out_msg,
        get_log_file
     )
from .filesdirs import (
        get_data_dates_dir,
        get_dir_date_range
     )
from .cdb import *

def update_rpolar_timerange(
        bioradar_dir, radar_id=1
    ):
    config_dir = os.path.join(
        bioradar_dir, 'BioConfigRadar'
    )
    dir_config = os.path.join(
        config_dir, 'config'
    )
    log_file = get_log_file(
        bioradar_dir, 'logs_polar', 'polar_data'
    )

    yaml_file = os.path.join(
        dir_config, 'config_datasets.yaml'
    )
    if not os.path.exists(yaml_file):
        msg = f'File does not exist: {yaml_file}'
        format_out_msg(msg, log_file)
        return None
    data_info = load_yaml_file(yaml_file)
    polar_id = f'polar_{radar_id}'
    polar_info = data_info['radar'][polar_id]
    dates_dir = get_data_dates_dir(polar_info)
    dates_dir = np.array(dates_dir)
    dates_dir = dates_dir[np.argsort(dates_dir)]
    mn_0, _ = get_dir_date_range(polar_info, dates_dir[0])
    _, mx_1 = get_dir_date_range(polar_info, dates_dir[-1])
    _update_rpolar_timerange(
        bioradar_dir, radar_id, mn_0, mx_1
    )

def _update_rpolar_timerange(
        bioradar_dir, radar_id,
        min_datetime, max_datetime
    ):
    cursor, conn = bioDBRadar(bioradar_dir)
    trg = queryDB_json(cursor,
            """
            SELECT start_time, end_time
            FROM rpolar_timerange
            WHERE radar_id=%s;
            """,
            (radar_id,)
        )

    if len(trg) == 0:
        executeSQLCmd(cursor,
            """
            INSERT INTO rpolar_timerange 
              (radar_id, start_time, end_time)
            VALUES 
              (%s, %s, %s);
            """,
            (radar_id, min_datetime, max_datetime)
        )
    else:
        if start_time < trg[0]['start_time']:
            executeSQLCmd(cursor,
                """
                UPDATE rpolar_timerange
                SET start_time = %s
                WHERE radar_id = %s;
                """,
                (min_datetime, radar_id)
            )

        if end_time > trg[0]['end_time']:
            executeSQLCmd(cursor,
                """
                UPDATE rpolar_timerange
                SET end_time = %s
                WHERE radar_id = %s;
                """,
                (max_datetime, radar_id)
            )

    cursor.close()
    conn.close()
    return 0
