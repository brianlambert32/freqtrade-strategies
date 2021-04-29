
# --- Do not remove these libs ---
from freqtrade.strategy.interface import IStrategy
from typing import Dict, List
from functools import reduce
from pandas import DataFrame
from datetime import datetime 
# --------------------------------

import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class MACDStrategy_crossed(IStrategy):
    """
        buy:
            MACD crosses MACD signal above
            and CCI < -50
        sell:
            MACD crosses MACD signal below
            and CCI > 100
    """

    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi"
    minimal_roi = {
        "60":  0.035,
        "30":  0.05,
        "20":  0.06,
        "0":  0.07
    }

    # Optimal stoploss designed for the strategy
    # This attribute will be overridden if the config file contains "stoploss"
    stoploss = -0.3
    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        if pair in ('BTC/USD','ETH/USD'):
            return -0.18
        elif pair in ('ADA/USD', 'BCH/USD'):
            return -0.20
        elif pair in ('QTUM/USD','LINK/USD', 'BAT/USD'):
            return -0.25
        return -0.28
    # Optimal timeframe for the strategy
    timeframe = '5m'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        dataframe['cci'] = ta.CCI(dataframe)

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the buy signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with buy column
        """
        dataframe.loc[
            (
                qtpylib.crossed_above(dataframe['macd'], dataframe['macdsignal']) &
                (dataframe['cci'] <= -45.0) |
                (dataframe['rsi'] < 22)
            ),
            'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the sell signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with buy column
        """
        dataframe.loc[
            (
                qtpylib.crossed_below(dataframe['macd'], dataframe['macdsignal']) &
                (dataframe['cci'] >= 80.0) &
                (dataframe['rsi'] > 65)
            ),
            'sell'] = 1

        return dataframe
