from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import requests

from fx_notifier.domain.errors import FXServiceError

JSONDict = dict[str, Any]
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


@dataclass
class FrankfurterClient:
    api_url: str
    base_currency: str
    api_currencies: tuple[str, ...]

    def get_latest_rates(
        self,
        timeout: float = 10,
        retries: int = 3,
        backoff_seconds: float = 1.0,
    ) -> JSONDict:
        return self._request_json(
            self._build_api_url("latest"),
            params={
                "base": self.base_currency,
                "symbols": ",".join(self.api_currencies),
            },
            timeout=timeout,
            retries=retries,
            backoff_seconds=backoff_seconds,
        )

    def get_historical_rates(
        self,
        quote_currencies: tuple[str, ...],
        latest_date: str,
        timeout: float = 10,
        retries: int = 3,
        backoff_seconds: float = 1.0,
        lookback_days: int = 7,
    ) -> JSONDict:
        currencies = tuple(
            dict.fromkeys(
                currency
                for currency in quote_currencies
                if currency and currency not in {"AZN", self.base_currency}
            )
        )
        if not currencies:
            return {"rates": {}}

        try:
            end_date = date.fromisoformat(latest_date)
        except ValueError as exc:
            raise FXServiceError("latest_date must be in YYYY-MM-DD format") from exc

        start_date = end_date - timedelta(days=max(1, lookback_days))
        return self._request_json(
            self._build_api_url(f"{start_date.isoformat()}..{end_date.isoformat()}"),
            params={
                "base": self.base_currency,
                "symbols": ",".join(currencies),
            },
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
        timeout: float,
        retries: int,
        backoff_seconds: float,
    ) -> JSONDict:
        attempts = max(1, retries)

        for attempt in range(1, attempts + 1):
            try:
                response = requests.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise FXServiceError("FX response JSON must be an object")
                if not isinstance(data.get("rates"), dict):
                    raise FXServiceError("FX response missing 'rates' field")
                return data
            except ValueError as exc:
                raise FXServiceError("FX response was not valid JSON") from exc
            except requests.RequestException as exc:
                if attempt >= attempts or not self._should_retry_request(exc):
                    raise
                time.sleep(backoff_seconds * attempt)

        raise FXServiceError("Failed to fetch FX rates")

    @staticmethod
    def _should_retry_request(exc: requests.RequestException) -> bool:
        if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
            return True

        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            return exc.response.status_code in RETRYABLE_STATUS_CODES

        return False
