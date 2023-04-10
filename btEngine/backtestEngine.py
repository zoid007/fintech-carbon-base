import matplotlib.pyplot as plt
import yfinance as yf
import json

import pandas as pd
import pandas_ta as ta
from tqdm import tqdm
import numpy as np



class Order:
    def __init__(self, ticker, size, side, idx, limit_price=None, order_type='market'):
        self.ticker = ticker
        self.side = side
        self.size = size
        self.type = order_type
        self.limit_price = limit_price
        self.idx = idx

class Trade:
    def __init__(self, ticker, side, size, price, order_type, idx):
        self.ticker = ticker
        self.side = side
        self.price = price
        self.size = size
        self.type = order_type
        self.idx = idx

    def __repr__(self):
        return f'<Trade: {self.idx} {self.ticker} {self.size}@{self.price}>'

class Strategy:
    def __init__(self):
        self.current_idx = None
        self.data = None
        self.cash = None
        self.orders = []
        self.trades = []
        self.buy_trades = 0
        self.sell_trades = 0

    def buy(self, ticker, size=1):
        self.orders.append(
            Order(
                ticker=ticker,
                side='buy',
                size=size,
                idx=self.current_idx
            ))

    def sell(self, ticker, size=1):
        self.orders.append(
            Order(
                ticker=ticker,
                side='sell',
                size=-size,
                idx=self.current_idx
            ))

    def buy_limit(self, ticker, limit_price, size=1):
        self.orders.append(
            Order(
                ticker=ticker,
                side='buy',
                size=size,
                limit_price=limit_price,
                order_type='limit',
                idx=self.current_idx
            ))

    def sell_limit(self, ticker, limit_price, size=1):
        self.orders.append(
            Order(
                ticker=ticker,
                side='sell',
                size=-size,
                limit_price=limit_price,
                order_type='limit',
                idx=self.current_idx
            ))

    @property
    def position_size(self):
        return sum([t.size for t in self.trades])

    @property
    def close(self):
        return self.data.loc[self.current_idx]['Close']

    def on_bar(self):
        """This method will be overridden by custom strategies."""
        pass

class Engine:
    def __init__(self, initial_cash=100000):
        self.strategy = None
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.data = None
        self.current_idx = None
        self.cash_series = {}
        self.stock_series = {}
        self.datetime = {}
        self.trading_days = 252 #US AND Indian market trading days

    def add_data(self, data: pd.DataFrame):
        # Add OHLC data to the engine
        data['Index'] = np.arange(data.shape[0])
        data = data.reset_index().set_index('Index')
        self.data = data

    def add_strategy(self, strategy):
        # Add a strategy to the engine
        self.strategy = strategy

    def run(self):
        # Preprocess a few things before running the backtest
        self.strategy.data = self.data
        self.strategy.cash = self.cash
        for idx in tqdm(self.data.index):
            # Fill orders from the previous period
            self._fill_orders()
            # Run the strategy on the current bar
            self.current_idx = idx
            self.strategy.current_idx = self.current_idx
            self.strategy.on_bar()
            self.cash_series[idx] = self.cash
            self.datetime[idx] = self.data.loc[self.current_idx]['Date']
            self.stock_series[idx] = self.strategy.position_size * self.data.loc[self.current_idx]['Close']
        return self._get_stats()

    def _fill_orders(self):
        for order in self.strategy.orders:
            fill_price = self.data.loc[self.current_idx]['Open']
            can_fill = False

            if order.side == 'buy' and self.cash >= self.data.loc[self.current_idx]['Open'] * order.size:
                if order.type == 'limit':
                    if order.limit_price >= self.data.loc[self.current_idx]['Low']:
                        fill_price = order.limit_price
                        can_fill = True
                    else:
                        print(self.current_idx, 'Buy NOT filled. ', "limit", order.limit_price, " / low", self.data.loc[self.current_idx]['Low'])
                else:
                    can_fill = True

            elif order.side == 'sell' and self.strategy.position_size >= order.size:
                if order.type == 'limit':
                    if order.limit_price <= self.data.loc[self.current_idx]['High']:
                        fill_price = order.limit_price
                        can_fill = True
                    else:
                        print(self.current_idx, 'Sell NOT filled. ', "limit", order.limit_price, " / high", self.data.loc[self.current_idx]['High'])
                else:
                    can_fill = True

            if can_fill:
                trade = Trade(
                    ticker=order.ticker,
                    side=order.side,
                    price=fill_price,
                    size=order.size,
                    order_type=order.type,
                    idx=self.current_idx)

                self.strategy.trades.append(trade)
                self.cash -= trade.price * trade.size
                self.strategy.cash = self.cash

            if order.side == 'buy':
                self.strategy.buy_trades += 1
            elif order.side == 'sell':
                self.strategy.sell_trades += 1
                
        self.strategy.orders = []

    def _get_stats(self):
        metrics = {}
        total_return = 100 * ((self.data.loc[self.current_idx]['Close'] * self.strategy.position_size + self.cash) / self.initial_cash - 1)
        metrics['Total Return in %'] = total_return
        metrics['Total Return in Cash'] = (self.strategy.position_size * self.data.loc[self.current_idx]['Close']) + self.cash - self.initial_cash
        portfolio_bh = pd.DataFrame({'data': (self.initial_cash / self.data.loc[self.data.index[0]]['Open']) * self.data.Close, 'date': self.datetime})
        portfolio_bh = portfolio_bh.set_index('date')

        portfolio = pd.DataFrame({'stock': self.stock_series, 'cash': self.cash_series, 'date': self.datetime})
        portfolio = portfolio.reset_index().set_index("date")

        portfolio['Total Assets under Management'] = portfolio['stock'] + portfolio['cash']

        profitable_trades = [t for t in self.strategy.trades if t.side == 'buy' and t.price < t.price + t.size]
        profitable_trades += [t for t in self.strategy.trades if t.side == 'sell' and t.price > t.price + t.size]
        
    
        loss_trades = [t for t in self.strategy.trades if t.side == 'buy' and t.price >= t.price + t.size]
        loss_trades += [t for t in self.strategy.trades if t.side == 'sell' and t.price <= t.price + t.size]
        
    
        metrics['Total Profitable Trades'] = len(profitable_trades)
        metrics['Total Loss-making Trades'] = len(loss_trades)
        portfolio['total_aum'] = portfolio['stock'] + portfolio['cash']

        metrics.update(self._calculate_metrics(portfolio, portfolio_bh))


        return metrics

    def _calculate_metrics(self, portfolio, portfolio_bh):
        metrics = {}

        metrics['Exposure in %'] = ((portfolio['stock'] / portfolio['total_aum']) * 100).mean()
        p = portfolio.total_aum
        metrics['Annualized Returns'] = ((p.iloc[-1] / p.iloc[0]) ** (1 / ((p.index[-1] - p.index[0]).days / 365)) - 1) * 100
        p_bh = portfolio_bh
        metrics['Annualized Returns Buy&Hold'] = ((p_bh.iloc[-1] / p_bh.iloc[0]) ** (1 / ((p_bh.index[-1] - p_bh.index[0]).days / 365)) - 1) * 100

        metrics['Annualized Volatility'] = p.pct_change().std() * np.sqrt(self.trading_days) * 100
        metrics['Annualized Volatility Buy&Hold'] = p_bh.pct_change().std() * np.sqrt(self.trading_days) * 100

        # Calculate Sharpe Ratio (assuming a risk-free rate of 0)
        self.risk_free_rate = 0
        metrics['Sharpe Ratio'] = (metrics['Annualized Returns'] - self.risk_free_rate) / metrics['Annualized Volatility']
        metrics['Sharpe Ratio Buy&Hold'] = (metrics['Annualized Returns Buy&Hold'] - self.risk_free_rate) / metrics['Annualized Volatility Buy&Hold']

        # Store the portfolio series for later plotting
        self.portfolio = portfolio
        self.portfolio_bh = portfolio_bh

        metrics['Number of Trades'] = len(self.strategy.trades)

        # Calculate max drawdown
        metrics['Max Drawdown'] = get_max_drawdown(portfolio.total_aum)
        metrics['Max Drawdown Buy&Hold'] = get_max_drawdown(portfolio_bh)

        metrics['Number of Trades'] = len(self.strategy.trades)
        metrics['Number of Buy Trades'] = self.strategy.buy_trades  # Add number of buy trades
        metrics['Number of Sell Trades'] = self.strategy.sell_trades  # Add number of sell trades

        metrics['Number of Open Positions'] = self.strategy.position_size

        return metrics

def get_max_drawdown(close):
    roll_max = close.cummax()
    daily_drawdown = close / roll_max - 1.0
    max_daily_drawdown = daily_drawdown.cummin()
    return max_daily_drawdown.min() * 100