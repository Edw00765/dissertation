from pathlib import Path
import sys

# Allow direct execution through the IDE's Run Python File button.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import matplotlib.pyplot as plt
from data_tools.data_preparation import prepare_market_bars
INPUT_TICKER = "TSLA"
INPUT_FILE = f"data/{INPUT_TICKER}_1min_10y.csv"
MARKET_OPEN_TIME = "9:30"
MARKET_CLOSE_TIME = "16:00"

STARTING_DATE = "2024-01-01"
END_DATE = "2025-12-31"
# DATE_COLUMN = ""
SHARES = 10

def get_EMA_trades(input_file):
    bars, incomplete_dates = prepare_market_bars(input_file=input_file, market_open=MARKET_OPEN_TIME, market_close=MARKET_CLOSE_TIME, starting_date=STARTING_DATE, end_date=END_DATE)
    print("Incomplete dates:", [str(date) for date in incomplete_dates])
    bars['day'] = bars.index.date

    # We need to calculate the ema seperately throughout each day, so we group them based on the day
    day_group = bars.groupby("day")["close"]
    bars["ema10"] = day_group.transform(lambda s: s.ewm(span=10, min_periods = 10, adjust=False).mean())
    bars["ema20"] = day_group.transform(lambda s: s.ewm(span=20, min_periods = 20, adjust=False).mean())

    # here we define our positions
    bars["signal"] = (bars["ema10"] > bars["ema20"]).astype(int)

    # The reason why we have shift is because in this version we are using the closing value, so technically if it
    # closes, we can only buy in the next minute, hence the shift
    # We first group by the day before shifting to ensure that each day shifts independently
    bars["position"] = bars.groupby("day")["signal"].shift(1).fillna(0)

    trades = []
    for day, day_bars in bars.groupby("day"):
        # Here we define trading data
        holding = False
        entry_time = None
        entry_price = None
        # We define when is the last trade where we need to exit.
        last_real_time = day_bars.index[-1]

        for timestamp, bar in day_bars.iterrows():
            desired_position = int(bar["position"])
            # In this case, we buy
            if not holding and desired_position == 1:
                if timestamp == last_real_time:
                    continue
                holding = True
                entry_time = timestamp
                entry_price = bar["open"]

            # In this case, we sell
            elif holding and desired_position == 0:
                exit_time = timestamp
                exit_price = bar["open"]
                gross_pnl = ((exit_price - entry_price) * SHARES)
                trades.append({
                    "day": day,
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "shares": SHARES,
                    "gross_pnl": gross_pnl,
                    "exit_reason": "SIGNAL"
                })
                holding = False
                entry_time = None
                entry_price = None

        if holding:
            last_bar = day_bars.iloc[-1]
            exit_time = last_real_time
            exit_price = last_bar["close"]

            gross_pnl = ((exit_price - entry_price) * SHARES)
            trades.append({
                "day": day,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "shares": SHARES,
                "gross_pnl": gross_pnl,
                "exit_reason": "END_OF_DAY"
            })
    return trades, bars

# Here we can print the trades if we want
trades, bar_chart = get_EMA_trades(INPUT_FILE)
trade_columns = [
    "day",
    "entry_time",
    "exit_time",
    "entry_price",
    "exit_price",
    "shares",
    "gross_pnl",
    # "commission",
    # "net_pnl",
    "exit_reason"
]

trade_log = pd.DataFrame(
    trades,
    columns=trade_columns
)

# print(trade_log)


# ---------------- RESULTS ----------------
if not trade_log.empty:
    total_trades = len(trade_log)
    total_pnl = trade_log["gross_pnl"].sum()
    # Cumulative purchase cost, including money reused across trades.
    total_spent = (trade_log["entry_price"] * trade_log["shares"]).sum()
    total_return_pct = (total_pnl / total_spent) * 100 if total_spent else 0.0

    winning_trades = (
        trade_log["gross_pnl"] > 0
    ).sum()
    win_rate = (
        winning_trades / total_trades
    ) * 100
    avg_pnl = trade_log["gross_pnl"].mean()

    print("\nRESULT")
    print(f"Total trades: {total_trades}")
    print(f"Total spent on purchases: ${total_spent:,.2f}")
    print(f"Total gross P&L: ${total_pnl:,.2f}")
    print(f"Overall gain/loss (% of total spent): {total_return_pct:+.2f}%")
    print(f"Win rate: {win_rate:.2f}%")
    print(f"Average P&L per trade: ${avg_pnl:.2f}")

    # I added this here incase we want to inspect the output
    # trade_log.to_csv(
    #     "trade_log.csv",
    #     index=False
    # )

else:
    print("No trades were generated.")




# ------------------ PLOTTING ------------------

# selected_day = bar_chart["day"].iloc[0]

# # Filter the price data for the selected day
# plot_data = bar_chart[bar_chart["day"] == selected_day]

# # Filter the trades for the selected day
# day_trades = trade_log[trade_log["day"] == selected_day]

# plt.figure(figsize=(14, 7))

# # Closing price
# plt.plot(
#     plot_data.index,
#     plot_data["close"],
#     label="AAPL Close",
#     color="black",
#     linewidth=1.2
# )

# # Fast EMA
# plt.plot(
#     plot_data.index,
#     plot_data["ema10"],
#     label="EMA 10",
#     color="blue",
#     linewidth=1.5
# )

# # Slow EMA
# plt.plot(
#     plot_data.index,
#     plot_data["ema20"],
#     label="EMA 20",
#     color="orange",
#     linewidth=1.5
# )

# # ---------------- BUY / SELL MARKERS ----------------

# if not day_trades.empty:

#     # Mark every buy at its actual entry price
#     plt.scatter(
#         day_trades["entry_time"],
#         day_trades["entry_price"],
#         marker="^",
#         color="green",
#         s=120,
#         label="BUY",
#         zorder=5
#     )

#     # Mark every sell at its actual exit price
#     plt.scatter(
#         day_trades["exit_time"],
#         day_trades["exit_price"],
#         marker="v",
#         color="red",
#         s=120,
#         label="SELL",
#         zorder=5
#     )

# # ---------------- FORMATTING ----------------

# plt.title(f"AAPL 1-Minute Price and EMAs — {selected_day}")
# plt.xlabel("Time (New York)")
# plt.ylabel("Price ($)")

# plt.legend()
# plt.grid(True, alpha=0.3)
# plt.tight_layout()

# plt.show()
