#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 26 13:32:15 2025

@author: Luke
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Event Study Regression Estimation comparing:
  - Hurricane Only (dynamic effect of wind_kt)
  - Hurricane × Evacuation (additional effect of wind_kt when an evacuation order occurs)
  
Fixed effects:
  - County (C(FIPS))
  - Month-Year (C(month_year))
Event time dummies are constructed from binned hurr_time.
Author: Luke (modified)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
import patsy
import re

# -----------------------------
# 1. Load and Reshape Employment Data
# -----------------------------
emp_df = pd.read_csv('employment_new.csv')
if 'Unnamed: 0' in emp_df.columns:
    emp_df.rename(columns={'Unnamed: 0': 'Date'}, inplace=True)
emp_df['Date'] = pd.to_datetime(emp_df['Date'])
id_vars = ['Date']
value_vars = [col for col in emp_df.columns if col not in id_vars]
long_df = emp_df.melt(id_vars=id_vars, value_vars=value_vars,
                      var_name='FIPS', value_name='employment')

# -----------------------------
# 2. Load Hurricane Data (with Storm NAME and wind_kt)
# -----------------------------
hurr_df = pd.read_csv('south_wdate_new.csv')
hurr_df['FIPS'] = hurr_df["GEOID"].astype(str).str.zfill(5)
hurr_df['max_wind_date'] = pd.to_datetime(hurr_df['max_wind_date'])
if 'NAME' not in hurr_df.columns or 'wind_kt' not in hurr_df.columns:
    raise Exception("Hurricane data must contain both 'NAME' and 'wind_kt' columns.")

# -----------------------------
# 3. Load Evacuation Data
# -----------------------------
evac_df = pd.read_csv('HEvOD_2014-2022.csv',
                      sep='|', encoding='utf-8-sig', quotechar='"', dtype={'County FIPS': str})
evac_df['FIPS'] = evac_df["County FIPS"]
evac_df['a_date'] = pd.to_datetime(evac_df['Announcement Date'])
evac_mand_df = evac_df[evac_df['Order Type Code'] == 1].copy()



# -----------------------------
# 4. Merge Employment with Hurricane Data
# -----------------------------

emp_hurr_df = pd.merge(long_df, hurr_df[['FIPS', 'max_wind_date', 'NAME', 'wind_kt', 'USA_SSHS','SEASON', 'USA_wind']],
                       on=['FIPS'], how='left', indicator=True)






print(emp_hurr_df['_merge'].value_counts())
emp_hurr_df = emp_hurr_df.drop('_merge', axis=1)

emp_hurr_df.to_csv("emp_hurr.csv")
# Create a new column 'hurr_time' representing the number of months between the employment date 
#and the hurricane's maximum wind date.
emp_hurr_df['hurr_time'] = ((emp_hurr_df['Date'].dt.year - emp_hurr_df['max_wind_date'].dt.year) * 12  +
                            (emp_hurr_df['Date'].dt.month - emp_hurr_df['max_wind_date'].dt.month))



# Keep only the rows where 'max_wind_date' is not missing.
# This ensures that the hurricane information is available for each observation.
emp_hurr_df = emp_hurr_df[emp_hurr_df['max_wind_date'].notnull()].copy()

print("After merge, missing max_wind_date values:", emp_hurr_df['max_wind_date'].isna().sum())
print("Summary of hurr_time:")
print(emp_hurr_df['hurr_time'].describe())
# -----------------------------
# 5. Determine Evacuation Status for Each County-Hurricane Event
# -----------------------------
# Set the time window (in days) around the hurricane event 

# -----------------------------

# Prepare Evacuation Data
# -----------------------------
# Ensure that the FIPS codes in the evacuation dataset are five-digit strings.
evac_mand_df['FIPS'] = evac_mand_df['FIPS'].astype(str).str.zfill(5)

# Convert the evacuation announcement date ('a_date') to datetime format.
evac_mand_df['a_date'] = pd.to_datetime(evac_mand_df['a_date'])




# Debug: Check the first few rows of evac_mand_df
print("Evacuation data sample:")
print(evac_mand_df[['FIPS', 'a_date']].head())



# Set threshold for relevant evacuation orders (in days)
threshold_days = 10


# --- Merge Evacuation Data with Employment-Hurricane Data ---
# Merge emp_hurr_df with evac_mand_df on FIPS.
# This produces a cartesian join: each employment-hurricane observation is paired with all 
# evacuation orders in that county.

emp_hurr_df['FIPS'] = emp_hurr_df['FIPS'].astype(str).str.strip().str.zfill(5)
evac_mand_df['FIPS'] = evac_mand_df['FIPS'].astype(str).str.strip().str.zfill(5)

print("Unique FIPS in emp_hurr_df:", emp_hurr_df['FIPS'].nunique())
print("Unique FIPS in evac_mand_df:", evac_mand_df['FIPS'].nunique())

# Optionally, print the actual unique FIPS codes (or a sample)
print("FIPS in emp_hurr_df:", sorted(emp_hurr_df['FIPS'].unique()))
print("FIPS in evac_mand_df:", sorted(evac_mand_df['FIPS'].unique()))


merged = pd.merge(
    emp_hurr_df,
    evac_mand_df[['FIPS', 'a_date']],
    on=['FIPS'],
    how='left',
    suffixes=('', '_evac'),
    indicator=True
)

merged['within_window'] = (
    (merged['a_date'] >= merged['max_wind_date'] - pd.Timedelta(days=threshold_days)) &
    (merged['a_date'] <= merged['max_wind_date'] + pd.Timedelta(days=threshold_days))
)


print(merged['_merge'].value_counts())



# --- Flag Evacuation Orders Within the Threshold Window ---
# For each merged row, check if the evacuation announcement date (a_date_evac) falls within
# the time window around the hurricane's maximum wind date.
merged['within_window'] = (
    (merged['a_date'] >= merged['max_wind_date'] - pd.Timedelta(days=threshold_days)) &
    (merged['a_date'] <= merged['max_wind_date'] + pd.Timedelta(days=threshold_days))
)

# --- Collapse Back to One Row Per emp_hurr_df Observation ---
# For each original observation (indexed as in emp_hurr_df), determine if there was ANY evacuation order within the window.
# Using groupby on the index of emp_hurr_df (which was preserved during merge):
had_evac_flag = merged.groupby(merged.index)['within_window'].max()

# Add the flag to emp_hurr_df. The flag is a boolean: True if any evacuation order is found within the window.
emp_hurr_df['had_evac'] = had_evac_flag.fillna(False)  # fill missing values with False
# Convert boolean to integer (1 if True, 0 if False) for further analysis.
emp_hurr_df['had_evac_int'] = emp_hurr_df['had_evac'].astype(int)


####sidequest for days before max wind. 
merged['had_evac'] = had_evac_flag.fillna(False)  # fill missing values with False
# Convert boolean to integer (1 if True, 0 if False) for further analysis.
merged['had_evac_int'] = merged['had_evac'].astype(int)
cut= merged.query('had_evac_int == 1')
cut['diff'] =cut['max_wind_date'] - cut['a_date']
grouped = cut.groupby(['FIPS', 'NAME'])['diff'].mean().reset_index()
grouped.to_csv("/Users/Luke/Documents/Syracuse/Research/Evacuation/Out/evac_diff.csv", index=False)
print(grouped)




# --- Check Counts ---
# Count total observations with an evacuation order:
num_evac = emp_hurr_df['had_evac'].sum()
print("Number of observations with evacuation order (had_evac=True):", num_evac)

# Count evacuation orders by county:
evac_counts_by_county = emp_hurr_df.groupby('FIPS')['had_evac'].sum()
print("Evacuation order count by county (FIPS):")

#sets event window and estimates just in that window;
#for speed its ahead of function but in general may want to run all together
print(evac_counts_by_county)
emp_hurr_df['SEASON'] = emp_hurr_df['SEASON'].astype(int)

emp_hurr_df = emp_hurr_df.query("SEASON < 2023")
           



event_window = 24# months before and after the hurricane event
bin_edges = list(range(-event_window, event_window + 2, 2))  # 2-month bins
emp_hurr_df['event_bin'] = pd.cut(emp_hurr_df['hurr_time'], bins=bin_edges, include_lowest=True)
emp_hurr_df['event_bin_str'] = emp_hurr_df['event_bin'].astype(str)
emp_hurr_df = emp_hurr_df[emp_hurr_df['event_bin'].notnull()].copy()


# -----------------------------
# 6. Focus on High-Wind Counties
# -----------------------------
#emp_hurr_df = emp_hurr_df[emp_hurr_df['USA_SSHS'] >1].copy()

# -----------------------------
# Define a function to check for evacuation orders within a window around the hurricane event
# -----------------------------
def had_evac_order(fips, hurr_date):
    """
    Determine whether an evacuation order was issued for a given county (FIPS)
    within a specified time window around the hurricane event.
    
    Parameters:
      fips (str): The county FIPS code.
      hurr_date (datetime): The hurricane's maximum wind date.
    
    Returns:
      bool: True if an evacuation order was issued between 
            (hurr_date - threshold_days) and (hurr_date + threshold_days),
            False otherwise.
    """
    # Filter the evacuation data to include only records for the specified county.
    subset = evac_mand_df[evac_mand_df['FIPS'] == fips]
    
    # If there are no evacuation orders for this county, return False.
    if subset.empty:
        return False
    
    # Define the time window: from threshold_days before to threshold_days after the hurricane date.
    window_start = hurr_date - pd.Timedelta(days=threshold_days)
    window_end   = hurr_date + pd.Timedelta(days=threshold_days)
    
    # Debug: Print the window for a sample FIPS if needed (optional)
    # print(f"For FIPS {fips} and hurricane date {hurr_date}, window: {window_start} to {window_end}")
    
    # Check if any evacuation announcement dates fall within this time window.
    return ((subset['a_date'] >= window_start) & (subset['a_date'] <= window_end)).any()

# -----------------------------
# Apply the function to the merged employment-hurricane dataset
# -----------------------------
# For each observation in emp_hurr_df, determine if an evacuation order was issued within the threshold window.
emp_hurr_df['had_evac'] = emp_hurr_df.apply(lambda row: had_evac_order(row['FIPS'], row['max_wind_date']), axis=1)

# Convert the boolean evacuation indicator to an integer (1 if True, 0 if False)
emp_hurr_df['had_evac_int'] = emp_hurr_df['had_evac'].astype(int)


# -----------------------------emp_hi
# Count the number of observations with an evacuation order (True values)
# -----------------------------
num_evac = emp_hurr_df['had_evac'].sum()
print("Number of observations with evacuation order (had_evac=True):", num_evac)

# Group by county (FIPS) and count the number of evacuation orders per county
evac_counts_by_county = emp_hurr_df.groupby('FIPS')['had_evac'].sum()
print("Evacuation order count by county (FIPS):")
print(evac_counts_by_county)





# -----------------------------
# 8. Create Month-Year and Continuous Time Variable
# -----------------------------
emp_hurr_df['month_year'] = emp_hurr_df['Date'].dt.to_period('M').astype(str)
emp_hurr_df['time_num'] = (emp_hurr_df['Date'] - emp_hurr_df['Date'].min()).dt.days / 30.0

# -----------------------------
# 9. Estimate the Event Study Regression Model
# -----------------------------
# Revised specification includes two dynamic interactions:
#   (a) Hurricane Only: C(event_bin_str):wind_kt
#   (b) Hurricane × Evacuation: C(event_bin_str):wind_kt:had_evac_int
emp_hurr_df['logemp'] = np.log(emp_hurr_df['employment'])
# === 2. Regression Specification ===
# Revised formula: includes dynamic hurricane-only effect and hurricane×evacuation effect.
formula = (
    'logemp ~ C(month_year) + wind_kt + had_evac_int + '
    'C(event_bin_str):had_evac_int + time_num'
)
cols_for_model = ['logemp', 'FIPS', 'event_bin_str', 'had_evac_int', 'wind_kt', 'time_num']



data_clean = emp_hurr_df.dropna(subset=cols_for_model)
data_clean = data_clean[data_clean['event_bin_str'] != 'nan'].reset_index(drop=True)
data_clean
print("Unique event_bin_str values:", data_clean['event_bin_str'].unique())

y, X = patsy.dmatrices(formula, data=data_clean, return_type='dataframe')
print("Design matrix shape:", X.shape)
print("Number of observations:", len(data_clean))

data_clean['FIPS_code'] = data_clean['FIPS'].astype('category').cat.codes.astype(int)
groups = data_clean['FIPS_code'].values
print("Unique groups:", np.unique(groups))
print("Min group:", groups.min(), "Max group:", groups.max())

data_clean.to_csv("data_clean.csv")

