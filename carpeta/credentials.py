import json
import os

CREDENTIALS_FILE = "./credentials.json"

def load_credentials(file_path=CREDENTIALS_FILE):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Archivo de credenciales no encontrado: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        creds = json.load(f)

    required_keys = ["username", "password", "client_id", "client_secret"]
    for key in required_keys:
        if key not in creds:
            raise ValueError(f"Falta la clave {key} en las credenciales")

    return creds