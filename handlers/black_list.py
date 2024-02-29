from datetime import datetime
from pandas_ods_reader import read_ods
import os
import aiofiles
import aiohttp

from loader import dp, types, bot, connect_bd, keyboard, banlist_state, FSMContext, gpt_api, dc_api, other_commands, bot_token
from filters.filter_commands import isPrivate

async def add_ban_list(ban_lists, user_id, chat, message, user_data):
  data = []
  async for word in connect_bd.mongo_conn.db.banlist.find({'word': {'$in': ban_lists}}):
    ban_lists.remove(word['word'])

  for i in range(0, len(ban_lists)):
    word = ban_lists[i]
    acc = {'user_id': user_id, 'word': word, 'date': datetime.now()}
    data.append(acc)

  if data:
    if len(data) > 1:
      await connect_bd.mongo_conn.db.banlist.insert_many(data)
    else:
      await connect_bd.mongo_conn.db.banlist.insert_one(data[0])

  await other_commands.set_trash(message, chat=chat)
  t, m = await keyboard.get_accounts_gpt()
  await bot.edit_message_text(f'Добавлено {len(data)} стоп-слов(-а, -ов)', chat, user_data['msg_id'], reply_markup=m)
  await banlist_state.control_ban_list.set()


@dp.message_handler(isPrivate(), commands=['black_list'], state="*")
async def accounts_manager(message: types.Message):
  chat, username, user_id = message.chat.id, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)

  t, m = await keyboard.ban_list_settings()
  await bot.send_message(chat, t, reply_markup=m)
  await banlist_state.control_ban_list.set()


@dp.callback_query_handler(isPrivate(), state=banlist_state.control_ban_list)
async def callback_data(message: types.CallbackQuery, state: FSMContext):
  chat, message_id = str(message.message.chat.id), message.message.message_id
  msg = ''

  if message.data == 'add_banlist_text':
    await other_commands.set_trash(chat=chat)
    msg = await bot.send_message(chat, 'Напишите каждое стоп-слово с новой строки')
    await banlist_state.add_banlist_with_text.set()

  if message.data == 'add_banlist_file':
    msg = await bot.send_message(chat, 'Отправьте файл со список стоп-слов, где каждое слово написано с новой строки')
    await banlist_state.add_banlist_with_file.set()

  await other_commands.set_trash(msg)
  await state.update_data(msg_id=message_id)

@dp.message_handler(isPrivate(), state=banlist_state.add_banlist_with_text)
async def add(message: types.Message, state: FSMContext):
  chat, username, user_id = message.chat.id, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)
  ban_words = message.text.strip().split('\n')
  user_data = await state.get_data()
  await add_ban_list(ban_words, user_id, chat, message, user_data)


@dp.message_handler(isPrivate(), content_types='document', state=banlist_state.add_banlist_with_file)
async def get_banlist_with_file(message: types.document, state: FSMContext):
  chat, user_id = message.chat.id, str(message.from_user.id)
  user_data = await state.get_data()
  file_id = message.document.file_id
  file_info = await bot.get_file(file_id)
  file_path, file_name = file_info.file_path, file_info.file_path.split("/")[len(file_info.file_path.split("/")) - 1]

  async with aiohttp.ClientSession() as session:
    res = await session.get(f'https://api.telegram.org/file/bot{bot_token}/{file_path}')
    if res.status == 200:
      if 'ods' in file_name:
        path = f'files/{file_name}'
        try:
          f = await aiofiles.open(path, mode='wb')
          await f.write(await res.read())
          await f.close()
        except:
          pass

        df = read_ods(path, 1, columns=["A"])
        ban_words = []
        for word_list in df.values:
          if word_list[0]:
            ban_words.append(word_list[0])

        os.remove(path)
        await add_ban_list(ban_words, user_id, chat, message, user_data)
      else:
        ban_words = (await res.text()).strip().replace('\r', '').split('\n')
        await add_ban_list(ban_words, user_id, chat, message, user_data)


