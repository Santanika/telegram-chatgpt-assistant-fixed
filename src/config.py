"""
Конфигурация для Telegram бота
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# OpenAI API Key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Authorized User ID
AUTHORIZED_USER_ID = int(os.getenv('AUTHORIZED_USER_ID', 0))

# Проверка обязательных переменных
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не установлен")

if not AUTHORIZED_USER_ID:
    raise ValueError("AUTHORIZED_USER_ID не установлен")

