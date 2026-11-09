import argparse
import csv
import os
from datetime import date, datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

from massive import RESTClient


def download_market_data(ticker, starting_date, end_date, output_file, adjusted=True):
    if date.fromisoformat(starting_date) > date.fromisoformat(end_date):
        raise ValueError("starting_date must be on or before end_date")

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    api_key = os.environ.get("MASSIVE_API_KEY")
    if not api_key:
        raise ValueError("Set the MASSIVE_API_KEY environment variable first")

    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    count = 0

    client = RESTClient(api_key)
    try:
        # Exclusive mode prevents overwriting an existing dataset.
        with output_file.open("x", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "timestamp_utc", "open", "high", "low", "close",
                "volume", "vwap", "transactions",
            ])

            for bar in client.list_aggs(
                ticker=ticker.upper(),
                multiplier=1,
                timespan="minute",
                from_=starting_date,
                to=end_date,
                adjusted=adjusted,
                sort="asc",
                limit=50000,
            ):
                timestamp = datetime.fromtimestamp(
                    bar.timestamp / 1000, tz=timezone.utc
                ).isoformat(timespec="seconds")
                writer.writerow([
                    timestamp, bar.open, bar.high, bar.low, bar.close,
                    bar.volume, bar.vwap, bar.transactions,
                ])
                count += 1
    finally:
        client.client.clear()

    print(f"Saved {count:,} bars to {output_file}")
    return output_file


if __name__ == "__main__":
    ticker = "NVDA"
    download_market_data(
        ticker, "2016-01-01", "2026-10-01", f"{ticker}_1min_10y.csv"
    )
