from loader import dp, types, connect_bd, imagine_state, queues_state, dc_api, FSMContext, keyboard, bot, bot_token, \
  server_ip, start_state, rate_limit, logging
from filters.filter_commands import isPrivate


@dp.callback_query_handler(lambda msg: 'capcha' in msg.data, state="*")
async def callback_data(message: types.CallbackQuery, state: FSMContext):
  chat, message_id = message.message.chat.id, message.message.message_id
  user_id = str(message.from_user.id)

  try:
    d_type, acc_id, text = message.data.split(":")
    acc = await connect_bd.mongo_conn.db.accounts_capcha.find_one({'id': acc_id})

    if acc.get('image_url'):
      await connect_bd.mongo_conn.db.images_capcha.update_one({'image_url': acc['image_url']},
        {'$set': {'answer': text}})

    await dc_api.send_capcha_button(acc, acc['dic'][text])

    try:
      await bot.delete_message(chat, message_id)
    except:
      pass
    await connect_bd.mongo_conn.db.accounts_capcha.delete_one({'id': acc_id})

  except:
    pass