import  asyncio

from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

# ----

import aiohttp


async def get_city(city: str):
    url = f'https://geocoding-api.open-meteo.com/v1/search?name={city.lower()}&count=1&language=ru&format=json'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if 'results' not in data:
                return None

            return [data["results"][0]["latitude"], data["results"][0]["longitude"], data["results"][0]["id"]]


async def get_weather(lat: float, lon: float):
    url = f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,precipitation,wind_speed_10m,wind_direction_10m&wind_speed_unit=ms'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 404:
                return None

            data = await resp.json()
            return data

# ----

import aiosqlite

DB_NAME = 'cities.sql'

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS cities (id INTEGER,full_name TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS weather (id INTEGER,temp FLOAT,wind_speed FLOAT,wind_direction TEXT)")
        await db.commit()

async def add_city(id, full_name):
    name = full_name.strip().lower()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO cities (id, full_name) VALUES (?, ?)", (id, name))
        await db.commit()

async def add_weather(id, temp, wind_speed, wind_direction):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO weather (id, temp, wind_speed, wind_direction) VALUES (?, ?, ?, ?)", (id, temp, wind_speed, wind_direction))
        await db.commit()

async def get_city_db(name):
    name = name.strip().lower()
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id FROM cities WHERE full_name = ?", (name, ))
        row = await cursor.fetchone()

        if row is None:
            return None
        return row[0]

async def get_weather_db(id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT temp, wind_speed, wind_direction FROM weather WHERE id = ?", (id, ))
        result = await cursor.fetchall()
        return result

# ---

async def direction(degrees: int):
    degrees = (degrees+22.5) % 360
    directions = ['С','СВ','В','ЮВ','Ю','ЮЗ','З','СЗ']
    return directions[int(degrees//45)]

# ----


@router.message(Command('start'))
async def start(message: Message):
    await init_db()
    await message.answer('Привет! Я показываю текущую погоду в любом городе. Для этого напиши команду: /w ГОРОД\nНапример: /w Москва')


@router.message(Command('w'))
async def weather_cmd(message: Message):
    parts = message.text.strip().split()

    if len(parts) != 2:
        await message.answer('Напишите команду корректно')
        return

    city_id = await get_city_db(parts[1])

    if city_id is None:

        try:
            coord = await get_city(parts[1])
        except Exception:
            await message.answer('Сервер не отвечает')
            return

        if coord is None:
            await message.answer('Город не найден')
            return

        weather = await get_weather(coord[0], coord[1])

        await add_city(coord[2], parts[1])

        temp = weather["current"]["temperature_2m"]
        wind_speed = weather["current"]["wind_speed_10m"]
        wind_direction = await direction(weather["current"]["wind_direction_10m"])

        await add_weather(coord[2], temp, wind_speed, wind_direction)

        await message.answer(f'Город: <b>{parts[1]}</b>\n\n'
                             f'Температура: <b>{temp}°C</b>\n'
                             f'Скорость ветра: <b>{wind_speed} м/с</b>\n'
                             f'Направление ветра: <b>{wind_direction}</b>', parse_mode='HTML'
                             )
    else:
        weather = await get_weather_db(city_id)

        await message.answer(f'Город: <b>{parts[1].upper()}</b>\n\n'
                             f'Температура: <b>{weather[0][0]}°C</b>\n'
                             f'Скорость ветра: <b>{weather[0][1]} м/с</b>\n'
                             f'Направление ветра: <b>{weather[0][2]}</b>', parse_mode='HTML')
