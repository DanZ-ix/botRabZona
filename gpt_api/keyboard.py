from loader import types

class apiGptKeyboard:

  async def get_keyboard(self, components):
    keyboard = types.InlineKeyboardMarkup(row_width=5)
    arr, data = [], []

    for l in components:
      arr = []
      if l.get('components'):
        for butt in l['components']:
          obj = {'text': butt.get('label') or (butt.get('emoji') and butt['emoji'].get('name')), 'callback_data': butt.get('custom_id')}
          data.append(obj)
          arr.append(obj)

        keyboard.add(*arr)

    return keyboard, data

keyboard_gpt = apiGptKeyboard()