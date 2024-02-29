import asyncio
import random

from loader import dp, types, state_profile, FSMContext, bot, keyboard, other_func, channel_subscribe, connect_bd, youmoney_web, conf, account_number, rate_limit, start_state, channel_in, channel_in1
from filters.filter_commands import isUser, isSubscribe, clearDownKeyboard


@dp.message_handler(isUser(), clearDownKeyboard(), isSubscribe(), commands=['profile'], state="*")
@rate_limit(2, 'profile')
async def menu(message: types.Message, state: FSMContext):
  chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)

  m, user_info = await other_func.get_profile(keyboard, user_id, bot)
  await bot.send_message(chat, user_info, reply_markup=m, parse_mode='html')
  await state_profile.get_attempts.set()


@dp.callback_query_handler(isUser(), isSubscribe(), state=state_profile.get_attempts)
@rate_limit(3, 'profile')
async def callback_data(message: types.CallbackQuery, state: FSMContext):
  chat, message_id = str(message.message.chat.id), message.message.message_id
  user_id = str(message.from_user.id)

  if message.data == 'get_free_attempts':
    m = await keyboard.get_variants_free_attempts()
    await bot.send_message(chat, '- Получить +1 попытку за каждую подписку (список обновляется)\n- Пригласить друга +1\n- Ежедневно +1 попытка', reply_markup=m)
    await state_profile.get_variants_for_attempts.set()

  if message.data == 'get_pay_attempts':
    m = await keyboard.get_variants_pay_attempts()
    await bot.send_message(chat, 'Что хотите приобрести?', reply_markup=m)
    await state_profile.get_variants_for_attempts_pay.set()

@dp.callback_query_handler(isUser(), isSubscribe(), state=state_profile.get_variants_for_attempts)
@rate_limit(1, 'profile')
async def callback_data(message: types.CallbackQuery, state: FSMContext):
  chat, message_id = str(message.message.chat.id), message.message.message_id
  user_id = str(message.from_user.id)

  if message.data == 'invite_friend':
    await bot.send_message(chat, f'Ваша пригласительная ссылка: <code>https://t.me/{bot["username"]}?start={user_id}</code>', parse_mode='html')

  if message.data == 'subscribe_channel':
    user = await connect_bd.mongo_conn.db.users.find_one({'user_id': user_id})
    if user.get('attempts_channel') == None:
      user['attempts_channel'] = []
      await connect_bd.mongo_conn.db.users.update_one({'user_id': user_id}, {'$set': {'attempts_channel': []}})

    t, m = await keyboard.variants_subscribe_to_channels(user_get_channel=True, filters_channels=user['attempts_channel'])
    if t:
      await bot.edit_message_text(t, chat, message_id, reply_markup=m, parse_mode='html', disable_web_page_preview=True)
      await state_profile.check_subscribe.set()
    else:
      if user.get('new_channel_notify') == None:
        m = await keyboard.set_notify_to_subscribe_channel()
        await bot.send_message(chat, 'Сейчас подписываться не на что.', reply_markup=m)
      else:
        await bot.send_message(chat, 'Сейчас подписываться не на что. Я вас уведомлю, когда что-то будет')


@dp.callback_query_handler(isUser(), isSubscribe(), state=state_profile.get_variants_for_attempts_pay)
@rate_limit(1, 'profile')
async def callback_data(message: types.CallbackQuery, state: FSMContext):
  chat, message_id = str(message.message.chat.id), message.message.message_id
  username, fullname, user_id = f'@{message.from_user.username}', message.from_user.full_name, str(message.from_user.id)

  d = message.data.split(':')
  try:
    settings = await connect_bd.mongo_conn.db.settings.find_one({'admin': True})
    n = settings['account']
    attempt, price = d[1], d[2]
    if attempt and price:
      url = await youmoney_web.get_youmoney_url(n, user_id, attempt, price)
      m = await keyboard.payment_url(url)
      await bot.send_message(chat, f'Вы выбрали набор из {attempt} шт. за {price}₽', reply_markup=m)
      await state_profile.get_attempts.set()
  except:
    pass

@dp.callback_query_handler(isUser(), state=state_profile.check_nec_sub)
@rate_limit(1, 'profile')
async def callback_data(message: types.CallbackQuery, state: FSMContext):
  chat, message_id = str(message.message.chat.id), message.message.message_id
  user_id = str(message.from_user.id)
  sub = 0
  try:
    for chat_id in channel_subscribe:
      ch = await bot.get_chat_member(chat_id, user_id)

      if ch.status in ['creator', 'administrator', 'member']:
        sub += 1
  except:
    pass

  if sub == len(channel_subscribe):
    m = await keyboard.select_neural_net()
    await bot.send_message(chat, 'Выберите, с какой нейросетью будете взаимодействовать', reply_markup=m)
    await start_state.select_neiro.set()
  else:
    await bot.send_message(chat, f'Вы не подписались на канал: {channel_in}', disable_web_page_preview=True, parse_mode='html')


@dp.callback_query_handler(isUser(), isSubscribe(), state=state_profile.check_subscribe)
@rate_limit(1, 'profile')
async def callback_data(message: types.CallbackQuery, state: FSMContext):
  chat, message_id = str(message.message.chat.id), message.message.message_id
  user_id = str(message.from_user.id)
  user = await connect_bd.mongo_conn.db.users.find_one({'user_id': user_id})

  count_sub1, count_sub2, all_channels = 0, 0, 0
  async for channel in connect_bd.mongo_conn.db.channels_subscribe.find():
    all_channels += 1
    if user.get('attempts_channel') != None:
      if channel['id'] in user['attempts_channel']:
        count_sub1 += 1
        continue

    try:
      ch = await bot.get_chat_member(channel['id'], user_id)
      if ch.status in ['creator', 'administrator', 'member']:
        count_sub2 += 1
        await connect_bd.mongo_conn.db.users.update_one({'user_id': user_id},
          {'$push': {'attempts_channel': channel['id']}, '$inc': {'attempts_pay': 1}})
        await bot.send_message(chat, f'Вы получили вознаграждение за подписку на канал: <b>{channel["title"]}</b>', parse_mode='html')
    except:
      pass

    await asyncio.sleep(0.5)

  if count_sub2 == 0 and count_sub1 != all_channels:
    await bot.send_message(chat, 'Вы ни на что ещё не подписались')

  if count_sub1 == all_channels:
    await bot.send_message(chat, 'Вы подписались уже на все доступные каналы')