from time import time
import re
from datetime import datetime
from aiogram.dispatcher.filters import BoundFilter

from loader import types, conf, connect_bd, channel_subscribe, bot, keyboard, imagine_state, state_profile, dp, invite_count_max_to_day, channel_in, channel_in1

class isInviteUser(BoundFilter):
  async def check(self, message: types.Message):
    chat, user_id = 'message' in message and message.message.chat.id or message.chat.id, message.from_user.id
    user_id_reward = message.get_args()

    if user_id_reward:
      is_user = await connect_bd.mongo_conn.db.users.find_one({'user_id': str(user_id)})
      if not re.findall(r'[a-z]+', user_id_reward, re.IGNORECASE):
        if not is_user:
          user = await connect_bd.mongo_conn.db.users.find_one({'user_id': user_id_reward})
          if user:
            is_inv = user.get('invite_count_now')
            if is_inv is None:
              await connect_bd.mongo_conn.db.users.update_one({'user_id': user_id_reward},
                {'$set': {'invite_count_now': 0}})
              invite_count = 0
            else:
              invite_count = is_inv

            sub = 0
            for chat_id in channel_subscribe:
              try:
                ch = await bot.get_chat_member(chat_id, user_id)

                if ch.status in ['creator', 'administrator', 'member']:
                  sub += 1
              except:
                pass

            if invite_count < invite_count_max_to_day or str(user_id_reward) in conf['admin']['id']:
              if sub == len(channel_subscribe):
                await connect_bd.mongo_conn.db.users.update_one({'user_id': user_id_reward}, {'$inc': {'attempts_pay': 1, 'invite_count_now': 1}})
                try:
                  await bot.send_message(user_id_reward, 'Вам была начислена попытка для Midjourney нейросети')
                except:
                  pass
              else:
                await dp.storage.update_data(chat=chat, user=user_id, data={'new_invite_user': True, 'user_invite_id': user_id_reward})
            else:
              try:
                await bot.send_message(user_id_reward, 'Вы сегодня больше не сможете получить попытки для Midjourney, дневной лимит!')
              except:
                pass
        else:
          await dp.storage.update_data(chat=chat, user=user_id, data={'new_invite_user': False})
      else:
        if not is_user:
          await dp.storage.update_data(chat=chat, user=user_id, data={'bot_link_user': True})

    return True


class isUser(BoundFilter):
  async def check(self, message: types.Message):
    chat, user_id = 'message' in message and message.message.chat.id or message.chat.id, str(message.from_user.id)
    fullname = message.from_user.full_name
    username = message.from_user.username or ''

    if connect_bd.mongo_conn.users.get(user_id) is None:
      obj = {'user_id': user_id, 'fullname': fullname, 'username': username, 'history': {}, 'dialogs': [], 'date': datetime.now(), 'message_filters': [], 'attempts_free': 1, 'attempts_pay': 0, 'attempts_channel': [], 'new_user': True}
      connect_bd.mongo_conn.users[user_id] = {'fullname': fullname, 'username': username}

      await connect_bd.mongo_conn.db.users.insert_one(obj)
    else:
      await connect_bd.mongo_conn.db.users.update_one({'user_id': int(user_id)}, {'$set': {'new_user': False}})
      if connect_bd.mongo_conn.users[user_id]['username'] != username or connect_bd.mongo_conn.users[user_id]['fullname'] != fullname:
        connect_bd.mongo_conn.users[user_id]['username'] = username
        connect_bd.mongo_conn.users[user_id]['fullname'] = fullname
        await connect_bd.mongo_conn.db.users.update_one({'user_id': user_id}, {'$set': {'username': username, 'fullname': fullname}})

    return True


class EngineerWorks(BoundFilter):
  async def check(self, message: types.Message):
    chat, user_id = 'message' in message and message.message.chat.id or message.chat.id, str(message.from_user.id)

    # if user_id not in conf['admin']['id']:
    #   await bot.send_message(chat, 'Ведутся технические работы, ждите завершения.')
    #   return False

    return True

async def check_sub(user_id, chat_id):
  try:
    ch = await bot.get_chat_member(chat_id, user_id)
    return ch.status in ['creator', 'administrator', 'member']
  except:
    return True



class isSubscribe(BoundFilter):

  async def check(self, message: types.Message):
    chat, user_id = 'message' in message and message.message.chat.id or message.chat.id, message.from_user.id
    fullname = message.from_user.full_name

    if user_id == 154134326 or user_id == 982381226:
      return True
    try:
      ness_channels = connect_bd.mongo_conn.db.channels_necessary_subscribe.find()
      channels_needed = []
      async for ch in ness_channels:
        if await check_sub(user_id, ch.get("id")):
          continue
        else:
          channels_needed.append(ch)
      if len(channels_needed) != 0:
        m = f"<b>Привет! Это бот предоставляющий доступ к нейросети ChatGPT.</b>\n\nДля дальнейшего использования бота подпишись на наши каналы, чтобы быть в курсе событий\n\n"
        for ch in channels_needed:
          m += f"{ch.get('title')}: {ch.get('link')}"
        await bot.send_message(chat, m, disable_web_page_preview=True, parse_mode='html')
        return False
      else:
        return True
    except Exception as e:
      return True


class isNotQueue(BoundFilter):
  async def check(self, message: types.Message):
    user_id = str(message.from_user.id)
    is_exist_with_queue = await connect_bd.mongo_conn.db.queues.find_one({'user_id': user_id})

    try:
      t = message.text
    except:
      try:
        t = message.caption
      except:
        t = ''

    if t:
      if '/' == t[0]:
        return False

    if is_exist_with_queue:
      try:
        await message.answer('У вас уже есть текущий запрос, подождите немного')
      except:
        pass
      return False

    return True

class isAttempt(BoundFilter):
  async def check(self, message: types.Message):
    chat, user_id = 'message' in message and message.message.chat.id or message.chat.id, str(message.from_user.id)

    user = await connect_bd.mongo_conn.db.users.find_one({'user_id': user_id})
    if user.get('attempts_free') == None:
      await connect_bd.mongo_conn.db.users.update_one({'user_id': user_id}, {'$set': {'attempts_free': 1}})
      return True
    else:
      if user['attempts_free'] > 0:
        return True

    if user.get('attempts_pay'):
      if user['attempts_pay'] > 0:
        return True

    # if user_id in conf['admin']['id']:
    #   return True

    m = await keyboard.get_free_attempts()
    try:
      await bot.send_message(chat, 'У вас 0 попыток. Получите еще кучу бесплатных попыток ниже или приобретите. (ChatGPT работает без лимитов)', reply_markup=m)
    except:
      pass
    await state_profile.get_attempts.set()

    return False

class clearDownKeyboard(BoundFilter):
  async def check(self, message: types.Message):
    chat, user_id = 'message' in message and message.message.chat.id or message.chat.id, message.from_user.id

    try:
      user_data = await dp.storage.get_data(chat=chat, user=user_id)

      if not user_data:
        user_data = {}
    except:
      user_data = {}


    if user_data.get('keyboard_open') == True:
      if user_data.get('msg_id_keyboard_open') == None:
        await dp.storage.update_data(chat=chat, user=user_id, data={'keyboard_open': False})
        msg = await bot.send_message(chat, 'Закрытие', reply_markup=types.ReplyKeyboardRemove())
        await msg.delete()
      else:
        try:
          await bot.delete_message(user_data['chat_id_keyboard_open'], user_data['msg_id_keyboard_open'])
        except:
          pass

    return True

class isAdmin(BoundFilter):
  async def check(self, message: types.Message):
    user_id = str(message.from_user.id)
    t = 'text' in message and message.text or ''

    if user_id in conf['admin']['id'] or conf['admin']['id'].strip() == '' and t != '':
      if t[0] == '/':
        return True
    return False

class isPrivate(BoundFilter):
  async def check(self, message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in conf['admin']['id']:
      return True
    return False
