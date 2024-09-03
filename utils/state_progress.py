from loader import StatesGroup, State

class Profile(StatesGroup):
  get_attempts = State()
  get_variants_for_attempts = State()
  get_variants_for_attempts_pay = State()
  check_subscribe = State()
  check_nec_sub = State()
  await_message = State()
  start_state = State()

class Mailing(StatesGroup):
  start_mail = State()
  new_button = State()

class Subscribe(StatesGroup):
  check_subscribe = State()
  select_neiro = State()

class Imagine(StatesGroup):
  set_query = State()
  set_buttons = State()

class GPT(StatesGroup):
  set_query = State()

class AccountsControl(StatesGroup):
  select_type_control = State()
  send_request = State()

  control_accounts_gpt = State()
  add_accounts_gpt_with_text = State()
  add_accounts_gpt_with_file = State()

  control_accounts_imagine = State()
  get_account_imagine = State()
  add_account_imagine = State()
  add_bot_id_account_imagine = State()
  delete_account_imagine = State()
  set_max_generation = State()

  sett_settings = State()
  sett_set_mode = State()
  sett_set_time_wait = State()

class Queues(StatesGroup):
  queues_update = State()

class BanList(StatesGroup):
  control_ban_list = State()
  add_banlist_with_text = State()
  add_banlist_with_file = State()

class AddChannels(StatesGroup):
  control_channels = State()
  add_channel = State()
  set_link = State()
  set_bot_link = State()
  set_mailing = State()

class AddNecessaryChannels(StatesGroup):
  control_channels = State()
  add_channel = State()
  set_link = State()
  set_bot_link = State()
  set_mailing = State()