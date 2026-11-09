import pandas as pd

# This function prepares the market data
# Essentially, it first converts the time to New York time to make it consistent and easier to track because of things like daylight savings. Since our stocks are all american and it follows this timezone, it makes sense
# Then, we filter following the start and end dates, making it a lot easier to get certain dates for backtesting
# After that, we filter so that we use only full dates and skip non complete days
# return both complete and incomplete dates
def prepare_market_bars(
    input_file,
    date_column="timestamp_utc",
    market_open="09:30",
    market_close="16:00",
    starting_date=None,
    end_date=None,
):
    df = pd.read_csv(input_file, parse_dates=[date_column])
    df = df.set_index(date_column).tz_convert("America/New_York")
    df.index = df.index.tz_localize(None)
    df = df.sort_index()

    start = pd.Timestamp(starting_date).normalize() if starting_date is not None else None
    end = pd.Timestamp(end_date).normalize() if end_date is not None else None
    if start is not None and end is not None and start > end:
        raise ValueError("starting_date must be on or before end_date")
    if start is not None:
        df = df[df.index.normalize() >= start]
    if end is not None:
        df = df[df.index.normalize() <= end]

    df = df.between_time(market_open, market_close, inclusive="left")

    days = []
    incomplete_dates = []
    for date, day_data in df.groupby(df.index.date):
        if len(day_data) < 390:
            incomplete_dates.append(date)
            continue
        day_data = day_data[
            ["open", "high", "low", "close", "volume"]
        ]
        days.append(day_data)

    if days:
        bars = pd.concat(days)
    else:
        bars = df[["open", "high", "low", "close", "volume"]].iloc[:0].copy()

    return bars, incomplete_dates
