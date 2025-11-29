# The Rhythm of Focus: Quantifying the Lagged Causal Effects of Musical Genre on Digital Productivity and Attention Fragmentation

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-Data_Analysis-150458?style=for-the-badge&logo=pandas&logoColor=white)
![Spotify](https://img.shields.io/badge/Spotify-API-1DB954?style=for-the-badge&logo=spotify&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active_Research-success?style=for-the-badge)

**Course:** CCDATSCL_COM222 - Data Science  
**Author:** Robbie Espaldon  
**Tech Stack:** Python, AppleScript, Spotify Web API, Last.fm API, Pandas, Statsmodels, Seaborn

---

## Executive Summary

In an era of constant digital stimulation, students often toggle between deep work ("Flow State"), background music, and digital distractions. This project pivots from general market trends to a **"Quantified Self"** approach, utilizing high-granularity personal data to model behavioral patterns.

I engineered a custom telemetry pipeline to answer a specific behavioral question:
> **"Does the genre and intensity of the music I listen to have a *lagged causal effect* on my cognitive load, productivity, and attention fragmentation?"**

---

## The Research Hypothesis: "The Joji Paradox"

Standard productivity studies often suggest that high-energy music aids alertness. However, this study investigates personal nuances, specifically **"The Joji Paradox"**:

1.  **The Flow Hypothesis:** Does low-valence, "sad," or lo-fi music (e.g., Joji, Indie) actually correlate with higher periods of sustained coding/writing productivity?
2.  **The Lag Hypothesis:** Does listening to "Hype" music (Hip-Hop, Trap) result in a "crash" or increased social media usage (Doomscrolling) in the **subsequent 15-minute window**?

---

## System Architecture & Data Sources

To bypass the limitations of commercial time-tracking tools (which often lack raw data access or fail on Apple Silicon), I built a custom **ETL (Extract, Transform, Load)** pipeline.

### 1. Desktop Telemetry (The "Work" Sensor)
* **Script:** `mac_tracker.py`
* **Technology:** Python + **AppleScript** (via `subprocess`).
* **Why AppleScript?** Standard Python libraries like `pyobjc` often fail to correctly identify active windows when macOS **Stage Manager** is active. AppleScript queries the OS directly for the "frontmost" process, ensuring 100% accuracy even when switching Spaces.
* **Data Point:** Logs `Timestamp`, `App Name`, and `Window Title` every 5 seconds. Includes a built-in session timer.

### 2. Music Consumption (The "Stimulus" Sensor)
* **Script:** `music_fetcher.py`
* **Technology:** **Spotify API** (OAuth2) + **Last.fm API**.
* **Engineering Challenge:** In late 2024, Spotify deprecated the `Audio Features` endpoint (BPM/Energy) for new apps.
* **The Solution:** I implemented a **Genre-Based Fallback System**:
    1.  The script attempts to resolve the track's primary Artist ID via Spotify.
    2.  It fetches the Artist's genres.
    3.  **Fallback:** If Spotify returns empty metadata (common for "Shadow Profiles"), the script automatically queries **Last.fm tags** to fill the gap.

### 3. Mobile Activity (The "Distraction" Sensor)
* **Source:** **OffScreen** (iOS App).
* **Method:** Manual CSV Export via AirDrop (`Pickup.csv`).
* **Data Point:** Granular timestamped logs of phone pickups and duration (Screen On Time).

### 4. Data Integrity & Recovery
* **Script:** `rescue_mission.py`
* **Purpose:** A failsafe mechanism designed to recover lost music data due to API latency or Timezone/UTC mismatches. It utilizes a "Brute Force" history fetch combined with "Smart Filtering" to reconstruct listening sessions post-hoc, ensuring zero data loss during critical observation windows.

---

## Advanced Methodology: The "Research Grade" Metrics

Raw duration data is insufficient for behavioral analysis. The `etl_pipeline.py` derives three advanced metrics to ensure internal validity:

### 1. The Fragmentation Index (Focus Quality)
I do not simply measure "Total Minutes Worked." I also measure **Cognitive Load** via context switching.
* **Logic:** The script detects every instance where the active window switches from a "Productive" state to a "Distracted" state within a 15-minute bucket.
* **Metric:** `fragmentation_count`.
* **Significance:** High duration + High fragmentation = **Scattered Focus**. High duration + Low fragmentation = **Deep Work**.

### 2. Circadian Normalization (Z-Scores)
To control for confounding variables (e.g., being naturally tired at 11 PM vs. alert at 10 AM), I normalized productivity against the **Hour of Day**.
* **Logic:** I calculated the Z-Score (Standard Deviation from Mean) for the user's productivity at specific hours.
* **Metric:** `productivity_z_score`.
* **Significance:** This allows us to ask: "Was I *unusually* productive for 2 PM?" rather than just "Was I productive?"

### 3. Genre Bucketing
Since I cannot use numerical "Energy" scores (e.g., valence), I mapped loose genre strings into broad **Analysis Buckets**:
* **Focus:** Lo-fi, Jazz, Classical, Instrumental.
* **Hype:** Hip-Hop, Rap, Trap, Pop, Rock.
* **Vibe:** Indie, R&B, Soul, OPM, K-Indie, Christmas/Holiday.

---

## Statistical Framework

This project moves beyond simple correlation matrices to test for predictive validity.

### Granger Causality Testing
Correlation implies association, but not sequence. I utilize **Granger Causality Tests** (`statsmodels`) to determine if Music Category $X$ at time $t$ provides statistically significant information about Productivity Metric $Y$ at time $t+1$.

* **Lag Period:** 15 Minutes ($t-1$).
* **Significance Threshold:** $p < 0.05$.
* **Null Hypothesis:** "Listening to Hype Music does not predict future phone distraction."

---

## Project Structure

Note: git ignored both etl_pipeline.py and analysis_dashboard.py (will be converting to .ipynb) since it's not yet February/end stages of the study for us to have a master dataset to analyze.

```bash
CCDATSCL_Project/
├── data/
│   ├── mac_activity_log.csv       # Raw output from mac_tracker
│   ├── music_data.csv             # Enriched log from music_fetcher
│   ├── phone_data_clean.csv       # Processed iOS logs
│   └── MASTER_ANALYSIS_TABLE.csv  # Final dataset (Target generation: End of Term)
├── scripts/
│   ├── mac_tracker.py             # AppleScript background logger (w/ Session Timer)
│   ├── music_fetcher.py           # Spotify/Last.fm scraper (Infinite Loop)
│   ├── phone_processor.py         # Cleans AirDropped iPhone CSVs
│   ├── etl_pipeline.py            # Merges, Resamples, and Encodes data
│   ├── rescue_mission.py          # Data recovery tool for Timezone mismatches
│   └── analysis_dashboard.py      # Generates Heatmaps & Granger Tests
├── .env                           # API Credentials (Local only)
└── README.md