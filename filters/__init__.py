from aiogram import Dispatcher
from .filter_commands import isUser, isAdmin, isPrivate, isNotQueue, isSubscribe, clearDownKeyboard, EngineerWorks, isAttempt, isInviteUser

def setup(dp: Dispatcher):
  dp.filters_factory.bind(isUser)