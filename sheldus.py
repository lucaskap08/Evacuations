
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 26 18:55:09 2025

@author: Luke
"""


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
import patsy
import re

pd.set_option('display.float_format', lambda x: '%.4f' % x)
np.set_printoptions(suppress=True, precision=4)

#read data_clean produced in merge.py
data_clean =pd.read_csv("data_clean.csv", dtype=str)
#read sheldus from univ of A
shel = pd.read_csv("sheldus.csv", dtype=str)

#reformat so mathcing
data_clean['Date'] = pd.to_datetime(data_clean['Date'], errors='coerce')
data_clean['employment'] = pd.to_numeric(data_clean['employment'], errors='coerce')
data_clean['Year'] = data_clean['SEASON']
data_clean.drop('SEASON', axis=1)


numeric_cols = ['wind_kt', 'hurr_time', 'time_num', 'logemp']
for col in numeric_cols:
    data_clean[col] = pd.to_numeric(data_clean[col], errors='coerce')


#aggregate based on means and time-invariant features. 
aggregated_df = data_clean.groupby(['FIPS', 'NAME'], as_index=False).agg({
   'wind_kt': 'mean',         # Now numeric, so mean will work
    'USA_SSHS': 'first',       # If these are constant
    'Year': 'first',
    'NAME': 'first',         # If constant
    'USA_wind': 'first',       # If constant
    'hurr_time': 'mean',       # Now numeric
    'had_evac': 'first',       # Typically boolean or constant per group
    'had_evac_int': 'first',   # Assuming constant
    'event_bin': 'first',      # Categorical, so take the first
    'event_bin_str': 'first',  # Categorical, so take the first
    'month_year': 'first',     # Depending on your needs
    'time_num': 'mean',        # Now numeric
    'logemp': 'mean'           # Now numeric
})

  
print(aggregated_df)
    
#matchup variables
shel['FIPS'] = shel['County_FIPS']
shel.drop('County_FIPS', axis=1)
frequency =shel['FIPS'].value_counts()
shel['NAME'] = shel['EventName'].str.split().str[-1].str.upper()


#select columns to sum 
cols_to_sum = [
    "Fatalities",
    "FatalitiesPerCapita",
    "Fatalities_Duration",
    "Injuries",
    "InjuriesPerCapita",
    "Injuries_Duration",
    "PropertyDmg",
    "PropertyDmg(ADJ)",
    "PropertyDmgPerCapita",
    "PropertyDmgDuration"
]



for col in cols_to_sum:
    shel[col] = pd.to_numeric(shel[col], errors='coerce')
    
# Group by county (FIPS) and storm name (NAME), and sum the numeric columns
aggregated_shel = (
    shel
    .groupby(["FIPS", "NAME"], as_index=False)[cols_to_sum]
    .sum()
)



#count duplicates; confirm 0 FIPS-NAME combinations
duplicates_count =aggregated_shel.groupby(['FIPS', 'NAME']).size().reset_index(name='count')
print(duplicates_count)
print(aggregated_shel)

#label property damage terciles among positive values
aggregated_shel['pdterc'] = pd.qcut(aggregated_shel['PropertyDmgPerCapita'], q=3, labels=['Low', 'Medium', 'High'])

#merge full aggregated dataset (one observatuin per storm-county pair)
ful_shel = pd.merge(aggregated_df, aggregated_shel,
                       on=['FIPS', 'NAME'], how='left', indicator=True)

#left represents emplyment+storm characteristics only; both means property damage record also
print(ful_shel['_merge'].value_counts())
ful_shel[cols_to_sum]= ful_shel[cols_to_sum].fillna(0)
ful_shel = ful_shel.drop(columns=['_merge'])

duplicates_count =ful_shel.groupby(['FIPS', 'NAME']).size().reset_index(name='count')

# Optionally, filter to see only those combinations that occur more than once
duplicates = duplicates_count[duplicates_count['count'] > 1]
print(duplicates)
ful_shel.to_csv("ful_shel.csv")


#write to csv


## Switch to event study dataset merge
ful_shelly = pd.merge(data_clean, aggregated_shel,
                       on=['FIPS', 'NAME'], how='left', indicator=True)
print(ful_shelly['_merge'].value_counts())

#data_clean in event_study should be set to USA_SSHS > 2
data_clean['post'] = (data_clean['hurr_time'] >= 0).astype(int)
data_clean['treated'] = data_clean['post'] * data_clean['had_evac_int']

# Create a dummy variable for USA_SHSS equal to 4
data_clean['ss_4'] = (data_clean['USA_SSHS'] == 4).astype(int)

# Create a dummy variable for USA_SHSS equal to 5
data_clean['ss_5'] = (data_clean['USA_SSHS'] == 5).astype(int)

data_clean['FIPS'] = data_clean['FIPS'].astype(str).str.strip().str.zfill(5)
data_clean['FIPS_code'] = data_clean['FIPS'].astype('category').cat.codes
len(data_clean)

ful_shelly = pd.merge(data_clean, aggregated_shel,
                       on=['FIPS', 'NAME'], how='left', indicator=True)

#correct to have left and both; no right only
print(ful_shelly['_merge'].value_counts())
ful_shelly[cols_to_sum] = ful_shelly[cols_to_sum].fillna(0) #from sheldus.py
ful_shelly = ful_shelly.drop(columns=['_merge'])

dummy_cols = pd.get_dummies(ful_shelly['pdterc'], prefix='pdterc')
dummy_cols = dummy_cols.astype(int)

# Join the new dummy columns back into the original DataFrame.
ful_shelly = ful_shelly.join(dummy_cols)

ful_shelly.to_csv("ful_shelly.csv")


#drop rows that didn't merge (from )




#emp_hurr_df = emp_hurr_df.drop('_merge', axis=1)