import pandas as pd
import json
from datetime import datetime, timezone
from pathlib import Path
from Telemetry_API import TelemetryAPI

# API
api = TelemetryAPI(page_size=100)

# CSV principal
csv_file = "telemetry_data.csv"

# Dispositius
devices = [217475]

# Data inicial
if Path(csv_file).exists():

    old_df = pd.read_csv(csv_file)
    print(old_df.columns.tolist())

    old_df["msgDatetime"] = pd.to_datetime(
        old_df["msgDatetime"],
        format="mixed",
        errors="coerce"
    )

    last_date = old_df["msgDatetime"].max()

    from_date = last_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

else:
    from_date = "2026-05-27T10:00:00.001Z"

# Data actual UTC
to_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

print("Descarregant des de:", from_date)
print("Fins a:", to_date)

# Descàrrega API
data = api.get_all_data(
    from_date,
    to_date,
    device_refs=devices
)

df = pd.DataFrame(data)

# Extreu temperatura
# Extreure temperatura des del rawData
def extract_temp(raw):

    try:

        if pd.isna(raw):
            return None

        # Busca bytes correspondència temperatura
        temp_hex = raw[34:38]

        # Hex -> decimal
        temp_value = int(temp_hex, 16)

        # Escala
        return temp_value / 10

    except:
        return None

df["temperature"] = df["rawData"].apply(extract_temp)

# Si no hi ha dades noves
if df.empty:
    print("No hi ha dades noves.")

else:

    if Path(csv_file).exists():

        final_df = pd.concat([old_df, df], ignore_index=True)

        final_df = final_df.drop_duplicates(subset=["deviceMsgUid"])

    else:
        final_df = df

    # Convertir dades
    final_df["msgDatetime"] = pd.to_datetime(
        final_df["msgDatetime"],
        errors="coerce"
    )

    final_df["gpsLocDatetime"] = pd.to_datetime(
        final_df["gpsLocDatetime"],
        errors="coerce"
    )

    # Endreça temporalment
    final_df = final_df.sort_values(
        "msgDatetime",
        na_position="last"
    )

    # Guarda CSV
    final_df.to_csv(csv_file, index=False)

    # CSV net
    clean_df = final_df[[
        "msgDatetime",
        "gpsLocLon",
        "gpsLocLat",
        "temperature",
        "deviceRef",
        "rawData"
    ]].copy()

    clean_df["gpsLocLon"] = clean_df["gpsLocLon"].ffill()
    clean_df["gpsLocLat"] = clean_df["gpsLocLat"].ffill()

    clean_df["temperature"] = clean_df["temperature"].ffill()

    clean_df = clean_df[clean_df["temperature"] > 0]
    clean_df = clean_df[clean_df["temperature"] < 100]

    clean_df = clean_df.rename(columns={
        "msgDatetime": "timestamp",
        "gpsLocLon": "lon",
        "gpsLocLat": "lat"
    })

    clean_df = clean_df.dropna(subset=["lon", "lat"])

    clean_df = clean_df.sort_values("timestamp").reset_index(drop=True)

    clean_df.to_csv("temperature_hex_data.csv", index=False)

    # CSV per la web
    web_df = final_df[[
        "msgDatetime",
        "gpsLocLon",
        "gpsLocLat",
        "temperature",
        "deviceRef"
    ]].copy()
    
    # Omplir GPS amb últim valor conegut
    web_df["gpsLocLon"] = web_df["gpsLocLon"].ffill()
    web_df["gpsLocLat"] = web_df["gpsLocLat"].ffill()

    # Omplir temperatura amb últim valor conegut
    web_df["temperature"] = web_df["temperature"].ffill()
    web_df = web_df[web_df["temperature"] > 0]
    web_df = web_df[web_df["temperature"] < 100]

    web_df = web_df.rename(columns={
        "msgDatetime": "timestamp",
        "gpsLocLon": "lon",
        "gpsLocLat": "lat"
    })
    web_df = web_df.dropna(subset=["lon", "lat"])

    web_df = web_df.sort_values("timestamp").reset_index(drop=True)
    web_df.to_csv("web_map_data.csv", index=False)

    print(f"CSV actualitzat amb {len(df)} noves files.")