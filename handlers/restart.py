from loader import dp, types, bot
from filters.filter_commands import isPrivate

@dp.message_handler(isPrivate(), commands=['restart'], state="*")
async def set_admin(message: types.Message):
  chat, first_name, username, user_id = message.chat.id, message.from_user.first_name or '', message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)

  await bot.send_message(chat, 'Бот ушёл на перезагрузку...')
  exit(1)