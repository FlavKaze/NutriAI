import pytz
import logging
from telegram import Update
from database import get_user_session
from datetime import datetime

fuso_horario = pytz.timezone('America/Sao_Paulo')


user_logger = logging.getLogger("user_messages")
user_logger.setLevel(logging.INFO)
user_logger.addHandler(logging.FileHandler("user_messages.log"))


def log_message(update: Update, response: str, method="None", context=None):
    date = datetime.now(fuso_horario).strftime("%d/%m/%Y %H:%M:%S")
    user_id = update.message.from_user.id
    username = get_user_session(user_id).get('name', 'Unknown')
    message = update.effective_message.text
    final_response = response.replace('\n', ' | ')
    user_logger.info(f"{date} - {method=} - {user_id=} - {username=} - sent message: {message or context} - Response: {final_response}")
