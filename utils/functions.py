from loader import connect_bd


class Functions():

    async def get_profile(self, keyboard, user_id, bot):
        user = await connect_bd.mongo_conn.db.users.find_one({'user_id': user_id})
        save = False
        if user.get('attempts_free') == None:
            save, user['attempts_free'] = True, 1
        if user.get('attempts_pay') == None:
            save, user['attempts_pay'] = True, 0
        if save:
            await connect_bd.mongo_conn.db.users.update_one({'user_id': user_id}, {
                '$set': {'attempts_free': user['attempts_free'], 'attempts_pay': user['attempts_pay']}})

        m = await keyboard.get_free_attempts()
        return m, f'Количество попыток:\n\nChatGPT: безлимитно\n\nВаша реферальная ссылка:\n<code>https://t.me/{bot["username"]}?start={user_id}</code>'
