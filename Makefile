install:
	python -m pip install -r requirements.txt

test:
	python -m pytest -q

run-dry:
	DRY_RUN=1 python fx_bot.py

run:
	python fx_bot.py
