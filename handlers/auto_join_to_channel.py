
from loader import dp, types, keyboard, bot, start_state, welcome_message, isChat, channel_subscribe, logging, FSMContext, channels_auto_join, connect_bd, bot_state
from filters.filter_commands import isUser
from utils import gpt_state


@dp.chat_join_request_handler()
async def join_request(update: types.ChatJoinRequest, state: FSMContext):
  chat, user_id = update.chat.id, update.from_user.id

  user, channels = await connect_bd.mongo_conn.db.users.find_one({'user_id': str(user_id)}), []
  if user:
    if user.get('necessary_channel'):
      channels.append(user['necessary_channel']['id'])

  if str(chat) in channels_auto_join or str(chat) in channels:
    try:
      if bot_state.get_add_to_channel():
        await update.approve()
      await bot.send_message(user_id, '<b>Благодарим за подписку на канал😊</b>\n\n👍 С помощью этого бота вы сможете найти удаленную работу или обучиться новой профессии.\n\nВ подарок для вас доступ к ChatGPT для использования нажмите /start\n\nНе отключайте уведомления и ознакомьтесь с бесплатными курсами по профессиям 👇', parse_mode='html', disable_web_page_preview=True)
      m = await keyboard.call_gpt()
      msg = await bot.send_message(chat, f'Начать чат', reply_markup=m)
      await state.update_data(keyboard_open=True, msg_id_keyboard_open=msg.message_id, chat_id_keyboard_open=chat)
      await gpt_state.set_query.set()
    except Exception as e:
      logging.error("Exception occurred AUTO_JOIN", exc_info=True)