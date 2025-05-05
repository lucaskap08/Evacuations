import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import gaussian_kde
import pandas as pd
plt.rcParams['figure.dpi'] = 300

#-------------------------------
# Filter for each group and remove non-positive values
#-------------------------------
ful_shel = pd.read_csv("ful_shel.csv")

# For had_evac_int == 1
data1 = ful_shel.loc[ful_shel['had_evac_int'] == 1, 'PropertyDmgPerCapita'].dropna()
data1

data1 = data1[data1 > 0]  # remove zeroes and negative values
log_data1 = np.log(data1)  # apply the log transform

# For had_evac_int == 0
data0 = ful_shel.loc[ful_shel['had_evac_int'] == 0, 'PropertyDmgPerCapita'].dropna()
data0 = data0[data0 > 0]  # remove zeroes and negative values
log_data0 = np.log(data0)  # apply the log transform

#-------------------------------
# Create a common set of bins using the log-transformed data
#-------------------------------
min_val = min(log_data0.min(), log_data1.min())
max_val = max(log_data0.max(), log_data1.max())
bins = np.linspace(min_val, max_val, 30)

#-------------------------------
# Plot the overlayed histograms with density curves
#-------------------------------

min_val = min(np.min(log_data1), np.min(log_data0))
max_val = max(np.max(log_data1), np.max(log_data0))

# Use a style, then override the facecolors to white
plt.style.use('ggplot')
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('white')  # Change the overall figure background
ax.set_facecolor('white')          # Change the axes background

# Plot histograms
ax.hist(log_data1, bins=bins, density=True, alpha=0.5, label='Evacuation', color='blue', edgecolor='black')
ax.hist(log_data0, bins=bins, density=True, alpha=0.5, label='No Evacuation', color='orange', edgecolor='black')

# Compute KDE curves and plot
kde1 = gaussian_kde(log_data1)
kde0 = gaussian_kde(log_data0)
xs = np.linspace(min_val, max_val, 200)
ax.plot(xs, kde1(xs), color='darkblue', linewidth=2)
ax.plot(xs, kde0(xs), color='orange', linewidth=2)

# Add title and labels
ax.set_title('')
ax.set_xlabel('Property Damage Per Capita (log scale)')
ax.set_ylabel('Density')
ax.legend()

# Save the figure
fig.savefig("property_damage_distribution.png", dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
plt.show()


#repeat but for only category 3+ events
#distributions are much mroe similar
ful_shel= ful_shel[ful_shel['USA_SSHS'] >2].copy()
data1 = ful_shel.loc[ful_shel['had_evac_int'] == 1, 'PropertyDmgPerCapita'].dropna()
data1

data1 = data1[data1 > 0]  # remove zeroes and negative values
log_data1 = np.log(data1)  # apply the log transform

# For had_evac_int == 0
data0 = ful_shel.loc[ful_shel['had_evac_int'] == 0, 'PropertyDmgPerCapita'].dropna()
data0 = data0[data0 > 0]  # remove zeroes and negative values
log_data0 = np.log(data0)  # apply the log transform

#-------------------------------
# Create a common set of bins using the log-transformed data
#-------------------------------
min_val = min(log_data0.min(), log_data1.min())
max_val = max(log_data0.max(), log_data1.max())
bins = np.linspace(min_val, max_val, 30)

#-------------------------------
# Plot the overlayed histograms with density curves
#-------------------------------

min_val = min(np.min(log_data1), np.min(log_data0))
max_val = max(np.max(log_data1), np.max(log_data0))

# Use a style, then override the facecolors to white
plt.style.use('ggplot')
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('white')  # Change the overall figure background
ax.set_facecolor('white')          # Change the axes background

# Plot histograms
ax.hist(log_data1, bins=bins, density=True, alpha=0.5, label='Evacuation', color='blue', edgecolor='black')
ax.hist(log_data0, bins=bins, density=True, alpha=0.5, label='No Evacuation', color='orange', edgecolor='black')

# Compute KDE curves and plot
kde1 = gaussian_kde(log_data1)
kde0 = gaussian_kde(log_data0)
xs = np.linspace(min_val, max_val, 200)
ax.plot(xs, kde1(xs), color='darkblue', linewidth=2)
ax.plot(xs, kde0(xs), color='orange', linewidth=2)

# Add title and labels
ax.set_title('')
ax.set_xlabel('Property Damage Per Capita (log scale)')
ax.set_ylabel('Density')
ax.legend()

# Save the figure
fig.savefig("property_damage_distribution_cat3.png", dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
plt.show()



