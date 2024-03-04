import asyncio
import time
import re
from datetime import datetime

from loader import dp, types, mailing_state, FSMContext, bot_state
from filters.filter_commands import isPrivate


@dp.message_handler(isPrivate(), commands=['toggle_add_to_channel'], state="*")
async def toggle_add_to_channel(message: types.Message, state: FSMContext):
    bot_state.toggle_add_to_channel()
    if bot_state.get_add_to_channel():
        await message.answer("Прием в канал был включен")
    else:
        await message.answer("Прием в канал был выключен")



