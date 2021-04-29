# --- Do not remove these libs ---
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from datetime import datetime
from freqtrade.persistence import Trade


# --------------------------------


class BbandRsi(IStrategy):
    """

    author@: Gert Wohlgemuth

    converted from:

    https://github.com/sthewissen/Mynt/blob/master/src/Mynt.Core/Strategies/BbandRsi.cs

    """

    # Minimal ROI designed for the strategy.
    # adjust based on market conditions. We would recommend to keep it low for quick turn arounds
    # This attribute will be overridden if the config file contains "minimal_roi"
    minimal_roi = {
        "0": 0.08
    }

    # Optimal stoploss designed for the strategy
    stoploss = -0.06
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True

    #use_custom_stoploss = True
    #def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float, current_profit: float, **kwargs) -> float:
    #    if current_profit >= 0.05:
    #        return (-0.03 + current_profit)
    #    if current_profit >= 0.025:
    #        return (-0.01 + current_profit)
    #    if current_profit > 0.06:
    #        return (-0.04 + current_profit)
    #    if current_profit > 0.04:
    #        return (-0.01 + current_profit)
    #    return 1 



    # Optimal timeframe for the strategy
    timeframe = '1h'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['cci'] = ta.CCI(dataframe)
        dataframe['ema_high'] = ta.EMA(dataframe, timeperiod=5, price='high')
        dataframe['ema_close'] = ta.EMA(dataframe, timeperiod=5, price='close')
        dataframe['ema_low'] = ta.EMA(dataframe, timeperiod=5, price='low')

        stoch_rsi = ta.STOCHRSI(dataframe)
        dataframe['fastd_rsi'] = stoch_rsi['fastd']
        dataframe['fastk_rsi'] = stoch_rsi['fastk']

        macd = ta.MACD(dataframe,12,26,1)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']

        # Bollinger bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                    (dataframe['macd'] > dataframe['macd'].shift(1)) &
                    (dataframe['macdsignal'] > dataframe['macdsignal'].shift(1)) &
                    #(dataframe['macd'] > dataframe['macdsignal']) &
                    (dataframe['fastk_rsi'] >= 10) & (dataframe['fastk_rsi'] <= 80) &
                    (dataframe['fastd_rsi'] >= 10) & (dataframe['fastd_rsi'] <= 80) &
                    (dataframe['rsi'] < 20) |
                    (dataframe['close'] < dataframe['bb_lowerband']) |
                    (dataframe['cci'] < -175)
            ),
            'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                    (dataframe['rsi'] > 70) &
                    (dataframe['close'] >= dataframe['bb_upperband']) &
                    (dataframe['macd'] < dataframe['macd'].shift(2)) &
                    (dataframe['macdsignal'] < dataframe['macdsignal'].shift(2))
                    #(dataframe['macd'] < dataframe['macdsignal'])
                    #(dataframe['rsi'] > 90)
                    #(dataframe['cci'] > 100)
                    
                    #(dataframe['rsi'] < 20 ) &
                    #(dataframe['cci'] < -10) |
                    #(dataframe['ema10'] > dataframe['bb_upperband']) 
                    

            ),
            'sell'] = 1
        return dataframe
