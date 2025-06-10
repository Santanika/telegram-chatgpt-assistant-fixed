"""
Клиент для работы с OpenAI API
"""
import logging
from typing import List, Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class ChatGPTClient:
    """Клиент для взаимодействия с ChatGPT API"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4", max_tokens: int = 2000, temperature: float = 0.7):
        """Инициализация клиента OpenAI"""
        # Импортируем конфигурацию внутри метода, чтобы избежать циклических импортов
        if not api_key:
            from config import Config
            api_key = Config.OPENAI_API_KEY
            model = Config.OPENAI_MODEL
            max_tokens = Config.OPENAI_MAX_TOKENS
            temperature = Config.OPENAI_TEMPERATURE
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Хранилище контекста разговоров для каждого пользователя
        self.conversations: Dict[int, List[Dict[str, str]]] = {}
        
        logger.info(f"ChatGPT клиент инициализирован с моделью: {self.model}")
    
    def get_conversation(self, user_id: int) -> List[Dict[str, str]]:
        """Получить историю разговора для пользователя"""
        if user_id not in self.conversations:
            self.conversations[user_id] = [
                {
                    "role": "system",
                    "content": "Ты полезный ассистент. Отвечай на русском языке, если пользователь пишет на русском. Будь дружелюбным и помогай пользователю."
                }
            ]
        return self.conversations[user_id]
    
    def add_message_to_conversation(self, user_id: int, role: str, content: str):
        """Добавить сообщение в историю разговора"""
        conversation = self.get_conversation(user_id)
        conversation.append({"role": role, "content": content})
        
        # Ограничиваем размер истории (оставляем системное сообщение + последние 20 сообщений)
        if len(conversation) > 21:
            self.conversations[user_id] = [conversation[0]] + conversation[-20:]
    
    def clear_conversation(self, user_id: int):
        """Очистить историю разговора для пользователя"""
        if user_id in self.conversations:
            del self.conversations[user_id]
        logger.info(f"История разговора очищена для пользователя {user_id}")
    
    async def get_response(self, user_id: int, message: str) -> Optional[str]:
        """
        Получить ответ от ChatGPT
        
        Args:
            user_id: ID пользователя Telegram
            message: Сообщение пользователя
            
        Returns:
            Ответ от ChatGPT или None в случае ошибки
        """
        try:
            # Добавляем сообщение пользователя в историю
            self.add_message_to_conversation(user_id, "user", message)
            
            # Получаем историю разговора
            conversation = self.get_conversation(user_id)
            
            logger.info(f"Отправка запроса к OpenAI для пользователя {user_id}")
            
            # Отправляем запрос к OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=conversation,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Извлекаем ответ
            assistant_message = response.choices[0].message.content
            
            # Добавляем ответ ассистента в историю
            self.add_message_to_conversation(user_id, "assistant", assistant_message)
            
            logger.info(f"Получен ответ от OpenAI для пользователя {user_id}")
            return assistant_message
            
        except Exception as e:
            logger.error(f"Ошибка при обращении к OpenAI API: {e}")
            return None
    
    def get_conversation_stats(self, user_id: int) -> Dict[str, int]:
        """Получить статистику разговора"""
        conversation = self.get_conversation(user_id)
        user_messages = sum(1 for msg in conversation if msg["role"] == "user")
        assistant_messages = sum(1 for msg in conversation if msg["role"] == "assistant")
        
        return {
            "total_messages": len(conversation) - 1,  # Исключаем системное сообщение
            "user_messages": user_messages,
            "assistant_messages": assistant_messages
        }

