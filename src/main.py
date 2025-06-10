"""
Основной файл для запуска Telegram бота
"""
import os
import sys

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from super_personal_assistant_bot import SuperPersonalAssistantBot

if __name__ == "__main__":
    bot = SuperPersonalAssistantBot()
    bot.run()

