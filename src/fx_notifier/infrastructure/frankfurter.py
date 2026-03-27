from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import requests

from fx_notifier.domain.errors import FXServiceError

JSONDict = dict[str, Any]


@dataclass
class FrankfurterClient:
    api_url: str
    base_currency: str
    api_currencies: tuple[str, ...]

    def get_latest_rates(
        self,
        timeout: int = 10,
        retries: int = 3,
        backoff_seconds: float = 1.0,
    ) -> JSONDict:
        url = self._build_api_url("latest")
        params = {
            "from": self.base_currency,
            "to": ",".join(self.api_currencies),
        }
        return self._request_json(
            url,
            params=params,
            timeout=timeout,
            retries=retries,
            backoff_seconds=backoff_seconds,
        )

    def get_historical_rates(
        self,
        quote_currencies: tuple[str, ...],
        latest_date: str,
        timeout: int = 10,
        retries: int = 3,
        backoff_seconds: float = 1.0,
        lookback_days: int = 7,
    ) -> JSONDict:
        currencies = tuple(
            dict.fromkeys(
                currency
                for currency in quote_currencies
                if currency and currency != "AZN"
            )
        )
        if not currencies:
            return {"rates": {}}

        end_date = date.fromisoformat(latest_date)
        start_date = end_date - timedelta(days=max(1, lookback_days))
        url = self._build_api_url(f"{start_date.isoformat()}..{end_date.isoformat()}")
        params = {
            "base": self.base_currency,
            "symbols": ",".join(currencies),
        }
        return self._request_json(
            url,
            params=params,
            timeout=timeout,
            retries=retries,
            backoff_seconds=backoff_seconds,
        )

    def _build_api_url(self, resource: str) -> str:
        api_url = self.api_url.rstrip("/")
        if api_url.endswith("/latest"):
            return f"{api_url.rsplit('/', 1)[0]}/{resource}"
        return f"{api_url}/{resource}"

    def _request_json(
        self,
        url: str,
        *,
        params: dict[str, str],
        timeout: int,
        retries: int,
        backoff_seconds: float,
    ) -> JSONDict:
        attempts = max(1, retries)
        last_request_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = requests.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                data = response.json()
                if "rates" not in data:
                    raise FXServiceError("FX response missing 'rates' field")
                return data
            except requests.RequestException as exc:
                last_request_error = exc
                if attempt < attempts:
                    time.sleep(backoff_seconds * attempt)

        if last_request_error is not None:
            raise last_request_error

        raise FXServiceError("Failed to fetch FX rates")
