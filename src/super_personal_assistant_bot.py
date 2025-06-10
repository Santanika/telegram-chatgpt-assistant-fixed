"""
Обновленный персональный ассистент с AI функциями
"""
import asyncio
import logging
import os
import tempfile
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

from config import Config, setup_logging
from models.user import db, User
from chatgpt_client import ChatGPTClient
from services.smart_task_service import SmartTaskService
from services.voice_service import VoiceService
from services.internal_calendar_service import InternalCalendarService
from services.finance_service import FinanceService
from services.notification_scheduler import NotificationScheduler
from services.predictive_analytics import PredictiveAnalytics
from services.ticktick_integration import TickTickIntegration

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)

class SuperPersonalAssistantBot:
    """Супер персональный ассистент с AI функциями"""
    
    def __init__(self):
        self.config = Config()
        self.authorized_user_id = 398613499  # Только для вас
        
        # Инициализация сервисов
        self.chatgpt = ChatGPTClient()
        self.smart_tasks = SmartTaskService(str(self.authorized_user_id))
        self.voice_service = VoiceService()
        self.calendar_service = InternalCalendarService()
        self.finance_service = FinanceService()
        self.analytics = PredictiveAnalytics(str(self.authorized_user_id))
        self.ticktick = TickTickIntegration()
        
        # Создание приложения
        self.application = Application.builder().token(self.config.telegram_token).build()
        
        # Регистрация обработчиков
        self.register_handlers()
        
        logger.info("Супер персональный ассистент инициализирован")
    
    def check_authorization(self, user_id: int) -> bool:
        """Проверка авторизации пользователя"""
        return user_id == self.authorized_user_id
    
    async def unauthorized_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик для неавторизованных пользователей"""
        await update.message.reply_text("🔒 Этот бот приватный. Доступ запрещен.")
    
    def register_handlers(self):
        """Регистрация обработчиков команд"""
        
        # Команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("tasks", self.tasks_command))
        self.application.add_handler(CommandHandler("analytics", self.analytics_command))
        self.application.add_handler(CommandHandler("sync", self.sync_command))
        self.application.add_handler(CommandHandler("delegate", self.delegate_command))
        self.application.add_handler(CommandHandler("report", self.report_command))
        
        # Обработчики сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
        # Callback обработчики
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        if not self.check_authorization(update.effective_user.id):
            await self.unauthorized_handler(update, context)
            return
        
        welcome_text = """
🤖 **Супер Персональный Ассистент** готов к работе!

🧠 **AI Функции:**
• Предиктивная аналитика
• Умные напоминания
• Анализ продуктивности
• Еженедельные отчеты

📋 **Задачи:**
• Умное планирование
• Делегирование (Аня, Дима, Олег)
• TickTick синхронизация
• Пошаговые планы

📸 **Анализ изображений:**
• Чеки и квитанции
• Заметки и документы
• Автоматические действия

Просто напишите что нужно сделать - я проанализирую и предложу оптимальный план!
        """
        
        keyboard = [
            [KeyboardButton("📋 Мои задачи"), KeyboardButton("📊 Аналитика")],
            [KeyboardButton("🔄 Синхронизация"), KeyboardButton("📈 Отчет")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
        # Записываем взаимодействие
        self.analytics.record_interaction('start_command')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        if not self.check_authorization(update.effective_user.id):
            await self.unauthorized_handler(update, context)
            return
        
        help_text = """
🆘 **Помощь по командам:**

**Основные команды:**
• `/start` - Запуск бота
• `/tasks` - Список задач
• `/analytics` - Аналитика и предсказания
• `/sync` - Синхронизация с TickTick
• `/delegate` - Делегированные задачи
• `/report` - Еженедельный отчет

**Как использовать:**
1. Напишите задачу - получите план и советы
2. Отправьте фото - автоматический анализ
3. Голосовое сообщение - распознавание речи
4. Используйте кнопки для быстрого доступа

**Делегирование:**
• **Аня** - личные задачи
• **Дима** - маркетинг (контент, креативы)
• **Олег** - маркетинг (стратегия, процессы)
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def tasks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /tasks"""
        if not self.check_authorization(update.effective_user.id):
            await self.unauthorized_handler(update, context)
            return
        
        try:
            pending_tasks = self.smart_tasks.get_pending_tasks()
            delegated_tasks = self.smart_tasks.get_delegated_tasks()
            
            if not pending_tasks and not any(delegated_tasks.values()):
                await update.message.reply_text("📋 У вас нет активных задач!")
                return
            
            response = "📋 **Ваши задачи:**\n\n"
            
            # Личные задачи
            personal_tasks = [t for t in pending_tasks if not t.get('delegated_to')]
            if personal_tasks:
                response += "👤 **Личные задачи:**\n"
                for task in personal_tasks[:5]:
                    status_icon = "🔄" if task['status'] == 'pending' else "✅"
                    response += f"{status_icon} {task['title']}\n"
                response += "\n"
            
            # Делегированные задачи
            for delegate_key, tasks in delegated_tasks.items():
                if tasks:
                    delegate_name = self.smart_tasks.delegates[delegate_key]['name']
                    response += f"👥 **Делегировано {delegate_name}:**\n"
                    for task in tasks[:3]:
                        response += f"• {task['title']}\n"
                    response += "\n"
            
            # Кнопки действий
            keyboard = [
                [InlineKeyboardButton("➕ Новая задача", callback_data="new_task")],
                [InlineKeyboardButton("🔄 Синхронизация", callback_data="sync_tasks")],
                [InlineKeyboardButton("📊 Аналитика", callback_data="show_analytics")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(response, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Ошибка в команде tasks: {e}")
            await update.message.reply_text("❌ Ошибка при получении задач")
    
    async def analytics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /analytics"""
        if not self.check_authorization(update.effective_user.id):
            await self.unauthorized_handler(update, context)
            return
        
        try:
            # Получаем предсказания
            predictions = self.analytics.generate_predictions()
            insights = self.analytics.get_productivity_insights()
            
            response = "🧠 **Предиктивная аналитика:**\n\n"
            
            if predictions:
                response += "🔮 **Предсказания:**\n"
                for pred in predictions:
                    confidence = int(pred['confidence'] * 100)
                    response += f"• {pred['message']} ({confidence}%)\n"
                response += "\n"
            
            if insights:
                response += "📊 **Инсайты продуктивности:**\n"
                for key, insight in insights.items():
                    response += f"• {insight['message']}\n"
                response += "\n"
            
            # Предложения действий
            response += "💡 **Рекомендации:**\n"
            current_hour = datetime.now().hour
            
            if 9 <= current_hour <= 11:
                response += "• Утро - время для планирования дня\n"
            elif 14 <= current_hour <= 16:
                response += "• День - время для важных задач\n"
            elif 17 <= current_hour <= 19:
                response += "• Вечер - время для подведения итогов\n"
            
            keyboard = [
                [InlineKeyboardButton("📈 Еженедельный отчет", callback_data="weekly_report")],
                [InlineKeyboardButton("🎯 Создать задачу", callback_data="new_task")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(response, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Ошибка в команде analytics: {e}")
            await update.message.reply_text("❌ Ошибка при получении аналитики")
    
    async def sync_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /sync"""
        if not self.check_authorization(update.effective_user.id):
            await self.unauthorized_handler(update, context)
            return
        
        try:
            await update.message.reply_text("🔄 Синхронизация с TickTick...")
            
            result = await self.smart_tasks.sync_with_ticktick()
            
            if result.get('success'):
                response = f"✅ Синхронизация завершена!\n\n"
                response += f"📊 Синхронизировано: {result.get('synced_count', 0)} задач\n"
                response += f"➕ Новых задач: {result.get('new_tasks', 0)}"
            else:
                response = f"❌ Ошибка синхронизации: {result.get('error', 'Неизвестная ошибка')}"
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации: {e}")
            await update.message.reply_text("❌ Ошибка при синхронизации")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        if not self.check_authorization(update.effective_user.id):
            await self.unauthorized_handler(update, context)
            return
        
        try:
            user_message = update.message.text
            
            # Записываем взаимодействие
            self.analytics.record_interaction('text_message', {'message': user_message})
            
            # Проверяем, это задача или обычное сообщение
            task_keywords = ['сделать', 'задача', 'нужно', 'план', 'делегировать']
            
            if any(keyword in user_message.lower() for keyword in task_keywords):
                await self.handle_task_creation(update, context, user_message)
            else:
                # Обычный чат с ChatGPT
                await self.handle_chat(update, context, user_message)
                
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            await update.message.reply_text("❌ Ошибка при обработке сообщения")
    
    async def handle_task_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_text: str):
        """Обработка создания задачи"""
        try:
            await update.message.reply_text("🧠 Анализирую задачу...")
            
            # Создаем умную задачу
            task = await self.smart_tasks.create_smart_task(task_text)
            
            if task.get('error'):
                await update.message.reply_text(f"❌ Ошибка создания задачи: {task['error']}")
                return
            
            analysis = task.get('analysis', {})
            
            # Формируем ответ
            response = f"✅ **Задача создана!**\n\n"
            response += f"📋 **{task['title']}**\n\n"
            
            # Анализ и рекомендации
            response += f"⏱️ Время: {analysis.get('estimated_time', 'не определено')}\n"
            response += f"🎯 Приоритет: {analysis.get('priority', 'средний')}\n\n"
            
            # Предложение делегирования
            suggested_delegate = analysis.get('suggested_delegate')
            if suggested_delegate:
                delegate_name = self.smart_tasks.delegates[suggested_delegate]['name']
                response += f"👥 **Рекомендую делегировать: {delegate_name}**\n\n"
            
            # План действий
            steps = analysis.get('steps', [])
            if steps:
                response += "📝 **План действий:**\n"
                for i, step in enumerate(steps[:3], 1):
                    response += f"{i}. {step}\n"
                if len(steps) > 3:
                    response += f"... и еще {len(steps) - 3} шагов\n"
                response += "\n"
            
            # Кнопки действий
            keyboard = []
            if suggested_delegate:
                keyboard.append([InlineKeyboardButton(f"👥 Делегировать {delegate_name}", 
                                                    callback_data=f"delegate_{task['id']}_{suggested_delegate}")])
            
            keyboard.extend([
                [InlineKeyboardButton("📋 Подробный план", callback_data=f"task_details_{task['id']}")],
                [InlineKeyboardButton("✅ Выполнено", callback_data=f"complete_task_{task['id']}")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(response, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Ошибка создания задачи: {e}")
            await update.message.reply_text("❌ Ошибка при создании задачи")
    
    async def handle_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message: str):
        """Обработка обычного чата"""
        try:
            # Получаем предсказания для контекста
            predictions = self.analytics.generate_predictions()
            context_info = ""
            
            if predictions:
                context_info = "Текущие предсказания: " + "; ".join([p['message'] for p in predictions[:2]])
            
            # Отправляем в ChatGPT с контекстом
            user_id = update.effective_user.id
            full_message = f"{message}. Контекст: {context_info}" if context_info else message
            response = await self.chatgpt.get_response(user_id, full_message)
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Ошибка чата: {e}")
            await update.message.reply_text("❌ Ошибка при обработке сообщения")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback кнопок"""
        if not self.check_authorization(update.effective_user.id):
            return
        
        try:
            query = update.callback_query
            await query.answer()
            
            data = query.data
            
            if data.startswith("delegate_"):
                parts = data.split("_")
                task_id = int(parts[1])
                delegate_key = parts[2]
                
                result = await self.smart_tasks.delegate_task(task_id, delegate_key)
                
                if result.get('success'):
                    response = f"✅ Задача делегирована {result['delegate']}!\n\n"
                    response += f"📋 **Инструкции:**\n{result['instructions']}"
                else:
                    response = f"❌ Ошибка делегирования: {result.get('error')}"
                
                await query.edit_message_text(response, parse_mode=ParseMode.MARKDOWN)
            
            elif data.startswith("task_details_"):
                task_id = int(data.split("_")[2])
                summary = await self.smart_tasks.get_task_summary(task_id)
                await query.edit_message_text(summary, parse_mode=ParseMode.MARKDOWN)
            
            elif data == "weekly_report":
                summary = self.analytics.get_weekly_summary()
                
                response = "📊 **Еженедельный отчет:**\n\n"
                response += f"📋 Создано задач: {summary.get('tasks_created', 0)}\n"
                response += f"💰 Общие расходы: {summary.get('total_expenses', 0)} грн\n"
                
                if summary.get('most_active_day'):
                    response += f"📅 Самый активный день: {summary['most_active_day']}\n"
                
                if summary.get('productivity_score'):
                    response += f"📈 Оценка продуктивности: {summary['productivity_score']}/100\n"
                
                await query.edit_message_text(response, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Ошибка callback: {e}")
            await query.edit_message_text("❌ Ошибка при обработке действия")
    
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка голосовых сообщений"""
        if not self.check_authorization(update.effective_user.id):
            await self.unauthorized_handler(update, context)
            return
        
        try:
            await update.message.reply_text("🎤 Обрабатываю голосовое сообщение...")
            
            # Скачиваем голосовое сообщение
            voice_file = await update.message.voice.get_file()
            
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                await voice_file.download_to_drive(temp_file.name)
                
                # Распознаем речь
                text = await self.voice_service.speech_to_text(temp_file.name)
                
                if text:
                    await update.message.reply_text(f"📝 Распознано: {text}")
                    
                    # Обрабатываем как обычное сообщение
                    context.user_data['last_message'] = text
                    await self.handle_message(update, context)
                else:
                    await update.message.reply_text("❌ Не удалось распознать речь")
                
                # Удаляем временный файл
                os.unlink(temp_file.name)
                
        except Exception as e:
            logger.error(f"Ошибка обработки голоса: {e}")
            await update.message.reply_text("❌ Ошибка при обработке голосового сообщения")
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фотографий"""
        if not self.check_authorization(update.effective_user.id):
            await self.unauthorized_handler(update, context)
            return
        
        try:
            await update.message.reply_text("📸 Анализирую изображение...")
            
            # Скачиваем фото
            photo_file = await update.message.photo[-1].get_file()
            
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                await photo_file.download_to_drive(temp_file.name)
                
                # Анализируем изображение
                analysis = await self.chatgpt.analyze_image_with_text(temp_file.name)
                
                if analysis:
                    response = f"🔍 **Анализ изображения:**\n\n{analysis}\n\n"
                    
                    # Предлагаем действия
                    keyboard = [
                        [InlineKeyboardButton("📋 Создать задачу", callback_data="create_task_from_image")],
                        [InlineKeyboardButton("💰 Добавить расход", callback_data="add_expense_from_image")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(response, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                else:
                    await update.message.reply_text("❌ Не удалось проанализировать изображение")
                
                # Удаляем временный файл
                os.unlink(temp_file.name)
                
        except Exception as e:
            logger.error(f"Ошибка обработки фото: {e}")
            await update.message.reply_text("❌ Ошибка при анализе изображения")
    
    def run_sync(self):
        """Синхронный запуск бота"""
        try:
            logger.info("Запуск супер персонального ассистента...")
            self.application.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
            raise

