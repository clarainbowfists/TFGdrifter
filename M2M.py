import pandas as pd
import json
import struct
import math
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

# parser identificar variables
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

#funció i filtre de posicions no vàlides segons velocitats possibles

def haversine(lat1, lon1, lat2, lon2):

    R = 6371000  # metres

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(dlambda / 2) ** 2
    )

    return 2 * R * math.asin(math.sqrt(a))

def smart_speed_filter(
    df,
    max_speed=3
):

    if len(df) < 3:

        return df

    keep = [True]

    for i in range(1, len(df)-1):
        A = df.iloc[i-1]
        B = df.iloc[i]
        C = df.iloc[i+1]

        # velocitat A->B
        dAB = haversine(

            A["gpsLocLat"],
            A["gpsLocLon"],

            B["gpsLocLat"],
            B["gpsLocLon"]

        )

        tAB = (
            B["msgDatetime"]
            -
            A["msgDatetime"]

        ).total_seconds()

        # velocitat B->C
        dBC = haversine(

            B["gpsLocLat"],
            B["gpsLocLon"],

            C["gpsLocLat"],
            C["gpsLocLon"]

        )

        tBC = (

            C["msgDatetime"]
            -
            B["msgDatetime"]

        ).total_seconds()

        # velocitat A->C
        dAC = haversine(

            A["gpsLocLat"],
            A["gpsLocLon"],

            C["gpsLocLat"],
            C["gpsLocLon"]

        )

        tAC = (

            C["msgDatetime"]
            -
            A["msgDatetime"]

        ).total_seconds()


        vAB = dAB/tAB if tAB > 0 else 999999
        vBC = dBC/tBC if tBC > 0 else 999999
        vAC = dAC/tAC if tAC > 0 else 999999


        spike = (

            vAB > max_speed
            and
            vBC > max_speed
            and
            vAC < max_speed
            and
            dAB > 500
            and
            dBC > 500

        )

        keep.append(not spike)

    keep.append(True)

    return df[keep].reset_index(drop=True)

#filtre de pics de gps
def spike_filter(df, threshold=2000):

    keep = [True]

    for i in range(1, len(df)-1):

        A = df.iloc[i-1]
        B = df.iloc[i]
        C = df.iloc[i+1]

        dAB = haversine(
            A["gpsLocLat"],
            A["gpsLocLon"],
            B["gpsLocLat"],
            B["gpsLocLon"]
        )

        dBC = haversine(
            B["gpsLocLat"],
            B["gpsLocLon"],
            C["gpsLocLat"],
            C["gpsLocLon"]
        )

        dAC = haversine(
            A["gpsLocLat"],
            A["gpsLocLon"],
            C["gpsLocLat"],
            C["gpsLocLon"]
        )

        spike = (

            dAB > threshold and
            dBC > threshold and
            dAC < threshold

        )

        keep.append(not spike)

    keep.append(True)

    return df[keep].reset_index(drop=True)

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

# endreçar
df["msgDatetime"] = pd.to_datetime(
    df["msgDatetime"],
    errors="coerce"
)

df = df.sort_values("msgDatetime")

# filtre velocitat
df = smart_speed_filter(
    df,
    max_speed=2
)

# filtre pics
df = spike_filter(
    df,
    threshold=1000
)

# eliminar duplicats
if Path(csv_file).exists():
    final_df = pd.concat([old_df, df], ignore_index=True)

    final_df["msgDatetime"] = pd.to_datetime(
        final_df["msgDatetime"],
        errors="coerce"
    )

    final_df = final_df.sort_values(
        "msgDatetime"
    )

    final_df = smart_speed_filter(
        final_df,
        max_speed=2
    )

    final_df = spike_filter(
        final_df,
        threshold=1500
    )

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