from unittest.mock import Mock

import pytest

from fx_notifier.app.workflows import build_performance_by_currency
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
