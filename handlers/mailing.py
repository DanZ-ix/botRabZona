import asyncio
import time
import re

from loader import dp, types, mailing_state, FSMContext, bot, keyboard, other_commands, connect_bd, exceptions, conf, \
    logging
from filters.filter_commands import isPrivate


class Mail():
    def __init__(self, text, video, photo, reply_markup, save_user, state, mail_new_channel=False, admin_mail=False):
        self.state = state
        self.mail_new_channel = mail_new_channel
        self.admin_mail = admin_mail

        self.count_users = 0
        self.sleep = 0
        self.all_users = 0
        self.die = 0
        self.send = 0
        self.block_bot = 0
        self.delete_user = 0
        self.acc_not_active = 0
        self.acc_not_active = 0
        self.other_error = []
        self.error = 0

        self.save_user = save_user
        self.timer = 0
        self.text = text
        self.video = video
        self.photo = photo
        self.reply_markup = reply_markup

    async def background_edit(self):
        while True:
            info = f'Время выполнения: {await other_commands.getTimeFormat(int(time.time()) - self.start_mail)}\nВсего пользователей: {self.count_users}\nВсего отправлено: {self.all_users}\nУспешно отправлено: {self.send}\nЗаблокировали бота: {self.block_bot}\nУдалённых пользователей: {self.delete_user}\nАккаунт не действителен: {self.acc_not_active}\nУходил в сон: {self.sleep}\nКоличество ошибок: {self.error}\nПрочие ошибки: {self.other_error and " | ".join(self.other_error) or "нет"}'
            # info = f'Время выполнения: {await other_commands.getTimeFormat(int(time.time()) - self.start_mail)}\n\n🔰Рассылка🔰\n👥 Пользователи\n├ Всего: {self.count_users}\n├ Живые: {self.send}\n└ Мертвые: {self.die}'

            self.timer += 1
            if self.timer > 150:
                self.timer = 0
                await self.state.update_data(save_user=self.all_users)
                for obj in self.msg_ids:
                    try:
                        await bot.edit_message_text(info, obj['user_id'], obj['message_id'])
                    except Exception as e:
                        pass

            if self.all_users >= self.count_users:
                await self.state.update_data(save_user=0)
                for obj in self.msg_ids:
                    try:
                        await bot.send_message(obj['user_id'], info)
                    except:
                        pass

                break

            await asyncio.sleep(0.1)

    async def sender_init(self):
        self.msg_ids = []
        for id in conf['admin']['id']:
            try:
                msg = await bot.send_message(id, 'Рассылка началась, ожидайте...')
                await bot.pin_chat_message(id, msg.message_id)
                self.msg_ids.append({'user_id': id, 'message_id': msg.message_id})
            except:
                pass

        await asyncio.sleep(5)
        loop = asyncio.get_event_loop()
        self.users_ids, self.users = [], []
        self.start_mail = int(time.time())

        obj = {}
        if self.mail_new_channel:
            obj = {'new_channel_notify': True}

        if not self.admin_mail:
            async for user in connect_bd.mongo_conn.db.users.find(obj):
                self.users.append(user)
        else:
            for adm in conf['admin']['id']:
                self.users.append({'user_id': adm})

        self.count_users = len(self.users)
        loop.create_task(self.background_edit())

        c_user = 0
        for user in self.users:
            c_user += 1
            if self.save_user > 0:
                if c_user < self.save_user:
                    self.all_users += 1
                    continue

            loop.create_task(self.send_msg(user['user_id']))
            await asyncio.sleep(0.028)

    async def send_msg(self, id):
        try:
            try:
                if self.video:
                    await bot.send_video(id, video=self.video, caption=self.text, reply_markup=self.reply_markup,
                                         parse_mode='HTML')
                elif self.photo:
                    await bot.send_photo(id, photo=self.photo, caption=self.text, reply_markup=self.reply_markup,
                                         parse_mode='HTML')
                else:
                    await bot.send_message(id, self.text, reply_markup=self.reply_markup, parse_mode='HTML',
                                           disable_web_page_preview=True)
                self.send += 1

            except exceptions.RetryAfter as e:
                self.sleep += 1
                if str(e) not in self.other_error:
                    self.other_error.append(str(e))
                await asyncio.sleep(e.timeout)
                await self.send_msg(id)
            except exceptions.BotBlocked:
                self.die += 1
                self.block_bot += 1
            except exceptions.UserDeactivated:
                self.die += 1
                self.delete_user += 1
            except exceptions.ChatNotFound:
                self.die += 1
                self.acc_not_active += 1
            except Exception as e:
                self.die += 1
                self.error += 1
                if str(e) not in self.other_error:
                    self.other_error.append(str(e))

            self.all_users += 1
        except Exception as e:
            logging.error("Exception occurred", exc_info=True)


async def editor_mailing(chat, user_data, state=None, message_id='', preview=False, mailing=False, select_button='',
                         start_mailing=False, admin_mail=False):
    buttons = user_data.get('buttons') or []
    m = await keyboard.get_buttons_edit_mail(user_data, buttons, select_button=select_button, mailing=mailing,
                                             preview=preview)

    if not start_mailing:
        if user_data.get('photo') and user_data.get('video') == None:
            if message_id:
                try:
                    await bot.edit_message_caption(
                        types.InputMediaPhoto(media=user_data['photo'], caption=user_data.get('text') or None,
                                              parse_mode='html'),
                        chat, message_id, reply_markup=m)
                except:
                    try:
                        await bot.delete_message(chat, message_id)
                    except:
                        pass
                    msg = await bot.send_photo(chat, photo=user_data['photo'], caption=user_data.get('text') or None,
                                               reply_markup=m,
                                               parse_mode='html')
                    await state.update_data(message_id=msg.message_id)

            else:
                msg = await bot.send_photo(chat, photo=user_data['photo'], caption=user_data.get('text') or None,
                                           reply_markup=m,
                                           parse_mode='html')
                await state.update_data(message_id=msg.message_id)

        if user_data.get('video') and user_data.get('photo') == None:
            if message_id:
                try:
                    await bot.edit_message_media(
                        types.InputMediaVideo(media=user_data['video'], caption=user_data.get('text') or None,
                                              parse_mode='html'),
                        chat, message_id, reply_markup=m)
                except:
                    try:
                        await bot.delete_message(chat, message_id)
                    except:
                        pass
                    msg = await bot.send_video(chat, video=user_data['video'], caption=user_data.get('text') or None,
                                               reply_markup=m,
                                               parse_mode='html')
                    await state.update_data(message_id=msg.message_id)
            else:
                msg = await bot.send_video(chat, video=user_data['video'], caption=user_data.get('text') or None,
                                           reply_markup=m,
                                           parse_mode='html')
                await state.update_data(message_id=msg.message_id)

        if user_data.get('photo') == None and user_data.get('video') == None:
            try:
                await bot.edit_message_text(user_data['text'], chat, message_id, reply_markup=m, parse_mode='html',
                                            disable_web_page_preview=True)
            except exceptions.MessageNotModified:
                pass
            except Exception as e:
                try:
                    await bot.delete_message(chat, message_id)
                except:
                    pass
                msg = await bot.send_message(chat, user_data['text'], reply_markup=m, parse_mode='HTML',
                                             disable_web_page_preview=True)
                await state.update_data(message_id=msg.message_id)
    else:
        start_m = Mail(text=user_data['text'], photo=user_data.get('photo') or '', video=user_data.get('video') or '',
                       reply_markup=m, save_user=user_data.get('save_user') or 0, state=state, admin_mail=admin_mail)
        asyncio.create_task(start_m.sender_init())


@dp.message_handler(isPrivate(), commands=['mailing'], state="*")
async def start_mailing(message: types.Message, state: FSMContext):
    chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(
        message.from_user.id)
    user_data = await state.get_data()
    if user_data.get('text') == None:
        msg = await bot.send_message(chat, 'Начните писать текст, отправлять фото или видео', parse_mode='html')
        await state.update_data(message_id=msg.message_id)
    else:
        await editor_mailing(chat, user_data, state=state)

    await mailing_state.start_mail.set()


@dp.message_handler(isPrivate(), content_types=types.ContentType.ANY, state=mailing_state.start_mail)
async def get_content(message: types.Message, state: FSMContext):
    chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(
        message.from_user.id)

    if message.text or message.caption:
        text = message.html_text
    else:
        text = ''

    if '/' == text[0]:
        await bot.send_message(chat, 'Вышел с режима редактирования, отправьте ещё раз команду')
        await state.reset_state(with_data=False)
        return False

    photo, video = '', ''
    if 'photo' in message:
        photo = message.photo[0].file_id
    if 'video' in message:
        video = message.video.file_id
    if 'animation' in message:
        video = message.animation.file_id

    await other_commands.set_trash(message, chat=chat)
    async with state.proxy() as d:
        if photo or video:
            if photo:
                d['photo'] = photo
                if d.get('video'):
                    del d['video']

            if video:
                d['video'] = video
                if d.get('photo'):
                    del d['photo']

            if text:
                d['text'] = text
        else:
            d['text'] = text

        await editor_mailing(chat, d, message_id=d.get('message_id'), state=state)


@dp.callback_query_handler(isPrivate(), state=mailing_state.start_mail)
async def callback_data(message: types.CallbackQuery, state: FSMContext):
    chat, message_id = str(message.message.chat.id), message.message.message_id
    user_data = await state.get_data()
    d = message.data.split(":")

    if d[0] == 'new_buttons':
        msg = await bot.send_message(chat, 'Напишите текст кнопок', parse_mode='html')
        await other_commands.set_trash(msg)
        await state.update_data(message_id=message_id)
        await mailing_state.new_button.set()

    if d[0] == 'del_photo' or d[0] == 'del_video':
        async with state.proxy() as data:
            if d[0] == 'del_photo':
                if data.get('photo'):
                    del data['photo']
            else:
                if data.get('video'):
                    del data['video']

            await editor_mailing(chat, data, state=state)
            await mailing_state.start_mail.set()

    if d[0] == 'del_all':
        async with state.proxy() as data:
            if data.get('text'):
                del data['text']
            if data.get('photo'):
                del data['photo']
            if data.get('video'):
                del data['video']
            if data.get('buttons'):
                del data['buttons']
            if data.get('max_rows'):
                del data['max_rows']
            if data.get('message_id'):
                del data['message_id']

            msg = await bot.send_message(chat, 'Начните писать текст, отправлять фото или видео', parse_mode='html')
            await state.update_data(message_id=msg.message_id)

    if d[0] == 'preview_mode':
        await editor_mailing(chat, user_data, preview=True, message_id=message_id, state=state)
        await mailing_state.start_mail.set()

    if d[0] == 'edit_mode':
        await editor_mailing(chat, user_data, message_id=message_id, state=state)
        await mailing_state.start_mail.set()

    if d[0] == 'start_admin_mail':
        asyncio.create_task(editor_mailing(chat, user_data, state=state, preview=True, mailing=True, start_mailing=True,
                                           admin_mail=True))

    if d[0] == 'start_mailing':
        asyncio.create_task(
            editor_mailing(chat, user_data, state=state, preview=True, mailing=True, start_mailing=True))


@dp.message_handler(isPrivate(), state=mailing_state.new_button)
async def new_button(message: types.Message, state: FSMContext):
    chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(
        message.from_user.id)
    butt = message.text

    async with state.proxy() as data:
        rows = butt.split("\n")
        max_rows, buttons = 1, []
        for row in rows:
            if '|' in row:
                row_buttons = row.split('|')
                if len(row_buttons) > max_rows:
                    max_rows = len(row_buttons)
                for button_info in row_buttons:
                    text, url = button_info.split('-', maxsplit=1)
                    if re.findall(
                            r'^((ftp|http|https):\/\/)?(www\.)?([A-Za-zА-Яа-я0-9]{1}[A-Za-zА-Яа-я0-9\-]*\.?)*\.{1}[A-Za-zА-Яа-я0-9-]{2,8}(\/([\w#!:.?+=&%@!\-\/])*)?',
                            url.strip()):
                        buttons.append({'text': text.strip(), 'url': url.strip()})
                    else:
                        await bot.send_message(chat,
                                               f'Не могу добавить кнопку: <code>{button_info}</code>, не верный формат у ссылки',
                                               parse_mode='html')

            else:
                text, url = row.split('-', maxsplit=1)
                if re.findall(
                        r'^((ftp|http|https):\/\/)?(www\.)?([A-Za-zА-Яа-я0-9]{1}[A-Za-zА-Яа-я0-9\-]*\.?)*\.{1}[A-Za-zА-Яа-я0-9-]{2,8}(\/([\w#!:.?+=&%@!\-\/])*)?',
                        url.strip()):
                    buttons.append({'text': text.strip(), 'url': url.strip()})
                else:
                    await bot.send_message(chat,
                                           f'Не могу добавить кнопку: <code>{button_info}</code>, не верный формат у ссылки',
                                           parse_mode='html')

        data['buttons'] = buttons
        data['max_rows'] = max_rows

    await editor_mailing(chat, data, message_id=data.get('message_id'))
    await other_commands.set_trash(message, chat=chat)
    await mailing_state.start_mail.set()


@dp.message_handler(isPrivate(), commands=['add_link'], state="*")
async def add_invite_link(message: types.Message, state: FSMContext):
    chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(
        message.from_user.id)
    id = await connect_bd.mongo_conn.db.links.count_documents({})

    link = {'link_id': id, 'admin_id': user_id, 'invited_number': 0, 'deleted': False}
    await connect_bd.mongo_conn.db.links.insert_one(link)
    await bot.send_message(chat, 'Ссылка создана: ' + f'<code>https://t.me/{bot["username"]}?start={id}</code>',
                           parse_mode='html')


@dp.message_handler(isPrivate(), commands=['show_links'], state="*")
async def show_links(message: types.Message, state: FSMContext):
    chat, fullname, username, user_id = message.chat.id, message.from_user.full_name, message.from_user.username and f"@{message.from_user.username}" or "", str(
        message.from_user.id)

    user_links = []
    async for link in connect_bd.mongo_conn.db.links.find({'deleted': False}):
        if link.get('admin_id') == user_id:
            user_links.append(link)

    ret_message = 'Ваши ссылки: \n'

    if (len(user_links) == 0):
        await bot.send_message(chat, 'У вас пока нет ссылок, нужно создзать их с помощью команды /add_link',
                               parse_mode='html')
        return

    for link in user_links:
        ret_message += f'<code>https://t.me/{bot["username"]}?start={link.get("link_id")}</code>\nКоличество откликов по ней: {link.get("invited_number")}\n\n'

    await bot.send_message(chat, ret_message, parse_mode='html')
