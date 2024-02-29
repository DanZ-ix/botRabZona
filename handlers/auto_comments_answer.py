import asyncio
from datetime import datetime
import time

from loader import dp, types, connect_bd, gpt_state, gpt_api, FSMContext, keyboard, bot, start_state, rate_limit, logging, conf, account_number, isChat, channel_subscribe
from filters.filter_commands import isUser

@dp.message_handler(isUser(), isChat(chat_id=-1001905217371), state="*")
async def get_query(message: types.Message):
  chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(message.from_user.id)

  if message.reply_to_message:
    if str(message.reply_to_message.sender_chat.id) in channel_subscribe:

      try:
        query = message.text.strip()
        dialogs = [{'role': 'user', 'content': query}]
        print(chat)
        data = {'user_id': user_id, 'chat_id': chat, 'query': query, 'date': datetime.now(), 'start_time': int(time.time()),
            'dialogs': dialogs, 'type': 'gpt', 'message_id': message.message_id, 'status': 'wait', 'repeat': 0, 'not_message': True}
        await connect_bd.mongo_conn.db.queues.insert_one(data)

      except Exception as e:
        logging.error("Exception occurred", exc_info=True)