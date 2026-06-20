from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram import Bot
import asyncio
import httpx

import json
import sys
import os
from dotenv import load_dotenv
from pathlib import Path
import logging

load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
_PROMPTS_DIR = Path(__file__).parent.parent.parent / os.getenv("PROMPTS_DIR", "prompts")

from agent.agent_wrapper import process_message
from agent.flights_agent import agent, memory

router = Router()

def setup_command_logger():
    chat_logger = logging.getLogger('chat_logs')
    chat_logger.setLevel(logging.INFO)
    chat_logger.propagate = False
    chat_logger.handlers.clear()
    chat_handler = logging.FileHandler(
        filename="../logs/chat_logs.log",
        mode="a",
        encoding='utf-8'
    )
    chat_formatter = logging.Formatter('[CHAT LOGS]: %(levelname)s | %(message)s')
    chat_handler.setFormatter(chat_formatter)
    chat_logger.addHandler(chat_handler)
    return chat_logger

chat_logger = setup_command_logger()

def get_main_button_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text='Репозиторий GitHub со мной',
                                               url='https://github.com/Gribnik24/Flights-AI-agent')]],
        resize_keyboard=True
    )
    
    return keyboard

@router.message(Command("start"))
async def start(message: Message):
    chat_logger.info('Передача команды `/start` в бота')
    start_message = f"""
    Привет, {message.from_user.first_name}! Я бот, который умеет искать *информацию о полетах* ✈️.
Ты можешь прописать следующие команды:
• */about* - чтобы узнать подробнее, что я умею и в чем мой смысл
• */CreatePresentation [количество слайдов]* - чтобы создать презентацию по истории нашей переписки и рассуждениями агента с указанным количеством слайдов
• */restart* - чтобы очистить историю нашей переписки
    """
    await message.answer(start_message, parse_mode='Markdown', reply_markup=get_main_button_keyboard())
    chat_logger.info('Успешное завершение команды `/start`')
    
    
@router.message(Command('about'))
async def about(message: Message):
    chat_logger.info('Передача команды `/about` в бота')
    about_message = """
Я — AI-бот для поиска информации о рейсах ✈️

*Что я умею:*

🔍 *Поиск аэропортов* — по названию города или полному названию аэропорта (на русском или английском)
🛫 *Расписание рейсов* — по аэропорту, дате и типу события (вылет/прилёт)
🕒 *Фильтрация рейсов* — по городу отправления/прилёта, времени, авиакомпании

**Примеры запросов:**

• «Найди аэропорты Москвы»
• «Какие рейсы из Шереметьево 15 января?»
• «Покажи прилёты в Домодедо до 12:00»
• «Рейсы из SVO в JFK завтра»
    """
    await message.answer(about_message, parse_mode='markdown')
    chat_logger.info('Успешное завершение команды `/about`')
    

@router.message(Command('CreatePresentation'))
async def create_presentation(message: Message, bot: Bot, command: CommandObject):
    chat_logger.info('Передача команды `/CreatePresentation` в бота')
    
    # Обрабатываем параметры
    chat_logger.info('Старт обработки параметров')
    args = command.args
    if args is None:
        await message.answer('Неправильный вызов команды. Введите в формате /CreatePresentation {количество слайдов}')
        chat_logger.warning('Ошибка. Неправильный вызов команды. Ввод без количества слайдов')
        return
    try:
        slides_num = int(args)
    except Exception as e:
        await message.answer('Неправильный вызов команды. Введите в формате /CreatePresentation {количество слайдов}. Количество слайдов должно быть целым числом')
        chat_logger.warning('Ошибка. Неправильный вызов команды. Количество слайдов не является числом')
        return
    chat_logger.info('Успешное завершение обработки параметров')

    # Собираем историю переписки
    chat_logger.info('Старт сбора истории переписки')
    loading_message = await message.answer('Вспоминаю наш диалог для создания презентации...')
    config = {'configurable': {'thread_id': str(message.from_user.id)}}
    state = agent.get_state(config)
    messages = state.values.get("messages", [])
    if len(messages) == 0:
        await message.answer('История нашей переписки пока пуста. Спросите у меня что-нибудь, а потом повторите команду')
        chat_logger.warning('Ошибка. История переписки пуста')
        return
    chat_logger.info('Успешное завершение сбора истории переписки')

    # Создаем контекст презентации
    chat_logger.info('Старт создания контекста презентации')
    await bot.edit_message_text(chat_id=message.chat.id,
                                message_id=loading_message.message_id,
                                text='Создаю контекст для презентации...')
    presentation_context = ''
    for msg in messages:
        msg_type = type(msg).__name__
        if msg_type == 'HumanMessage':
            presentation_context += f'HUMAN MESSAGE: {msg.content}\n'
        elif msg_type == 'AIMessage' and hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                if not msg.content and msg.additional_kwargs:
                    presentation_context += f'THOUGHT: {msg.additional_kwargs['reasoning_content']}\n'
                presentation_context += f'ACTION: {tc["name"]}({json.dumps(tc["args"], ensure_ascii=False)})\n'
        elif msg_type == 'AIMessage' and not getattr(msg, 'tool_calls', None):
            if msg.content:
                presentation_context += f'FINAL ANSWER: {msg.content}\n'

    if not presentation_context.strip():
        await bot.delete_message(
            chat_id=message.chat.id,
            message_id=loading_message.message_id)
        await message.answer('В истории переписки нет текста для презентации')
        chat_logger.warning('Ошибка. В истории переписки нет текста для презентации')
        return
    chat_logger.info(f'Успешное завершение создания контекста презентации:\n{presentation_context}')
    
    chat_logger.info('Старт присоединения системного промта для создания презентаций к контексту')
    path = _PROMPTS_DIR / os.getenv("PRESENTATION_SYSTEM_PROMPT_PATH")
    system_prompt = path.read_text(encoding="utf-8")
    presentation_context = system_prompt + presentation_context
    chat_logger.info('Успешное присоединение системного промта для создания презентаций к контексту')

    await bot.edit_message_text(chat_id=message.chat.id,
                                message_id=loading_message.message_id,
                                text='Приступаю к созданию презентации...')

    chat_logger.info('Старт формирования запроса через API к генератору презентаций')
    try:
        creating_url = "https://api.presenton.ai/api/v3/presentation/generate/async"
        creating_data = {
            "content": presentation_context,
            "n_slides": slides_num,
            "language": "Russian",
            "standard_template": "modern",
            "export_as": "pptx"
            }
        creating_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('PRESENTON_API_KEY')}"
            }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(creating_url, json=creating_data, headers=creating_headers)
            response.raise_for_status()
            result = response.json()
        presentation_id = result.get('id', None)

        if presentation_id is None:
            await bot.delete_message(
                chat_id=message.chat.id,
                message_id=loading_message.message_id)
            await message.answer('Ошибка создания презентации')
            chat_logger.error('Ошибка. Не удалось получить значения по ключу `id` из ответа сервера')
            return
        
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=loading_message.message_id,
            text='Генерация презентации...')
        
        chat_logger.info('Старт процесса генерации презентации')

        status_url = f"https://api.presenton.ai/api/v3/async-task/status/{presentation_id}"
        status_headers = {"Authorization": f"Bearer {os.getenv('PRESENTON_API_KEY')}"}
        max_retries = 60
        retry_delay = 10
        download_path = None

        for _ in range(max_retries):
            await asyncio.sleep(retry_delay)
            async with httpx.AsyncClient(timeout=30) as client:
                status_resp = await client.get(status_url, headers=status_headers)
                status_resp.raise_for_status()
                status_data = status_resp.json()

            cur_status = status_data.get('status', None)
            
            if cur_status is None:
                await bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=loading_message.message_id)
                await message.answer('Ошибка создания презентации.')
                chat_logger.error('Ошибка генерации презентации. Не удалось получить значения по ключу `status` из ответа сервера.')
                return
            
            if cur_status == 'failed':
                await bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=loading_message.message_id)
                await message.answer('Ошибка создания презентации.')
                chat_logger.error('Ошибка генерации презентации. Ключ `status` из ответа сервера имеет значение `failed`.')
                return
            
            if cur_status == 'completed': 
                download_path = status_data.get('data', {}).get("path", None)
                if download_path:
                    chat_logger.info('Успешное получение ссылки для скачивания презентации')
                    chat_logger.info('Запрос через API к генератору презентаций завершился успешно')
                    break
        
        # Если после всех попыток путь не получен
        if not download_path:
            await bot.delete_message(
                chat_id=message.chat.id,
                message_id=loading_message.message_id)
            await message.answer('Ошибка создания презентации.')
            chat_logger.error('Ошибка. После всех попыток запроса не удалось получить ссылку на скачивание презентации.')
            return

        # Скачиваем файл
        chat_logger.info('Старт скачивания презентации')
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=loading_message.message_id,
            text='Скачиваю презентацию...')

        async with httpx.AsyncClient(timeout=60) as client:
            file_resp = await client.get(download_path)
            file_resp.raise_for_status()
        chat_logger.info('Скачивание презентации завершилось успешно')

        # Отправляем файл пользователю
        chat_logger.info('Старт отправки презентации пользователю')
        await bot.delete_message(
            chat_id=message.chat.id,
            message_id=loading_message.message_id)
            
        # Создаем объект файла из байтов
        file_to_send = BufferedInputFile(
            file_resp.content,  # байты файла
            filename="presentation.pptx"
        )

        await message.answer_document(
            file_to_send,
            caption="Ваша презентация по нашей переписке готова!"
        )
        chat_logger.info('Успешное завершение отправки презентации пользователю.')

    except httpx.HTTPStatusError as e:
        await message.answer('Ошибка создания презентации')
        chat_logger.error(f'Ошибка сервера: {e.response.status_code} — {e.response.text[:200]}')
    except httpx.RequestError as e:
        await message.answer('Ошибка создания презентации')
        chat_logger.error(f'Сетевая ошибка: {type(e).__name__} — {e}')
    except Exception as e:
        await message.answer('Ошибка создания презентации')
        chat_logger.error(f'Ошибка: {type(e).__name__} — {e}')
    

@router.message(Command('restart'))
async def restart(message: Message):
    chat_logger.info('Передача команды `/restart` в бота')
    try:
        memory.delete_thread(thread_id=str(message.from_user.id))
    except Exception as e:
        chat_logger.error(f'Очистить историю не удалось. Команда `/restart` завершилась с ошибкой: {e}')
        await message.answer('Возникла ошибка. Очистить историю не удалось.')
        return
    await message.answer('История успешно стерта')
    chat_logger.info('Успешное завершение команды `/restart`')
    

@router.message()
async def income_message(message: Message, bot: Bot):  
    text = message.text.strip()
    chat_logger.info(f'Запуск обработки обычного сообщения: {text}')  
    if text.startswith('/'):
        await message.answer('К сожалению мне не известна эта команда')
        chat_logger.warning(f'Входное сообщение является неизвестной командой')
        return
    
    loading_message = await message.answer("Ищу и размышляю...")
    
    try:
        response = await process_message(text, message.from_user.id)
        
        await bot.delete_message(
            chat_id=message.chat.id,
            message_id=loading_message.message_id
        )
        
        await message.answer(response)
        chat_logger.info('Успешное завершение команды обработки обычного сообщения')
    
    except Exception as e:
        await bot.delete_message(
            chat_id=message.chat.id,
            message_id=loading_message.message_id
        )
        
        await message.answer(f"Произошла ошибка при обработке запроса: {e}")
        chat_logger.error(f'Обработка обычного сообщения завершилась ошибкой: {e}')