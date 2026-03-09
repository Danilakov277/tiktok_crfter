from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

menu = InlineKeyboardMarkup(inline_keyboard=[
                             [InlineKeyboardButton(text='нет',callback_data='next')],
                             [InlineKeyboardButton(text='выложить',callback_data='upload')]
                             ])