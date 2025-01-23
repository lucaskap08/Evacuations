#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 14:26:39 2025

@author: Luke
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString
import matplotlib.pyplot as plt

# -------------------------------------------------------------------
# 1. LOAD & PREPARE DATA
# -------------------------------------------------------------------

file_name = '/Users/Luke/Documents/Syracuse/Research/Evacuation/tracs_1980.csv'
st = pd.read_csv(file_name, sep=",", encoding='utf-8-sig')

# Ensure numeric fields
st['SEASON'] = pd.to_numeric(st['SEASON'], errors='coerce')
st['LON'] = pd.to_numeric(st['LON'], errors='coerce')
st['LAT'] = pd.to_numeric(st['LAT'], errors='coerce')

# Adjust LON if > 180 => convert by subtracting 360
st['LON'] = st['LON'].apply(lambda x: x - 360 if x > 180 else x)

# Filter for 2014+
st_2014 = st[st['SEASON'] >= 2014].copy()

# Convert to a GeoDataFrame (EPSG:4326 = WGS84)
st_2014['geometry'] = st_2014.apply(lambda r: Point(r['LON'], r['LAT']), axis=1)
hurricane_gdf = gpd.GeoDataFrame(st_2014, geometry='geometry', crs="EPSG:4326")

# Check that NAME column is present
# print(hurricane_gdf.columns)

# Load Florida counties
florida_path = "/Users/Luke/Documents/Syracuse/Research/Evacuation/Counties.shp/Counties.shp"
florida_gdf = gpd.read_file(florida_path).to_crs("EPSG:4326")

# -------------------------------------------------------------------
# 2. CREATE A 50-MILE BUFFER AROUND FLORIDA (IN A PROJECTED CRS)
# -------------------------------------------------------------------
florida_albers = florida_gdf.to_crs("EPSG:5070")
buffer_dist_m = 80450  # 50 miles in meters
florida_buffer_albers = florida_albers.buffer(buffer_dist_m)
florida_buffer = florida_buffer_albers.to_crs("EPSG:4326")

# -------------------------------------------------------------------
# 3. FILTER HURRICANE POINTS WITHIN 50 MILES OF FLORIDA
# -------------------------------------------------------------------
points_near_florida = gpd.sjoin(
    hurricane_gdf, 
    florida_buffer.to_frame(name='geometry'),
    how="inner",
    predicate="intersects"
)
fl_storm_ids = points_near_florida['SID'].unique()

florida_tracks_points = hurricane_gdf[hurricane_gdf['SID'].isin(fl_storm_ids)]

# -------------------------------------------------------------------
# 4. BUILD HURRICANE TRACK LINES & CLIP
# -------------------------------------------------------------------
def make_linestring(g):
    coords = g[['LON','LAT']].values
    return LineString(coords) if len(coords) > 1 else None

track_lines = florida_tracks_points.groupby("SID").apply(make_linestring).dropna()

track_lines_gdf = gpd.GeoDataFrame(
    {'SID': track_lines.index, 'geometry': track_lines},
    crs="EPSG:4326"
)

tracks_clipped = gpd.overlay(track_lines_gdf, florida_buffer.to_frame('geometry'), how='intersection')



# -------------------------------------------------------------------
# 5. CREATE WIND POLYGONS (USA COLUMNS EXAMPLE) & INCLUDE STORM NAME
# -------------------------------------------------------------------
# Example: for USA_R34, USA_R50, USA_R64, each quadrant in nautical miles.
hurricane_gdf['SEASON'] = hurricane_gdf['SEASON'].astype(int)
usa_wind_categories = {
    'USA_R34': 'yellow',  # 34-kt radius
    'USA_R50': 'orange',  # 50-kt radius
    'USA_R64': 'red'      # 64-kt radius
}

# Make sure columns are numeric
import numpy as np

for base in usa_wind_categories.keys():
    for quad in ['NE','SE','SW','NW']:
        col = f"{base}_{quad}"
        if col in hurricane_gdf.columns:
            hurricane_gdf[col] = pd.to_numeric(hurricane_gdf[col], errors='coerce')
        else:
            # If a column is missing, create it with NaN so we can handle it gracefully
            hurricane_gdf[col] = np.nan

hurricane_albers = hurricane_gdf.to_crs("EPSG:5070")

wind_polygons = []
for idx, row in hurricane_albers.iterrows():
    point_geom = row['geometry']
    if point_geom is None or not point_geom.is_valid:
        continue
    
    # We'll store the NAME for each polygon
    storm_name = row.get('NAME', 'Unknown')  # fallback if missing

    for base_var, color in usa_wind_categories.items():
        for quad in ['NE','SE','SW','NW']:
            colname = f"{base_var}_{quad}"
            if colname in row and pd.notna(row[colname]):
                radius_nm = float(row[colname])
                radius_m = radius_nm * 1852.0  # 1 nm = 1852 m
                wind_poly = point_geom.buffer(radius_m)
                
                if wind_poly.is_valid:
                    wind_polygons.append({
                        'SID': row['SID'],
                        'NAME': storm_name,
                        'SEASON': row['SEASON'], 
                        'geometry': wind_poly,
                        'color': color
                    })

wind_albers_gdf = gpd.GeoDataFrame(wind_polygons, crs="EPSG:5070")
wind_gdf = wind_albers_gdf.to_crs("EPSG:4326")
# Clip to 50-mile buffer
wind_clipped = gpd.overlay(wind_gdf, florida_buffer.to_frame('geometry'), how='intersection')

# -------------------------------------------------------------------
# 6. PLOT (OPTIONAL)
# -------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10,6))
florida_gdf.plot(ax=ax, color='lightgrey', edgecolor='black', label='Florida Counties')

if not wind_clipped.empty:
    for clr in usa_wind_categories.values():
        subset = wind_clipped[wind_clipped['color'] == clr]
        if not subset.empty:
            subset.plot(ax=ax, color=clr, alpha=0.3, edgecolor='black')
else:
    print("No wind polygons intersect the buffer; skipping wind plot.")

if not tracks_clipped.empty:
    tracks_clipped.plot(ax=ax, color='red', linewidth=1.2, alpha=0.7, label="Tracks")
else:
    print("No track segments intersect the buffer.")

florida_gdf.boundary.plot(ax=ax, color='black', linewidth=1)
plt.legend()
plt.title("USA Wind Speed Polygons Near Florida (2014+)")
ax.set_aspect('auto')
plt.show()

# -------------------------------------------------------------------
# 7. LABEL EACH COUNTY W/ STORM NAME & DUMMY=1
# -------------------------------------------------------------------
# We'll intersect the wind polygons with counties.
# Then group by county + storm name, etc.
florida_gdf.rename(
    columns={"NAME": "COUNTYNAME"},  # old_name: new_name
    inplace=True
)
county_wind = gpd.overlay(florida_gdf, wind_clipped, how='intersection')


# Create dummy=1 for each intersection
county_wind['dummy'] = 1

# Optional: convert color -> numeric wind (34, 50, 64 kt)
def color_to_kt(c):
    if c == 'yellow': return 34
    elif c == 'orange': return 50
    elif c == 'red': return 64
    return None

county_wind['wind_kt'] = county_wind['color'].apply(color_to_kt)

# Finally, group by county + SID + NAME
# The columns in your shapefile might differ
# e.g. if you have 'NAME' for county, rename it or see which field has county names
county_storm_agg = (
    county_wind
    .groupby(["COUNTYNAME", "FIPS", "SID", "NAME", "SEASON"], as_index=False)  # This might differ if the shapefile also has 'NAME'
    # or if your county field is "COUNTYNAME", do ["COUNTYNAME", "SID", "NAME"]
    .agg({
       "dummy": "max",
       "wind_kt": "max",
       # If your polygon had 'NAME' for storms, that might appear as "NAME_right" in overlay
       # or you might have "NAME_left" for counties, "NAME_right" for storms
    })
)

# Or, if you prefer simpler naming, rename your columns after grouping
print(county_storm_agg.head(20))

# Save to CSV
county_storm_agg.to_csv("florida_counties_storm_dummy_windspeed.csv", index=False)
