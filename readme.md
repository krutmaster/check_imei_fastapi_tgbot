# Описание
Back для получения информации об аппарате по IMEI (через сервис https://imeicheck.net) на fastapi. Также телеграм бот, использующий поднятый backend.
# Подготовка
1. Внести нужные значения в `temp.env`;
2. Переименовать в `.env`.
# Запуск
1. Установка зависимостей: `pip install -r requirements.txt`;
2. Запуск fastapi, пример: `uvicorn main:app --reload`;
3. Запуск бота: `python tg_bot.py`.