import os
import yaml
from datetime import datetime, timedelta

def format_out_msg(msg, log_file, append=True):
    dates = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    hr = '*********************************'
    mode = 'a' if append else 'w'
    with open(log_file, mode) as file:
        file.write(f'Time: {dates}\n{msg}{hr}\n')

def get_log_file(bioradar_dir, log_dir, prefix):
    dir_log = os.path.join(
        bioradar_dir, 'BioDataRadar', log_dir
    )
    if not os.path.isdir(dir_log):
        os.makedirs(dir_log)
    date_log = datetime.now().strftime('%Y%m%d')
    file_log = f'{prefix}_{date_log}.txt'
    path_log = os.path.join(dir_log, file_log)
    return path_log

def load_yaml_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            conf = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f'Error {e}')
    return conf

def split_start_end_time(
        start_time, end_time, step_hour
    ):
    frmt = '%Y-%m-%d %H:%M:%S'
    start_time = datetime.strptime(start_time, frmt)
    end_time = datetime.strptime(end_time, frmt)
    intervals = []
    current = start_time
    one_hour = timedelta(hours=step_hour)

    i = 0
    while current < end_time:
        interval_start = current
        interval_end = current + one_hour
        if i > 0:
            interval_start = interval_start + timedelta(seconds=1)
        if interval_end > end_time:
            interval_end = end_time
        intervals.append({
            'start': interval_start.strftime(frmt),
            'end': interval_end.strftime(frmt)
        })
        current = interval_end
        # current = current + one_hour
        i += 1

    return intervals
