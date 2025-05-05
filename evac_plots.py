#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr  2 10:22:52 2025

@author: Luke
"""

import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely import wkt

# File paths
orders_file = 'HEvOD_2014-2022.csv'
southern_counties_csv = 'southern_counties.csv'
shapefile_path = 'cb_2018_us_county_500k.shp'

# Read counties CSV data
plt.rcParams['figure.dpi'] = 300

counties = pd.read_csv(southern_counties_csv)
# Rename column and ensure FIPS are 5-digit strings
counties = counties.rename(columns={'GEOID': 'FIPS'})
counties['FIPS'] = counties['FIPS'].astype(str).str.zfill(5)


# Check if the counties DataFrame has a geometry column; if not, read the shapefile
if 'geometry' not in counties.columns:
    print("No geometry column found in CSV; reading shapefile for geometry.")
    counties_shp = gpd.read_file(shapefile_path)
    counties_shp = counties_shp[['GEOID', 'geometry']]
    counties_shp = counties_shp.rename(columns={'GEOID': 'FIPS'})
    counties_shp['FIPS'] = counties_shp['FIPS'].astype(str).str.zfill(5)
    # Use the shapefile GeoDataFrame for mapping
    counties = counties_shp
else:
    # If geometry is in WKT format, convert it to shapely objects
    counties['geometry'] = counties['geometry'].apply(wkt.loads)
    counties = gpd.GeoDataFrame(counties, geometry='geometry')

# Read evacuation orders data
df = pd.read_csv(orders_file, sep='|', encoding='utf-8-sig', quotechar='"', dtype={'County FIPS': str})
df['order_type'] = df["Order Type"]
df = df[df['order_type'].str.contains("Mandatory", na=False)]
df['FIPS'] = df['County FIPS'].astype(str).str.zfill(5)


#df = df[df['Event Name'].astype(str).str.contains("Ian", case=False, na=False)].copy()


# Group by FIPS and count orders
# Drop duplicate event entries per county
unique_events = df.drop_duplicates(subset=['FIPS', 'Event Name'])

# Now group by FIPS and count the unique events
order_counts = unique_events.groupby('FIPS').size().reset_index(name='order_count')


# Merge the counts with the counties data
counties_with_orders = counties.merge(order_counts, on='FIPS', how='left', indicator=True)


print(counties_with_orders['_merge'].value_counts())

# Fill counties with no orders with a count of 0
counties_with_orders['order_count'] = counties_with_orders['order_count'].fillna(0)
print(counties_with_orders[['FIPS', 'order_count']].head())

# Create the figure and axes
fig, ax = plt.subplots(figsize=(12, 8))


# Set the facecolors of the figure and axes to white.
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

# Plot the counties with a blue sequential colormap (Blues)
county_plot = counties_with_orders.plot(
    column='order_count',
    ax=ax,
    cmap='Blues',
    edgecolor='black',
    linewidth=0.5,
    legend=True,
    legend_kwds={
        'label': "Mandatory Evacuation Orders", 
        'orientation': "vertical",
        'shrink': 0.5,
        'pad': 0.02
    }
)

# Set a descriptive title with enhanced styling
#ax.set_title('Mandatory Evacuation Orders by County, 2014-2022', fontsize=16, fontweight='bold', pad=20)

# Remove axis ticks and labels for a cleaner look
ax.set_xticks([])
ax.set_yticks([])
ax.set_axis_off()

plt.savefig("county_evacs.png", dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
plt.show()


