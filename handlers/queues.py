from aiogram.types import InputFile

from loader import dp, types, queues_state, FSMContext, keyboard, bot, connect_bd
from filters.filter_commands import isPrivate


@dp.message_handler(isPrivate(), commands=['queues'], state="*")
async def get_imagine_phrase(message: types.Message, state: FSMContext):
  chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)

  await state.update_data(type_check_queues='gpt')
  m, t = await keyboard.get_queues(type='gpt')
  await bot.send_message(chat, t, reply_markup=m, parse_mode='html')
  await queues_state.queues_update.set()


@dp.message_handler(isPrivate(), commands=['get_users'], state="*")
async def get_users(message: types.Message, state: FSMContext):
    try:
        bot_name = await bot.get_me()
        file_name = bot_name.username + "_users.txt"
        users = await connect_bd.mongo_conn.db.users.find({}).to_list(length=None)
        user_ids = [user.get("user_id") for user in users]
        with open(file_name, "w", encoding='utf-8') as file:
            file.write("\n".join(user_ids))
        await message.answer_document(InputFile(file_name))
    except Exception as e:
        print(e)


@dp.callback_query_handler(isPrivate(), state=queues_state.queues_update)
async def callback_data(message: types.CallbackQuery, state: FSMContext):
  chat, message_id = str(message.message.chat.id), message.message.message_id
  user_id = str(message.from_user.id)
  user_data = await state.get_data()
  d = message.data


  if d == 'queues_update':
    m, t = await keyboard.get_queues(update=True, type=user_data['type_check_queues'])
    try:
      await bot.edit_message_text(t, chat, message_id, reply_markup=m, parse_mode='html')
    except:
      pass

  if d == 'select_gpt':
    await state.update_data(type_check_queues='gpt')
    m, t = await keyboard.get_queues(type='gpt')
    try:
      await bot.edit_message_text(t, chat, message_id, reply_markup=m, parse_mode='html')
    except:
      pass
    await queues_state.queues_update.set()

  if d == 'select_midjourney':
    await state.update_data(type_check_queues='midjorney')
    m, t = await keyboard.get_queues(type='midjorney')
    try:
      await bot.edit_message_text(t, chat, message_id, reply_markup=m, parse_mode='html')
    except:
      pass
    await queues_state.queues_update.set()

  return True