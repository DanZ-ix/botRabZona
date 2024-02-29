import re
import time
from datetime import datetime, timedelta
from loader import types, connect_bd

class aio_keyboard:

  async def subscribe_channel(self, user_id, ch, ch1):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    if ch:
      url, text = re.search(r'href=\"(.*)\">(.*)<', ch).groups()
      keyboard.add({'text': text, 'url': url})
    if ch1:
      url1, text1 = re.search(r'href=\"(.*)\">(.*)<', ch1).groups()
      keyboard.add({'text': text1, 'url': url1})

    keyboard.add({'text': 'Готово ✅', 'callback_data': 'check_channels'})
    return keyboard

  async def select_neural_net(self):
    keyboard = types.InlineKeyboardMarkup(row_width=2)

    keyboard.add(*[
      {'text': 'ChatGPT', 'callback_data': 'gpt_chat'},
      {'text': 'Midjorney', 'callback_data': f'imagine'}
    ])
    keyboard.add({'text': '👤 Профиль', 'callback_data': 'get_profile'})

    return keyboard



  async def call_gpt(self):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    keyboard.add(*[{'text': 'Начать чат'}, {'text': 'Бесплатные курсы'}])
    return keyboard

  async def get_accounts_gpt(self):
    keyboard = types.InlineKeyboardMarkup(row_width=2)

    count_gpt_tokens = await connect_bd.mongo_conn.db.accounts.count_documents({'type': 'gpt'})
    t, arr = f'Добавление токенов для GPT нейросети, сейчас {count_gpt_tokens} токен(-а, -ов)', []

    keyboard.add(*[
      {'text': 'Добавить текстом', 'callback_data': 'add_acc_text'},
      {'text': 'Добавить через файл', 'callback_data': f'add_acc_file'}
    ])

    return t, keyboard


  async def get_courses(self):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(*[
      {'text': '🧠 Специалист по нейросетям', 'url': 'https://www.puwdtw.ru/click?pid=32319&offer_id=1574'},
      {'text': '🤯 Менеджер Маркетплейсов', 'url': 'https://www.puwdtw.ru/click?pid=32319&offer_id=1509'},
      {'text': '🤟 Настройщик Интернет рекламы', 'url': 'https://www.puwdtw.ru/click?pid=32319&offer_id=1293'},
      {'text': '🧚 Дизайнер интерьеров', 'url': 'https://www.puwdtw.ru/click?pid=32319&offer_id=925'}
    ])
    return keyboard





  async def get_accounts_imagine(self, acc_id=''):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    t, mode_select, arr, max_generate = 'Управление аккаунтами:', '', [], 0

    async for acc in connect_bd.mongo_conn.db.accounts.find({'type': 'midjourney'}):
      mode = acc.get('mode')
      if acc_id == acc['id']:
        now = acc['date']
        max_generate = acc.get('max_generate') and acc['max_generate'] or 1
        date = f'{now.hour}:{now.minute}:{now.second} {now.day}/{now.month}/{now.year}'
        mode_select = acc.get('mode')
        t = f'Дата добавления: {date}\nЮзеримя: {acc["username"]}\nПочта: {acc["email"]}\nРежим работы: {mode and mode or "не определён"}\nID канала с ботом: {acc.get("dc_bot_id") and acc["dc_bot_id"] or "нет"}'
        arr.append({'text': f'✅ {acc["username"]}', 'callback_data': f'select:{acc["id"]}'})
      else:
        arr.append({'text': f'{mode == "fast" and "⚡ " or ""}{acc["username"]}', 'callback_data': f'select:{acc["id"]}'})

    keyboard.add(*arr)

    if acc_id:
      keyboard.add({'text': f'Одновременная генерация: {max_generate}', 'callback_data': f'edit_max_generate:{acc_id}'})
      keyboard.add(*[
        {'text': mode_select == 'fast' and '✅ Fast mode' or 'Fast mode', 'callback_data': f'mode:fast:{acc_id}'},
        {'text': mode_select == 'relax' and '✅ Relax mode' or 'Relax mode', 'callback_data': f'mode:relax:{acc_id}'}
      ])
      # keyboard.add({'text': 'Добавить ID канала с ботом', 'callback_data': f'add_bot_id:{acc_id}'})


    keyboard.add(*[
      {'text': 'Добавить', 'callback_data': 'new_acc:'},
      {'text': acc_id and 'Удалить' or '', 'callback_data': f'del_acc:{acc_id}'}
    ])

    keyboard.add({'text': 'Настройки', 'callback_data': 'settings_acc'})

    return t, keyboard

  async def settings_for_dc(self, account_number):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    sett = await connect_bd.mongo_conn.db.settings.find_one({'admin': True})

    if not sett:
      sett = {'admin': True, 'mode': {'fast': {'min_queues': 30, 'max_queues': 100, 'time_wait': 5}, 'relax': {'min_queues': 1, 'max_queues': 30, 'time_wait': 15}}, 'account': account_number}
      await connect_bd.mongo_conn.db.settings.insert_one(sett)


    t = f'Макс. время ожидания ответа для <b>Fast</b>: {sett["mode"]["fast"]["time_wait"]} мин.\nМакс. время ожидания ответа для <b>Relax</b>: {sett["mode"]["relax"]["time_wait"]} мин.\n\n<strong>Что хотите изменить?</strong>'

    keyboard.add({'text': 'Макс. время ответа fast режима', 'callback_data': 'time_wait:fast'})
    keyboard.add({'text': 'Макс. время ответа relax режима', 'callback_data': 'time_wait:relax'})

    keyboard.add({'text': 'Назад', 'callback_data': 'exit_settings'})
    return t, keyboard


  async def get_save_keyboard(self, buttons, select_callback_data=''):
    keyboard = types.InlineKeyboardMarkup(row_width=5)
    arr = []

    for butt in buttons:
      if select_callback_data != butt['callback_data']:
        arr.append(butt)
      else:
        arr.append({'text': f"✔ {butt['text']}", 'callback_data': butt['callback_data']})

    keyboard.add(*arr)

    return keyboard, arr

  async def get_queues(self, update=False, type=''):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    t, i = 'Сейчас очереди нет', 0

    users_all = await connect_bd.mongo_conn.db.users.count_documents({})

    pre_day = datetime.now() - timedelta(days=1)
    new_users_day = await connect_bd.mongo_conn.db.users.count_documents({'date': {'$gt': pre_day}})

    pre_week = datetime.now() - timedelta(days=7)
    new_users_week = await connect_bd.mongo_conn.db.users.count_documents({'date': {'$gt': pre_week}})

    pre_month = datetime.now() - timedelta(days=30)
    new_users_month = await connect_bd.mongo_conn.db.users.count_documents({'date': {'$gt': pre_month}})

    queues, count_active_queues, count_active_relax_queues, count_active_fast_queues = [], 0, 0, 0
    async for queue in connect_bd.mongo_conn.db.queues.find({'type': type}):
      queues.append(queue)
      if queue.get('request') == True and type == 'midjorney':
        count_active_queues += 1

      if queue.get('status') == 'process' and type == 'gpt':
        count_active_queues += 1

    keyboard.add({'text': '🔁 Обновить', 'callback_data': 'queues_update'})
    keyboard.add(*[
      {'text': type == 'gpt' and '✅ chatGPT' or 'chatGPT', 'callback_data': 'select_gpt'},
    ])
    if queues:

      t = f'{update and f"[<code>{datetime.fromtimestamp(int(time.time()))}</code>]" or ""}\n\nОчередь запросов:\n\n'
      for queue in queues[-10:]:
        user = connect_bd.mongo_conn.users[queue["user_id"]]
        tag = f'<a href="tg://user?id={queue["user_id"]}">{user["fullname"]}</a> {user["username"] and "@"+user["username"] or ""}'
        i += 1

        m = queue.get("mode") != None and queue["mode"]+f", {queue.get('acc_username')}, " or ""
        if i < 10:
          t += f'{i}. {tag}: <b>{queue["type"] == "midjorney" and queue["query"] or queue["query"][0:20]+"..."}</b> ({queue["type"] == "midjorney" and m or ""}ожидает {int(time.time())-queue["start_time"]} сек.)\n'
        else:
          queue = queues[-1]
          t += f'.....\n{len(queues)}. {tag} ({queue["type"] == "midjorney" and m or ""}ожидает {int(time.time())-queue["start_time"]} сек.)'
          break

    t += f'\n\nВсего запросов в процессе выполнения: {count_active_queues}'
    t += f'\n\nВсего юзеров: {users_all}\nНовых юзеров за день: {new_users_day}\nНовых юзеров за неделю: {new_users_week}\nНовых юзеров за месяц: {new_users_month}\n'

    return keyboard, t

  async def variant_add_account(self):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(*[
      {'text': 'GPT аккаунты', 'callback_data': 'gpt_add_acc'},
    ])
    return keyboard

  async def start_chat(self, type='gpt', v='', ratio=''):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)

    if type == 'gpt':
      keyboard.add('Назад')

    if type == 'midjourney' and v and ratio:
      keyboard.add(*[f'Версия: {v}', f'Соотношение: {ratio}'])
      keyboard.add('Нaзад')

    var, var_full = [], []
    if v and not ratio:
      versions = ['v4', 'v5']

      for ver in versions:
        if ver == v:
          var.append(f'✅ {ver}')
        else:
          var.append(ver)
      keyboard.add(*var)

    if ratio and not v:
      versions = ['1:1', '2:3', '3:2', '4:7', '5:4', '7:4', '16:9']

      for ver in versions:
        if ver == ratio:
          var.append(f'✅ {ver}')
        else:
          var.append(ver)

        if len(var) > 3:
          keyboard.add(*var)
          var = []
      if var:
        keyboard.add(*var)

    return keyboard

  async def set_dialog(self, dialog):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add({'text': dialog and 'Завершить диалог' or 'Начать диалог', 'callback_data': 'set_dialog'})
    return keyboard


  async def ban_list_settings(self):
    keyboard = types.InlineKeyboardMarkup(row_width=2)

    try:
      count_ban_list = await connect_bd.mongo_conn.db.banlist.count_documents()
    except:
      count_ban_list = 0

    t, arr = f'Количество запрещённых слов: {count_ban_list}', []

    keyboard.add(*[
      {'text': 'Добавить текстом', 'callback_data': 'add_banlist_text'},
      {'text': 'Добавить через файл', 'callback_data': f'add_banlist_file'}
    ])

    return t, keyboard

  async def get_free_attempts(self):
    keyboard = types.InlineKeyboardMarkup(row_width=1)

    return keyboard

  async def get_variants_free_attempts(self):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(*[
      {'text': 'Получить за подписку', 'callback_data': f'subscribe_channel'},
      {'text': 'Пригласить друга', 'callback_data': f'invite_friend'}
    ])

    return keyboard

  async def get_variants_pay_attempts(self):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(*[
      {'text': '25 шт. - 199₽', 'callback_data': f'buy_attempts:25:199'},
      {'text': '50 шт. - 359₽', 'callback_data': f'buy_attempts:50:359'},
      {'text': '100 шт. - 499₽', 'callback_data': f'buy_attempts:100:499'},
      {'text': '200 шт. - 899₽', 'callback_data': f'buy_attempts:200:899'}
    ])

    return keyboard

  async def payment_url(self, url):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(*[
      {'text': 'Перейти к оплате', 'url': url}
    ])

    return keyboard

  async def get_buttons_edit_mail(self, user_data, buttons, select_button='', mailing=False, preview=False, not_url=False):
    max_rows = user_data.get('max_rows') or 2
    keyboard = types.InlineKeyboardMarkup(row_width=max_rows)
    arr = []

    if buttons and not not_url:
      for butt in buttons:
        arr.append({'text': butt['text'], 'url': butt['url']})

    keyboard.add(*arr)

    if not preview:
      keyboard.add({'text': '➖➖➖➖➖➖➖➖➖➖➖➖', 'callback_data': 'edit_command'})
      keyboard.add({'text': 'Добавить кнопки', 'callback_data': f'new_buttons'})

      keyboard.add(*[
        {'text': user_data.get('photo') and 'Удалить 📷' or '', 'callback_data': f'del_photo'},
        {'text': user_data.get('video') and 'Удалить 📹' or '', 'callback_data': f'del_video'},
        {'text': 'Удалить всё' or '', 'callback_data': f'del_all'}
      ])

      keyboard.add(*[
        {'text': 'Предпросмотр', 'callback_data': f'preview_mode'},
        {'text': 'Сделать рассылку', 'callback_data': f'start_mailing'}
      ])
      keyboard.add({'text': 'Админ рассылка', 'callback_data': f'start_admin_mail'})
    else:
      if not mailing:
        keyboard.add({'text': '📝 Режим редактора', 'callback_data': 'edit_mode'})

    return keyboard

  async def variants_subscribe_to_channels(self, user_get_channel=False, select_channel_id='', filters_channels=None):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    t, count = user_get_channel == False and 'Список каналов для получения попыток в Midjourney' or 'Чтобы получить n количество попыток для midjourney - подпишись на каналы и жми «Проверить подписку»', 0
    async for channel in connect_bd.mongo_conn.db.channels_subscribe.find():
      if filters_channels:
        if channel['id'] in filters_channels:
          continue

      if str(channel['id']) == str(select_channel_id):
        t = f'ID канала: <code>{channel["id"]}</code>\nНазвание: {channel["title"]}\nСсылка: {channel["link"]}'
        keyboard.add({'text': f"✅ {channel['title']}", 'callback_data': f'get_ch:{channel["id"]}'})
      else:
        count += 1
        if not user_get_channel:
          keyboard.add({'text': channel['title'], 'callback_data': f'get_ch:{channel["id"]}'})
        else:
          if 't.me' in channel['link']:
            keyboard.add({'text': channel['title'], 'url': channel['link']})

    if not user_get_channel:
      keyboard.add(*[
        {'text': select_channel_id and 'Удалить' or '', 'callback_data': f'del_ch:{select_channel_id}'},
        {'text': 'Добавить', 'callback_data': f'add_ch'}
      ])
      keyboard.add(*[
        {'text': 'Изменить ссылку', 'callback_data': f'edit_link:{select_channel_id}'},
        {'text': 'Рассылка', 'callback_data': f'mailing:{select_channel_id}'}
      ])

    else:
      keyboard.add({'text': 'Проверить подписку', 'callback_data': f'check_subscribe'})

    if count == 0 and user_get_channel:
      t = ''

    return t, keyboard

  async def variants_subscribe_necessary_to_channels(self, user_get_channel=False, key_channel_id='',
    filters_channels=None):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    id, t, count, arr = '', 'Список каналов для обязательной подписки', 0, []

    repeat_ch = {}
    async for channel in connect_bd.mongo_conn.db.channels_necessary_subscribe.find():
      if repeat_ch.get(channel['id']) == None:
        repeat_ch[channel['id']] = 0
      repeat_ch[channel['id']] += 1

      if filters_channels:
        if channel['id'] in filters_channels:
          continue

      if channel['key'] == str(key_channel_id):
        t = f'ID канала: <code>{channel["id"]}</code>\nНазвание: {channel["title"]} {repeat_ch[channel["id"]] > 1 and repeat_ch[channel["id"]] or ""}\nСсылка: {channel["link"]}\nСсылка для бота: <code>{channel.get("bot_link") or "нет"}</code>'
        id = channel['id']
        arr.append({'text': f"✅ {channel['title']} {repeat_ch[channel['id']] > 1 and repeat_ch[channel['id']] or ''}", 'callback_data': f'get_ch:{channel["key"]}'})
      else:
        count += 1
        if not user_get_channel:
          arr.append({'text': f"{channel['title']} {repeat_ch[channel['id']] > 1 and repeat_ch[channel['id']] or ''}", 'callback_data': f'get_ch:{channel["key"]}'})
        else:
          keyboard.add({'text': channel['title'], 'url': channel['link']})

    if arr:
      keyboard.add(*arr)

    if not user_get_channel:
      keyboard.add(*[
        {'text': key_channel_id and 'Удалить' or '', 'callback_data': f'del_ch:{key_channel_id}'},
        {'text': 'Добавить', 'callback_data': f'add_ch'}
      ])
      keyboard.add(*[
        {'text': 'Изменить ссылку', 'callback_data': f'edit_link:{key_channel_id}'},
        {'text': 'Ссылка для бота', 'callback_data': f'url_to_bot:{key_channel_id}'}
      ])
      keyboard.add({'text': 'Дублировать канал', 'callback_data': f'double_сh:{id}:{key_channel_id}'})

    else:
      keyboard.add({'text': 'Проверить подписку', 'callback_data': f'check_subscribe'})

    if count == 0 and user_get_channel:
      t = ''

    return t, keyboard

  async def get_attempt_to_subs_channel(self):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add({'text': 'Получить', 'callback_data': 'open_attempt_variants'})
    return keyboard

  async def set_notify_to_subscribe_channel(self):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add({'text': 'Уведомить о новых попытках', 'callback_data': 'notify_attempt_variants'})
    return keyboard