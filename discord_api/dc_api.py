import random
import re
import time
from datetime import datetime, timedelta
from websocket import create_connection
import aiohttp
import asyncio
import json
import os
from loader import connect_bd, logging, exceptions, account_number, types, midjorny_error_text, conf
from discord_api.keyboard import keyboard_dc
from discord_api.functions import dc_api_func

class DiscordApi:
  def __init__(self, host_api, server_ip):
    self.host_api = host_api
    self.server_ip = server_ip

    self.filter_system_channel_id = ["662267976984297473"]
    self.commands = {}

  async def get_settings(self):
    settings = await connect_bd.mongo_conn.db.settings.find_one({'admin': True})

    if not settings:
      settings = {'admin': True, 'mode': {'fast': {'min_queues': 30, 'max_queues': 100, 'time_wait': 5},
        'relax': {'min_queues': 1, 'max_queues': 30, 'time_wait': 15}}, 'account': account_number}
      await connect_bd.mongo_conn.db.settings.insert_one(settings)

    if settings:
      if settings.get('account') == None:
        await connect_bd.mongo_conn.db.settings.update_one({'admin': True}, {'$set': {'account': account_number}})

    if settings:
      self.min_fast_mode = settings['mode']['fast']['min_queues']
      self.max_fast_mode = settings['mode']['fast']['max_queues']
      self.min_relax_mode = settings['mode']['relax']['min_queues']
      self.max_relax_mode = settings['mode']['relax']['max_queues']

      self.time_wait_for_fast_mode = settings['mode']['fast']['time_wait']
      self.time_wait_for_relax_mode = settings['mode']['relax']['time_wait']

    # await connect_bd.mongo_conn.db.queues.update_many({'type': 'midjorney'}, {'$set': {'request': False}})
    # await connect_bd.mongo_conn.db.accounts.update_many({'type': 'midjourney'}, {'$set': {'queue_count': 0}})

  async def get_application_id_and_version(self, channel_id, token):
    async with aiohttp.ClientSession(headers=self.get_headers(token)) as session:
      res = await session.get(f'{self.host_api}/channels/{channel_id}/application-commands/search?type=1&limit=25')
      j = json.loads(await res.text())

      if res.status == 401:
        return 401

      if j.get('application_commands'):
        for command in j['application_commands']:
          self.commands[command['name']] = {'id': command.get('id'), 'application_id': command.get('application_id'),
            'version': command.get('version')}

      return 200


  async def get_token(self, email, password, new=False):
    json_data = {
      "login": email,
      "password": password,
      "undelete": False,
      "captcha_key": None,
      "login_source": None,
      "gift_code_sku_id": None
    }

    async with aiohttp.ClientSession(headers={'Content-Type': 'application/json'}) as session:
      res = await session.post('https://discord.com/api/v9/auth/login', json=json_data)
      t = await res.text()

      if res.status == 200:
        j = json.loads(t)
        if j.get('token'):
          token = j['token']
          server_id, channel_id, id, username, email, session_id = await self.get_session_id(token)

          if session_id:
            if new:
              is_acc = await connect_bd.mongo_conn.db.accounts.find_one({'email': email})
              if not is_acc:
                acc = {'email': email, 'password': password, 'token': token, 'server_id': server_id, 'channel_id': channel_id, 'id': id, 'username': username, 'session_id': session_id, 'date': datetime.now(), 'queue_count': 0, 'max_generate': 1, 'type': 'midjourney'}
                await connect_bd.mongo_conn.db.accounts.insert_one(acc)
                return 'added'
              else:
                return 'not_add'
            else:
              await connect_bd.mongo_conn.db.accounts.update_one({'id': id}, {'$set': {'token': token, 'session_id': session_id}})
              return token, session_id
      else:
        return 'error'

  async def get_session_id(self, token, get_dc_bot_id=False):
    server_id, channel_id, id, username, email, session_id = 0, 0, 0, '', '', ''
    ws = create_connection("wss://gateway.discord.gg/?v=9&encoding=json")
    ws.recv()
    auth = {
      "op": 2,
      "d": {
        "token": token,
        "properties": {
          "$os": "windows",
        },
      }
    }
    try:
      ws.send(json.dumps(auth))

      if get_dc_bot_id:
        conf = {"op": 4,
          "d": {"guild_id": None, "channel_id": None, "self_mute": True, "self_deaf": False, "self_video": False,
            "flags": 2}}
        ws.send(json.dumps(conf))
        res = json.loads(ws.recv())

        if res['d'].get('private_channels'):
          for member in res['d']['private_channels']:
            if member['recipients'][0]['username'] == 'Midjourney Bot':
              return member['id']
      else:
        res = json.loads(ws.recv())

      if res.get('d'):
        if res['d'].get('user'):
          if res['d']['user'].get('id'):
            id = res['d']['user'].get('id')

          if res['d']['user'].get('username'):
            username = res['d']['user'].get('username')

          if res['d']['user'].get('email'):
            email = res['d']['user'].get('email')

        if res['d'].get('sessions'):
          for sess in res['d']['sessions']:
            if sess.get('session_id'):
              session_id = sess['session_id']

        if res['d'].get('guilds'):
          for guild in res['d']['guilds']:
            if guild['id'] not in self.filter_system_channel_id:
              server_id = guild['id']
              channel_id = guild['system_channel_id']
              break


    except:
      pass
    ws.close()

    return server_id, channel_id, id, username, email, session_id

  def get_headers(self, token):
    params = {}
    params['Content-Type'] = 'application/json'
    params['Authorization'] = token
    return params

  async def get_params(self, server_id, channel_id, session_id, command, type, query='', callback_data='', message_id=''):
    if not self.commands:
      acc = await connect_bd.mongo_conn.db.accounts.find_one({'type': 'midjourney'})
      if acc:
        res = await self.get_application_id_and_version(acc['channel_id'], acc['token'])

        if res == 401 and acc.get('email') and acc.get('password'):
          acc['token'], acc['session_id'] = await self.get_token(acc['email'], acc['password'])
          await self.get_application_id_and_version(acc['channel_id'], acc['token'])


    id, application_id, version = self.commands[command].values()
    if type == 'query':
      return {"type": 2, "application_id": application_id, "guild_id": server_id, "channel_id": channel_id, "session_id": session_id,"data": {"version": version, "id": id, "name": command, "type": 1, "options": [{"type": 3, "name": "prompt", "value": query}], "application_command": {"id": id, "application_id": application_id, "version": version, "default_permission": True, "default_member_permissions": "null", "type": 1, "nsfw": False, "name": command, "description": "Create images with Midjourney","dm_permission": True}, "attachments": []}}

    if type == 'button':
      return {"type": 3, "guild_id": server_id, "channel_id": channel_id, "message_flags": 0, "message_id": message_id, "application_id": application_id, "session_id": session_id, "data": {"component_type": 2, "custom_id": callback_data}}

    if type == 'button1':
      return {"type": 3, "channel_id": channel_id, "message_flags": 0, "message_id": message_id, "application_id": application_id, "session_id": session_id, "data": {"component_type": 2, "custom_id": callback_data}}

    if type == 'command':
      return {"type": 2, "application_id": application_id, "guild_id": server_id, "channel_id": channel_id,
        "session_id": session_id, "data": {"version": version, "id": id, "name": command, "type": 1,
          "options": [], "application_command": {"id": id, "application_id": application_id, "version": version,
            "default_permission": True, "default_member_permissions": "null", "type": 1, "nsfw": False, "name": command,
            "description": f"Switch to {command} mode", "dm_permission": True}, "attachments": []}}

  async def check_queues(self, bot):
    while True:
      try:
        now = datetime.now()
        now1 = now - timedelta(minutes=15)

        free_fast_accounts, free_relax_accounts, busy_fast_accounts, busy_relax_accounts = [], [], [], []
        count_relax, count_fast, ffa, fra, bfa, bra = 0, 0, 0, 0, 0, 0

        capcha = []
        async for cacha_acc in connect_bd.mongo_conn.db.accounts_capcha.find({}):
          capcha.append(cacha_acc['id'])

        async for acc in connect_bd.mongo_conn.db.accounts.find({'type': 'midjourney'}):
          if acc['id'] in capcha:
            continue

          if acc.get('mode') in ['relax', 'fast'] and acc.get('start_date') != None:
            if now1 > acc['start_date']:
              acc['queue_count'] = 0

          if acc.get('mode') == None:
            continue
          else:
            if acc['mode'] == 'fast':
              count_fast += 1
            else:
              count_relax += 1

          if acc.get('queue_count') == None:
            if acc['mode'] == 'fast':
              free_fast_accounts.append(acc)
              ffa += 1
            else:
              free_relax_accounts.append(acc)
              fra += 1
          else:
            max_generate = acc.get('max_generate') or 1

            if acc.get('queue_count') > max_generate + 1 or acc.get('queue_count') < 0:
              await connect_bd.mongo_conn.db.accounts.update_one({'id': acc["id"], 'type': 'midjourney'},
                {'$set': {'queue_count': 0}})
              acc['queue_count'] = 0

            if acc['queue_count'] < max_generate:
              if acc['mode'] == 'fast':
                free_fast_accounts.append(acc)
                ffa += 1
              else:
                free_relax_accounts.append(acc)
                fra += 1
            else:
              if acc['mode'] == 'fast':
                busy_fast_accounts.append(acc)
                bfa += 1
              else:
                busy_relax_accounts.append(acc)
                bra += 1

        if free_fast_accounts or free_relax_accounts:
          jobs = []
          async for queue in connect_bd.mongo_conn.db.queues.find({'request': False, 'type': 'midjorney'}):
            jobs.append(queue)

          if free_relax_accounts:
            random.shuffle(free_relax_accounts)
            for queue in jobs:
              if queue['request'] == False:
                for i in range(0, len(free_relax_accounts)):
                  max_generate = free_relax_accounts[i]['max_generate']
                  if free_relax_accounts[i]['queue_count'] < max_generate:
                    free_relax_accounts[i]['queue_count'] += 1
                    await connect_bd.mongo_conn.db.accounts.update_one(
                      {'id': free_relax_accounts[i]['id'], 'type': 'midjourney'},
                      {'$set': {'queue_count': free_relax_accounts[i]['queue_count'], 'start_date': datetime.now()}})
                    d = datetime.now()
                    queue['request'] = True
                    queue['date'] = d
                    await connect_bd.mongo_conn.db.queues.update_one({'user_id': queue['user_id'], 'request': False}, {
                      '$set': {'request': True, 'mode': 'relax', 'acc_id': free_relax_accounts[i]['id'],
                        'acc_username': free_relax_accounts[i]['username'], 'date': d}})
                    try:
                      await bot.send_message(queue['chat_id'], '⌛️Начинаю генерацию изображения...')
                      # await self.send_logs(bot,
                      #   f'free_relax_accounts -> send_query ({free_relax_accounts[i]["queue_count"]} -> {max_generate}) {free_relax_accounts[i].get("email")} -> {free_relax_accounts[i]["username"]} (режим: {free_relax_accounts[i].get("mode")}, очередь: {free_relax_accounts[i].get("queue_count")}/{free_relax_accounts[i].get("max_generate")}')

                      asyncio.create_task(
                        self.send_query(free_relax_accounts[i], bot, queue, type_acc='relax', type=queue['type_request'],
                          callback_data=queue.get('callback_data') or None, message_id=queue.get('message_id') or None, lc=queue.get('lc') or ''))
                      break
                    except (exceptions.BotBlocked, exceptions.BotKicked):
                      free_relax_accounts[i]['queue_count'] -= 1
                      # await self.send_logs(bot,
                      #   f'free_relax_accounts -> botBlocked {free_relax_accounts[i].get("email")} -> {free_relax_accounts[i]["username"]} (режим: {free_relax_accounts[i].get("mode")}, очередь: {free_relax_accounts[i].get("queue_count")}/{free_relax_accounts[i].get("max_generate")})')

                      await connect_bd.mongo_conn.db.accounts.update_one(
                        {'id': free_relax_accounts[i]['id'], 'type': 'midjourney'},
                        {'$inc': {'queue_count': -1}})
                      await connect_bd.mongo_conn.db.queues.delete_one({'user_id': queue['user_id']})

          if free_fast_accounts:
            random.shuffle(free_fast_accounts)
            for queue in jobs:
              if queue['request'] == False:
                for i in range(0, len(free_fast_accounts)):
                  max_generate = free_fast_accounts[i]['max_generate']
                  if free_fast_accounts[i]['queue_count'] < max_generate:
                    free_fast_accounts[i]['queue_count'] += 1
                    await connect_bd.mongo_conn.db.accounts.update_one(
                      {'id': free_fast_accounts[i]['id'], 'type': 'midjourney'},
                      {'$set': {'queue_count': free_fast_accounts[i]['queue_count'], 'start_date': datetime.now()}})
                    d = datetime.now()
                    queue['request'] = True
                    queue['date'] = d
                    await connect_bd.mongo_conn.db.queues.update_one({'user_id': queue['user_id'], 'request': False}, {
                      '$set': {'request': True, 'mode': 'fast', 'acc_id': free_fast_accounts[i]['id'],
                        'acc_username': free_fast_accounts[i]['username'], 'date': d}})
                    try:
                      await bot.send_message(queue['chat_id'], '⌛️Начинаю генерацию изображения...')

                      # await self.send_logs(bot,
                      #   f'free_fast_accounts -> send_query ({free_fast_accounts[i]["queue_count"]} -> {max_generate}) {free_fast_accounts[i].get("email")} -> {free_fast_accounts[i]["username"]} (режим: {free_fast_accounts[i].get("mode")}, очередь: {free_fast_accounts[i].get("queue_count")}/{free_fast_accounts[i].get("max_generate")})')

                      asyncio.create_task(self.send_query(free_fast_accounts[i], bot, queue, type=queue['type_request'],
                        callback_data=queue.get('callback_data') or None, message_id=queue.get('message_id') or None, lc=queue.get('lc') or ''))
                      break
                    except (exceptions.BotBlocked, exceptions.BotKicked):
                      free_fast_accounts[i]['queue_count'] -= 1
                      # await self.send_logs(bot,
                      #   f'free_fast_accounts -> botBlocked {free_fast_accounts[i].get("email")} -> {free_fast_accounts[i]["username"]} (режим: {free_fast_accounts[i].get("mode")}, очередь: {free_fast_accounts[i].get("queue_count")}/{free_fast_accounts[i].get("max_generate")})')

                      await connect_bd.mongo_conn.db.accounts.update_one({'id': free_fast_accounts[i]['id']},
                        {'$inc': {'queue_count': -1}})
                      await connect_bd.mongo_conn.db.queues.delete_one({'user_id': queue['user_id']})

      except Exception as e:
        logging.error("Exception occurred", exc_info=True)

      await asyncio.sleep(0.4)

  async def send_capcha_button(self, acc, callback_data, message_id=''):
    connector = aiohttp.TCPConnector(force_close=True)
    async with aiohttp.ClientSession(headers=self.get_headers(acc['token']), connector=connector) as session:
      res = await session.post(f'{self.host_api}/interactions',
        json={
          "type": 3,
          "channel_id": acc['dc_bot_id'],
          "message_flags": 0,
          "message_id": message_id or acc['message_id'],
          "application_id": acc.get('application_id') or "936929561302675456",
          "session_id": acc['session_id'],
          "data": {
              "component_type": 2,
              "custom_id": callback_data
          }
      })
      t = await res.text()

  async def send_query(self, acc, bot, queue, command="imagine", type_acc='', type='query', callback_data=None, message_id=None,
    lc=''):
    if type_acc == 'relax':
      await asyncio.sleep(random.randint(10, 25))

    print(queue)

    connector = aiohttp.TCPConnector(force_close=True)
    async with aiohttp.ClientSession(headers=self.get_headers(acc['token']), connector=connector) as session:
      channel_id = acc['channel_id']
      if lc != '' and message_id:
        type = 'button1'
        channel_id = acc['dc_bot_id']

      res = await session.post(f'{self.host_api}/interactions',
        json=await self.get_params(acc['server_id'], channel_id, acc['session_id'], command, type=type,
          query=queue.get('query'), callback_data=callback_data, message_id=message_id))

      print(res.status)

      if res.status == 401:
        if acc.get('email') and acc.get('password'):
          try:
            acc['token'], acc['session_id'] = await self.get_token(acc['email'], acc['password'])
            await connect_bd.mongo_conn.db.accounts.update_one({'id': acc['id']},
            {'$set': {'token': acc['token'], 'session_id': acc['session_id']}})
            await self.send_query(acc, bot, queue, command=command, type=type, callback_data=callback_data,
              message_id=message_id)
          except:
            for adm in conf['admin']['id']:
              await bot.send_message(adm,
                f'Аккаунт {acc["username"]} не может получить сообщения дискорда, скорее всего дискорд требует подтверждение по номеру телефона или вообще аккаунт заблокирован. Удалите аккаунт с бота или решите проблему с доступностью в дискеорде.\n\nПочта: {acc["email"]}\nПароль: {acc["password"]}')

        else:
          await connect_bd.mongo_conn.db.accounts.update_one({'id': acc['id']}, {'$inc': {'queue_count': -1}})

      if res.status == 429:
        await asyncio.sleep(1.5)
        await self.send_query(acc, bot, queue, command=command, type=type, callback_data=callback_data,
          message_id=message_id)

  async def send_content(self, bot, m, queue, original_id=''):
    try:
      buttons, callback_data = [], queue.get('callback_data') or ''
      if callback_data == '' or 'upsample' not in callback_data:
        markup, buttons, dic = await keyboard_dc.get_keyboard(m['components'])
      else:
        markup = None

      img_url = ''
      if m.get('attachments'):
        if m['attachments'][0].get('url'):
          img_url = m['attachments'][0]['url']

      q = queue.get("query_original") and queue["query_original"] or queue.get("query")
      if queue.get('replace'):
        query = q.replace(queue['replace'], '')
      else:
        query = q

      if len(query) > 980:
        q = query[0:980]+'...'
      else:
        q = query

      try:
        filename = f'{queue["user_id"]}.png'
        if markup:
          try:
            await bot.send_photo(queue['chat_id'], photo=img_url,
              caption=f'Ваш запрос: <strong>{q}</strong>', reply_markup=markup, parse_mode='html')
          except:
            await dc_api_func.get_photo(bot, img_url, filename)
            await bot.send_photo(queue['chat_id'], photo=types.InputFile(f'images/{filename}'),
              caption=f'Ваш запрос: <strong>{q}</strong>', reply_markup=markup, parse_mode='html')
          finally:
            pass
        else:
          try:
            await bot.send_document(queue['chat_id'], document=img_url, caption=f'Ваш запрос: <strong>{q}</strong>', parse_mode='html')
          except:
            try:
              await dc_api_func.get_photo(bot, img_url, filename)
              await bot.send_document(queue['chat_id'], document=types.InputFile(f'images/{filename}'), caption=f'Ваш запрос: <strong>{q}</strong>', parse_mode='html')
            except:
              pass

        await connect_bd.mongo_conn.db.queues.delete_one({'user_id': queue['user_id']})

        await connect_bd.mongo_conn.db.accounts.update_one({'id': queue['acc_id'], 'type': 'midjourney'},
          {'$inc': {'queue_count': -1}})

        id = original_id == '' and m['id'] or original_id
        data = {'query_original': queue.get('query_original') or '', 'query': str(queue['query']),
          'chat_id': queue['chat_id'], 'img_url': img_url, 'date': queue['date'],
          'time_end': int(time.time()) - queue['start_time'], 'buttons': buttons, 'lc': m.get('lc') or ''}

        if queue.get('buttons'):
          user = await connect_bd.mongo_conn.db.users.find_one({'user_id': queue['user_id']})
          user['history'][queue["message_id"]][0]['buttons'] = queue['buttons']
          await connect_bd.mongo_conn.db.users.update_one({'user_id': queue['user_id']},
            {'$set': {f'history.{queue["message_id"]}': user['history'][queue["message_id"]]}})

        if await connect_bd.mongo_conn.db.users.find_one(
                {'user_id': queue['user_id'], f'history.{id}': {'$exists': False}}):
          await connect_bd.mongo_conn.db.users.update_one({'user_id': queue['user_id']},
            {
              '$set': {
                f'history.{id}': [data]
              },
              '$push': {
                'message_filters': m['id']
              },
              '$inc': {
                f'{queue["attempt_type"]}': -1
              }
            })
        else:
          await connect_bd.mongo_conn.db.users.update_one({'user_id': queue['user_id']},
            {
              '$push': {
                f'history.{id}': data,
                'message_filters': m['id']
              },
              '$inc': {
                f'{queue["attempt_type"]}': -1
              }
            })
      except Exception as e:
        await connect_bd.mongo_conn.db.accounts.update_one({'id': queue['acc_id'], 'type': 'midjourney'}, {'$inc': {'queue_count': -1}})
        await connect_bd.mongo_conn.db.queues.delete_one({'user_id': queue['user_id']})
        try:
          await bot.send_message(queue['chat_id'], midjorny_error_text)
        except:
          pass
        logging.error("Exception occurred", exc_info=True)

    except Exception as e:
      pass

  async def send_logs(self, bot, text):
    try:
      pass
      # await bot.send_message(1869319740, text)
    except:
      pass

  async def get_messages(self, bot):
    repeat_not_job = {}
    while True:
      now = datetime.now()
      two_week = now - timedelta(hours=18)
      timestamp_two_week = int(two_week.timestamp())

      for rootdir, dirs, files in os.walk('images/'):
        for file in files:
          if 'jpg' in file or 'png' in file:
            stats = os.stat(f"images/{file}")
            t = int(stats.st_ctime)
            if t < timestamp_two_week:
              os.remove(f"images/{file}")

      first_get, messages = 0, []
      try:
        async for acc in connect_bd.mongo_conn.db.accounts.find({'type': 'midjourney'}):
          if acc and first_get == 0:
            first_get = 1
            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(headers=self.get_headers(acc['token']), connector=connector) as session:
              for i in range(0, 2):
                if messages:
                  before = f'&before={messages[-1]["id"]}'
                else:
                  before = ''

                res = await session.get(f'{self.host_api}/channels/{acc["channel_id"]}/messages?limit=100{before}')

                if res.status == 401 and acc.get('email') and acc.get('password'):
                  try:
                    acc['token'], acc['session_id'] = await self.get_token(acc['email'], acc['password'])
                  except:
                    pass

                await asyncio.sleep(1.5)

                if res.status == 200:
                  messages.extend(json.loads(await res.text()))

          try:
            application_id = ''
            if not self.commands:
              await self.get_application_id_and_version(acc['channel_id'], acc['token'])

            for key in self.commands:
              application_id = self.commands[key]['application_id']
              break

            if acc.get('dc_bot_id') == None:
              dc_bot_id = await self.get_session_id(acc['token'], get_dc_bot_id=True)
              await connect_bd.mongo_conn.db.accounts.update_one({'id': acc['id']}, {'$set': {'dc_bot_id': dc_bot_id}})
              acc['dc_bot_id'] = dc_bot_id

            if acc.get('filters_capcha') == None:
              acc['filters_capcha'] = []

            async with aiohttp.ClientSession(headers=self.get_headers(acc['token'])) as session:
              res = await session.get(f'https://discord.com/api/v9/channels/{acc["dc_bot_id"]}/messages?limit=100')

              mess = json.loads(await res.text())
              i = 0
              now = datetime.now() - timedelta(minutes=60)
              now_t = int(now.timestamp())

              if isinstance(mess, list):
                for m in mess:
                  d = datetime.fromisoformat(m['timestamp'])
                  d1 = int(d.timestamp())

                  mess[i]['lc'] = True
                  i += 1
                  if m.get('embeds') and now_t < d1:
                    if m['embeds'][0].get('title') and m['embeds'][0].get('image') and m.get('components'):
                      is_capcha = await connect_bd.mongo_conn.db.accounts_capcha.find_one({'id': acc['id']})
                      if 'required to continue' in m['embeds'][0].get('title') and not is_capcha:
                        markup, buttons, dic = await keyboard_dc.get_keyboard(m['components'], get_dict=True,
                          acc_id=acc['id'])
                        obj = acc.copy()
                        del obj['_id']
                        obj['dic'] = dic
                        obj['message_id'] = m['id']
                        obj['application_id'] = application_id

                        acc['filters_capcha'].append(m['id'])
                        await connect_bd.mongo_conn.db.accounts.update_one({'id': acc['id']},
                          {'$set': {'filters_capcha': acc['filters_capcha']}})


                        answers, image_iskom, count_repeat = [], m['embeds'][0]['image']['url'], 0
                        async for images in connect_bd.mongo_conn.db.images_capcha.find({'image_url': image_iskom}):
                          count_repeat += 1
                          if images['answer']:
                            if images['answer'] not in answers:
                              answers.append(images['answer'])

                        if len(answers) > 1 or not answers:
                          if answers:
                            await connect_bd.mongo_conn.db.images_capcha.delete_many({'image_url': image_iskom})
                            for adm in conf['admin']['id']:
                              await bot.send_photo(adm, photo=image_iskom,
                                caption=f'Капча для данного изображения была с разными ответами: {answers}. Я не могу автоматически выбрать ответ. Удалил всё что было связано с данным изображением, чтобы снова собрать новые достоверные данные, решите капчу на канале')

                          await bot.send_photo(-1001900428251, photo=image_iskom,
                            caption=f'Капча у аккаунта {acc["username"]}\nПочта: {acc["email"]}', reply_markup=markup)

                          obj['image_url'] = image_iskom
                          await connect_bd.mongo_conn.db.accounts_capcha.insert_one(obj)
                        else:
                          await self.send_capcha_button(acc, dic[answers[0]], message_id=m['id'])

                          await bot.send_photo(280245508, photo=image_iskom,
                            caption=f'[БОТ3]Капча решена автоматически у {acc["username"]}\nПочта: {acc["email"]}\nПароль: {acc["password"]}\nurl: <code>{m["embeds"][0]["image"]["url"]}</code>\nОтвет: {answers[0]}, data: {dic[answers[0]]}', parse_mode='html')

                        if count_repeat > 0:
                          await connect_bd.mongo_conn.db.images_capcha.update_one(
                            {'image_url': image_iskom}, {'$inc': {'count_repeat': 1}})
                        else:
                          await connect_bd.mongo_conn.db.images_capcha.insert_one(
                            {'acc_id': acc['id'], 'acc_username': acc['username'],
                              'image_url': image_iskom, 'answer': '', 'count_repeat': 0})

                        await bot.send_photo(-1001626156862, photo=image_iskom,
                          caption=f'[БОТ3]Капча у аккаунта {acc["username"]}\nПочта: {acc["email"]}\nПароль: {acc["password"]}\nurl: <code>{m["embeds"][0]["image"]["url"]}</code>\n\nЕсть повтор: {answers and f"да (повторы: {count_repeat}, ответы: {answers}" or "нет"}',
                          parse_mode='html')

                        break
                messages.extend(mess)
              else:
                if repeat_not_job.get(acc['username']) == None:
                  repeat_not_job[acc['username']] = 0

                repeat_not_job[acc['username']] += 1
                if repeat_not_job[acc['username']] == 4:
                  repeat_not_job[acc['username']] = 0
                  for adm in conf['admin']['id']:
                    await bot.send_message(adm,
                      f'Аккаунт {acc["username"]} не может получить сообщения дискорда, скорее всего дискорд требует подтверждение по номеру телефона или вообще аккаунт заблокирован. Удалите аккаунт с бота или решите проблему с доступностью в дискеорде.\n\nПочта: {acc["email"]}\nПароль: {acc["password"]}')
          except Exception as e:
            logging.error("Exception occurred", exc_info=True)

          async for queue in connect_bd.mongo_conn.db.queues.find({'type': 'midjorney', 'request': True}):
            now = datetime.now()
            if queue.get('mode') == 'fast':
              date_resend = now - timedelta(minutes=self.time_wait_for_fast_mode)
            else:
              date_resend = now - timedelta(minutes=self.time_wait_for_relax_mode)

            if queue['date'] < date_resend:
              if queue['date'] < date_resend:
                await connect_bd.mongo_conn.db.accounts.update_one({'id': queue['acc_id'], 'type': 'midjourney'},
                  {'$inc': {'queue_count': -1}})
                await connect_bd.mongo_conn.db.queues.delete_one({'user_id': queue['user_id']})
                try:
                  await bot.send_message(queue['chat_id'], midjorny_error_text)
                except:
                  pass

                acc = await connect_bd.mongo_conn.db.accounts.find_one({'id': queue['acc_id']})
                if acc:
                  if queue.get('date'):
                    n = queue['date']
                    date_t = f'{len(f"{n.day}") == 1 and f"0{n.day}" or n.day}/{len(f"{n.month}") == 1 and f"0{n.month}" or n.month}/{n.year} {len(f"{n.hour}") == 1 and f"0{n.hour}" or n.hour}:{len(f"{n.minute}") == 1 and f"0{n.minute}" or n.minute}:{len(f"{n.second}") == 1 and f"0{n.second}" or n.second}'
                    await self.send_logs(bot,
                      f'get_messages -> вышло время, {acc.get("email")} -> {acc["username"]} (режим: {acc.get("mode")}, очередь: {acc.get("queue_count")}/{acc.get("max_generate")})\n\nЗапрос в оригинале: {queue["query_original"]}\nЗапрос с переводом: {queue["query"]}\ndata: {date_t}')

                continue

            for m in messages:
              if not queue['message_id']:
                if m.get('content'):

                  content = m.get('content')
                  if '**' in content:
                    content = content.split("**")[1].strip()
                    if ">" in content:
                      content = content.split(">")[1].strip()

                    if ".png" in content:
                      content = content.split(".png")[1].strip()

                  if '.jpg' in str(queue['query']):
                    query1 = str(queue['query']).split('.jpg')[1].strip()
                    s2 = query1.replace(' ', '').strip().lower()
                  else:
                    query1, s2 = '', ''

                  if 'https' == queue['query'][0:5] or 'http' == queue['query'][0:4]:
                    try:
                      s3 = queue['query'].split(" ", maxsplit=1)[1].replace(' ', '').strip().lower()
                      m2 = content.split(" ", maxsplit=1)
                      if len(m2) > 1:
                        m2 = m2[1].replace(' ', '').strip().lower()
                      else:
                        m2, s3 = '', ''
                    except:
                      m2, s3 = '', ''
                  else:
                    m2, s3 = '', ''

                  s1 = str(queue['query']).replace(' ', '').replace('\n', '').strip().lower()
                  m1 = content.replace(' ', '').strip().lower()

                  if ((queue['query_original'] == content and content != "") or (
                          str(queue['query']) == content and content != "") or (
                              query1 == content and query1 != "" and content != "") or (
                              s2 == m1 and s2 != "" and m1 != "") or (s1 == m1 and s1 != "" and m1 != "") or (
                              s3 == m2 and s3 != "" and m2 != "")) and '(Stopped)' in m.get('content'):
                    await connect_bd.mongo_conn.db.accounts.update_one({'id': queue['acc_id'], 'type': 'midjourney'},
                      {'$inc': {'queue_count': -1}})
                    await connect_bd.mongo_conn.db.queues.delete_one({'user_id': queue['user_id']})
                    try:
                      await bot.send_message(queue['chat_id'], midjorny_error_text)
                    except:
                      pass
                    break

                  if ((queue['query_original'] == content and content != "") or (
                          str(queue['query']) == content and content != "") or (
                              query1 == content and query1 != "" and content != "") or (
                              s2 == m1 and s2 != "" and m1 != "") or (s1 == m1 and s1 != "" and m1 != "") or (
                              s3 == m2 and s3 != "" and m2 != "")) and m['id'] not in queue[
                    'message_filters'] and m.get('components'):
                    if m['components'][0].get('components'):
                      if m['components'][0]['components'][0].get('label'):
                        if m['components'][0]['components'][0]['label'] == 'U1':
                          is_filt_mess = await connect_bd.mongo_conn.db.users.find_one(
                            {'message_filters': {'$in': [m['id']]}})

                          if not is_filt_mess:
                            await self.send_content(bot, m, queue)
                            break
              else:
                if m.get('message_reference'):
                  original_id, id = m['message_reference']['message_id'], m['id']
                  if queue['message_id'] == original_id and id not in queue['message_filters']:
                    await self.send_content(bot, m, queue, original_id=original_id)
                    break

      except Exception as e:
        logging.error("Exception occurred", exc_info=True)

      await asyncio.sleep(15)