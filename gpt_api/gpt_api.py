import random
import time
from datetime import datetime, timedelta
import aiohttp
import asyncio
import json

from loader import connect_bd, conf, keyboard, logging, exceptions
from gpt_api.keyboard import keyboard_gpt

time_start = datetime.now()

class gptApi:
  def __init__(self, host, dialog_max_tokens):
    self.host = host
    self.c = 0
    self.dialog_max_tokens = dialog_max_tokens
    self.limit_message_tokens = 4095


  async def check_accounts(self):
    await connect_bd.mongo_conn.db.queues.update_many({'type': 'gpt'}, {'$set': {'status': 'wait'}})
    # await connect_bd.mongo_conn.db.accounts.update_many({'type': 'gpt'}, {'$set': {'queue_count': 0}})

  async def get_account(self) -> dict:
    acc = await connect_bd.mongo_conn.db.accounts.find_one({'type': 'gpt', 'queue_count': 0})
    if acc:
      await connect_bd.mongo_conn.db.accounts.update_one({'token': acc['token'], 'type': 'gpt'}, {'$set': {'queue_count': 1}})
      return acc
    else:
      return {}


  def get_headers(self, token):
    params = {}
    params['Content-Type'] = 'application/json'
    params['Authorization'] = f'Bearer {token}'
    return params

  def get_params(self, dialogs, query):
    params = {}

    if dialogs:
      params['model'] = 'gpt-3.5-turbo'
      params['messages'] = dialogs
    else:
      params['model'] = 'text-davinci-003'
      params['prompt'] = query
      params['max_tokens'] = 512
      params['temperature'] = 0.8

    return params

  async def get_grants(self, token, full_dict=False):
    async with aiohttp.ClientSession(headers=self.get_headers(token)) as session:
      res = await session.get('https://api.openai.com/dashboard/billing/credit_grants')
      if res.status == 200:
        try:
          t = await res.text()
          if full_dict:
            return t

          j = json.loads(t)

          if j.get('total_available'):
            await session.close()
            return float(j["total_available"])
          else:
            await session.close()
            return 0.0
        except:
          await session.close()
          return 0.0
      else:
        await session.close()
        return False

  async def send_query(self, acc, bot, data, type='chat/completions'):
    try:
      print('Запрос начат', acc, data)
      async with aiohttp.ClientSession(headers=self.get_headers(acc['token']), timeout=aiohttp.ClientTimeout(total=900)) as session:
        res = await session.post(f'{self.host}/{type}', json=self.get_params(data['dialogs'], data['query']))
        t = await res.text()
        try:
          json_data = json.loads(t)

          print(res.status)

          if json_data.get('error'):
            if json_data['error'].get('message'):
              if 'maximum context length' in json_data['error']['message']:
                await connect_bd.mongo_conn.db.users.update_one({'user_id': data['user_id']}, {'$set': {'dialogs': []}})
                await connect_bd.mongo_conn.db.queues.delete_one({'user_id': data['user_id']})
                return f'Был достигнут лимит, Слишком длинный запрос, возможно вы вели диалог. На данной модели максимальная длина 4097 символов', ''

          if res.status == 200:
            await connect_bd.mongo_conn.db.accounts.update_one({'token': acc['token'], 'type': 'gpt'}, {'$set': {'queue_count': 0}})
            if json_data.get('choices'):
              if isinstance(json_data['choices'], list):
                if not data['dialogs']:
                  answer = random.choice(json_data['choices'])
                  await session.close()
                  return answer['text'], ''
                else:
                  answer = random.choice(json_data['choices'])
                  await session.close()
                  return answer['message']['content'], ''

          else:
            if res.status != 429:
              await session.close()
              if res.status == 500:
                return False, 'update'

          if res.status == 401:
            if acc['token'] == '':
              await connect_bd.mongo_conn.db.accounts.delete_many({'token': '', 'type': 'gpt'})

              count_queues = await connect_bd.mongo_conn.db.accounts.count_documents({'type': 'gpt'})
              for id in conf['admin']['id']:
                await bot.send_message(id,
                  f'Были удалены пустые токены. Осталось: <strong>{count_queues}</strong>',
                  parse_mode='html')

            if json_data.get('error'):
              if json_data['error']['code'] == 'invalid_api_key':
                await connect_bd.mongo_conn.db.accounts.delete_one({'token': acc['token'], 'type': 'gpt'})

                count_queues = await connect_bd.mongo_conn.db.accounts.count_documents({'type': 'gpt'})
                for id in conf['admin']['id']:
                  await bot.send_message(id, f'Токен <code>{acc["token"]}</code> невалидный. Осталось: <strong>{count_queues}</strong>',
                    parse_mode='html')

            return False, 'update'

          if res.status == 524:
            if json_data.get('error'):
              if json_data['error']['code'] == 524:
                await bot.send_message(data['chat_id'], f'К сожалению, Ваш запрос не был выполнен. Попробуйте спросить что-то другое.')
                await connect_bd.mongo_conn.db.queues.delete_one({'user_id': data['user_id']})
                return False, ''

          if res.status == 429:
            if json_data.get('error'):
              if json_data['error']['type'] != 'server_error' and 'quota' in json_data['error']['type']:
                await connect_bd.mongo_conn.db.accounts.delete_one({'token': acc['token'], 'type': 'gpt'})
                await session.close()
                count_queues = await connect_bd.mongo_conn.db.accounts.count_documents({'type': 'gpt'})
                for id in conf['admin']['id']:
                  await bot.send_message(id, f'Токен <code>{acc["token"]}</code> израсходован. Осталось: <strong>{count_queues}</strong>', parse_mode='html')
                return False, 'update'
              else:
                await session.close()
                return False, 'update'

        except Exception as e:
          return False, 'update'
    except asyncio.TimeoutError as e:
      logging.error("Exception occurred", exc_info=True)
      return False, 'update'

  async def get_answer_repeat(self, acc, bot, queue):
    try:
      queue['dialogs'] = [d for d in queue['dialogs'] if (d['role'] == 'user' or isinstance(d['content'], str))]
      # logging.warning(f"Запрос юзера\n\n{queue}")
      # await bot.send_message(280245508, f'{queue["date"]}, {queue["query"]}')

      if queue.get('not_message') == None:
        try:
          await bot.delete_message(queue['chat_id'], queue['message_id'])
        except:
          pass

        if queue.get('repeat') == 0 or queue.get('repeat') == None:
          try:
            msg = await bot.send_message(queue['chat_id'], '⌛️ Подготовка ответа...')
            await connect_bd.mongo_conn.db.queues.update_one({'user_id': queue['user_id']},
              {'$set': {'message_id1': msg.message_id}})
          except (exceptions.BotBlocked, exceptions.BotKicked):
            await connect_bd.mongo_conn.db.queues.delete_one({'user_id': queue['user_id']})
            await connect_bd.mongo_conn.db.accounts.update_one({'token': acc['token'], 'type': 'gpt'},
              {'$set': {'queue_count': 0}})
            return False

      answer, trigger = await self.send_query(acc, bot, queue)
      if answer:
        queue['dialogs'].append({'role': 'assistant', 'content': answer})
        token_count = 0
        for d in queue['dialogs']:
          if d.get('content'):
            token_count += len(d['content'])

        user = await connect_bd.mongo_conn.db.users.find_one({'user_id': queue['user_id']})
        set_dialog = user.get('set_dialog') and user['set_dialog'] or False
        if token_count < self.dialog_max_tokens:
          await connect_bd.mongo_conn.db.users.update_one({'user_id': queue['user_id']}, {'$set': {'dialogs': queue['dialogs']}})
        else:
          await connect_bd.mongo_conn.db.users.update_one({'user_id': queue['user_id']}, {'$set': {'dialogs': [], 'set_dialog': False}})
          set_dialog = False

        m = await keyboard.set_dialog(set_dialog)
        edit = True

        q = await connect_bd.mongo_conn.db.queues.find_one({'user_id': queue['user_id'], 'type': 'gpt'})
        while answer != '':
          t = answer[0:self.limit_message_tokens]
          answer = answer.replace(t, '')
          try:
            if queue.get('not_message') == None:
              if not edit:
                await bot.send_message(queue['chat_id'], t, reply_markup=m)
              else:
                edit = False
                await bot.edit_message_text(t, queue['chat_id'], q['message_id1'], reply_markup=m)
            else:
              await bot.send_message(queue['chat_id'], t, reply_to_message_id=queue['message_id'])

          except:
            pass

          await asyncio.sleep(1)

        await connect_bd.mongo_conn.db.queues.delete_one({'user_id': queue['user_id']})
        return True
      else:
        await connect_bd.mongo_conn.db.accounts.update_one({'token': acc['token'], 'type': 'gpt'}, {'$set': {'queue_count': 0}})

        if trigger == 'update':
          if queue.get('repeat') != None:
            await connect_bd.mongo_conn.db.queues.update_one({'user_id': queue['user_id'], 'type': 'gpt'},
              {'$set': {'status': 'wait'}, '$inc': {'repeat': 1}})
          else:
            await connect_bd.mongo_conn.db.queues.update_one({'user_id': queue['user_id'], 'type': 'gpt'},
              {'$set': {'status': 'wait', 'repeat': 1}})


    except (exceptions.BotKicked, exceptions.BotBlocked):
      logging.error("Exception occurred", exc_info=True)
      await connect_bd.mongo_conn.db.queues.delete_one({'user_id': queue['user_id']})
      acc['queue_count'] = 0
      await connect_bd.mongo_conn.db.accounts.update_one({'token': acc['token'], 'type': 'gpt'}, {'$set': {'queue_count': 0}})
    except Exception as e:
      logging.error("Exception occurred", exc_info=True)

  async def check_gpt_queues(self, bot):
    while True:
      try:
        now = datetime.now()
        date_resend = now - timedelta(minutes=8)

        async for acc in connect_bd.mongo_conn.db.accounts.find({'type': 'gpt'}):
          if acc['date'] < date_resend and acc['queue_count'] == 1:
            await connect_bd.mongo_conn.db.accounts.update_one({'token': acc['token'], 'type': 'gpt'}, {'$set': {'queue_count': 0}})

        async for queue in connect_bd.mongo_conn.db.queues.find({'type': 'gpt'}):
          try:
            if queue['date'] < date_resend and queue['status'] == 'process':
              await connect_bd.mongo_conn.db.queues.delete_one({'type': 'gpt', 'user_id': queue['user_id']})
              await connect_bd.mongo_conn.db.accounts.update_one({'token': queue['token'], 'type': 'gpt'}, {'$set': {'queue_count': 0}})
              await bot.send_message(queue['chat_id'], 'К сожалению, Ваш запрос не был выполнен. Попробуйте спросить что-то другое.')
              continue

            if queue['status'] == 'wait':
              acc = await self.get_account()
              if acc:
                await connect_bd.mongo_conn.db.queues.update_one({'user_id': queue['user_id'], 'type': 'gpt'}, {'$set': {'token': acc['token'], 'status': 'process', 'date': datetime.now()}})
                asyncio.create_task(self.get_answer_repeat(acc, bot, queue))
          except Exception as e:
            logging.error("Exception occurred", exc_info=True)

      except Exception as e:
        logging.error("Exception occurred", exc_info=True)
      await asyncio.sleep(1)
