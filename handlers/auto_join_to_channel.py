
from loader import dp, types, keyboard, bot, start_state, welcome_message, isChat, channel_subscribe, logging, FSMContext, channels_auto_join, connect_bd
from filters.filter_commands import isUser
import asyncio

@dp.chat_join_request_handler()
async def join_request(update: types.ChatJoinRequest, state: FSMContext):
  chat, user_id = update.chat.id, update.from_user.id

  user, channels = await connect_bd.mongo_conn.db.users.find_one({'user_id': str(user_id)}), []
  if user:
    if user.get('necessary_channel'):
      channels.append(user['necessary_channel']['id'])

  if str(chat) in channels_auto_join or str(chat) in channels:
    try:
      await update.approve()
      await bot.send_message(user_id, '<b>Благодарим за подписку на канал😊</b>\n\n👍 С помощью этого бота вы сможете найти удаленную работу или обучиться новой профессии.\n\nВ подарок для вас доступ к ChatGPT для использования нажмите /start\n\nНе отключайте уведомления и ознакомьтесь с бесплатными курсами по профессиям 👇', parse_mode='html', disable_web_page_preview=True)
      await asyncio.sleep(10)
      
      message_dict = await connect_bd.mongo_conn.db.saved_messages.find_one({"message_id": {"$gt": 0}})
      if message_dict is not None:
        try:
          new_message = types.Message.to_object(message_dict)
          file_json = sorted(new_message.photo, key=lambda d: d['file_size'])[-1]

          file = await bot.download_file_by_id(file_json.file_id)
          await bot.send_photo(user_id, file, caption=new_message.caption,
                                     caption_entities=new_message.caption_entities,
                                     reply_markup=new_message.reply_markup, disable_web_page_preview=True)
        except Exception:
          new_message = types.Message.to_object(message_dict)
          await bot.send_message(user_id, new_message.text,
                                       entities=new_message.entities,
                                       reply_markup=new_message.reply_markup, disable_web_page_preview=True)
      await gpt_state.set_query.set()
    except Exception as e:
      logging.error("Exception occurred AUTO_JOIN", exc_info=True)