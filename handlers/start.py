import asyncio
import datetime

from loader import dp, types, connect_bd, start_state, gpt_state, imagine_state, FSMContext, keyboard, bot, \
    channel_subscribe, welcome_message, other_func, state_profile, rate_limit, channel_in, channel_in1, logging, user_states
from filters.filter_commands import isUser, isSubscribe, clearDownKeyboard, isInviteUser


@dp.message_handler(isUser(), isSubscribe(), clearDownKeyboard(), commands=['start'], state="*")
@rate_limit(2, 'start')
async def start(message: types.Message, state: FSMContext):
    chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(
        message.from_user.id)

    m = await keyboard.call_gpt()
    await bot.send_message(chat, welcome_message, reply_markup=m, parse_mode='html')
    await start_state.select_neiro.set()


@dp.callback_query_handler(isUser(), clearDownKeyboard(), isSubscribe(), state=start_state.check_subscribe)
@rate_limit(2, 'start')
async def callback_data(message: types.CallbackQuery, state: FSMContext):
    chat, message_id = str(message.message.chat.id), message.message.message_id
    user_data = await state.get_data()
    if chat in user_states:
        user_states[chat]["stop"] = True

    m = await keyboard.select_neural_net()
    await bot.send_message(chat, welcome_message, reply_markup=m, parse_mode='html')
    await start_state.select_neiro.set()


@dp.callback_query_handler(isUser(), clearDownKeyboard(), isSubscribe(), state=start_state.select_neiro)
async def callback_data(message: types.CallbackQuery, state: FSMContext):
    chat, message_id = str(message.message.chat.id), message.message.message_id
    user_id = str(message.from_user.id)

    try:
        try:
            user_data = await state.get_data()
            if not user_data:
                user_data = {}
        except:
            user_data = {}

        if message.data == 'gpt_chat':
            m = await keyboard.start_chat()
            msg = await bot.send_message(chat, 'Подключаюсь к нейросети...', reply_markup=m)
            await state.update_data(keyboard_open=True, msg_id_keyboard_open=msg.message_id, chat_id_keyboard_open=chat)

            m = await keyboard.set_dialog(False)
            await bot.send_message(chat, f'Введите ваш запрос или начните диалог.', reply_markup=m)
            await gpt_state.set_query.set()

            async with state.proxy() as d:
                if d.get('dialog'):
                    del d['dialog']
                    await connect_bd.mongo_conn.db.users.update_one({'user_id': user_id}, {'$set': {'dialogs': []}})

        if message.data == 'get_profile':
            m, user_info = await other_func.get_profile(keyboard, user_id, bot)
            await bot.send_message(chat, user_info, reply_markup=m, parse_mode='html')
            await state_profile.get_attempts.set()
    except Exception as e:
        logging.error("Exception occurred", exc_info=True)


@dp.message_handler(isUser(), isSubscribe(), text="Бесплатные курсы", state="*")
@rate_limit(2, 'get_query')
async def get_gpt_chat_text_call(message: types.Message, state: FSMContext):
    chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(
        message.from_user.id)
    m = await keyboard.get_courses()
    mess = "Выбор за тобой. С чего хочешь начать?"
    await bot.send_message(chat, mess, reply_markup=m, parse_mode='html')


@dp.message_handler(isUser(), isSubscribe(), commands=['get_courses'], state="*")
@rate_limit(2, 'get_query')
async def get_courses(message: types.Message, state: FSMContext):
    chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(
        message.from_user.id)
    m = await keyboard.get_courses()
    mess = "Выбор за тобой. С чего хочешь начать?"
    await bot.send_message(chat, mess, reply_markup=m, parse_mode='html')

