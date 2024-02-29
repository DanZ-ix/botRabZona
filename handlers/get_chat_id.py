import re
import asyncio
from loader import dp, types, bot, server_ip
from filters.filter_commands import isPrivate
from discord_api.functions import dc_api_func

@dp.message_handler(isPrivate(), commands=["get_chat"], state="*")
async def get_query(message: types.Message):
  chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)
  await message.delete()
  await bot.send_message(user_id, f'ID чата: <code>{chat}</code>', parse_mode="html")