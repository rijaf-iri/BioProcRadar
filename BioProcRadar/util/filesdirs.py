import os
import re
import glob
from datetime import datetime

def get_data_dates_dir(data_info):
    dates_dir = data_info['dir']
    dates_dir = [
        os.path.join(dates_dir, d)
        for d in os.listdir(dates_dir)
    ]
    if len(dates_dir) == 0:
        return None
    dates_dir = [
        os.path.basename(d)
        for d in dates_dir
        if os.path.isdir(d)
    ]
    if len(dates_dir) == 0:
        return None
    tmp_path = []
    for d in dates_dir:
        try:
            tmp = datetime.strptime(
                d, data_info['format_dir']
            )
            tmp_path += [d]
        except:
            continue
    if len(tmp_path) == 0:
        return None

    return tmp_path

def get_data_file_path(data_info, time_str):
    format_time = '%Y-%m-%d %H:%M:%S'
    time_req = datetime.strptime(time_str, format_time)
    date_dir = time_req.strftime(data_info['format_dir'])
    data_dir = os.path.join(data_info['dir'], date_dir)
    if not os.path.isdir(data_dir):
        return None
    data_files = glob.glob(
        f'{data_dir}/{data_info['pattern']}'
    )
    if len(data_files) == 0:
        return None
    data_files = [
        os.path.basename(p)
        for p in data_files
    ]
    date_files = extract_filename_dates(
        data_files, data_info['format_file']
    )
    if len(date_files) == 0:
        return None
    it = [d is None for d in date_files]
    if all(it):
        return None
    data_files = [
        data_files[i] for i, j in enumerate(it) if not j
    ]
    date_files = [
        date_files[i] for i, j in enumerate(it) if not j
    ]
    date_files = [
        datetime.strptime(f, '%Y%m%d%H%M%S')
        for f in date_files
    ]
    it = min(
        range(len(date_files)),
        key=lambda i: abs(date_files[i] - time_req)
    )
    file = data_files[it]

    return os.path.join(data_dir, file)

def get_data_files_list(data_info, start_time, end_time):
    format_time = '%Y-%m-%d %H:%M:%S'
    start = datetime.strptime(start_time, format_time)
    end = datetime.strptime(end_time, format_time)
    start_date = start.date()
    end_date = end.date()

    dates_dir = get_data_dates_dir(data_info)
    if dates_dir is None:
        return None
    dt_dir = [
        datetime.strptime(d, data_info['format_dir'])
        for d in dates_dir
    ]
    dt_dir = [d.date() for d in  dt_dir]
    it = [
        d >= start_date and d <= end_date
        for d in dt_dir
    ]
    if not any(it):
        return None
    dates_dir = [
        dates_dir[i] for i, j in enumerate(it) if j
    ]

    list_out = []
    for d in dates_dir:
        data_dir = os.path.join(data_info['dir'], d)
        data_files = glob.glob(
            f'{data_dir}/{data_info['pattern']}'
        )
        if len(data_files) == 0:
            continue
        data_files = sorted([
            os.path.basename(p) for p in data_files
        ])
        date_files = extract_filename_dates(
            data_files, data_info['format_file']
        )
        if len(date_files) == 0:
            continue
        it = [d is None for d in date_files]
        if all(it):
            continue
        data_files = [
            data_files[i] for i, j in enumerate(it) if not j
        ]
        date_files = [
            date_files[i] for i, j in enumerate(it) if not j
        ]
        date_files = [
            datetime.strptime(f, '%Y%m%d%H%M%S')
            for f in date_files
        ]

        it = [t >= start and t <= end for t in date_files]
        if not any(it):
            continue
        data_files = [
            data_files[i] for i, j in enumerate(it) if j
        ]
        list_out += [{'dir': d, 'files': data_files}]
    if len(list_out) == 0:
        return None

    return list_out

def double_backslash_non_alnum(s):
    return re.sub(r'([^A-Za-z0-9])', r'\\\1', s)

def double_backslash_non_alnum_list(strings):
    if isinstance(strings, str):
        strings = [strings]
    escaped = []
    for s in strings:
        for v in set(re.findall(r'[^A-Za-z0-9]', s)):
            s = s.replace(v, '\\' + v)
        escaped.append(s)
    return escaped

def extract_filename_dates(filenames, fileformat):
    expr = [
        m.start() for m in re.finditer('%', fileformat)
    ]
    length_expr = [2] * len(expr)
    ret = []
    if expr:
        rr = [False]
        ss = [1]
        se = [len(fileformat)]
        nl = len(expr)
        for i in range(nl):
            rr += [True, False]
            ss += [expr[i] + 1, expr[i] + length_expr[i] + 1]
            j = nl - i - 1
            se = [expr[j], expr[j] + length_expr[j]] + se

        res = []
        for i in range(len(rr)):
            v = fileformat[ss[i]-1:se[i]]
            if v == '' or rr[i]:
                continue
            res.append(v)

        if res:
            res = list(dict.fromkeys(res))
            # res = [double_backslash_non_alnum(r) for r in res]
            res = double_backslash_non_alnum_list(res)
            pattern = re.sub(r'\\\*', '.+', '|'.join(res))
            for fname in filenames:
                cleaned = re.sub(pattern, '', fname)
                ret.append(cleaned)
    if ret:
        ret = [None if re.search(r'[^0-9]', r) else r for r in ret]
    return ret
