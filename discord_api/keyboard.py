from loader import types

class apiDiscordKeyboard:

  async def get_keyboard(self, components, get_dict=False, acc_id=''):
    keyboard = types.InlineKeyboardMarkup(row_width=5)
    arr, data, dic = [], [], {}

    for l in components:
      try:
        arr = []
        if l.get('components'):
          for butt in l['components']:
            text = butt.get('label') or (butt.get('emoji') and butt['emoji'].get('name'))

            if not get_dict:
              obj = {'text': text, 'callback_data': butt.get('custom_id')}
            else:
              dic[text] = butt.get('custom_id')
              obj = {'text': text, 'callback_data': f'capcha:{acc_id}:{text}'}
            data.append(obj)
            arr.append(obj)

          keyboard.add(*arr)
      except:
        pass

    return keyboard, data, dic

keyboard_dc = apiDiscordKeyboard()