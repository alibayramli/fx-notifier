import unittest
from unittest.mock import patch, Mock
import sys
import os

# Add the parent directory to the sys.path to allow imports from the main project folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fx_bot import get_fx_rates, format_message, send_telegram_message

class TestFxBot(unittest.TestCase):

    @patch('requests.get')
    def test_get_fx_rates_success(self, mock_get):
        """Test that get_fx_rates returns the correct data on a successful API call."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "amount": 1.0,
            "base": "EUR",
            "date": "2024-07-26",
            "rates": {
                "USD": 1.088,
                "HUF": 393.4,
                "AZN": 1.8494
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        rates_data = get_fx_rates()
        self.assertEqual(rates_data['base'], 'EUR')
        self.assertIn('USD', rates_data['rates'])

    def test_format_message(self):
        """Test that format_message correctly formats the message."""
        rates_data = {
            "amount": 1.0,
            "base": "EUR",
            "date": "2024-07-26",
            "rates": {
                "USD": 1.088,
                "HUF": 393.4,
                "AZN": 1.8494
            }
        }
        message = format_message(rates_data)
        self.assertIn("FX Rates for 2024-07-26 (Base: EUR):", message)
        self.assertIn("- USD: 1.088", message)
        self.assertIn("- HUF: 393.4", message)
        self.assertIn("- AZN: 1.8494", message)

    @patch('os.environ.get', return_value=None)
    def test_send_telegram_message_missing_env_vars(self, mock_env_get):
        """Test that send_telegram_message raises a ValueError if environment variables are not set."""
        with self.assertRaises(ValueError):
            send_telegram_message("Test message")

if __name__ == '__main__':
    unittest.main()
