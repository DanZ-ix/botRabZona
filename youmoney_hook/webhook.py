from aiohttp import web
from aiohttp.web_request import BaseRequest
from loader import connect_bd
from yoomoney import Quickpay

class NotifyYoumoney():
  def __init__(self, account_number, bot):
    self.account = account_number
    self.bot = bot

  async def get_youmoney_url(self, account, user_id, attempts, sum):
    quickpay = Quickpay(
      receiver=account,
      quickpay_form="shop",
      targets="Пополнение попыток для Midjorney",
      paymentType="SB",
      label=f'{user_id}:{attempts}',
      sum=sum,
    )
    return quickpay.base_url

  async def web_hooks(self):
    routes = web.RouteTableDef()

    @routes.post('/kassa/')
    async def web_hook(request: BaseRequest):
      payload = await request.post()

      user_info = payload.get('label')
      if user_info:
        user_id, attempt = payload['label'].split(':')
        if int(float(payload.get('withdraw_amount'))) in [199, 359, 499, 899]:
          if payload.get('currency') == '643' and payload.get('unaccepted') == 'false':
            await connect_bd.mongo_conn.db.users.update_one({'user_id': user_id}, {'$inc': {'attempts_pay': int(attempt)}})
            await connect_bd.mongo_conn.db.payments.insert_one(dict(payload))

      return web.Response(text='YES', status=200)

    app = web.Application()
    runner = web.AppRunner(app)
    await runner.setup()
    app.router._frozen = False
    app.add_routes(routes)
    app.router._frozen = True
    site = web.TCPSite(runner, host='127.0.0.1', port=1234)
    await site.start()