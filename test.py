from ib_async import *
import pandas as pd

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

# This describes what stock we want to see, through what instrument (SMART), and described in what currency
contract = Stock('AAPL', 'SMART', 'USD')
account = ib.managedAccounts()[0]
pnl = ib.reqPnL(account)
ib.sleep(2)   # give TWS time to send the data

# Example: place a paper order
# order = MarketOrder('BUY', 1)
# order.tif = "GTC"
# buy = ib.placeOrder(contract, order)
# ib.sleep(2)
# print("Buy status:", buy.orderStatus.status, "| filled:", buy.orderStatus.filled)

# for p in ib.positions():
#     print(p.contract.symbol, p.position, p.avgCost)

# sell = ib.placeOrder(contract, MarketOrder('SELL', 1))
# ib.sleep(2)
# print("Sell status:", sell.orderStatus.status, "| filled:", sell.orderStatus.filled)


rows = [{
    'time': f.execution.time,
    'symbol': f.contract.symbol,
    'side': f.execution.side,
    'qty': f.execution.shares,
    'price': f.execution.price,
    'commission': f.commissionReport.commission,
} for f in ib.reqExecutions()]
# print(pd.DataFrame(rows))


# To check how much I made today, shown in GBP
print("Today's P&L:  ", pnl.dailyPnL)
print("  Realized:   ", pnl.realizedPnL)
print("  Unrealized: ", pnl.unrealizedPnL)

for item in ib.accountSummary():
    if item.tag in ('NetLiquidation', 'TotalCashValue'):
        print(item.tag, item.value, item.currency)

ib.disconnect()