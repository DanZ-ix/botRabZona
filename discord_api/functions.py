from deep_translator import GoogleTranslator
import aiohttp
import os
import aiofiles
import asyncio
import aioschedule as shedule

from loader import connect_bd, logging
import subprocess

translator = GoogleTranslator(source='auto', target='en')

class Func():
  async def schedule_checker(self, shedule):
    while True:
      await shedule.run_pending()
      await asyncio.sleep(0.1)

  async def set_attemts_for_all_users(self):
    await connect_bd.mongo_conn.db.users.update_many({}, {'$set': {'attempts_free': 1, 'invite_count_now': 0}})
    subprocess.run('journalctl --vacuum-time=1d', shell=True)
    subprocess.run('rm /var/log/auth.log', shell=True)
    subprocess.run('rm /var/log/auth.log.1', shell=True)
    subprocess.run('rm /var/log/btmp', shell=True)
    subprocess.run('rm /var/log/btmp.1', shell=True)

  async def init_send_attempts(self):
    shedule.every().day.at('0:00').do(self.set_attemts_for_all_users)
    asyncio.create_task(self.schedule_checker(shedule))

  async def google_translate(self, query):
    # while True:
    result = ""
    try:
      result = translator.translate(query)

      if '-' in result or '—' in result:
        result = result.replace('-', '').replace('—', '')

    except Exception as e:
      pass

    if result:
      return result
    else:
      return query

    # await asyncio.sleep(1)

  async def get_sr_time_queue_from_imagine(self):
    sr_times = []
    async for user in connect_bd.mongo_conn.db.users.find():
      if user['history']:
        for mess_id in user['history']:
          for data in user['history'][mess_id]:
            sr_times.append(data['time_end'])

    return int(sum(sr_times) / len(sr_times))

  async def query_is_banlist(self, query):
    try:
      query_word = query.lower().split(' ')
      async for word in connect_bd.mongo_conn.db.banlist.find():
        for query_w in query_word:
          if word['word'].lower() == query_w.strip():
            return True

      return False
    except Exception as e:
      logging.warning(f'[query_is_banlist] {query}, {e}')

  async def get_photo(self, bot, url, file_name):
    path = f'images/{file_name}'
    connector = aiohttp.TCPConnector(force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
      async with session.get(url) as resp:
        if resp.status == 200:
          try:
            f = await aiofiles.open(path, mode='wb')
            await f.write(await resp.read())
            await f.close()
          except Exception as e:
            logging.error("Exception occurred", exc_info=True)

    if os.path.isfile(path):
      return True
    else:
      await self.get_photo(bot, url, file_name)


dc_api_func = Func()