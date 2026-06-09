from flask import Flask, jsonify, render_template
import pandas as pd

app = Flask(__name__)

CSV_FILE = "web_map_data.csv"

# Web
@app.route('/')
def home():

    return render_template('api.html')

# Api

from flask import request

@app.route('/api/telemetry')
def telemetry():
    try:
        df = pd.read_csv(CSV_FILE)

        df = df.dropna(subset=["timestamp", "lon", "lat", "temperature"])
        df = df.sort_values("timestamp")

        # nous paràmetres
        device_id = request.args.get("device_id")
        from_date = request.args.get("from")
        to_date = request.args.get("to")

        # filtrar per device
        if device_id:
            df = df[df["deviceRef"].astype(str) == str(device_id)]

        # filtrar per dates
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        if from_date:
            df = df[df["timestamp"] >= pd.to_datetime(from_date)]

        if to_date:
            df = df[df["timestamp"] <= pd.to_datetime(to_date)]

        df = df.sort_values("timestamp")

        return jsonify(df.to_dict(orient="records"))

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == '__main__':

    app.run(debug=True)