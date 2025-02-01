import asyncio
import json
import logging
import sqlite3
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
import os
from dotenv import load_dotenv


load_dotenv()
tg_token = os.getenv('tg_token')
api_url = os.getenv('api_url')
api_username = os.getenv('api_username')
api_password = os.getenv('api_password')


token_lock = asyncio.Lock()
access_token = None

bot = Bot(token=tg_token)
dp = Dispatcher()


async def get_token():
    global access_token
    async with token_lock:
        response = requests.post(f"{api_url}/token", data={"username": api_username, "password": api_password})
        if response.status_code == 200:
            access_token = response.json().get("access_token")
            logging.info(f"Token has been updated: {access_token[:10]}...")
        else:
            logging.error(f"Error while tried get token: {response.text}")
            access_token = None


def is_user_in_db(tg_id: int) -> bool:
    conn = sqlite3.connect("db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM tg_users WHERE tg_id = ?", (tg_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


async def get_device_info(imei: str) -> dict:
    global access_token
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {"imei": imei}

    response = requests.post(f"{api_url}/imei/", json=payload, headers=headers)

    if response.status_code == 401:  # Если токен истёк или недействителен
        await get_token()
        headers["Authorization"] = f"Bearer {access_token}"
        response = requests.post(f"{api_url}/imei/", json=payload, headers=headers)

    return response.json()


def format_properties(data: dict) -> str:
    properties = data.get("properties", {})
    if not properties:
        return "Ошибка: В ответе API нет информации о `properties`."
    formatted_text = "\n".join([f"{key}: {value}" for key, value in properties.items()])
    return formatted_text


@dp.message(lambda message: message.text.isdigit() and 8 <= len(message.text) <= 15)
async def process_imei(message: Message):
    tg_id = message.from_user.id
    imei = message.text

    if not is_user_in_db(tg_id):
        await message.reply("❌ У вас нет доступа к этой функции.")
        return

    await message.reply("🔍 Проверяю IMEI, пожалуйста, подождите...")

    device_info = await get_device_info(imei)

    if "errors" in device_info:
        logging.error(f"Error while tried get device_info:\n{tg_id}\n{device_info}")
        await message.reply(f"❌ Ошибка: {device_info}")
    else:
        formatted_info = format_properties(device_info)
        await message.reply(f"📱 Информация об устройстве:\n```{formatted_info}```", parse_mode="MarkdownV2")


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(filename='log.log', format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s', datefmt='%H:%M:%S', level=logging.INFO, encoding='UTF-8')
    asyncio.run(main())
