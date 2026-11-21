FROM freqtradeorg/freqtrade:stable

# Копируем стратегию v7
COPY BbandRsi_Hedge_v7.py /freqtrade/user_data/strategies/BbandRsi_Hedge_v7.py
# Копируем конфиг
COPY config.json /freqtrade/user_data/config.json

# Запускаем бота
CMD ["trade"]
