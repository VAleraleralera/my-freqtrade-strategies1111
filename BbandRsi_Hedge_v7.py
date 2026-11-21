# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class BbandRsi_Hedge_v7(IStrategy):
    """
    Финальная версия: Long & Short для фьючерсов.
    Учтены: риск с плечом, гэпы, симметрия.
    """
    INTERFACE_VERSION: int = 3
    can_short: bool = True

    # 1. ТЕХНИЧЕСКИЕ ПРАВИЛА
    startup_candle_count: int = 1000 
    process_only_new_candles = True
    ignore_buying_expired_candle_after = 60

    # 2. НАСТРОЙКИ РИСКА (С учетом плеча 3x)
    exit_profit_only = True
    exit_profit_offset = 0.01 

    minimal_roi = {
        "0": 0.025,   # 2.5%
        "30": 0.02,   # 2%
        "60": 0.015,  # 1.5%
        "120": 0.01   # 1%
    }

    # СТОП-ЛОСС: 3% от цены. При плече 3x это 9% от маржи (безопаснее, чем 4%).
    stoploss = -0.03
    
    # 3. ТРЕЙЛИНГ-СТОП (Работает в обе стороны)
    trailing_stop = True
    trailing_stop_positive = 0.01 
    trailing_stop_positive_offset = 0.02 
    trailing_only_offset_is_reached = True

    timeframe = '15m'

    # 4. ЗАЩИТА
    @property
    def protections(self):
        return [
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 288, 
                "trade_limit": 3,               
                "stop_duration_candles": 24,    
                "only_per_pair": False,
            },
            {
                "method": "MaxDrawdown",
                "calculation_mode": "equity",
                "lookback_period_candles": 500, 
                "trade_limit": 10,              
                "stop_duration_candles": 96,    
                "max_allowed_drawdown": 0.1,    
            }
        ]

    # 5. ФИЛЬТР 4H
    @informative('4h')
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    # 6. ИНДИКАТОРЫ
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']

        dataframe['volume_mean'] = dataframe['volume'].rolling(50).mean()
        return dataframe

    # 7. ЛОГИКА ВХОДА
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # ЛОНГ
        dataframe.loc[
            (
                (dataframe['rsi'] < 30) &
                (dataframe['close'] < dataframe['bb_lowerband']) &
                (dataframe['ema200_4h'].notna()) &
                (dataframe['close_4h'] > dataframe['ema200_4h']) &
                (dataframe['volume'] > dataframe['volume_mean'] * 1.1) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1

        # ШОРТ
        dataframe.loc[
            (
                (dataframe['rsi'] > 70) &
                (dataframe['close'] > dataframe['bb_upperband']) &
                (dataframe['ema200_4h'].notna()) &
                (dataframe['close_4h'] < dataframe['ema200_4h']) &
                (dataframe['volume'] > dataframe['volume_mean'] * 1.2) &
                (dataframe['volume'] > 0)
            ),
            'enter_short'] = 1

        return dataframe

    # 8. ЛОГИКА ВЫХОДА
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['rsi'] > 70), 'exit_long'] = 1
        dataframe.loc[(dataframe['rsi'] < 30), 'exit_short'] = 1
        return dataframe
