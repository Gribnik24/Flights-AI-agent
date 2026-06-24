import os
from dotenv import load_dotenv

import json
from typing import Optional
import logging

from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pandas as pd
import sqlite3

import asyncio
from langchain_core.tools import tool

logging.basicConfig(level=logging.INFO, filename="../logs/chat_logs.log", filemode="a", encoding='utf-8')
load_dotenv()

@tool
async def get_current_time(timezone: str = 'UTC') -> str:
    """
    Возвращает текущие дату и время для указанного часового пояса в формате IANA.
    Args:
        timezone: Имя часового пояса в формате IANA (например 'Europe/Moscow', 'Asia/Novosibirsk', 'UTC'). По умолчанию 'UTC'.
    Returns:
        Строка в формате JSON с полями `date` (YYYY-MM-DD) и `time` (HH:MM:SS) в указанном часовом поясе.
    """
    logging.info(f'Запуск инструмента tools.get_current_time для получения текущего времени')
    try:
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        result = {'date': now.strftime('%Y-%m-%d'), 'time': now.strftime('%H:%M:%S')}
        logging.info('Успешное завершение инструмента tools.get_current_time')
        return json.dumps(result, ensure_ascii=False)
    except Exception:
        logging.error('Ошибка Получения текущего времени', exc_info=True)
        return json.dumps({'error': 'Ошибка Получения текущего времени'}, ensure_ascii=False)

@tool
async def get_airport_data(mode: str,
                           ru_name: Optional[str] = None,
                           en_name: Optional[str] = None) -> str:
    """
    Позволяет получить информацию по аэропортам.
    Если параметр `mode` равен `city`, то выполняется поиск всех имеющихся аэропортов в указанном городе.
    Если параметр `mode` равен `iata`, то выполняется поиск кода iata по указанному полному названию аэропорта.
    Принимает два аргумента (`ru_name` и `en_name`, по умолчанию оба равны None). В случае заполнения обоих, использоваться будет только `ru_name` - название на русском.
    
    Args:
        ru_name: Полное название аэропорта на русском (например 'Аэропорт Шереметьево' для аэропорта Шереметьево в Москве)
        en_name: Полное название аэропорта на английском (например 'Los Angeles International Airport' для аэропорта в Лос-Анджелесе)
        
    Returns:
        Строка в формате JSON с полем `airports`. В нем содержится список аэропортов со следующей информацией:
        airport_name_ru: Название аэропорта на русском.
        airport_name_en: Название аэропорта на английском.
        iata_code: Код IATA.
        city_ru: Город нахождения аэропорта.
        country_ru: Страна нахождения аэропорта.
        timezone: часовой пояс аэропорта в формате IANA.
    """
    # Нормализация строки (убираем дефисы и лишние пробелы)
    def normalize(s: str) -> str:
        if not s:
            return ""
        return s.replace('-', ' ').replace('  ', ' ').strip()
    
    logging.info(f'Запуск инструмента tools.get_airport_data с параметрами: mode={mode}, ru_name={ru_name}, en_name={en_name}')
    
    # Очистка параметров от строки "None"
    if ru_name == "None" or ru_name == "null":
        ru_name = None
    if en_name == "None" or en_name == "null":
        en_name = None
    
    # Проверка параметра `mode`
    if mode.lower() not in ('city', 'iata'):
        logging.error('Ошибка вызова инструмента. Параметр mode не принимает значения `city` или `iata`', exc_info=True)
        return json.dumps({'error': 'Ошибка вызова инструмента. Параметр mode должен принимать `city` или `iata`'}, ensure_ascii=False)
    if en_name is None and ru_name is None:
        logging.error('Ошибка вызова инструмента. Не указаны значения `ru_name` и `en_name`', exc_info=True)
        return json.dumps({'error': 'Укажите `ru_name` или `en_name`'}, ensure_ascii=False)
    
    # Подключение к БД
    try:
        conn = sqlite3.connect('../data/flights_info.db', check_same_thread=False)
        logging.info('Подключение к БД выполнено успешно')
    except Exception:
        logging.error('Ошибка подключения к базе данных.', exc_info=True)
        return json.dumps({'error': 'Ошибка подключения к базе данных.'}, ensure_ascii=False)
    
    try:
        # Определение колонок для SQL запроса
        if mode == 'iata':
            if ru_name is not None:
                lw_name = normalize(ru_name)
                df_column = 'name_ru'
            else: 
                lw_name = normalize(en_name)
                df_column = 'name_en'
        else:
            if ru_name is not None:
                lw_name = normalize(ru_name)
                df_column = 'city_ru'
            else:
                lw_name = normalize(en_name)
                df_column = 'city_en'
    
        # SQL запрос к таблице airports_info
        query = f'SELECT * FROM airports_info WHERE {df_column} = ?;'
        
        # Запуск синхронного запроса в потоке, чтобы не блокировать цикл
        loop = asyncio.get_running_loop()
        df = await loop.run_in_executor(
            None, 
            lambda: pd.read_sql(sql=query, con=conn, params=(lw_name,))
        )
        
    except Exception as e:
        logging.error(f'Ошибка выполнения SQL запроса к БД: {e}', exc_info=True)
        return json.dumps({'error': 'Ошибка выполнения SQL запроса к БД'}, ensure_ascii=False)
    
    # Обработка результата
    df_len = len(df)
    if df_len == 0 and mode == 'iata':
        return json.dumps({'error': 'Для данного названия кодов IATA не найдено'}, ensure_ascii=False)
    
    elif df_len == 0 and mode == 'city':
        return json.dumps({'error': 'Для данного города аэропортов не найдено'}, ensure_ascii=False)
    
    else:
        airports = []
        for _, row in df.iterrows():
            airports.append({
                'airport_name_ru': None if pd.isna(row['name_ru']) else row['name_ru'],
                'airport_name_en': None if pd.isna(row['name_en']) else row['name_en'],
                'iata_code': None if pd.isna(row['IATA']) else row['IATA'],
                'city_ru': None if pd.isna(row['city_ru']) else row['city_ru'],
                'country_ru': None if pd.isna(row['country_ru']) else row['country_ru'],
                'timezone': None if pd.isna(row['timezone']) else row['timezone']
            })
    
    logging.info('Успешное завершение инструмента tools.get_airport_data')
    return json.dumps({'airports': airports}, indent=2, ensure_ascii=False)        
          
@tool
async def get_station_timetable(station_code: str,
                                event_date: str,
                                event: str,
                                departure_city: Optional[str] = None,
                                arrival_city: Optional[str] = None,
                                time_lower_bound: Optional[str] = None,
                                time_upper_bound: Optional[str] = None,
                                exact_time: Optional[str] = None,
                                company_name: Optional[str] = None) -> str:
    """
    Позволяет получить список рейсов, отправляющихся от указанного аэропорта и информацию по каждому рейсу
    Позволяет выполнить фильтрацию результата функции по названию компании, которая организовывает перелет, времени событий или городу вылета или отлета.
    
    Args:
        station_code: код аэропорта,
        event_date: Дата, на которую необходимо получить список рейсов. Должна быть указана в формате, соответствующем стандарту ISO 8601. Например, YYYY-MM-DD.
        event: Событие, для которого нужно отфильтровать нитки в расписании.
                 Возможные значения: departure — включить в ответ только отправляющиеся со станции нитки; arrival — включить в ответ только прибывающие на станцию нитки.
        departure_city: Город отправления, по которому необходимо отфильтровать результаты. Опциональный параметр.
        arrival_city: Город прилета, по которому необходимо отфильтровать результаты. Опциональный параметр.
        time_lower_bound: Начальная включительная граница времени в формате hh:mm. Опциональный параметр.
        time_upper_bound: Конечная включительная граница времени в формате hh:mm. Опциональный параметр.
        exact_time: Точное время события в формате hh:mm. Опциональный параметр. В случае заполнения параметры time_lower_bound и time_upper_bound игнорируются.
        company_name: Название компании, которая организовывает полет. Опциональный параметр.
    
    Returns:
        Строка в формате JSON со следующими полями:
        date: Запрашиваемая дата событий.
        total_values: Количество событий на запрашиваемую дату.
        station_type_eng: Тип станции на английском.
        station_type_ru: Тип станции на русском.
        schedule: Массив с информацией по конкретным вылетам или прилетам (в зависимости от аргумента event). Содержит поля:
                    trip_number: Номер рейса.
                    transport_name: Название транспорта (например 'Boeing 737-800')
                    company_name: Название компании, которая организовывает полет.
                    event_time: Время вылета или прилета в формате hh:mm (в зависимости от аргумента event)
                    trip_title: Название нитки. Составляется из полных названий первой и последней станций следования.
                    departure_point: Начальная точка следования.
                    arrival_point: Конечная точка следования.
    """
    def get_hh_mm(dt_string):
        """
        Преобразование времени в формат %H:%M
        """
        try:
            dt = datetime.fromisoformat(dt_string)
            return dt.strftime('%H:%M')
        except Exception as e:
            raise e
    
    logging.info(f'Запуск инструмента tools.get_station_timetable с параметрами: station_code={station_code}, event_date={event_date}, event={event}')
    
    # Получение данных через API
    url = "https://api.rasp.yandex-net.ru/v3.0/schedule/"
    params = {
        'apikey': os.getenv('YANDEX_API_KEY'),
        'station': station_code,
        'date': event_date,
        'transport_types': 'plane',
        'event': event,
        'system': 'iata',
    }
    logging.info('Старт получения данных рейсов через API')
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status() # Проверяем статус ответа (4xx, 5xx)
            data = response.json()
    except httpx.HTTPError as e:
        logging.error(f'Ошибка сети или сервера: {e}', exc_info=True)
        return json.dumps({'error': f'Ошибка сети или сервера: {e}'})
    except json.JSONDecodeError:
        logging.error('Ошибка: ответ от сервера не является валидным JSON', exc_info=True)
        return json.dumps({'error': 'Ошибка: ответ от сервера не является валидным JSON'})
    except:
        logging.error('Ошибка получения информации по API', exc_info=True)
        return json.dumps({'error': 'Ошибка получения информации по API'})
    logging.info('Успешное завершение получения данных рейсов через API')
    
    # Обработка json-результата
    logging.info('Старт обработки данных рейсов, полученных через API')
    station_timetable = {}
    station_timetable['date'] = data.get('date', event_date)
    station_timetable['total_values'] = data.get('pagination', {}).get('total', None)
    station_timetable['station_type_eng'] = data.get('station', {}).get('station_type', None)
    station_timetable['station_type_ru'] = data.get('station', {}).get('station_type_name', None)
    
    trips = data.get('schedule', [])
    trips_info = []
    for trip in trips:
        cur_trip_info = {}
        cur_trip_info['trip_number'] = trip.get('thread', {}).get('number', None)
        cur_trip_info['transport_name'] = trip.get('thread', {}).get('vehicle', None)
        cur_trip_info['company_name'] = trip.get('thread', {}).get('carrier', {}).get('title', None)
        
        cur_trip_info['event_time'] = trip.get(event, None)
        try:
            cur_trip_info['event_time'] = get_hh_mm(cur_trip_info['event_time'])
        except Exception as e:
            logging.warning(f'Ошибка преобразования поля event_time с временем события в формат %H:%M: {e}')
            pass
        
        cur_trip_info['trip_title'] = trip.get('thread', {}).get('title', None)
        try:
            cur_trip_info['departure_point'], cur_trip_info['arrival_point'] = cur_trip_info['trip_title'].split(' — ')
        except Exception as e:
            logging.warning(f'Ошибка получения точки отправления и точки прибытия из поля названия нитки: {e}')
            pass
        
        trips_info.append(cur_trip_info)
    
    station_timetable['schedule'] = trips_info
    logging.info('Успешное завершение обработки данных рейсов, полученных через API')
    
    
    logging.info(f'Старт фильтрация с параметрами: departure_city={departure_city}, arrival_city={arrival_city},'
                f' time_lower_bound={time_lower_bound}, time_upper_bound={time_upper_bound}, exact_time={exact_time}, company_name={company_name}')
    
    # Фильтрация по параметрам
    trips = station_timetable.get('schedule', [])
    if departure_city is not None:
        lw_city = departure_city.lower()
        trips = [trip for trip in trips if trip['departure_point'] is not None and trip['departure_point'].lower() == lw_city]
        
    if arrival_city is not None:
        lw_city = arrival_city.lower()
        trips = [trip for trip in trips if trip['arrival_point'] is not None and trip['arrival_point'].lower() == lw_city]
        
    if time_lower_bound is not None:
        trips = [trip for trip in trips if trip['event_time'] is not None and datetime.strptime(time_lower_bound, "%H:%M") <= datetime.strptime(trip['event_time'], "%H:%M")]
        
    if time_upper_bound is not None:
        trips = [trip for trip in trips if trip['event_time'] is not None and datetime.strptime(time_upper_bound, "%H:%M") >= datetime.strptime(trip['event_time'], "%H:%M")]
        
    if exact_time is not None:
        trips = [trip for trip in trips if trip['event_time'] is not None and datetime.strptime(exact_time, "%H:%M") == datetime.strptime(trip['event_time'], "%H:%M")]
        
    if company_name is not None:
        lw_company = company_name.lower()
        trips = [trip for trip in trips if trip['departure_point'] is not None and trip['company_name'].lower() == lw_company]
        
    station_timetable['schedule'] = trips
    
    logging.info('Успешное завершение инструмента tools.get_station_timetable')
    
    return json.dumps(station_timetable, ensure_ascii=False)

tools_list = [get_current_time, get_airport_data, get_station_timetable]