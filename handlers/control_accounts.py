import asyncio
import time
from datetime import datetime
import aiohttp

from loader import dp, types, bot, connect_bd, keyboard, accounts_state, FSMContext, gpt_api, dc_api, other_commands, bot_token, account_number
from filters.filter_commands import isPrivate

async def add_gpt_acc(tokens, user_id, chat, message, user_data):
  data = []
  async for acc in connect_bd.mongo_conn.db.accounts.find({'token': {'$in': tokens}}):
    tokens.remove(acc['token'])

  new_acc, no_valid_token = [], 0
  for i in range(0, len(tokens)):
    token = tokens[i]
    # balance = await gpt_api.get_grants(token)
    balance = 2
    if balance == 0.0:
      balance = 0.1
    if balance:
      if balance > 1:
        acc = {'user_id': user_id, 'chat_id': chat, 'token': token, 'date': datetime.now(), 'used': False, 'type': 'gpt', 'queue_count': 0}
        data.append(acc)
      else:
        no_valid_token += 1
    else:
      i -= 1

  if data:
    if len(data) > 1:
      await connect_bd.mongo_conn.db.accounts.insert_many(data)
    else:
      await connect_bd.mongo_conn.db.accounts.insert_one(data[0])

  await other_commands.set_trash(message, chat=chat)
  t, m = await keyboard.get_accounts_gpt()
  await bot.edit_message_text(f'Добавлено {len(data)} токенов для GPT, невалидных токенов: {no_valid_token}', chat, user_data['msg_id'], reply_markup=m)
  await accounts_state.control_accounts_gpt.set()

@dp.message_handler(isPrivate(), commands=['control_accounts'], state="*")
async def accounts_manager(message: types.Message):
  chat, username, user_id = message.chat.id, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)

  m = await keyboard.variant_add_account()
  await bot.send_message(chat, 'Добавить токены ChatGPT?', reply_markup=m)
  await accounts_state.select_type_control.set()

@dp.callback_query_handler(isPrivate(), state=accounts_state.select_type_control)
async def callback_data(message: types.CallbackQuery, state: FSMContext):
  chat, message_id = str(message.message.chat.id), message.message.message_id

  if message.data == 'gpt_add_acc':
    t, m = await keyboard.get_accounts_gpt()
    await bot.edit_message_text(t, chat, message_id, reply_markup=m)
    await accounts_state.control_accounts_gpt.set()

  if message.data == 'midjourney_add_acc':
    t, m = await keyboard.get_accounts_imagine()
    await bot.edit_message_text(t, chat, message_id, reply_markup=m)
    await accounts_state.control_accounts_imagine.set()

@dp.callback_query_handler(isPrivate(), state=accounts_state.control_accounts_gpt)
async def callback_data(message: types.CallbackQuery, state: FSMContext):
  chat, message_id = str(message.message.chat.id), message.message.message_id

  msg, d = '', message.data.split(":")

  if d[0] == 'add_acc_text':
    await other_commands.set_trash(chat=chat)
    msg = await bot.send_message(chat, 'Напишите каждый токен с новой строки')
    await accounts_state.add_accounts_gpt_with_text.set()

  if d[0] == 'add_acc_file':
    await other_commands.set_trash(chat=chat)
    msg = await bot.send_message(chat, 'Отправьте файл с токенами, где каждый токен написан с новой строки')
    await accounts_state.add_accounts_gpt_with_file.set()

  await other_commands.set_trash(msg)
  await state.update_data(msg_id=message_id)


@dp.message_handler(isPrivate(), state=accounts_state.add_accounts_gpt_with_text)
async def add(message: types.Message, state: FSMContext):
  chat, username, user_id = message.chat.id, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)
  tokens = message.text.strip().split('\n')
  user_data = await state.get_data()
  await add_gpt_acc(tokens, user_id, chat, message, user_data)

@dp.message_handler(isPrivate(), content_types='document', state=accounts_state.add_accounts_gpt_with_file)
async def get_tokens_with_file(message: types.document, state: FSMContext):
  chat, user_id = message.chat.id, str(message.from_user.id)
  user_data = await state.get_data()
  file_id = message.document.file_id
  f = await bot.get_file(file_id)
  async with aiohttp.ClientSession() as session:
    res = await session.get(f'https://api.telegram.org/file/bot{bot_token}/{f.file_path}')
    tokens = (await res.text()).strip().replace('\r', '').split('\n')
    await add_gpt_acc(tokens, user_id, chat, message, user_data)


@dp.callback_query_handler(isPrivate(), state=accounts_state.control_accounts_imagine)
async def callback_data(message: types.CallbackQuery, state: FSMContext):
  chat, message_id = str(message.message.chat.id), message.message.message_id

  d = message.data.split(":")

  if d[0] == 'select':
    t, m = await keyboard.get_accounts_imagine(acc_id=d[1])
    await bot.edit_message_text(t, chat, message_id, reply_markup=m)
    await other_commands.set_trash(chat=chat)

  if d[0] == 'request':
    msg = await bot.send_message(chat, 'Отправьте текст запроса')
    await accounts_state.send_request.set()
    await other_commands.set_trash(msg)
    await state.update_data(acc_id=d[1], message_id=message_id)

  if d[0] == 'new_acc':
    await other_commands.set_trash(chat=chat)
    msg = await bot.send_message(chat, 'Введите почту и пароль, разделённые пробелом')
    await other_commands.set_trash(msg)
    await state.update_data(msg_id=message_id)
    await accounts_state.add_account_imagine.set()

  if d[0] == 'add_bot_id':
    await other_commands.set_trash(chat=chat)
    msg = await bot.send_message(chat, 'Введите ID канала. Перейдите в переписку с ботом по ссылке: https://discord.com/channels/@me')
    await other_commands.set_trash(msg)
    await state.update_data(msg_id=message_id, acc_id=d[1])
    await accounts_state.add_bot_id_account_imagine.set()

  if d[0] == 'del_acc':
    await connect_bd.mongo_conn.db.accounts.delete_one({'id': d[1]})
    t, m = await keyboard.get_accounts_imagine(acc_id=d[1])
    await bot.edit_message_text(t, chat, message_id, reply_markup=m)

  if d[0] == 'edit_max_generate':
    acc_id = d[1]
    msg = await bot.send_message(chat, 'Сколько может быть одновременных запросов на генерирацию изображений?')
    await accounts_state.set_max_generation.set()
    await other_commands.set_trash(msg)
    await state.update_data(acc_id=acc_id, message_id=message_id)


  if d[0] == 'mode':
    mode, acc_id = d[1], d[2]
    await connect_bd.mongo_conn.db.accounts.update_one({'id': acc_id}, {'$set': {'mode': mode}})
    acc = await connect_bd.mongo_conn.db.accounts.find_one({'id': acc_id})
    await dc_api.send_query(acc, bot, {}, command=mode, type='command')
    t, m = await keyboard.get_accounts_imagine(acc_id=d[2])
    await bot.edit_message_text(t, chat, message_id, reply_markup=m)

  if d[0] == 'settings_acc':
    t, m = await keyboard.settings_for_dc(account_number)
    await bot.edit_message_text(t, chat, message_id, reply_markup=m, parse_mode='html')
    await accounts_state.sett_settings.set()


@dp.callback_query_handler(isPrivate(), state=accounts_state.sett_settings)
async def callback_data(message: types.CallbackQuery, state: FSMContext):
  chat, message_id = str(message.message.chat.id), message.message.message_id
  d = message.data.split(":")

  if d[0] == 'time_wait':
    msg = await bot.send_message(chat, f'Введите максимальное время ожидания ответа для <b>{d[1] == "fast" and "⚡ Fast" or "🐌 Relax"}</b> режима, когда запрос юзера должен автоматически удаляться и уведомлять юзера, что его запрос не прошёл и не отнимать попытку', parse_mode='html')
    await state.update_data(mode=d[1], message_id=message_id)
    await accounts_state.sett_set_time_wait.set()
    await other_commands.set_trash(msg)

  if d[0] == 'exit_settings':
    t, m = await keyboard.get_accounts_imagine()
    await bot.edit_message_text(t, chat, message_id, reply_markup=m)
    await accounts_state.control_accounts_imagine.set()

@dp.message_handler(isPrivate(), state=accounts_state.send_request)
async def send_request_midjorny(message: types.Message, state: FSMContext):
  chat, username, user_id = message.chat.id, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)
  user_data = await state.get_data()
  query = message.text.strip()

  user = await connect_bd.mongo_conn.db.users.find_one({'user_id': user_id})
  attempt1 = user.get('attempts_free')
  attempt_type = attempt1 > 0 and 'attempts_free' or 'attempts_pay'
  acc = await connect_bd.mongo_conn.db.accounts.find_one({'id': user_data['acc_id']})

  queue = {'user_id': user_id, 'chat_id': chat, 'message_id': '', 'query_original': message.text, 'query': query, 'img_url': '', 'start_time': int(time.time()), 'message_filters': user['message_filters'], 'type': 'midjorney', 'request': True, 'type_request': 'query', 'attempt_type': attempt_type, 'mode': 'fast', 'acc_id': acc['id'], 'acc_username': acc['username'], 'date': datetime.now()}
  await connect_bd.mongo_conn.db.queues.insert_one(queue)
  await bot.send_message(chat, f'Ваш запрос отправлен')
  await dc_api.send_query(acc, bot, queue, type=queue['type_request'],
    callback_data=queue.get('callback_data') or None, message_id=queue.get('message_id') or None)


@dp.message_handler(isPrivate(), state=accounts_state.set_max_generation)
async def set_max_generate_for_acc(message: types.Message, state: FSMContext):
  chat, username, user_id = message.chat.id, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)
  user_data = await state.get_data()
  try:
    value = int(message.text.strip())
  except:
    value = ''

  if isinstance(value, int):
    await connect_bd.mongo_conn.db.accounts.update_one({'id': user_data['acc_id']}, {'$set': {'max_generate': value}})
    await other_commands.set_trash(message, chat=chat)
    t, m = await keyboard.get_accounts_imagine(acc_id=user_data['acc_id'])
    await bot.edit_message_text(t, chat, user_data['message_id'], reply_markup=m)
    await accounts_state.control_accounts_imagine.set()
  else:
    msg = await bot.send_message(chat, 'Вы ввели не число')
    await other_commands.set_trash(msg)


@dp.message_handler(isPrivate(), state=accounts_state.sett_set_time_wait)
async def set_time_wait_for_discord(message: types.Message, state: FSMContext):
  chat, username, user_id = message.chat.id, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)
  user_data = await state.get_data()
  try:
    value = int(message.text.strip())
  except:
    value = ''

  if isinstance(value, int):
    await connect_bd.mongo_conn.db.settings.update_one({'admin': True}, {'$set': {f'mode.{user_data["mode"]}.time_wait': value}})
    await other_commands.set_trash(message, chat=chat)
    t, m = await keyboard.settings_for_dc(account_number)
    await bot.edit_message_text(t, chat, user_data['message_id'], reply_markup=m, parse_mode='html')
    await accounts_state.sett_settings.set()
    await dc_api.get_settings()
  else:
    msg = await bot.send_message(chat, 'Вы ввели не число')
    await other_commands.set_trash(msg)


@dp.message_handler(isPrivate(), state=accounts_state.add_bot_id_account_imagine)
async def add_bot_id_account(message: types.Message, state: FSMContext):
  chat, username, user_id = message.chat.id, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)
  bot_id = message.text.strip()
  user_data = await state.get_data()

  await connect_bd.mongo_conn.db.accounts.update_one({'id': user_data['acc_id']}, {'$set': {'dc_bot_id': bot_id}})

  t, m = await keyboard.get_accounts_imagine()
  await bot.edit_message_text(t, chat, message_id=user_data['msg_id'], reply_markup=m)
  await other_commands.set_trash(message, chat)
  await accounts_state.control_accounts_imagine.set()

@dp.message_handler(isPrivate(), state=accounts_state.add_account_imagine)
async def add_mail_and_pass(message: types.Message, state: FSMContext):
  chat, username, user_id = message.chat.id, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)
  email, password = message.text.split(" ")
  user_data = await state.get_data()

  status = await dc_api.get_token(email, password, new=True)

  if status == 'added':
    t, m = await keyboard.get_accounts_imagine()
    await bot.edit_message_text(t, chat, message_id=user_data['msg_id'], reply_markup=m)
  elif status == 'not_add':
    t, m = await keyboard.get_accounts_imagine()
    await bot.edit_message_text(
      f'Такая почта уже была добавлена', chat,
      message_id=user_data['msg_id'], reply_markup=m)
  else:
    await bot.send_message(chat,
      'Что-то не так: почта или пароль неверные или не сделан был вход в дискорд через прокси сервера')

    await other_commands.set_trash(message, chat)
  await accounts_state.control_accounts_imagine.set()

