FROM freqtradeorg/freqtrade:stable

# Копируем твою стратегию из репозитория в папку стратегий бота
COPY BbandRsi_Safe_v5.py /freqtrade/user_data/strategies/BbandRsi_Safe_v5.py

# Запускаем бота (он возьмет стратегию из переменных Railway)
CMD ["trade"]
