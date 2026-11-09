
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
from ib_async import IB, Stock, MarketOrder

# ------------- SETTINGS -------------

HOST = "127.0.0.1"
PORT = 7497
CLIENT_ID = 10

SYMBOL = "AAPL"
SHARES = 10

FAST_EMA = 10
SLOW_EMA = 20

# Send buy and sell orders to the connected paper account.
PLACE_PAPER_ORDERS = True

NY = ZoneInfo("America/New_York")

ENTRY_CUTOFF = time(15, 50) # Ensure we cant buy past this time
FLATTEN_TIME = time(15, 55) # Ensure we cant sell past this time, these values can still be changed

ib = IB()
stock = Stock(SYMBOL, "SMART", "USD")

last_processed_bar = None
flatten_attempted_day = None


# ------------- HELPERS -------------

def ny_timestamp(value):
    ts = pd.Timestamp(value)

    if ts.tzinfo is None:
        raise ValueError("Expected timezone-aware IBKR data")

    return ts.tz_convert(NY)


def position_quantity():
    """Read actual AAPL holdings from TWS."""
    return sum(
        float(p.position)
        for p in ib.positions()
        if p.account == paper_account
        and p.contract.conId == stock.conId
    )


def has_open_order():
    """Prevent overlapping orders for AAPL."""
    return any(
        t.contract.conId == stock.conId
        for t in ib.openTrades()
        if not t.isDone()
    )


def send_order(action, quantity, reason):
    if not PLACE_PAPER_ORDERS:
        print(f"[SIGNAL ONLY] {action} {quantity} {SYMBOL}")
        return

    if not ib.isConnected():
        print("Disconnected: no order sent.")
        return

    if has_open_order():
        print("Existing order pending: skipping.")
        return

    order = MarketOrder(
        action,
        quantity,
        tif="DAY",
        account=paper_account
    )

    trade = ib.placeOrder(stock, order)

    print(
        f"SUBMITTED: {action} {quantity} {SYMBOL}"
        f" | Reason: {reason}"
        f" | Order ID: {trade.order.orderId}"
    )


# ------------- EMA STRATEGY -------------

def on_bar_update(updated_bars, has_new_bar):
    global last_processed_bar

    # The newest bar is still forming.
    if not has_new_bar or len(updated_bars) < 2:
        return

    closed_time = ny_timestamp(updated_bars[-2].date)
    new_bar_time = ny_timestamp(updated_bars[-1].date)

    if closed_time == last_processed_bar:
        return

    last_processed_bar = closed_time

    now = datetime.now(NY)

    # Reject stale/delayed data and missing-minute gaps.
    if not (0 <= (now - new_bar_time).total_seconds() <= 90):
        print("Stale data: skipping.")
        return

    if new_bar_time - closed_time != pd.Timedelta(minutes=1):
        print("Gap in market data: skipping.")
        return

    # Only process regular US trading hours.
    if not (time(9, 30) <= new_bar_time.time() < ENTRY_CUTOFF):
        return

    if new_bar_time.date() != now.date():
        return

    # Build DataFrame from completed candles ONLY.
    records = [
        (ny_timestamp(b.date), float(b.close))
        for b in updated_bars[:-1]
    ]

    df = pd.DataFrame(
        records,
        columns=["timestamp", "close"]
    ).set_index("timestamp")

    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]

    # Reset EMA calculations each trading day.
    df = df[df.index.date == closed_time.date()]
    df = df.between_time("09:30", "16:00",
                         inclusive="left")

    if len(df) < SLOW_EMA:
        return

    # Skip if recent observations aren't consecutive.
    recent_times = df.index[-SLOW_EMA:]
    if not (recent_times.to_series().diff().iloc[1:]
            == pd.Timedelta(minutes=1)).all():
        print("Recent candles missing: skipping.")
        return

    df["ema10"] = df["close"].ewm(
        span=FAST_EMA,
        min_periods=FAST_EMA,
        adjust=False
    ).mean()

    df["ema20"] = df["close"].ewm(
        span=SLOW_EMA,
        min_periods=SLOW_EMA,
        adjust=False
    ).mean()

    latest = df.iloc[-1]

    ema10 = latest["ema10"]
    ema20 = latest["ema20"]
    close = latest["close"]

    if pd.isna(ema10) or pd.isna(ema20):
        return

    # Same EMA rule as your backtest.
    desired_position = SHARES if ema10 > ema20 else 0

    print(
        f"{closed_time:%H:%M} | "
        f"Close: ${close:.2f} | "
        f"EMA10: {ema10:.2f} | "
        f"EMA20: {ema20:.2f} | "
        f"Target: {desired_position}"
    )

    if not PLACE_PAPER_ORDERS:
        return

    # Never act while another order is pending.
    if has_open_order():
        return

    actual_position = position_quantity()

    # Only manage flat or the intended long position.
    if actual_position not in (0, SHARES):
        print("Unexpected position: trading halted.")
        return

    if actual_position == 0 and desired_position == SHARES:
        send_order("BUY", SHARES, "EMA10 > EMA20")

    elif actual_position == SHARES and desired_position == 0:
        send_order("SELL", SHARES, "EMA10 <= EMA20")


# ------------- CONNECT TO TWS -------------

try:
    print("Connecting to IBKR Paper Trading...")

    ib.connect(
        HOST,
        PORT,
        clientId=CLIENT_ID,
        timeout=15
    )

    accounts = ib.managedAccounts()

    # Safety: only accept a single paper account.
    if len(accounts) != 1 or not accounts[0].startswith("DU"):
        raise RuntimeError(
            f"Expected one paper account, got: {accounts}"
        )

    paper_account = accounts[0]
    print("Connected to paper account:", paper_account)

    ib.qualifyContracts(stock)

    if PLACE_PAPER_ORDERS:
        if position_quantity() != 0 or has_open_order():
            raise RuntimeError(
                "Start with no AAPL position or pending orders."
            )

    # Ask for live market data.
    ib.reqMarketDataType(1)

    # Historical 1-minute candles + ongoing updates.
    live_bars = ib.reqHistoricalData(
        stock,
        endDateTime="",
        durationStr="2 D",
        barSizeSetting="1 min",
        whatToShow="TRADES",
        useRTH=True,
        formatDate=2,
        keepUpToDate=True
    )

    if not live_bars:
        raise RuntimeError("No market data received.")

    live_bars.updateEvent += on_bar_update

    print("EMA strategy running. Press Ctrl+C to stop.")

    # Keep the connection and strategy running.
    while ib.isConnected():
        now = datetime.now(NY)

        # Attempt to close holdings before 4 PM ET.
        if FLATTEN_TIME <= now.time() < time(16, 0):
            if flatten_attempted_day != now.date():
                if PLACE_PAPER_ORDERS:
                    qty = position_quantity()

                    if qty == SHARES and not has_open_order():
                        send_order("SELL", SHARES, "END_OF_DAY")
                        flatten_attempted_day = now.date()

                    elif qty == 0:
                        flatten_attempted_day = now.date()

        ib.sleep(1)

except KeyboardInterrupt:
    print("Strategy stopped by user.")

except Exception as error:
    print("ERROR:", error)

finally:
    if ib.isConnected():
        ib.disconnect()

    print("Disconnected from TWS.")
