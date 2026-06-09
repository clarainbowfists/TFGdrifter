import pandas as pd
import json
import struct
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

    old_df["msgDatetime"] = pd.to_datetime(
        old_df["msgDatetime"],
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

# parser

def parse_raw(raw):

    try:
        if pd.isna(raw) or len(raw) < 40:
            return None, None, None

        lat_hex = raw[8:16]
        lon_hex = raw[16:24]
        temp_hex = raw[34:38]

        # signed int32
        lat_int = struct.unpack(">i", bytes.fromhex(lat_hex))[0]
        lon_int = struct.unpack(">i", bytes.fromhex(lon_hex))[0]

        lat = lat_int / 1e6
        lon = lon_int / 1e6
        temp = int(temp_hex, 16) / 10

        return lat, lon, temp

    except:
        return None, None, None


# aplicar parser
parsed = df["rawData"].apply(parse_raw)

df["gpsLocLat"] = parsed.apply(lambda x: x[0] if x else None)
df["gpsLocLon"] = parsed.apply(lambda x: x[1] if x else None)
df["temperature"] = parsed.apply(lambda x: x[2] if x else None)
#filtre temperatures vàlides
df = df[(df["temperature"] >= 0) & (df["temperature"] <= 100)]
#filtre geogràfic
df = df[
    (df["gpsLocLat"].between(40.5, 42.8)) &
    (df["gpsLocLon"].between(0.5, 3.5))
]

# eliminar dades corruptes
df = df.dropna(subset=["gpsLocLat", "gpsLocLon", "temperature"])

# ordenar
df = df.sort_values("msgDatetime")

# eliminar duplicats
if Path(csv_file).exists():
    final_df = pd.concat([old_df, df], ignore_index=True)
    final_df = final_df.drop_duplicates(subset=["deviceMsgUid"])
else:
    final_df = df

# convertir temps
final_df["msgDatetime"] = pd.to_datetime(final_df["msgDatetime"], errors="coerce")

# ordenar final
final_df = final_df.sort_values("msgDatetime")

# guardar CSV brut
final_df.to_csv(csv_file, index=False)

# CSV net

clean_df = final_df[[
    "msgDatetime",
    "gpsLocLon",
    "gpsLocLat",
    "temperature",
    "deviceRef"
]].copy()

clean_df = clean_df.rename(columns={
    "msgDatetime": "timestamp",
    "gpsLocLon": "lon",
    "gpsLocLat": "lat"
})

clean_df = clean_df.sort_values("timestamp").reset_index(drop=True)

clean_df.to_csv("temperature_hex_data.csv", index=False)

# CSV web

web_df = final_df[[
    "msgDatetime",
    "gpsLocLon",
    "gpsLocLat",
    "temperature",
    "deviceRef"
]].copy()

web_df = web_df.rename(columns={
    "msgDatetime": "timestamp",
    "gpsLocLon": "lon",
    "gpsLocLat": "lat"
})

web_df = web_df.dropna(subset=["lon", "lat", "temperature"])
web_df = web_df[(web_df["temperature"] > 0) & (web_df["temperature"] < 100)]

web_df = web_df.sort_values("timestamp").reset_index(drop=True)

web_df.to_csv("web_map_data.csv", index=False)

print(f"CSV actualitzat amb {len(df)} noves files.")