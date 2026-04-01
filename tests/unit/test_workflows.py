import asyncio
from unittest.mock import Mock

import pytest
import requests

from fx_notifier.app.workflows import (
    PERFORMANCE_WARNING,
    build_performance_by_currency,
    get_performance_context,
    run_notification_workflow,
)
from fx_notifier.services import FXService


def test_build_performance_by_currency_tracks_eur_instrument_moves(fx_env):
    service = FXService.from_env()
    service.get_previous_rates = Mock(return_value={"USD": 1.085, "HUF": 392.8})  # type: ignore[method-assign]

    performance = build_performance_by_currency(
        service,
        {
            "date": "2024-07-26",
            "rates": {"USD": 1.088, "HUF": 393.4},
        },
    )

    assert performance["USD"] == pytest.approx(0.2764976958525302)
    assert performance["HUF"] == pytest.approx(0.1527494908350189)
    assert performance["AZN"] == pytest.approx(0.2764976958525178)


def test_run_notification_workflow_surfaces_performance_warning(fx_env):
    service = FXService.from_env()
    service.get_fx_rates = Mock(  # type: ignore[method-assign]
        return_value={
            "date": "2024-07-26",
            "rates": {"USD": 1.088, "HUF": 393.4},
        }
    )
    service.get_previous_rates = Mock(  # type: ignore[method-assign]
        side_effect=requests.RequestException("history unavailable")
    )

    class FakeNotifier:
        def __init__(self) -> None:
            self.messages: list[str] = []

        async def send_message(self, message: str) -> None:
            self.messages.append(message)

    notifier = FakeNotifier()
    message = asyncio.run(run_notification_workflow(service=service, notifier=notifier))

    assert PERFORMANCE_WARNING in message
    assert notifier.messages == [message]


def test_get_performance_context_returns_warning_on_failure(fx_env):
    service = FXService.from_env()
    service.get_previous_rates = Mock(  # type: ignore[method-assign]
        side_effect=requests.RequestException("history unavailable")
    )

    performance_by_currency, warnings = get_performance_context(
        service,
        {
            "date": "2024-07-26",
            "rates": {"USD": 1.088, "HUF": 393.4},
        },
    )

    assert performance_by_currency == {}
    assert warnings == [PERFORMANCE_WARNING]
