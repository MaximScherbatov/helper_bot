import requests


DADATA_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"


class DaDataClient:
    def suggest_party(self, api_key: str, query: str, count: int = 1) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Token {api_key}",
        }
        payload = {
            "query": query,
            "count": count,
        }

        response = requests.post(
            DADATA_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()