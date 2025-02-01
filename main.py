from fastapi import FastAPI, Query, HTTPException, Depends, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from contextlib import asynccontextmanager
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta
import sqlite3
import requests
import os
from dotenv import load_dotenv


load_dotenv()
secret_key = os.getenv('secret_key')
token_algorithm = "HS256"
access_token_expire_hours = 24
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Создаем таблицу при старте приложения
    """
    conn = sqlite3.connect("db.db")
    cursor = conn.cursor()
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS tg_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL UNIQUE
            )
        """)
    conn.commit()
    conn.close()
    yield

app = FastAPI(lifespan=lifespan)


class Token(BaseModel):
    access_token: str
    token_type: str


class Device(BaseModel):
    imei: str


class User(BaseModel):
    tg_id: str


def get_db():
    conn = sqlite3.connect("db.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=token_algorithm)


def verify_token(token: str):
    try:
        payload = jwt.decode(token, secret_key, algorithms=[token_algorithm])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Генерация JWT токена (имитация реальной аутентификации)
    """
    if form_data.username == "admin" and form_data.password == "adminpass":
        token_data = {"sub": form_data.username}
        access_token = create_access_token(token_data, expires_delta=timedelta(hours=access_token_expire_hours))
        return {"access_token": access_token, "token_type": "bearer"}

    raise HTTPException(status_code=401, detail="Invalid username or password")


async def check_imei(imei: str, token_imei: str = os.getenv('token_imei')):
    url = "https://api.imeicheck.net/v1/checks"
    payload = {
        "deviceId": imei,
        "serviceId": 12
    }
    headers = {
        'Authorization': f'Bearer {token_imei}',
        'Accept-Language': 'ru',
        'Content-Type': 'application/json'
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()


@app.post("/imei/", dependencies=[Depends(get_current_user)])
async def get_device_info(device: Device):
    """
    Проверка IMEI
    """
    device_info = await check_imei(device.imei)
    if device_info:
        return device_info

    raise HTTPException(status_code=404, detail="IMEI not found")


@app.post("/add_tg_user/", dependencies=[Depends(get_current_user)])
async def add_tg_user(user: User, db: sqlite3.Connection = Depends(get_db)):
    """
    Добавление пользователя телеграм в белый список
    """
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO tg_users (tg_id) VALUES (?)",
        (user.tg_id,),
    )
    db.commit()
    return {"id": cursor.lastrowid, "message": "User created successfully"}
