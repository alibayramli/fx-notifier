from fx_notifier.services import format_message


def test_format_message(fx_env):
    rates_data = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2024-07-26",
        "rates": {
            "USD": 1.088,
            "HUF": 393.4,
        },
    }

    green_indicator = "\U0001F7E2"
    red_indicator = "\U0001F534"

    message = format_message(
        rates_data,
        performance_by_currency={"USD": 0.28, "HUF": -0.33, "AZN": 0.28},
    )

    expected = (
        "<b>EUR FX Update</b> 2024-07-26\n"
        "<pre>\n"
        "Pair      1 EUR  Perf\n"
        f"EUR/USD   1.088  {green_indicator} +0.28%\n"
        f"EUR/HUF   393.4  {red_indicator} -0.33%\n"
        f"EUR/AZN  1.8496  {green_indicator} +0.28%\n"
        "</pre>"
    )

    assert message == expected
