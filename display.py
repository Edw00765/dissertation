import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

df = pd.DataFrame({
    "Ticker": ["AAPL", "AMZN", "GOOGL", "META", "MSFT",
               "NVDA", "TSLA", "QQQ", "SPY"],
    "Trades": [4336, 4274, 4240, 4292, 4408, 4373, 4278, 4273, 4137],
    "Purchases": [
        9521332.27, 8607830.07, 7944731.17,
        25292082.02, 19483497.88, 5711497.52,
        12486137.03, 21703799.38, 24055402.58
    ],
    "PnL": [
        111.75, 401.84, 186.79, -275.68, -273.59,
        231.30, 1259.54, 629.36, 826.91
    ]
})

df["PnL_per_trade"] = df["PnL"] / df["Trades"]
df["PnL_pct"] = df["PnL"] / df["Purchases"] * 100

charts = [
    ("PnL", "Total net P&L", "Dollars", "${:,.2f}"),
    ("PnL_per_trade", "Average P&L per trade", "Dollars per trade", "${:.3f}"),
    ("PnL_pct", "P&L per dollar purchased", "Percent (%)", "{:.4f}%"),
]

fig, axes = plt.subplots(1, 3, figsize=(17, 6))

for ax, (column, title, xlabel, label_format) in zip(axes, charts):
    # Sort each chart independently, with the highest value at the top.
    data = df.sort_values(column, ascending=False)
    colors = ["#20966b" if value >= 0 else "#d9534f"
              for value in data[column]]

    bars = ax.barh(data["Ticker"], data[column], color=colors)
    ax.invert_yaxis()
    ax.axvline(0, color="#555555", linewidth=0.8)

    labels = [
        label_format.format(value)
        if value >= 0 else "−" + label_format.format(abs(value))
        for value in data[column]
    ]
    ax.bar_label(bars, labels=labels, padding=5, fontsize=9)

    ax.set_title(title, fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel(xlabel)
    ax.margins(x=0.35)
    ax.set_axisbelow(True)
    ax.grid(axis="x", alpha=0.2)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)

axes[0].xaxis.set_major_formatter(
    FuncFormatter(lambda value, _: f"${value:,.0f}")
)
axes[1].xaxis.set_major_formatter(
    FuncFormatter(lambda value, _: f"${value:.2f}")
)

fig.suptitle("Trading performance by ticker", fontsize=17, fontweight="bold")
plt.tight_layout()
plt.savefig("trading_performance.png", dpi=200, bbox_inches="tight")
plt.show()