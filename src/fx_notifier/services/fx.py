from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from fx_notifier.config import FXSettings
from fx_notifier.domain.errors import FXServiceError
from fx_notifier.infrastructure.frankfurter import FrankfurterClient

JSONDict = dict[str, Any]


@dataclass
class FXService:
    settings: FXSettings
    client: FrankfurterClient | None = None

    def __post_init__(self) -> None:
        if self.client is None:
            self.client = FrankfurterClient(
                api_url=self.settings.api_url,
                base_currency=self.settings.base_currency,
                api_currencies=self.settings.api_currencies,
            )

    @classmethod
    def from_env(cls) -> FXService:
        return cls(FXSettings.from_env())

    @property
    def api_url(self) -> str:
        return self.settings.api_url

    @property
    def base_currency(self) -> str:
        return self.settings.base_currency

    @property
    def api_currencies(self) -> tuple[str, ...]:
        return self.settings.api_currencies

    @property
    def report_currencies(self) -> tuple[str, ...]:
        return self.settings.report_currencies

    @property
    def usd_azn_peg(self) -> float:
        return self.settings.usd_azn_peg

    def get_fx_rates(
        self,
        timeout: int = 10,
        retries: int = 3,
        backoff_seconds: float = 1.0,
    ) -> JSONDict:
        assert self.client is not None
        return self.client.get_latest_rates(
            timeout=timeout,
            retries=retries,
            backoff_seconds=backoff_seconds,
        )

    def get_previous_rates(
        self,
        quote_currencies: Iterable[str],
        latest_date: str,
        timeout: int = 10,
        retries: int = 3,
        backoff_seconds: float = 1.0,
        lookback_days: int = 7,
    ) -> dict[str, float]:
        assert self.client is not None
        data = self.client.get_historical_rates(
            tuple(quote_currencies),
            latest_date,
            timeout=timeout,
            retries=retries,
            backoff_seconds=backoff_seconds,
            lookback_days=lookback_days,
        )

        previous_rates: dict[str, float] = {}
        for rate_date in sorted(data.get("rates", {})):
            if rate_date >= latest_date:
                break

            day_rates = data["rates"][rate_date]
            for currency in quote_currencies:
                value = day_rates.get(currency)
                if value is None:
                    continue

                try:
                    previous_rates[currency] = float(value)
                except (TypeError, ValueError) as exc:
                    raise FXServiceError(
                        f"Invalid historical rate for {currency}: {value!r}"
                    ) from exc

        return previous_rates

    def derive_azn_rate(self, rates: dict[str, float]) -> float:
        eur_usd = rates.get("USD")
        if eur_usd is None:
            raise FXServiceError("USD rate missing; cannot derive AZN")

        try:
            derived = float(eur_usd) * self.usd_azn_peg
        except (TypeError, ValueError) as exc:
            raise FXServiceError("Invalid USD rate; cannot derive AZN") from exc

        return round(derived, 6)

    def normalize_rates(
        self,
        rates_data: JSONDict,
        report_currencies: Iterable[str] | None = None,
    ) -> dict[str, float]:
        active_report_currencies = (
            tuple(report_currencies) if report_currencies is not None else self.report_currencies
        )

        rates: dict[str, float] = {}
        for currency, value in rates_data.get("rates", {}).items():
            try:
                rates[currency] = float(value)
            except (TypeError, ValueError) as exc:
                raise FXServiceError(f"Invalid rate for {currency}: {value!r}") from exc

        rates[self.base_currency] = 1.0

        if "AZN" in active_report_currencies:
            rates["AZN"] = self.derive_azn_rate(rates)

        return rates
