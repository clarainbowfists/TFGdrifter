import math
import json
import csv
import time
import requests

from credentials import load_credentials

creds = load_credentials("credentials.json")


class TelemetryAPI:

    def __init__(self, page_size=50):

        self.TOKEN_URL = (
            "https://account.groupcls.com/auth/realms/cls/protocol/openid-connect/token"
        )

        self.COUNT_URL = (
            "https://api.groupcls.com/telemetry/api/v1/retrieve-bulk-count?lang=<string>"
        )

        self.DATA_URL = (
            "https://api.groupcls.com/telemetry/api/v1/retrieve-bulk?lang=<string>"
        )

        self.USERNAME = creds["username"]
        self.PASSWORD = creds["password"]
        self.CLIENT_ID = creds["client_id"]
        self.CLIENT_SECRET = creds["client_secret"]

        self.PAGE_SIZE = page_size

        self.access_token = None

    # Token

    def _get_token(self):

        token_data = {
            "grant_type": "password",
            "username": self.USERNAME,
            "password": self.PASSWORD
        }

        r = requests.post(
            self.TOKEN_URL,
            data=token_data,
            auth=(self.CLIENT_ID, self.CLIENT_SECRET)
        )

        r.raise_for_status()

        self.access_token = r.json()["access_token"]

        return self.access_token

    # Headers

    def _headers(self):

        if not self.access_token:
            self._get_token()

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    # Total count

    def get_total_count(self, from_date, to_date):

        payload = {
            "groupBy": "deviceUid",
            "fromDatetime": from_date,
            "toDatetime": to_date
        }

        r = requests.post(
            self.COUNT_URL,
            json=payload,
            headers=self._headers()
        )

        r.raise_for_status()

        return r.json()["totalCount"]

    # Fetch page

    def fetch_page(
        self,
        from_date,
        to_date,
        after_cursor=None,
        device_refs=None
    ):

        pagination = {
            "first": self.PAGE_SIZE
        }

        if after_cursor is not None:
            pagination["after"] = str(after_cursor)

        if device_refs is None:
            device_refs = []

        payload = {
            "pagination": pagination,
            "retrieveMetadata": True,
            "retrieveRawData": True,
            "retrieveDoppler": True,
            "retrieveGpsLoc": True,
            "retrieveSensors": True,
            "retrieveAdditionnalProperties": True,
            "deviceRefs": device_refs,
            "fromDatetime": from_date,
            "toDatetime": to_date,
            "datetimeFormat": "DATETIME"
        }

        # reintents automàtics
        for attempt in range(5):

            try:

                r = requests.post(
                    self.DATA_URL,
                    json=payload,
                    headers=self._headers()
                )

                # TOO MANY REQUESTS
                if r.status_code == 429:

                    wait_time = 5 * (attempt + 1)

                    print(
                        f"Masses peticions. Esperant {wait_time}s..."
                    )

                    time.sleep(wait_time)

                    continue

                # TOKEN CADUCAT
                if r.status_code == 401:

                    print("Token caducat. Renovant token...")

                    self._get_token()

                    continue

                r.raise_for_status()

                return r.json()["contents"]

            except requests.exceptions.RequestException as e:

                print(f"Error API: {e}")

                time.sleep(5)

        print("No s'ha pogut descarregar la pàgina.")

        return []

    # Recopila tot

    def get_all_data(
        self,
        from_date,
        to_date,
        device_refs=None,
        sleep=1
    ):

        print("Pidiendo total count...")

        total = self.get_total_count(
            from_date,
            to_date
        )

        print("Total registros:", total)

        total_pages = math.ceil(
            total / self.PAGE_SIZE
        )

        print("Total páginas:", total_pages)

        all_results = []

        after_cursor = None

        for page in range(total_pages):

            print(
                f"Página {page + 1}/{total_pages} | after={after_cursor}"
            )

            # pausa entre pàgines
            time.sleep(sleep)

            page_data = self.fetch_page(
                from_date,
                to_date,
                after_cursor,
                device_refs
            )

            all_results.extend(page_data)

            after_cursor = (
                (page + 1) * self.PAGE_SIZE - 1
            )

        print("Total descargado:", len(all_results))

        return all_results

    # Guarda CSV

    @staticmethod
    def save_csv(filename, data):

        if not data:

            print("No hay datos para guardar")

            return

        fieldnames = sorted({
            k for row in data for k in row.keys()
        })

        with open(
            filename,
            "w",
            newline="",
            encoding="utf-8"
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames
            )

            writer.writeheader()

            writer.writerows(data)

        print("CSV guardado:", filename)