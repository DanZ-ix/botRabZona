import asyncio
import logging
import re
import time

from loader import dp, types, bot, connect_bd, keyboard, FSMContext, channels_necessary_state, other_commands
from filters.filter_commands import isPrivate
from handlers.mailing import Mail

@dp.message_handler(isPrivate(), commands=['channels_necessary'], state="*")
async def subscribe_manager(message: types.Message):
  chat, username, user_id = message.chat.id, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)

  t, m = await keyboard.variants_subscribe_necessary_to_channels()
  await bot.send_message(chat, t, reply_markup=m, parse_mode='html', disable_web_page_preview=True)
  await channels_necessary_state.control_channels.set()

@dp.callback_query_handler(isPrivate(), state=channels_necessary_state.control_channels)
async def callback_data(message: types.CallbackQuery, state: FSMContext):
  chat, message_id = str(message.message.chat.id), message.message.message_id

  d = message.data.split(":")

  if d[0] == 'add_ch':
    msg = await bot.send_message(chat, 'Перешлите запись с нужного канала ко мне')
    await other_commands.set_trash(msg)
    await state.update_data(message_id=message_id)
    await channels_necessary_state.add_channel.set()

  if d[0] == 'edit_link' or d[0] == 'url_to_bot':
    if d[0] == 'edit_link':
      msg = await bot.send_message(chat, 'Пришли мне новую ссылку для вступления')
      await channels_necessary_state.set_link.set()
    else:
      msg = await bot.send_message(chat, f'Ссылка по которой будут переходить в бота, например: <code>https://t.me/{bot["username"]}?start=abg543</code>',parse_mode='html')
      await channels_necessary_state.set_bot_link.set()

    await other_commands.set_trash(msg)
    await state.update_data(message_id=message_id, key_channel=d[1])

  if d[0] == 'mailing':
    msg = await bot.send_message(chat, 'Подтвердите рассылку, напишите "Да"')
    await other_commands.set_trash(msg)
    await state.update_data(message_id=message_id, key_channel=d[1])
    await channels_necessary_state.set_mailing.set()

  if d[0] == 'double_сh':
    chs, channel_title, all_count, link = [], '', 0, ''
    async for ch in connect_bd.mongo_conn.db.channels_necessary_subscribe.find({'id': d[1]}):
      all_count += 1

      if d[2] == ch['key']:
        channel_title = ch['title']
        link = ch['link']

    t = str(int(time.time()))
    await connect_bd.mongo_conn.db.channels_necessary_subscribe.insert_one(
      {'key': t, 'id': d[1], 'title': f"{channel_title}", 'link': link})
    t, m = await keyboard.variants_subscribe_necessary_to_channels(key_channel_id=t)
    await bot.edit_message_text(t, chat, message_id, reply_markup=m, parse_mode='html',
      disable_web_page_preview=True)
    await channels_necessary_state.control_channels.set()


  if d[0] == 'get_ch' or d[0] == 'del_ch':
    if d[0] == 'get_ch':
      t, m = await keyboard.variants_subscribe_necessary_to_channels(key_channel_id=d[1])
    else:
      await connect_bd.mongo_conn.db.users.update_many({'necessary_channel.key': d[1]}, {'$unset': {'necessary_channel': True}})
      await connect_bd.mongo_conn.db.channels_necessary_subscribe.delete_one({'key': d[1]})
      t, m = await keyboard.variants_subscribe_necessary_to_channels()

    await bot.edit_message_text(t, chat, message_id, reply_markup=m, parse_mode='html', disable_web_page_preview=True)
    await channels_necessary_state.control_channels.set()



@dp.message_handler(isPrivate(), state=channels_necessary_state.add_channel, content_types=types.ContentType.ANY)
async def add_channel(message: types.Message, state: FSMContext):
  chat, username, user_id = message.chat.id, message.from_user.username and f"@{message.from_user.username}" or "", str(
    message.from_user.id)
  user_data = await state.get_data()

  channel_id = str(message.forward_from_chat.id)
  channel_title = message.forward_from_chat.title

  try:
    channel_info = await bot.get_chat(channel_id)
  except:
    channel_info = None

  if channel_info:
    t = str(int(time.time()))
    await connect_bd.mongo_conn.db.channels_necessary_subscribe.insert_one({'key': t, 'id': channel_id, 'title': channel_title, 'link': 'нет'})
    t, m = await keyboard.variants_subscribe_necessary_to_channels(key_channel_id=t)
    await bot.edit_message_text(t, chat, user_data['message_id'], reply_markup=m, parse_mode='html', disable_web_page_preview=True)
    await channels_necessary_state.control_channels.set()
  else:
    await bot.send_message(chat, 'Бота на данном канале нет в админах')
    await channels_necessary_state.control_channels.set()

  await other_commands.set_trash(message, chat)


@dp.message_handler(isPrivate(), state=channels_necessary_state.set_mailing, content_types=types.ContentType.TEXT)
async def start_mail_info_channel(message: types.Message, state: FSMContext):
  chat, username, user_id = message.chat.id, message.from_user.username and f"@{message.from_user.username}" or "", str(
    message.from_user.id)

  if message.text.lower() == 'да':
    m = await keyboard.get_attempt_to_subs_channel()
    start_m = Mail(text='Вы можете получить дополнительную бесплатную попытку', photo='', video='', reply_markup=m, save_user=0, state=state, mail_new_channel=True)
    asyncio.create_task(start_m.sender_init())


@dp.message_handler(isPrivate(), state=channels_necessary_state.set_link, content_types=types.ContentType.TEXT)
async def edit_link(message: types.Message, state: FSMContext):
  chat, username, user_id = message.chat.id, message.from_user.username and f"@{message.from_user.username}" or "", str(
    message.from_user.id)
  user_data = await state.get_data()
  link = message.text.strip()

  if 't.me' in link:
    await connect_bd.mongo_conn.db.users.update_many({'necessary_channel.key': user_data['key_channel']}, {'$set': {'necessary_channel.link': link}})
    await connect_bd.mongo_conn.db.channels_necessary_subscribe.update_one({'key': user_data['key_channel']}, {'$set': {'link': link}})
    t, m = await keyboard.variants_subscribe_necessary_to_channels(key_channel_id=user_data['key_channel'])
    await bot.edit_message_text(t, chat, user_data['message_id'], reply_markup=m, parse_mode='html', disable_web_page_preview=True)
    await channels_necessary_state.control_channels.set()
    await other_commands.set_trash(message, chat)


@dp.message_handler(isPrivate(), state=channels_necessary_state.set_bot_link, content_types=types.ContentType.TEXT)
async def edit_bot_link(message: types.Message, state: FSMContext):
  chat, username, user_id = message.chat.id, message.from_user.username and f"@{message.from_user.username}" or "", str(
    message.from_user.id)
  user_data = await state.get_data()
  link = message.text.strip()

  if 't.me' in link:
    await connect_bd.mongo_conn.db.channels_necessary_subscribe.update_one({'key': user_data['key_channel']}, {'$set': {'bot_link': link}})
    t, m = await keyboard.variants_subscribe_necessary_to_channels(key_channel_id=user_data['key_channel'])
    await bot.edit_message_text(t, chat, user_data['message_id'], reply_markup=m, parse_mode='html', disable_web_page_preview=True)
    await channels_necessary_state.control_channels.set()
    await other_commands.set_trash(message, chat)