# --- Do not remove these libs ---
import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
# --------------------------------
import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
from datetime import datetime, timedelta
from freqtrade.persistence import Trade

def bollinger_bands(stock_price, window_size, num_of_std):
    rolling_mean = stock_price.rolling(window=window_size).mean()
    rolling_std = stock_price.rolling(window=window_size).std()
    lower_band = rolling_mean - (rolling_std * num_of_std)
    return np.nan_to_num(rolling_mean), np.nan_to_num(lower_band)


class CombinedBinHAndCluc(IStrategy):
    # Based on a backtesting:
    # - the best perfomance is reached with "max_open_trades" = 2 (in average for any market),
    #   so it is better to increase "stake_amount" value rather then "max_open_trades" to get more profit
    # - if the market is constantly green(like in JAN 2018) the best performance is reached with
    #   "max_open_trades" = 2 and minimal_roi = 0.01
    minimal_roi = {
        "0": 0.105,
        "60": 0.08,
        "120": 0.06,
        "240": 0.03,
        "300": 0.02,
        "400": 0.012,
    }
    stoploss = -0.20
    timeframe = '5m'
    
    protections = [
        {
          "method": "MaxDrawdown",
            "lookback_period": 300,
            "trade_limit": 4,
            "stop_duration": 180,
            "max_allowed_drawdown": 0.15  
        },
        {
            "method": "StoplossGuard",
            "lookback_period": 240,
            "trade_limit": 3,
            "stop_duration": 200,
            "onlt_per_pair": False
      }
    ]

    use_sell_signal = True
    sell_profit_only = True
    ignore_roi_if_buy_signal = True

    trailing_stop = True
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.04

    use_custom_stoploss = True

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:

        # Make sure you have the longest interval first - these conditions are evaluated from top to bottom.
        if current_time - timedelta(minutes=1200) > trade.open_date:
            return -0.05
        elif current_time - timedelta(minutes=720) > trade.open_date:
            return -0.08
        elif current_time - timedelta(minutes=360) > trade.open_date:
            return -0.12
        return 1

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # strategy BinHV45
        mid, lower = bollinger_bands(dataframe['close'], window_size=20, num_of_std=1)
        dataframe['lower'] = lower
        dataframe['bbdelta'] = (mid - dataframe['lower']).abs()
        dataframe['closedelta'] = (dataframe['close'] - dataframe['close'].shift()).abs()
        dataframe['tail'] = (dataframe['close'] - dataframe['low']).abs()
        # strategy ClucMay72018
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=10, stds=1)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['volume_mean_slow'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        dataframe['max'] = dataframe['high'].rolling(20).max()

        dataframe['min'] = dataframe['low'].rolling(20).min()

        dataframe['upper'] = np.where(dataframe['max'] > dataframe['max'].shift(),1,0)

        dataframe['lower'] = np.where(dataframe['min'] < dataframe['min'].shift(),1,0)

        dataframe['up_trend'] = np.where(dataframe['upper'].rolling(10, min_periods=1).sum() != 0,1,0)
                                  
        dataframe['dn_trend'] = np.where(dataframe['lower'].rolling(10, min_periods=1).sum() != 0,1,0)

        stoch = ta.STOCH(dataframe)
        dataframe['slowd'] = stoch['slowd']
        dataframe['slowk'] = stoch['slowk']

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (  # strategy BinHV45
                    dataframe['lower'].shift().gt(0) &
                    dataframe['bbdelta'].gt(dataframe['close'] * 0.015) &
                    dataframe['closedelta'].gt(dataframe['close'] * 0.0175) &
                    dataframe['tail'].lt(dataframe['bbdelta'] * 1.5) &
                    dataframe['close'].lt(dataframe['lower'].shift()) &
                    dataframe['close'].le(dataframe['close'].shift()) &
                    (dataframe['bb_middleband'] > (dataframe['bb_upperband'].shift(3)))
            ) |
            (  # strategy BinHV452
                    dataframe['lower'].shift().gt(0) &
                    dataframe['bbdelta'].gt(dataframe['close'] * 0.025) &
                    dataframe['closedelta'].gt(dataframe['close'] * 0.005) |
                    dataframe['tail'].lt(dataframe['bbdelta'] * 1.5) & 
                    dataframe['close'].lt(dataframe['lower'].shift()) &
                    dataframe['close'].le(dataframe['close'].shift()) &
                    (dataframe['bb_middleband'] > (dataframe['bb_upperband'].shift(3)))
            ) |
            (
                    (dataframe['close'] < (dataframe['bb_lowerband'] *0.98)) &
                    (dataframe['bb_upperband'] > (dataframe['bb_upperband'].shift(3))) &
                    (dataframe['bb_lowerband'] > (dataframe['bb_lowerband'].shift(2))) 
                    
                    
            ) |
            (
                    (dataframe['rsi'] < 30) &
                    (dataframe['close'] < 0.986 * dataframe['bb_lowerband']) 
                    #(dataframe['bb_lowerband'] > dataframe['bb_lowerband'].shift(1))
            ) |
            (  # strategy ClucMay72018
                    (dataframe['close'] < dataframe['ema_slow']*0.9) &
                    (dataframe['close'] < 0.985 * dataframe['bb_lowerband']) &
                    (dataframe['volume'] < (dataframe['volume_mean_slow'].shift(1) * 20))
            ),
            'buy'
        ] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        """
        dataframe.loc[
            (
                (dataframe['close'] > (dataframe['bb_upperband'] * 1.01)) 
                
            ),
            'sell'
        ] = 1
        return dataframe
