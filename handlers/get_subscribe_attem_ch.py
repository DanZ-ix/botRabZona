
from loader import dp, types, state_profile, FSMContext, bot, keyboard, other_func, attempts_channels, connect_bd, conf, account_number, rate_limit
from filters.filter_commands import isUser, isSubscribe, clearDownKeyboard

@dp.callback_query_handler(isUser(), isSubscribe(), text=['open_attempt_variants'], state="*")
@rate_limit(1, 'profile')
async def callback_data(message: types.CallbackQuery, state: FSMContext):
  chat, message_id = str(message.message.chat.id), message.message.message_id
  username, fullname, user_id = f'@{message.from_user.username}', message.from_user.full_name, str(message.from_user.id)

  user = await connect_bd.mongo_conn.db.users.find_one({'user_id': user_id})
  if user.get('attempts_channel') == None:
    user['attempts_channel'] = []
    await connect_bd.mongo_conn.db.users.update_one({'user_id': user_id}, {'$set': {'attempts_channel': []}})

  t, m = await keyboard.variants_subscribe_to_channels(user_get_channel=True, filters_channels=user['attempts_channel'])
  if t:
    await bot.edit_message_text(t, chat, message_id, reply_markup=m, parse_mode='html', disable_web_page_preview=True)
    await state_profile.check_subscribe.set()
  else:
    await bot.send_message(chat, 'Сейчас подписываться не на что.')


@dp.callback_query_handler(isUser(), isSubscribe(), text=['notify_attempt_variants'], state="*")
@rate_limit(1, 'profile')
async def callback_data(message: types.CallbackQuery, state: FSMContext):
  chat, message_id = str(message.message.chat.id), message.message.message_id
  username, fullname, user_id = f'@{message.from_user.username}', message.from_user.full_name, str(message.from_user.id)

  user = await connect_bd.mongo_conn.db.users.find_one({'user_id': user_id})

  if user.get('new_channel_notify') != True:
    await connect_bd.mongo_conn.db.users.update_one({'user_id': user_id}, {'$set': {'new_channel_notify': True}})
    await bot.send_message(chat, 'Я вас уведомлю, когда появится новый канал для подписки')
  else:
    await bot.send_message(chat, 'Вы уже подписались на уведомление, ожидайте')
