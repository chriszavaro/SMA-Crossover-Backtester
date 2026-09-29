import pandas as pd
import yfinance as yf

class MarketDataHandler:
    """Handles data ingestion and ensures temporal consistency"""
    def __init__(self, ticker: str, start_date: str, end_date: str):
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
        self.data = None

    def fetch_data(self):
        """Downloads historical market data for the specified ticker and date range"""
        print(f"Fetching data for {self.ticker} from {self.start_date} to {self.end_date}")
        self.data = yf.download(self.ticker, start=self.start_date, end=self.end_date)

        #Clean columns ensure uniform formatting
        if isinstance(self.data.columns, pd.MultiIndex):
            self.data.columns = self.data.columns.get_level_values(0)

        return self.data

class SimpleMovingAverageStrategy:
    """Calculates strategy indicators and generates point-in-time trading signals"""
    def __init__(self, short_window: int = 10, long_window: int = 200):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Computes indicators and evaluates conditional buy/sell conditions."""
        # Create a clean working copy to avoid mutating raw market cache data
        df = data.copy()

        # Step 1: Calculate moving averages using pandas rolling windows
        df['short_ma'] = df['Close'].rolling(window=self.short_window).mean()
        df['long_ma'] = df['Close'].rolling(window=self.long_window).mean()

        # Step 2: Initialize signal column to 0 (Cash/Out of market)
        df['signal'] = 0.0

        # Step 3: Set Signal to 1 (Long) when Short SMA is strictly above Long SMA
        # Vectorized assignments prevent look-ahead bias by acting on current-day data
        df.loc[df['short_ma'] > df['long_ma'], 'signal'] = 1.0

        # Step 4: Shift signals by 1 day because you can only execute trades 
        # on the NEXT market open after a signal closes
        df['Position'] = df['signal'].shift(1)

        return df

class BacktestEngine:
    """Simulates trading execution and measures portfolio performance metrics."""
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital

    def run_backtest(self, processed_data: pd.Dateframe):
        """Calculates returns based on strategy positions."""
        df = processed_data.copy()

        #Calculate daily percentage returns of the underlying asset
        df["Market_Returns"] = df["Close"].pct_change()

        #Calculate strategy returns based on positions
        df["Strategy_Returns"] = df["Position"] * df["Market_Returns"]

        # Compute cumulative growth using standard compounding math
        df['Cumulative_Market'] = (1.0 + df['Market_Returns'].fillna(0)).cumprod()
        df['Cumulative_Strategy'] = (1.0 + df['Strategy_Returns'].fillna(0)).cumprod()

        # Calculate final cash values
        final_market_value = self.initial_capital * df['Cumulative_Market'].iloc[-1]
        final_strategy_value = self.initial_capital * df['Cumulative_Strategy'].iloc[-1]

        return {
            "Initial Capital": self.initial_capital,
            "Final Market Value": round(final_market_value, 2),
            "Final Strategy Value": round(final_strategy_value, 2),
            "Strategy Outperformance (%)": round(((final_strategy_value - final_market_value) / final_market_value) * 100, 2)
        }



if __name__ == "__main__":
    TICKER = "AAPL"
    START = "2020-01-01"
    END = "2024-01-01"

    #1. Pipeline Ingestion Engine
    data_handler = MarketDataHandler(ticker=TICKER, start_date=START, end_date=END)
    raw_data = data_handler.fetch_data()

    #2. Strategy Signal Generation
    strategy = SimpleMovingAverageStrategy(short_window=10, long_window=200)
    signals_df = strategy.generate_signals(raw_data)

    #3. Backtest Execution
    backtest_engine = BacktestEngine(initial_capital=10000.0)
    backtest_results = backtest_engine.run_backtest(signals_df)

    print("\n" + "="*30 + " BACKTEST RESULTS " + "="*30)
    for metric, value in backtest_results.items():
        print(f"{metric:<30}: {value}")
    print("="*78)