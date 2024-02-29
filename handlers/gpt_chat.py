import asyncio
from datetime import datetime
import time

from loader import dp, types, connect_bd, gpt_state, gpt_api, FSMContext, keyboard, bot, start_state, rate_limit, logging, conf, account_number
from filters.filter_commands import isUser, isNotQueue, isSubscribe


@dp.message_handler(isUser(), isSubscribe(), commands=['chat'], state="*")
@rate_limit(2, 'get_query')
async def get_gpt_chat(message: types.Message, state: FSMContext):
  chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)

  m = await keyboard.start_chat()
  msg = await message.answer('Подключаюсь к нейросети...', reply_markup=m)
  await state.update_data(keyboard_open=True, msg_id_keyboard_open=msg.message_id, chat_id_keyboard_open=chat)

  m = await keyboard.set_dialog(False)
  await message.answer(f'Введите ваш запрос или начните диалог.', reply_markup=m)


  await gpt_state.set_query.set()

  async with state.proxy() as d:
    if d.get('dialog'):
      del d['dialog']

      d['start_dialog'] = True
      await connect_bd.mongo_conn.db.users.update_one({'user_id': user_id}, {'$set': {'dialogs': []}})



@dp.message_handler(isUser(), isSubscribe(), text="Начать чат", state="*")
@rate_limit(2, 'get_query')
async def get_gpt_chat_text_call(message: types.Message, state: FSMContext):
  chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)

  m = await keyboard.start_chat()
  msg = await message.answer('Подключаюсь к нейросети...', reply_markup=m)
  await state.update_data(keyboard_open=True, msg_id_keyboard_open=msg.message_id, chat_id_keyboard_open=chat)

  m = await keyboard.set_dialog(False)
  await message.answer(f'Введите ваш запрос или начните диалог.', reply_markup=m)


  await gpt_state.set_query.set()

  async with state.proxy() as d:
    if d.get('dialog'):
      del d['dialog']

      d['start_dialog'] = True
      await connect_bd.mongo_conn.db.users.update_one({'user_id': user_id}, {'$set': {'dialogs': []}})



@dp.message_handler(isUser(), text='Назад', state="*")
@rate_limit(2, 'get_query')
async def end_gpt_chat(message: types.Message, state: FSMContext):
  chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)

  try:
    await bot.send_message(chat, 'Общение с ChatGPT нейросетью завершено', reply_markup=types.ReplyKeyboardRemove())

    m = await keyboard.select_neural_net()
  except:
    pass
  await start_state.select_neiro.set()

@dp.message_handler(isUser(), isNotQueue(), state=gpt_state.set_query)
@rate_limit(1, 'get_query gpt')
async def get_query(message: types.Message, state: FSMContext):
  chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)

  if '/' == message.text[0]:
    await bot.send_message(chat, 'Вы ввели команду бота и при этом находитель в режиме общения с ChatGPT нейросетью. Нажмите в нижнем меню "Назад" и переходите, куда собирались')
    return False

  try:
    query = message.text.strip()

    user = await connect_bd.mongo_conn.db.users.find_one({'user_id': user_id})
    count_queues = await connect_bd.mongo_conn.db.queues.count_documents({'type': 'gpt', 'status': 'wait'})
    if count_queues > 0:
      msg = await bot.send_message(chat, f'Ваш запрос добавлен в очередь. Номер в очереди: {count_queues}.')
    else:
      msg = await bot.send_message(chat, f'Ваш запрос добавлен в очередь.')

    if user.get('set_dialog'):
      dialogs = user.get('dialogs') or []
      dialogs.append({'role': 'user', 'content': query})
    else:
      dialogs = []
      dialogs.append({'role': 'user', 'content': query})

    data = {'user_id': user_id, 'chat_id': chat, 'query': query, 'date': datetime.now(), 'start_time': int(time.time()),
        'dialogs': dialogs, 'type': 'gpt', 'message_id': msg.message_id, 'status': 'wait', 'repeat': 0}
    await connect_bd.mongo_conn.db.queues.insert_one(data)

  except Exception as e:
    logging.error("Exception occurred", exc_info=True)

@dp.callback_query_handler(isUser(), isSubscribe(), state=gpt_state.set_query)
@rate_limit(1, 'get_query')
async def callback_data(message: types.CallbackQuery, state: FSMContext):
  chat, message_id = str(message.message.chat.id), message.message.message_id
  user_id = str(message.from_user.id)

  if message.data == 'set_dialog':
    user = await connect_bd.mongo_conn.db.users.find_one({'user_id': user_id})
    if user.get('set_dialog') == None:
      await connect_bd.mongo_conn.db.users.update_one({'user_id': user_id}, {'$set': {'set_dialog': True, 'dialogs': []}})
      await bot.send_message(chat, 'Диалог начат. Теперь бот будет запоминать предыдущие сообщения')

    else:
      if user['set_dialog'] == False:
        await connect_bd.mongo_conn.db.users.update_one({'user_id': user_id}, {'$set': {'set_dialog': True, 'dialogs': []}})
        await bot.send_message(chat, 'Диалог начат. Теперь бот будет запоминать предыдущие сообщения')
      else:
        await connect_bd.mongo_conn.db.users.update_one({'user_id': user_id}, {'$set': {'set_dialog': False, 'dialogs': []}})
        m = await keyboard.set_dialog(False)
        await bot.send_message(chat, 'Диалог завершён.', reply_markup=m)
