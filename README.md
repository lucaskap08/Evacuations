# Kaplan Evacuation‑Order Research &nbsp;|&nbsp; *Employment Pipeline*

This repository contains a set of Python scripts that clean, merge, and visualize data for the employment portion of Kaplan’s evacuation‑order research.

---

## Script Overview

| Script | Purpose / Output |
|--------|------------------|
| **`southeast_wind.py`** | • Reads **`tracs_1980.csv`** (HURDAT hurricane tracks).<br>• Intersects storm tracks with county shapefile for the target states.<br>• Explores buffer radii & generates exploratory wind‐speed plots.<br>• **Outputs:** `south_wdate_new.csv`. |
| **`merge.py`** | • Merges:<br>&nbsp;&nbsp;– `south_wdate_new.csv` (from previous step)<br>&nbsp;&nbsp;– **`HEvOD_2014-2022.csv`** (evacuation orders)<br>&nbsp;&nbsp;– **`employment_new.csv`**<br>• Cleans dates and builds a **two‑year panel** (pre/post) for each storm‑county.<br>• **Outputs:** `data_clean.csv`. |
| **`sheldus.py`** | • Loads **`sheldus.csv`** (property damage & fatalities).<br>• Creates:<br>&nbsp;&nbsp;1. `ful_shelly.csv` – **long** (county‑month) panel.<br>&nbsp;&nbsp;2. `ful_shel.csv` – **event‑level** (county‑storm) aggregation. |
| **`distributions.py`** | • Uses `ful_shel.csv` to plot property‑damage distributions:<br>&nbsp;&nbsp;– All storms **Category ≥ 2**.<br>&nbsp;&nbsp;– Separately for **Category 4 & 5**. |
| **`southeast_plot.py`** | • Visualizes counts of **high wind speed (>103 mph)** at the county level.<br>• Generates additional exploratory wind‑metric maps. |
| **`evac_plots.py`** | • Plots county‑level counts of evacuation orders.<br>• Reads **`southern_counties.csv`**, `HEvOD_2014-2022.csv`, and the county shapefile. |
| **`event_study.py`** | • Produces the employment **event‑study figure**.<br>• Requires `ful_shelly.csv` (from `sheldus.py`). |
| **`unemployment.py`** *(optional)* | • Builds `employment_new.csv` from raw unemployment data.<br>• **⚠️ Slow – not needed if `employment_new.csv` already exists.** |

---

##  Execution Order

1. `southeast_wind.py`
2. `merge.py`
3. `sheldus.py`
4. `distributions.py`
5. `southeast_plot.py`
6. `evac_plots.py`
7. `event_study.py`
8. *(optional)* `unemployment.py` → should be run **before** `merge.py` if `employment_new.csv` is missing.

---