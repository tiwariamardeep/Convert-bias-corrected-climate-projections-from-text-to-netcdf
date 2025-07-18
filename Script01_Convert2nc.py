# This code converts text files of bias-corrected CMIP6 climate projections from Mishra, Tiwari et al. (2020) to netCDF files
# Written by Amar Deep Tiwari (tiwaria6@msu.edu)
# July 18, 2025

import pandas as pd
import numpy as np
import xarray as xr

def convert_txt_to_gridded_netcdf(filename, output_nc, var_name, units):
    # Read file lines
    with open(filename, 'r') as f:
        lines = f.readlines()

    # Extract longitudes and latitudes from first two lines (skip first 3 columns)
    lons = np.array(lines[0].strip().split()[3:], dtype=float)
    lats = np.array(lines[1].strip().split()[3:], dtype=float)

    # Identify unique sorted coordinates for grid
    unique_lons = np.sort(np.unique(lons))
    unique_lats = np.sort(np.unique(lats))[::-1]  # reverse lat for (north -> south)

    # Create index maps for (lon, lat)
    lon_idx = {lon: i for i, lon in enumerate(unique_lons)}
    lat_idx = {lat: i for i, lat in enumerate(unique_lats)}

    # Read time-series data
    df = pd.read_csv(filename, sep=r'\s+', skiprows=2, header=None)

    # Extract and convert time to "days since 1951-01-01"
    time_raw = pd.to_datetime(df[[0, 1, 2]].rename(columns={0: 'year', 1: 'month', 2: 'day'}))
    ref_time = pd.Timestamp("1951-01-01")
    time_days = (time_raw - ref_time) / pd.Timedelta(days=1)

    # Initialize empty array [time, lat, lon]
    nt, ny, nx = df.shape[0], len(unique_lats), len(unique_lons)
    data_array = np.full((nt, ny, nx), np.nan, dtype=np.float32)

    # Fill in values
    values = df.iloc[:, 3:].values
    for i, (lon, lat) in enumerate(zip(lons, lats)):
        x = lon_idx[lon]
        y = lat_idx[lat]
        data_array[:, y, x] = values[:, i]

    # Set temperature threshold for TMax and TMin
    if var_name in ["tmax", "tmin"]:
        data_array[data_array < -50] = np.nan

    # Build xarray Dataset with CF-compliant time
    ds = xr.Dataset(
        {
            var_name: (["time", "lat", "lon"], data_array)
        },
        coords={
            "time": ("time", time_days, {
                "units": "days since 1951-01-01",
                "calendar": "standard"
            }),
            "lon": unique_lons,
            "lat": unique_lats
        },
        attrs={
            "description": f"{var_name} from {filename}"
        }
    )

    # Set variable units
    ds[var_name].attrs["units"] = units

    # Save to NetCDF
    ds.to_netcdf(output_nc)
    print(f"Saved gridded NetCDF: {output_nc}")

# Convert to netcdf
convert_txt_to_gridded_netcdf("Mahi/ACCESS-CM2/historical/PrecipData", "PrecipData.nc", var_name="precip", units="mm/day")
convert_txt_to_gridded_netcdf("Mahi/ACCESS-CM2/historical/TMaxData", "TMaxData.nc", var_name="tmax", units="degC")
convert_txt_to_gridded_netcdf("Mahi/ACCESS-CM2/historical/TMinData", "TMinData.nc", var_name="tmin", units="degC")
