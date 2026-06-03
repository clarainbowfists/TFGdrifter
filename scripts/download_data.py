from Telemetry_API import TelemetryAPI

import pandas as pd
import os

from datetime import datetime, timedelta

# Config

CSV_FILE = "telemetry_data.csv"

DEVICE_ID = 217475

api = TelemetryAPI(page_size=100)

# Última dada

if os.path.exists(CSV_FILE):

    old_df = pd.read_csv(CSV_FILE)

    if len(old_df) > 0:

        last_timestamp = old_df.iloc[-1]["timestamp"]

        from_date = datetime.fromisoformat(
            last_timestamp.replace("Z", "")
        )

    else:

        from_date = datetime.utcnow() - timedelta(hours=1)

else:

    old_df = pd.DataFrame()

    from_date = datetime.utcnow() - timedelta(hours=1)

# Afegir marge petit
from_date = from_date - timedelta(minutes=1)

to_date = datetime.utcnow()

# Format CLS
from_date_str = from_date.strftime(
    "%Y-%m-%dT%H:%M:%S.000Z"
)

to_date_str = to_date.strftime(
    "%Y-%m-%dT%H:%M:%S.000Z"
)

print("Descarregant:")
print(from_date_str)
print(to_date_str)

# Descarrega

data = api.get_all_data(
    from_date_str,
    to_date_str,
    device_refs=[DEVICE_ID]
)

if not data:

    print("No hi ha noves dades")
    exit()

# Processa

rows = []

for item in data:

    temperature = None

    sensors = item.get("sensors", [])

    if isinstance(sensors, list):

        for sensor in sensors:

            name = str(
                sensor.get("name", "")
            ).lower()

            if "temp" in name:

                temperature = sensor.get("value")
                break

    gps = item.get("gpsLoc", {})

    row = {

        "timestamp": item.get("msgDatetime"),

        "temperature": temperature,

        "latitude": gps.get("lat"),

        "longitude": gps.get("lon")
    }

    rows.append(row)

new_df = pd.DataFrame(rows)

# Concatenar

df = pd.concat([old_df, new_df])

# Eliminar duplicats
df = df.drop_duplicates()

# Ordenar
df = df.sort_values("timestamp")

# Guardar
df.to_csv(CSV_FILE, index=False)

print("CSV actualitzat")
print("Files totals:", len(df))