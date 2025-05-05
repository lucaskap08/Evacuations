#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 14 14:52:42 2025

@author: Luke
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 26 16:27:48 2025

@author: Luke
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
import patsy
import re
from statsmodels.iolib.summary2 import summary_col
# -----------------------------
# ful_shelly is already prepared, and it contains:
# - logemp: natural log of employment,
# - wind_kt: wind speed,
# - had_evac_int: evacuation indicator (1 if evacuation order issued, 0 otherwise),
# - event_bin_str: event time bins as strings (e.g., "-12.001, -10.0"),
# - month_year: fixed effect for month and year,
# - time_num: continuous time trend variable.
# -----------------------------
ful_shelly = pd.read_csv("ful_shelly.csv") # from sheldus.py saved in directory


#restricted analysis to category 3+ storms
ful_shelly= ful_shelly[ful_shelly['USA_SSHS'] >2].copy()

#formula for event study)
formula = (
    'logemp ~ C(month_year) +had_evac_int+'
    'C(event_bin_str):had_evac_int:pdterc_High + time_num +C(FIPS) + USA_SSHS + pdterc_Medium'
)


#mess around with other specification that is slightly less strong a result
formula = (
    'logemp ~ C(month_year) +had_evac_int+'
    'C(event_bin_str):had_evac_int:pdterc_High + time_num +C(FIPS) + USA_SSHS + pdterc_Medium +pdterc_Low + USA_wind + Fatalities'
)




# Ensure that FIPS is correctly formatted as a string (if not already done) and that you have a clustering variable.
ful_shelly['FIPS'] = ful_shelly['FIPS'].astype(str).str.strip().str.zfill(5)
ful_shelly['FIPS_code'] = ful_shelly['FIPS'].astype('category').cat.codes

# Estimate the fixed effects model, clustering standard errors at the county level.
#model_fe = smf.ols(formula=formula, data=ful_shelly).fit(
 #   cov_type='cluster', cov_kwds={'groups': ful_shelly['FIPS_code']}
#)




# Drop observations with missing values in relevant columns:
cols_for_model = ['logemp','had_evac_int', 'USA_wind', 'FIPS', 'month_year', 'event_bin_str', 'time_num', 'NAME', 'pdterc_Medium', 
                  'pdterc_High', 'PropertyDmgPerCapita','Fatalities']
data_model = ful_shelly.dropna(subset=cols_for_model).reset_index(drop=True)
#data_model = data_model.query('pdterc_High == 1')
#in order to have the proper bin omitted, and in order to have sufficient aggregation in each 'bin':
#2 month buns with specified order are listed.  
desired_order = desired_order = [
    "(-2.0, 0.0]",
    "(0.0, 2.0]",
    "(-24.001, -22.0]",
    "(-22.0, -20.0]",
    "(-20.0, -18.0]",
    "(-18.0, -16.0]",
    "(-16.0, -14.0]",
    "(-14.0, -12.0]",
    "(-12.0, -10.0]",
    "(-10.0, -8.0]",
    "(-8.0, -6.0]",
    "(-6.0, -4.0]",
    "(-4.0, -2.0]",
    "(2.0, 4.0]",
    "(4.0, 6.0]",
    "(6.0, 8.0]",
    "(8.0, 10.0]",
    "(10.0, 12.0]",
    "(12.0, 14.0]",
    "(14.0, 16.0]",
    "(16.0, 18.0]",
    "(18.0, 20.0]",
    "(20.0, 22.0]",
    "(22.0, 24.0]"
]


data_model['event_bin_str'] = pd.Categorical(
    data_model['event_bin_str'],
    categories=desired_order,
    ordered=True
)
# Build design matrices and add a FIPS_code for clustering:
y, X = patsy.dmatrices(formula, data=data_model, return_type='dataframe')
data_model['FIPS_code'] = data_model['FIPS'].astype('category').cat.codes
groups = data_model['FIPS_code'].values

# Estimate the model with clustered standard errors
model = smf.ols(formula=formula, data=data_model).fit(
    cov_type='cluster', cov_kwds={'groups': groups}
)
print(model.summary())


summary_df = model.summary2().tables[1]

# Filter the rows for the variables you want
#selected_vars = ['had_evac_int', 'USA_wind']
#selected_summary = summary_df.loc[selected_vars]
#print(selected_summary)
#results_table = summary_col(
  #  [model],
 #   model_names=["Fixed Effect Model"],
  #  stars=True,
  #  float_format='%0.2f',
  #  regressor_order=['had_evac_int', 'USA_wind'],  # Only include these variables in the table
  #  info_dict={'N': lambda x: f"{int(x.nobs)}"}
#)

#print(results_table)
# -----------------------------
# Extract the dynamic treatment (evacuation) effects:
# We are interested in the coefficients on the interaction terms, which should appear
# in the parameter names that include both "C(event_bin_str)" and "had_evac_int".
# -----------------------------
def extract_event_bin_label(var_name):
    """
    Extract the event bin label from a variable name.
    
    For example:
      "C(event_bin_str)[T.(-12.001, -10.0)]":had_evac_int -> "-12.001, -10.0"
    
    This function removes any "T.(" or "T(" markers and strips off extra parentheses/brackets.
    """
    if not isinstance(var_name, str):
        return None
    prefix = "C(event_bin_str)["
    start = var_name.find(prefix)
    if start == -1:
        return None
    content = var_name[start + len(prefix):]
    # Remove "T.(" or "T(" if present.
    if content.startswith("T.("):
        content = content[len("T.("):]
    elif content.startswith("T("):
        content = content[len("T("):]
    # Split at the first delimiter among ")]", "]:", or just "]"
    for delim in [")", "]:", "]"]:
        pos = content.find(delim)
        if pos != -1:
            candidate = content[:pos]
            # Strip any remaining leading/trailing parentheses or brackets.
            return candidate.lstrip("([ ").rstrip(")] ").strip()
    return None

# Build list of coefficients for the interaction terms

treatment_effects = [
    {'event_bin': extract_event_bin_label(var),
     'coef': model.params[var],
     'se': model.bse[var]}
    for var in model.params.index
    if 'C(event_bin_str)' in var and 'had_evac_int' in var and 'pdterc_High' in var
]


treatment_df = pd.DataFrame(treatment_effects)
treatment_df = treatment_df.drop(treatment_df.index[0])
print("Extracted dynamic treatment effects:")
print(treatment_df)


####I played around with a few different ways of organizing the dots.  That is, to place 2 month before at 0 or at -2 


# -----------------------------
# Convert event bin label to a numeric value.
# Midpoint of the bin
# -----------------------------
def extract_midpoint(bin_str):
    """
    Extract the midpoint from a bin string.
    For example, from "-12.001, -10.0" return (-12.001 + (-10.0)) / 2.
    """
    try:
        parts = bin_str.split(',')
        low = float(parts[0].strip())
        high = float(parts[1].strip())
        return (low + high) / 2
    except Exception:
        return None

treatment_df['midpoint'] = treatment_df['event_bin'].apply(extract_midpoint)
treatment_df = treatment_df[treatment_df['midpoint'].notnull()].sort_values(by='midpoint')

# -----------------------------
# Plot the dynamic treatment effects over event time.
# -----------------------------
plt.figure(figsize=(10,6))
plt.errorbar(treatment_df['midpoint'], treatment_df['coef'],
             yerr=1.96 * treatment_df['se'], fmt='-o', label='Evacuation Treatment Effect')
plt.axhline(0, color='black', linestyle='--', linewidth=1)
plt.xlabel('Event Time (Months)')
plt.ylabel('Coefficient Estimate (logemp)')
plt.title('Event Study: Dynamic Treatment Effects (Evacuation × Post)')
plt.legend()
plt.tight_layout()
plt.show()


def extract_upper_bound(bin_str):
    """
    Extract the upper bound from a bin string.
    For example, from "(-12.001, -10.0]" return -10.0.
    """
    try:
        # Remove outer parentheses if present
        bin_str = bin_str.strip("()")
        parts = bin_str.split(',')
        # Remove the trailing ']' and any extra spaces from the upper bound string
        upper_str = parts[1].replace("]", "").strip()
        return float(upper_str)
    except Exception:
        return None


# Option: Upper bound
treatment_df['x_value'] = treatment_df['event_bin'].apply(extract_upper_bound)

# Filter out rows with no valid x_value and sort by it.
treatment_df = treatment_df[treatment_df['x_value'].notnull()].sort_values(by='x_value')

# -----------------------------
# Plot the dynamic treatment effects over event time.


# -----------------------------

plt.rcParams['font.family'] = 'Georgia'
# Create a figure and an axes
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')
fig.patch.set_edgecolor('white')
for spine in ax.spines.values():
    spine.set_visible(False)

# Plot the dynamic evacuation treatment effect with error bars.
#ax.errorbar(treatment_df['x_value'], treatment_df['coef'],
           # yerr=1.96 * treatment_df['se'], fmt='-o',
           # label='Evacuation Treatment Effect -- Highest Quartile of Damages')


# Add a horizontal reference line at 0
ax.axvline(0, color='black', linestyle='--', linewidth=1)

# Set axis labels and title
ax.set_xlabel('Event Time (Months)')
ax.set_ylabel('Log Employment')
ax.set_title('')
ax.axhline(0, color='black', linestyle=':', linewidth=1)
# Add a legend to differentiate the lines
ax.legend()
# ── 1) thin black connecting line ──────────────────────────────────────────────
# Do the markers + errors first (no connecting line) …
ax.errorbar(
    treatment_df['midpoint'], treatment_df['coef'],
    yerr=1.96 * treatment_df['se'],
    fmt='o',                    # marker only
    markersize=5,
    markeredgecolor='red',
    markerfacecolor='white',    # hollow circles (AER style)
    ecolor='black', elinewidth=0.75, capsize=2,
    label='Evacuation Treatment Effect — Highest Quartile of Damages'
)

# …then draw the thin black line that connects the centres
#ax.plot(
   # treatment_df['x_value'], treatment_df['coef'],
   # color='black', linewidth=0.75, zorder=2
#)

# ── 2) dot at the omitted (normalised-to-zero) bin ─────────────────────────────
# If the omitted bin is event time –1, use x = -1; if it’s event time 0, use x = 0.
omitted_x = -0          # or -1, depending on which bin you normalised away
ax.scatter(
    omitted_x, 0,
    color='black', s=40, zorder=3   # size ~40 gives a nice solid dot
)

# (everything else in your script stays the same)


# Improve layout and save the figure
fig.tight_layout()
fig.savefig("event_study.png", dpi=300, bbox_inches='tight')

# Display the plot
plt.show()

# ── 1) thin black connecting line ──────────────────────────────────────────────
# Do the markers + errors first (no connecting line) …

