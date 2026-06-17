from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Bot
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from agent.agent_wrapper import process_message
from agent.flights_agent import memory

router = Router()

def get_main_button_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text='Репозиторий GitHub со мной',
                                               url='https://github.com/Gribnik24/Flights-AI-agent')]],
        resize_keyboard=True
    )
    
    return keyboard

@router.message(Command("start"))
async def start(message: Message):
    start_message = f"""
    Привет, {message.from_user.first_name}! Я бот, который умеет искать *информацию о полетах* ✈️.
Ты можешь прописать следующие команды:
• */about* - чтобы узнать подробнее, что я умею и в чем мой смысл
• */CreatePresentation* - чтобы создать презентацию по истории нашей переписки
• */restart* - чтобы очистить историю нашей переписки
    """
    await message.answer(start_message, parse_mode='Markdown', reply_markup=get_main_button_keyboard())
    
    
@router.message(Command('about'))
async def about(message: Message):
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
    

@router.message(Command('CreatePresentation'))
async def create_presentation(message: Message, bot: Bot):
    await message.answer('тестовое сообщение')
    # document = # логика получения документа
    # file_id = document.file_id
    
    # file_name = await bot.get_file(file_id)
    # file_path = file_name.file_path
    
    # file = FSInputFile(file_path)
    
    # await message.answer_document(file, caption="Ваша презентация по нашей переписке готова!")
    

@router.message(Command('restart'))
async def restart(message: Message):
    memory.delete_thread(thread_id=str(message.from_user.id))
    await message.answer('История успешно стерта.')
    

@router.message()
async def income_message(message: Message, bot: Bot):    
    text = message.text.strip()
    if text.startswith('/'):
        await message.answer('К сожалению мне не известна эта команда')
        return
    
    loading_message = await message.answer("Ищу и размышляю...")
    
    try:
        response = await process_message(text, message.from_user.id)
        
        await bot.delete_message(
            chat_id=message.chat.id,
            message_id=loading_message.message_id
        )
        
        await message.answer(response, parse_mode='Markdown')
    
    except Exception as e:
        await bot.delete_message(
            chat_id=message.chat.id,
            message_id=loading_message.message_id
        )
        
        await message.answer(f"Произошла ошибка при обработке запроса: {e}")