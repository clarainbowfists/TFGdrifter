#!/usr/bin/env python
# coding: utf-8

from skyfield.api import load, wgs84, EarthSatellite, utc
from datetime import datetime, timedelta
import pandas as pd
import requests
import base64
import json

# -------------------- CONFIG --------------------
LOCATIONS = {
    "BCN": (41.382279, 2.184751),
    "VNG": (41.223573, 1.736298),
    "SGC": (41.191972, 1.604549),
}

DAYS_AHEAD = 30
MIN_ELEV = 30.0
MIN_DURATION = 3.0

SPREADSHEET_ID = "1X15ymR6I5HdzuzyzWHqI_JHTQ636_VgDvE4vK6sZhT4"
RANGE = "Pass1!A1"
SERVICE_ACCOUNT_FILE = "credentials.json"
# ------------------------------------------------

ts = load.timescale()

# List of NORAD IDs
satellites = {
    "KINEIS-1A": 60084,
    "KINEIS-1B": 60079,
    "KINEIS-1C": 60081,
    # "KINEIS-1D": 60082, # N/A
    "KINEIS-1E": 60083,

    "KINEIS-2A": 62932,
    "KINEIS-2B": 62934,
    "KINEIS-2C": 62929,
    "KINEIS-2D": 62930,
    "KINEIS-2E": 62931,

    "KINEIS-3A": 61223,
    "KINEIS-3B": 61224,
    # "KINEIS-3C": 61220, # N/A
    "KINEIS-3D": 61221,
    "KINEIS-3E": 61222,
    
    "KINEIS-4A": 63303,
    "KINEIS-4B": 63304,
    # "KINEIS-4C": 63301, # N/A
    "KINEIS-4D": 63302,
    "KINEIS-4E": 63300,

    "KINEIS-5A": 62084,
    # "KINEIS-5B": 62085, # N/A
    "KINEIS-5C": 62081,
    "KINEIS-5D": 62082,
    "KINEIS-5E": 62083,
    #---Argos satellites---
     # "ANGELS": 44876, # N/A
     "Metop-B": 38771,
     # "CS-HOPS": 54053, # N/A
     "Metop-C": 43689,
     # "NOAA-18": 28654, # N/A
     # "NOAA-19": 33591, # N/A
     "SARAL": 39086,
     # "NOAA-15": 25338, # N/A
     "Oceansat-3": 54361
}

def fetch_tle(norad_id):
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad_id}&FORMAT=TLE"
    r = requests.get(url)
    r.raise_for_status()
    return r.text.strip().splitlines()

# -------------------- CACHE TLE --------------------
tle_cache = {}
for name, norad in satellites.items():
    try:
        _, l1, l2 = fetch_tle(norad)
        tle_cache[name] = (l1, l2)
    except Exception as e:
        print(f"Error TLE {name}: {e}")

# -------------------- CALCULO --------------------
results = []
today = datetime.now(tz=utc)
for day_offset in range(DAYS_AHEAD):
    day = today + timedelta(days=day_offset)
    start_dt = datetime(day.year, day.month, day.day, tzinfo=utc)
    end_dt = start_dt + timedelta(days=1)
    start = ts.from_datetime(start_dt)
    end = ts.from_datetime(end_dt)
    for loc_name, (LAT, LON) in LOCATIONS.items():
        observer = wgs84.latlon(LAT, LON)
        for sat_name, (l1, l2) in tle_cache.items():
            try:
                sat = EarthSatellite(l1, l2, sat_name, ts)
                t, events = sat.find_events(observer, start, end, altitude_degrees=MIN_ELEV)
                for i in range(0, len(events), 3):
                    if i + 2 < len(events):
                        if events[i] == 0 and events[i+1] == 1 and events[i+2] == 2:
                            rise_time = t[i]
                            culm_time = t[i+1]
                            set_time = t[i+2]
                            alt, _, _ = (sat - observer).at(culm_time).altaz()
                            elevation = alt.degrees
                            duration = (
                                set_time.utc_datetime() - rise_time.utc_datetime()
                            ).total_seconds() / 60
                            if duration >= MIN_DURATION:
                                results.append({
                                    "Location": loc_name,
                                    "Date": rise_time.utc_strftime('%Y-%m-%d'),
                                    "Satellite": sat_name,
                                    "Rise": rise_time.utc_strftime('%H:%M:%S'),
                                    "Culmination": culm_time.utc_strftime('%H:%M:%S'),
                                    "Set": set_time.utc_strftime('%H:%M:%S'),
                                    "Elevation": round(elevation, 1),
                                    "Duration": round(duration, 1)
                                })
            except Exception as e:
                print(f"Error {sat_name} {loc_name}: {e}")
df = pd.DataFrame(results)
# Ordenar
df = df.sort_values(by=["Date", "Location", "Rise"])


# -------------------- GITHUB CONFIG --------------------
GITHUB_TOKEN = "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"
GITHUB_REPO = "carlos-de-la-vega/SPP"
FILE_PATH = "data/passes.json"
BRANCH = "main"

# -------------------- CONVERTIR A JSON --------------------
json_content = df.to_json(orient="records", indent=2)
encoded_content = base64.b64encode(json_content.encode()).decode()

# -------------------- OBTENER SHA (si el archivo existe) --------------------
url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

response = requests.get(url, headers=headers)

sha = None
if response.status_code == 200:
    sha = response.json()["sha"]

# -------------------- SUBIR ARCHIVO --------------------
data = {
    "message": "Update satellite passes data",
    "content": encoded_content,
    "branch": BRANCH
}

if sha:
    data["sha"] = sha  # necesario para update

upload = requests.put(url, headers=headers, data=json.dumps(data))
upload.raise_for_status()

print("Datos subidos a GitHub correctamente")