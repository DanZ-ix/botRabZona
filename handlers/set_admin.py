from loader import dp, types, bot, conf, other_commands
from filters.filter_commands import isAdmin

@dp.message_handler(isAdmin(), commands=['set_admin'], state="*")
async def set_admin(message: types.Message):
  chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)

  if conf['admin']['id'] == '':
    admin_id = user_id
    conf['admin']['id'] = user_id
    conf.write()

    await other_commands.set_admin_commands(admin_id)
    await bot.send_message(chat, f'{fullname}, теперь вы админ бота, у вас появились в меню расширенные команды')
  else:
    conf['admin']['id'] = ''
    conf.write()
    await other_commands.delete_commands(user_id)
    await other_commands.set_commands(user_id)
    await bot.send_message(chat, f'{fullname}, теперь вы не админ бота, теперь через эту команду кто-то другой может стать админом')