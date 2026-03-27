from __future__ import annotations

import asyncio

from fx_notifier.app import main_async


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
