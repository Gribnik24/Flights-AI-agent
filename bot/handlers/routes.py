from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Bot
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.agent_wrapper import process_message

router = Router()

def get_main_button_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Помощь', callback_data='/help'),
             InlineKeyboardButton(text='Обо мне', callback_data='/about')],
            [InlineKeyboardButton(text='Репозиторий GitHub со мной',
                                  url='https://github.com/Gribnik24/Flights-AI-agent')]],
        resize_keyboard=True
    )
    
    return keyboard

@router.message(Command("start"))
async def start(message: Message):
    start_message = f"""
    Привет, {message.from_user.first_name}! Я бот, который умеет искать информацию о полетах.
Ты можешь прописать следующие команды:
**/help**  - для того, что я подсказал тебе мои действующие команды.
**/about** - чтобы узнать подробнее, что я умею и в чем мой смысл.
Либо нажми на кнопки на предоставленной клавиатуре ниже.
    """
    await message.answer(start_message, parse_mode='Markdown',
                         reply_markup=get_main_button_keyboard()
                         )
    

@router.message(Command('help'))
async def help(message: Message):
    help_message = """Тестовое сообщение help"""
    await message.answer(help_message)
    
    
@router.message(Command('about'))
async def about(message: Message):
    about_message = """Тестовое сообщение about"""
    await message.answer(about_message)
    

# @router.message(Command('create_presentation'))
# async def create_presentation(message: Message, bot: Bot):
#     document = # логика получения документа
#     file_id = document.file_id
    
#     file_name = await bot.get_file(file_id)
#     file_path = file_name.file_path
    
#     file = FSInputFile(file_path)
    
#     await message.answer_document(file, caption="Ваша презентация по нашей переписке готова!")
    

@router.message()
async def income_message(message: Message, bot: Bot):    
    text = message.text.strip()
    if text.startswith('/'):
        await message.answer('К сожалению мне не известна эта команда')
        return
    
    loading_message = await message.answer("Выполняю поиск информации...")
    
    try:
        response = await process_message(text, message.from_user.id)
        
        await bot.delete_message(
            chat_id=message.chat.id,
            message_id=loading_message.message_id
        )
        
        await message.answer(response)
    
    except Exception as e:
        await bot.delete_message(
            chat_id=message.chat.id,
            message_id=loading_message.message_id
        )
        
        await message.answer(f"Произошла ошибка при обработке запроса: {e}")