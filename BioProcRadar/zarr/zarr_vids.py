import numpy as np
import xarray as xr
from datetime import datetime

def create_zarr_vid_dataset(
        insect_files, bird_files,
        zarr_path, zarr_chunk
    ):
    ds_insect = _read_vid_dataset(
        insect_files, 'insect'
    )
    ds_bird = _read_vid_dataset(
        bird_files, 'bird' 
    )
    if ds_insect and ds_bird:
        ds = xr.concat(
            [ds_insect, ds_bird], dim='species'
        )
    elif ds_insect:
        ds = ds_insect
    elif ds_bird:
        ds = ds_bird
    else:
        return None

    ds = ds.assign_coords(
        species=ds.species.astype('int8')
    )
    ds = _add_vid_metadata(ds)
    ds = ds.chunk(zarr_chunk)

    ds.to_zarr(
        zarr_path,
        mode='w',
        consolidated=False,
        zarr_format=3
    )

def update_zarr_vid_dataset(
        vid_insect, vid_bird,
        zarr_path, zarr_chunk
    ):
    ds = xr.open_zarr(
        zarr_path, consolidated=False
    )

    files_insect = _get_species_files(
        ds.time.values, vid_insect
    )
    new_insect = len(files_insect['append']) > 0
    rep_insect = len(files_insect['replace']) > 0

    files_bird = _get_species_files(
        ds.time.values, vid_bird
    )
    new_bird = len(files_bird['append']) > 0
    rep_bird = len(files_bird['replace']) > 0

    if new_insect and new_bird:
        ds_insect = _read_vid_dataset(
            files_insect['append'], 'insect'
        )
        if ds_insect:
            if not _is_same_extent(ds, ds_insect):
                msg = 'Old and new insect datasets do not have'
                msg = f'{msg} the same lat/lon dimensions'
                raise ValueError(msg)

        ds_bird = _read_vid_dataset(
            files_bird['append'], 'bird'
        )
        if ds_bird:
            if not _is_same_extent(ds, ds_bird):
                msg = 'Old and new bird datasets do not have'
                msg = f'{msg} the same lat/lon dimensions'
                raise ValueError(msg)

        if ds_insect and ds_bird:
            ds_new = xr.concat(
                [ds_insect, ds_bird], dim='species'
            )
        elif ds_insect:
            ds_new = ds_insect
        elif ds_bird:
            ds_new = ds_bird
        else:
            return None

        ds_new = ds_new.assign_coords(
            species=ds_new.species.astype('int8')
        )
        ds_new = ds_new.chunk(zarr_chunk)
        ds_new.to_zarr(
            zarr_path,
            mode='a',
            append_dim='time',
            consolidated=False,
            zarr_format=3
        )

    if rep_insect and rep_bird:
        for species in ['insect', 'bird']:
            if species == 'insect':
                files = files_insect['replace']
            else:
                files = files_bird['replace']

            if len(files) == 0: continue

            for file in files:
                _replace_dataset(
                    ds, file, species, zarr_path
                )

def _is_same_extent(ds, ds_new):
    lat = ds.sizes['lat'] == ds_new.sizes['lat']
    lon = ds.sizes['lon'] == ds_new.sizes['lon']
    return lat and lon

def _replace_dataset(
        ds, file, species, zarr_path
    ):
    species_map = {
        'insect': 0,
        'bird': 1
    }

    ds_new = xr.open_dataset(
        file,
        engine='h5netcdf',
        decode_cf=False
    )
    lon = ds_new.get_index('lon')
    dup = lon.duplicated(keep='first')
    if any(dup):
        return None

    ds_new = xr.decode_cf(ds_new)

    if not _is_same_extent(ds, ds_new):
        msg = 'Old and new datasets do not have'
        msg = f'{msg} the same lat/lon dimensions'
        raise ValueError(msg)

    ds_new = ds_new.expand_dims({
        'species': [species_map[species]]
    })
    ds_new = ds_new.assign_coords(
        species=ds_new.species.astype('int8')
    )

    t_idx = np.where(np.in1d(
        ds.time.values,
        ds_new.time.values
    ))[0]
    t_idx = int(t_idx[0])
    s_idx = np.where(np.in1d(
        ds.species.values,
        ds_new.species.values
    ))[0]
    s_idx = int(s_idx[0])

    ds_new.to_zarr(
        zarr_path,
        mode='r+',
        region={
            'species': slice(s_idx, s_idx + 1),
            'time': slice(t_idx, t_idx + 1),
            'lat': slice(0, ds.sizes['lat']),
            'lon': slice(0, ds.sizes['lon'])
        },
        consolidated=False,
        zarr_format=3
    )

def _read_vid_dataset(files, species):
    species_map = {
        'insect': 0,
        'bird': 1
    }
    ds = _read_vid_nc(files)
    if ds is None:
        return None
    ds = xr.decode_cf(ds)
    ds = ds.expand_dims({
        'species': [species_map[species]]
    })
    return ds

# def _read_vid_nc(files):
#     return xr.open_mfdataset(
#         files,
#         combine='nested',
#         concat_dim='time',
#         engine='h5netcdf',
#         decode_cf=False
#     )

def _read_vid_nc(files):
    ds = []
    dup = []
    for file in files:
        nc = xr.open_dataset(
            file,
            engine='h5netcdf',
            decode_cf=False
        )
        ds += [nc]
        lon = nc.get_index('lon')
        dup += [lon.duplicated(keep='first')]
    dup = [any(d) for d in dup]
    ds = [ds[i] for i, d in enumerate(dup) if not d]
    if len(ds) == 0:
        return None
    return xr.concat(ds, dim='time')

def _add_vid_metadata(ds: xr.Dataset):
    ds.attrs.update({
        'title': 'Merged Bird/Insect VID data',
        'description': 'Spatial estimates of vertically integrated density',
        'Conventions': 'CF-1.8',
    })
    ds.species.attrs['meaning'] = '0=insect, 1=bird'
    ds.attrs['species_labels'] = {
        'insect': 0, 'bird': 1
    }
    return ds

def _get_datetime_index(ds_time, species_time):
    frmt = '%Y-%m-%d %H:%M:%S'
    ds_dt = [
        t.astype('datetime64[s]')
        for t in ds_time
    ]
    ds_dt = [
        t.astype(datetime).strftime(frmt)
        for t in ds_dt
    ]
    sp_dt = [
        t.strftime(frmt)
        for t in species_time
    ]
    index = [
        True if t in ds_dt else False 
        for t in sp_dt
    ]
    rep = [
        i for i, j in enumerate(index) if j
    ]
    new = [
        i for i, j in enumerate(index) if not j
    ]
    return {'replace': rep, 'append': new}

def _get_species_files(ds_time, vid_species):
    index = _get_datetime_index(
        ds_time,
        vid_species['dates']
    )
    files_new = [
        vid_species['files'][i]
        for i in index['append']
    ]
    files_rep = [
        vid_species['files'][i]
        for i in index['replace']
    ]
    return {
            'replace': files_rep,
            'append': files_new
        }
