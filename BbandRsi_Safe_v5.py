# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class BbandRsi_Safe_v5(IStrategy):
    """
    Финальная версия BbandRsi.
    Исправлено: конфликт трейлинга и ROI, trade_limit для MaxDrawdown, 
    защита от NaN, process_only_new_candles.
    """
    INTERFACE_VERSION: int = 3

    # 1. ТЕХНИЧЕСКИЕ ПРАВИЛА
    startup_candle_count: int = 1000 
    process_only_new_candles = True
    ignore_buying_expired_candle_after = 60

    # 2. НАСТРОЙКИ РИСКА
    exit_profit_only = True
    exit_profit_offset = 0.01 

    # ROI: Первый уровень 2.5%, чтобы трейлинг успел активироваться раньше
    minimal_roi = {
        "0": 0.025,   # 2.5%
        "30": 0.02,   # 2%
        "60": 0.015,  # 1.5%
        "120": 0.01   # 1%
    }

    stoploss = -0.04
    
    # 3. ТРЕЙЛИНГ-СТОП (Активируется на 2%, закрывает при откате на 1%)
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
                "lookback_period_candles": 288, # 72 часа
                "trade_limit": 3,               # 3 стопа за 72 часа
                "stop_duration_candles": 24,    # Пауза 6 часов
                "only_per_pair": False,
            },
            {
                "method": "MaxDrawdown",
                "calculation_mode": "equity",
                "lookback_period_candles": 500, # Увеличили окно до 125 часов
                "trade_limit": 10,              # Снизили порог до 10 сделок (чтобы срабатывало)
                "stop_duration_candles": 96,    # Пауза 24 часа
                "max_allowed_drawdown": 0.1,    # Просадка 10%
            }
        ]

    # 5. ФИЛЬТР СТАРШЕГО ТАЙМФРЕЙМА
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
        dataframe.loc[
            (
                (dataframe['rsi'] < 30) &
                (dataframe['close'] < dataframe['bb_lowerband']) &
                
                # Защита от NaN
                (dataframe['ema200_4h'].notna()) &
                (dataframe['close_4h'] > dataframe['ema200_4h']) &
                
                # Фильтр объема
                (dataframe['volume'] > dataframe['volume_mean'] * 1.2) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1
        return dataframe

    # 8. ЛОГИКА ВЫХОДА
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] > 70)
            ),
            'exit_long'] = 1
        return dataframe