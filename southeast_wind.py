#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 11:24:53 2025

@author: Luke
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb  5 13:16:52 2025
Updated for Southern States analysis
@author: Luke
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, LineString
import matplotlib.pyplot as  plt
import os
#os.chdir("/Users/Luke/Documents/Syracuse/Research/Evacuation/Git_evac/Evacuations/cb_2018_us_county_500k")


# -------------------------------------------------------------------
# 1. LOAD & PREPARE DATA
# -------------------------------------------------------------------
file_name = 'tracs_1980.csv'
st = pd.read_csv(file_name, sep=",", encoding='utf-8-sig')

# Convert columns to numeric (vectorized)
st['SEASON'] = pd.to_numeric(st['SEASON'], errors='coerce')
st['LON'] = pd.to_numeric(st['LON'], errors='coerce')
st['LAT'] = pd.to_numeric(st['LAT'], errors='coerce')

# Adjust LON if > 180 by subtracting 360 (vectorized)
st.loc[st['LON'] > 180, 'LON'] -= 360

# Filter for 2014+ and create GeoDataFrame using points_from_xy
st_2014 = st[st['SEASON'] >= 2014].copy()
hurricane_gdf = gpd.GeoDataFrame(
    st_2014,
    geometry=gpd.points_from_xy(st_2014['LON'], st_2014['LAT']),
    crs="EPSG:4326"
)

zip_path = "cb_2018_us_county_500k.zip"

# 1️⃣  When the archive contains only ONE shapefile in its root
counties_gdf = gpd.read_file(f"zip://{zip_path}").to_crs("EPSG:4326")

# …continue with your filter
southern_states = ["01", "12", "13", "22", "28", "37", "45", "48"]
southern_counties = counties_gdf[counties_gdf["STATEFP"].isin(southern_states)]

# -------------------------------------------------------------------
# 2. CREATE A 50-MILE BUFFER AROUND THE SOUTHERN STATES (IN A PROJECTED CRS)
# -------------------------------------------------------------------
# Convert southern counties to a projected CRS for accurate buffering
southern_albers = southern_counties.to_crs("EPSG:5070")
buffer_dist_m = 80450  # 50 miles in meters

# Union all southern counties into a single geometry and buffer it
southern_union = southern_albers.unary_union
southern_buffer_albers = southern_union.buffer(buffer_dist_m)

# Convert the buffered geometry back to EPSG:4326 and wrap in a GeoDataFrame
southern_buffer = gpd.GeoDataFrame(geometry=[southern_buffer_albers], crs="EPSG:5070")\
    .to_crs("EPSG:4326")

# -------------------------------------------------------------------
# 3. FILTER HURRICANE POINTS WITHIN 50 MILES OF THE SOUTHERN REGION
# -------------------------------------------------------------------
points_near_southern = gpd.sjoin(
    hurricane_gdf, 
    southern_buffer, 
    how="inner", 
    predicate="intersects"
)
southern_storm_ids = points_near_southern['SID'].unique()
southern_tracks_points = hurricane_gdf[hurricane_gdf['SID'].isin(southern_storm_ids)]


# -------------------------------------------------------------------
# 4. BUILD HURRICANE TRACK LINES & CLIP
# -------------------------------------------------------------------
def make_linestring(group):
    coords = group[['LON', 'LAT']].values
    return LineString(coords) if len(coords) > 1 else None

track_lines = southern_tracks_points.groupby("SID").apply(make_linestring).dropna()
track_lines_gdf = gpd.GeoDataFrame(
    {'SID': track_lines.index, 'geometry': track_lines},
    crs="EPSG:4326"
)
tracks_clipped = gpd.overlay(track_lines_gdf, southern_buffer, how='intersection')

# -------------------------------------------------------------------
# 5. CREATE WIND POLYGONS (USA COLUMNS EXAMPLE) & INCLUDE STORM NAME
# -------------------------------------------------------------------
# Ensure SEASON is integer and define wind categories
hurricane_gdf['SEASON'] = hurricane_gdf['SEASON'].astype(int)
usa_wind_categories = {
    'USA_R34': 'yellow',  # 34-kt radius
    'USA_R50': 'orange',  # 50-kt radius
    'USA_R64': 'red'      # 64-kt radius
}

# Convert wind radius columns to numeric (vectorized)
for base in usa_wind_categories:
    for quad in ['NE', 'SE', 'SW', 'NW']:
        col = f"{base}_{quad}"
        hurricane_gdf[col] = pd.to_numeric(hurricane_gdf.get(col, np.nan), errors='coerce')

# Reproject to Albers for distance (buffer) calculations
hurricane_albers = hurricane_gdf.to_crs("EPSG:5070")


wind_polygons = []
for _, row in hurricane_albers.iterrows():
    point_geom = row['geometry']
    if not point_geom or not point_geom.is_valid:
        continue
    storm_name = row.get('NAME', 'Unknown')
    for base_var, color in usa_wind_categories.items():
        for quad in ['NE', 'SE', 'SW', 'NW']:
            colname = f"{base_var}_{quad}"
            value = row[colname]
            if pd.notna(value):
                # Convert nautical miles to meters (1 nm = 1852 m)
                radius_m = float(value) * 1852.0
                wind_poly = point_geom.buffer(radius_m)
                if wind_poly.is_valid:
                    wind_polygons.append({
                        'SID': row['SID'],
                        'NAME': storm_name,
                        'SEASON': row['SEASON'],
                        'USA_SSHS': row.get('USA_SSHS', None),
                        'geometry': wind_poly,
                        'color': color,
                        'USA_WIND': row.get('USA_WIND', None),
                        'DATE': row.get("ISO_TIME")
                    })
if pd.notna(value):
    # ...
    if wind_poly.is_valid:
        poly_data = {
            'SID': row['SID'],
            'NAME': storm_name,
            'SEASON': row['SEASON'],
            'USA_SSHS': row.get('USA_SSHS', None),
            'geometry': wind_poly,
            'color': color,
            'USA_WIND': row.get('USA_WIND', None),  # Confirm this key
            'DATE': row.get("ISO_TIME")
        }
        wind_polygons.append(poly_data)
        # For debugging:
        print(poly_data)           

wind_albers_gdf = gpd.GeoDataFrame(wind_polygons, crs="EPSG:5070")
wind_gdf = wind_albers_gdf.to_crs("EPSG:4326")
# Clip the wind polygons to the southern buffer
wind_clipped = gpd.overlay(wind_gdf, southern_buffer, how='intersection')

# -------------------------------------------------------------------
# 6. PLOT (OPTIONAL)
# -------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 6))
southern_counties.plot(ax=ax, color='lightgrey', edgecolor='black', label='Southern Counties')

for clr in usa_wind_categories.values():
    subset = wind_clipped[wind_clipped['color'] == clr]
    if not subset.empty:
        subset.plot(ax=ax, color=clr, alpha=0.3, edgecolor='black')

if not tracks_clipped.empty:
    tracks_clipped.plot(ax=ax, color='red', linewidth=1.2, alpha=0.7, label="Tracks")
else:
    print("No track segments intersect the buffer.")

southern_counties.boundary.plot(ax=ax, color='black', linewidth=1)
plt.legend()
plt.title("USA Wind Speed Polygons Near Southern States (2014+)")
plt.show()

# -------------------------------------------------------------------
# 7. LABEL EACH COUNTY WITH STORM NAME & DUMMY=1
# -------------------------------------------------------------------
# Rename county NAME column to avoid confusion
southern_counties.rename(columns={"NAME": "COUNTYNAME"}, inplace=True)
county_wind = gpd.overlay(southern_counties, wind_clipped, how='intersection')

# Convert color to corresponding wind speed (in kt)
def color_to_kt(c):
    if c == 'yellow':
        return 34
    elif c == 'orange':
        return 50
    elif c == 'red':
        return 64
    return None

county_wind['wind_kt'] = county_wind['color'].apply(color_to_kt)


# Group by county, storm, and additional attributes
#county_storm_agg = (
 #   county_wind
#    .groupby(["COUNTYNAME", "GEOID", "SID", "NAME", "SEASON"], as_index=False)
 #   .agg({
 #      "dummy": "max",
 #      "wind_kt": "max",
  #     "USA_SSHS": "max"# Take max USA_SSHS for each group
 #   })
#)

#print(county_storm_agg.head())
#county_storm_agg.to_csv("southern_with_cat.csv", index=False)

# aggregation function to capture the date corresponding to the max wind_kt
def agg_func(group):
    # For wind_kt
    max_wind = group['wind_kt'].max()
    idx_wind = group['wind_kt'].idxmax()
    max_wind_date = group.loc[idx_wind, 'DATE']
    
    # For USA_WIND
    max_usa_wind = group['USA_WIND'].max()
    idx_usa = group['USA_WIND'].idxmax()
    max_usa_wind_date = group.loc[idx_usa, 'DATE']
    
    return pd.Series({
        'wind_kt': max_wind,
        'max_wind_date': max_wind_date,
        'USA_SSHS': group['USA_SSHS'].max(),
        'USA_wind': max_usa_wind,
        'max_usa_wind_date': max_usa_wind_date
    })

county_storm_agg = (
    county_wind
    .groupby(["GEOID","NAME", "SEASON"])
    .apply(agg_func)
    .reset_index()
)

print(county_storm_agg.head())
county_storm_agg.to_csv("south_wdate_new.csv", index=False)
