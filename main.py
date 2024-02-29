
async def start(dp):
  import asyncio
  import filters
  from loader import other_commands, types, bot, conf, connect_bd, logging, dc_api, gpt_api, keyboard, youmoney_web, dc_api_func

  asyncio.create_task(youmoney_web.web_hooks())
  asyncio.create_task(dc_api_func.init_send_attempts())

  bot_info = await bot.get_me()
  bot['username'] = bot_info.username
  print(bot_info.username)

  other_commands.bot = bot
  other_commands.dp = dp
  other_commands.logging = logging
  other_commands.types = types

  filters.setup(dp)
  await connect_bd.mongo_conn.connect_server()

  rep = {}
  async for img in connect_bd.mongo_conn.db.images_capcha.find():
    if rep.get(img['image_url']) == None:
      rep[img['image_url']] = img
    else:
      await connect_bd.mongo_conn.db.images_capcha.delete_one({'image_url': img['image_url']})

  await gpt_api.check_accounts()
  await dc_api.get_settings()
  asyncio.create_task(dc_api.check_queues(bot))
  asyncio.create_task(dc_api.get_messages(bot))

  asyncio.create_task(gpt_api.check_gpt_queues(bot))

  await other_commands.set_commands()
  if conf['admin']['id']:
    await other_commands.set_admin_commands(conf['admin']['id'])

if __name__ == '__main__':
  from aiogram import executor
  from handlers import dp

  executor.start_polling(dp, on_startup=start, skip_updates=True)