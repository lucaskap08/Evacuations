#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 11:29:55 2025

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
import matplotlib.pyplot as plt
import os
import matplotlib as mpl


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

# Load US counties shapefile and filter for southern states
zip_path = "cb_2018_us_county_500k.zip"

# 1️⃣  When the archive contains only ONE shapefile in its root
counties_gdf = gpd.read_file(f"zip://{zip_path}").to_crs("EPSG:4326")

# …continue with your filter
southern_states = ["01", "12", "13", "22", "28", "37", "45", "48"]
southern_counties = counties_gdf[counties_gdf["STATEFP"].isin(southern_states)]
southern_counties.to_csv("southern_counties.csv")
print(southern_counties)



print(type(hurricane_gdf["SEASON"]))

#can choose a specific storm to map
#hurricane_gdf = hurricane_gdf[hurricane_gdf["SID"].isin("2016273N13300")].copy()
#hurricane_gdf = hurricane_gdf[hurricane_gdf["MATTHEW"].astype(str).str.contains("IRMA", case=False, na=False)].copy()


# 2. CREATE A 10-MILE BUFFER AROUND THE SOUTHERN STATES (IN A PROJECTED CRS)
# -------------------------------------------------------------------
# Convert southern counties to a projected CRS for accurate buffering
southern_albers = southern_counties.to_crs("EPSG:5070")
buffer_dist_m = 10  # 50 miles in meters

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
                        'USA_WIND': row['USA_WIND'],
                        'USA_SSHS': row.get('USA_SSHS', None),
                        'geometry': wind_poly,
                        'color': color
                    })

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
        subset.plot(ax=ax, color=clr, alpha=0.3)

if not tracks_clipped.empty:
    tracks_clipped.plot(ax=ax, color='black', linewidth=3, alpha=1, label="Tracks")
else:
    print("No track segments intersect the buffer.")

southern_counties.boundary.plot(ax=ax, color='black', linewidth=1)
plt.legend()
plt.title("USA Wind Speed Polygons Near Southern States (2014+)")
plt.show()



#--------------------
# 1. Create wind polygons for events with USA_WIND of 64 kt or higher
wind_polygons = []
for _, row in hurricane_albers.iterrows():
    try:
        wind_speed = float(row['USA_WIND'])
    except (ValueError, TypeError):
        continue

    if wind_speed < 90:
        continue

    point_geom = row['geometry']
    if not point_geom or not point_geom.is_valid:
        continue

    storm_name = row.get('NAME', 'Unknown')
    sid = row.get('SID', 'Unknown')  # Unique storm ID

    for base_var, color in usa_wind_categories.items():
        for quad in ['NE', 'SE', 'SW', 'NW']:
            colname = f"{base_var}_{quad}"
            value = row[colname]
            if pd.notna(value):
                try:
                    radius_m = float(value) * 1852.0  # nm -> m
                except (ValueError, TypeError):
                    continue

                wind_poly = point_geom.buffer(radius_m)
                if wind_poly.is_valid:
                    wind_polygons.append({
                        'SID': sid,
                        'NAME': storm_name,
                        'SEASON': row.get('SEASON'),
                        'USA_WIND': wind_speed,
                        'USA_SSHS': row.get('USA_SSHS'),
                        'geometry': wind_poly,
                        'color': color
                    })

wind_albers_gdf = gpd.GeoDataFrame(wind_polygons, crs="EPSG:5070")
wind_gdf = wind_albers_gdf.to_crs("EPSG:4326")

# ---------------------------------------------------------
# 2. Clip the wind polygons to the southern buffer
wind_clipped = gpd.overlay(wind_gdf, southern_buffer, how='intersection')

# ---------------------------------------------------------
# 3. Spatially join counties with wind events
counties_with_64 = gpd.sjoin(southern_counties, wind_clipped, how='inner', predicate='intersects')

# Remove duplicates so each (county, storm) pair is only counted once
counties_with_64_unique = counties_with_64.drop_duplicates(subset=['GEOID', 'SID'])

# Count how many storms affected each county
event_counts = counties_with_64_unique.groupby('GEOID').size().reset_index(name='event_count')

# Merge counts back to the southern_counties GeoDataFrame
southern_counties = southern_counties.merge(event_counts, on='GEOID', how='left')
southern_counties['event_count'] = southern_counties['event_count'].fillna(0)


# ---------------------------------------------------------
# 1. Create a professional-quality choropleth map of event counts.
fig, ax = plt.subplots(figsize=(12, 8))

# Plot the counties with a choropleth based on event_count.
# Adjust the colormap (here 'OrRd') as needed.
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

county_plot = southern_counties.plot(
    ax=ax,
    column='event_count',
    cmap='OrRd',
    edgecolor='black',
    linewidth=0.8,
    legend=True,
    legend_kwds={
        'label': "Count of 90+ (103 mph) kt Hurricanes, ",
        'orientation': "vertical",
        'shrink': 0.5,
        'pad': 0.02
    }
)

# Clean up the axes for a modern look.
ax.set_xticks([])
ax.set_yticks([])
ax.set_axis_off()

# Set a descriptive title.
#ax.set_title("Number of Severe Hurricanes by County, 2014-2022", fontsize=16, fontweight='bold', pad=20)

plt.tight_layout()
plt.savefig("county_event_counts.png", dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
plt.show()
