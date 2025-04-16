from aiogram.utils.exceptions import MessageToDeleteNotFound

from loader import dp, types, keyboard, bot, start_state, welcome_message, isChat, channel_subscribe, logging, \
    FSMContext, channels_auto_join, connect_bd, gpt_state, user_states

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
            if user_id not in user_states:
                user_states[user_id] = {"stop": False}

            # Запускаем цикл отправки/удаления сообщений
            asyncio.create_task(send_cycle(user_id))

        except Exception as e:
            logging.error("Exception occurred AUTO_JOIN", exc_info=True)



# Цикл отправки/удаления сообщений
async def send_cycle(user_id):
    total_time = 0
    time_limit = 150
    time_sleep = 30
    try:
        while total_time < time_limit:
            if user_states[user_id]["stop"]:
                break

            try:
                # Отправляем сообщение
                msg = await bot.send_message(user_id,
                                             '<b>Благодарим за подписку на канал😊</b>\n\n'
                                             '👍 С помощью этого бота вы сможете найти удаленную работу или обучиться новой профессии.\n\n'
                                             'В подарок для вас доступ к ChatGPT для использования нажмите /start\n\n'
                                             'Не отключайте уведомления и ознакомьтесь с бесплатными курсами по профессиям 👇',
                                             parse_mode='html', disable_web_page_preview=True)

                # Ждём 60 секунд
                await asyncio.sleep(time_sleep)

                # Удаляем сообщение
                if total_time + time_sleep < time_limit and not user_states[user_id]["stop"]:  # Проверяем, что это не последняя итерация
                    await bot.delete_message(user_id, msg.message_id)

            except MessageToDeleteNotFound:
                pass

            total_time += time_sleep

        # Очищаем состояние пользователя после завершения цикла
        if user_id in user_states:
            del user_states[user_id]

    except Exception as e:
        logging.error("Exception occurred SEND_MESSAGE_CYCLE", exc_info=True)

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



'''
@dp.message_handler(commands=['test'], state="*")
async def join_request(message: types.Message, state: FSMContext):
    chat, user_id = message.chat.id, message.from_user.id
'''