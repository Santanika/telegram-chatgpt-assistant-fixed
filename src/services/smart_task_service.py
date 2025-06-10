"""
Исправленный умный сервис задач с правильными импортами
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import os
import asyncio

from services.ticktick_integration import TickTickIntegration

logger = logging.getLogger(__name__)

class SmartTaskService:
    """Умный сервис для управления задачами с TickTick интеграцией"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.tasks_file = f"/tmp/tasks_{user_id}.json"
        self.ticktick = TickTickIntegration()
        
        # Делегаты для задач
        self.delegates = {
            'anya': {
                'name': 'Аня',
                'type': 'personal',
                'skills': ['личные дела', 'покупки', 'дом', 'семья']
            },
            'dima': {
                'name': 'Дима',
                'type': 'marketing_creative',
                'skills': ['контент', 'креативы', 'дизайн', 'видео', 'фото']
            },
            'oleg': {
                'name': 'Олег',
                'type': 'marketing_strategy',
                'skills': ['стратегия', 'процессы', 'аналитика', 'планирование']
            }
        }
        
        logger.info(f"SmartTaskService инициализирован для пользователя {user_id}")
    
    def load_tasks(self) -> List[Dict[str, Any]]:
        """Загрузить задачи из файла"""
        try:
            if os.path.exists(self.tasks_file):
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки задач: {e}")
        return []
    
    def save_tasks(self, tasks: List[Dict[str, Any]]):
        """Сохранить задачи в файл"""
        try:
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"Ошибка сохранения задач: {e}")
    
    async def create_smart_task(self, task_text: str) -> Dict[str, Any]:
        """Создать умную задачу с анализом и предложениями"""
        try:
            # Анализируем задачу
            analysis = await self.analyze_task(task_text)
            
            # Создаем задачу
            task = {
                'id': len(self.load_tasks()) + 1,
                'title': analysis.get('title', task_text),
                'description': analysis.get('description', ''),
                'status': 'pending',
                'priority': analysis.get('priority', 'medium'),
                'estimated_time': analysis.get('estimated_time', 'не определено'),
                'created_at': datetime.now(),
                'due_date': analysis.get('due_date'),
                'steps': analysis.get('steps', []),
                'suggested_delegate': analysis.get('suggested_delegate'),
                'analysis': analysis,
                'external_id': None  # ID в TickTick
            }
            
            # Сохраняем локально
            tasks = self.load_tasks()
            tasks.append(task)
            self.save_tasks(tasks)
            
            # Синхронизируем с TickTick
            try:
                ticktick_id = await self.ticktick.sync_task_from_bot(task)
                if ticktick_id:
                    task['external_id'] = ticktick_id
                    # Обновляем локальную копию
                    tasks = self.load_tasks()
                    for t in tasks:
                        if t['id'] == task['id']:
                            t['external_id'] = ticktick_id
                            break
                    self.save_tasks(tasks)
                    logger.info(f"Задача синхронизирована с TickTick: {ticktick_id}")
            except Exception as e:
                logger.error(f"Ошибка синхронизации с TickTick: {e}")
            
            return task
            
        except Exception as e:
            logger.error(f"Ошибка создания умной задачи: {e}")
            return {'error': str(e)}
    
    async def analyze_task(self, task_text: str) -> Dict[str, Any]:
        """Анализировать задачу и дать рекомендации"""
        try:
            # Простой анализ на основе ключевых слов
            text_lower = task_text.lower()
            
            # Определяем заголовок
            title = task_text.split('.')[0].strip()
            if len(title) > 100:
                title = title[:100] + "..."
            
            # Определяем приоритет
            priority = 'medium'
            if any(word in text_lower for word in ['срочно', 'важно', 'критично', 'немедленно']):
                priority = 'high'
            elif any(word in text_lower for word in ['когда-нибудь', 'не спешно', 'потом']):
                priority = 'low'
            
            # Оценка времени
            estimated_time = 'не определено'
            if any(word in text_lower for word in ['быстро', 'минут', '5 мин']):
                estimated_time = '15-30 минут'
            elif any(word in text_lower for word in ['час', 'часа']):
                estimated_time = '1-2 часа'
            elif any(word in text_lower for word in ['день', 'дня']):
                estimated_time = '1 день'
            elif any(word in text_lower for word in ['неделя', 'недели']):
                estimated_time = '1 неделя'
            
            # Предложение делегирования
            suggested_delegate = None
            
            # Проверяем каждого делегата
            for delegate_key, delegate_info in self.delegates.items():
                for skill in delegate_info['skills']:
                    if skill in text_lower:
                        suggested_delegate = delegate_key
                        break
                if suggested_delegate:
                    break
            
            # Создаем план действий
            steps = self.generate_action_steps(task_text)
            
            # Определяем дедлайн
            due_date = None
            if any(word in text_lower for word in ['сегодня', 'сейчас']):
                due_date = datetime.now() + timedelta(hours=8)
            elif any(word in text_lower for word in ['завтра']):
                due_date = datetime.now() + timedelta(days=1)
            elif any(word in text_lower for word in ['неделя', 'на неделе']):
                due_date = datetime.now() + timedelta(days=7)
            
            return {
                'title': title,
                'description': task_text,
                'priority': priority,
                'estimated_time': estimated_time,
                'suggested_delegate': suggested_delegate,
                'steps': steps,
                'due_date': due_date,
                'analysis_confidence': 0.8
            }
            
        except Exception as e:
            logger.error(f"Ошибка анализа задачи: {e}")
            return {'title': task_text, 'error': str(e)}
    
    def generate_action_steps(self, task_text: str) -> List[str]:
        """Генерировать план действий для задачи"""
        text_lower = task_text.lower()
        steps = []
        
        # Базовые шаги в зависимости от типа задачи
        if any(word in text_lower for word in ['купить', 'покупка']):
            steps = [
                "Составить список необходимого",
                "Найти лучшие предложения",
                "Сделать покупку",
                "Проверить качество"
            ]
        elif any(word in text_lower for word in ['написать', 'создать контент']):
            steps = [
                "Исследовать тему",
                "Создать структуру",
                "Написать черновик",
                "Отредактировать и опубликовать"
            ]
        elif any(word in text_lower for word in ['встреча', 'созвон']):
            steps = [
                "Подготовить повестку дня",
                "Отправить приглашения",
                "Провести встречу",
                "Зафиксировать результаты"
            ]
        elif any(word in text_lower for word in ['анализ', 'исследование']):
            steps = [
                "Собрать данные",
                "Проанализировать информацию",
                "Сделать выводы",
                "Подготовить отчет"
            ]
        else:
            # Универсальные шаги
            steps = [
                "Определить требования",
                "Спланировать выполнение",
                "Выполнить основную работу",
                "Проверить результат"
            ]
        
        return steps[:4]  # Максимум 4 шага
    
    async def delegate_task(self, task_id: int, delegate_key: str) -> Dict[str, Any]:
        """Делегировать задачу"""
        try:
            tasks = self.load_tasks()
            task = None
            
            for t in tasks:
                if t['id'] == task_id:
                    task = t
                    break
            
            if not task:
                return {'error': 'Задача не найдена'}
            
            if delegate_key not in self.delegates:
                return {'error': 'Неизвестный делегат'}
            
            delegate = self.delegates[delegate_key]
            
            # Обновляем задачу
            task['delegated_to'] = delegate_key
            task['delegated_at'] = datetime.now()
            task['status'] = 'delegated'
            
            # Генерируем инструкции для делегата
            instructions = self.generate_delegation_instructions(task, delegate)
            task['delegation_instructions'] = instructions
            
            # Сохраняем изменения
            self.save_tasks(tasks)
            
            # Обновляем в TickTick (добавляем пометку о делегировании)
            if task.get('external_id'):
                try:
                    updated_title = f"[{delegate['name']}] {task['title']}"
                    await self.ticktick.update_task(
                        task['external_id'],
                        title=updated_title,
                        content=f"{task.get('description', '')}\n\nДелегировано: {delegate['name']}\n{instructions}"
                    )
                except Exception as e:
                    logger.error(f"Ошибка обновления делегированной задачи в TickTick: {e}")
            
            return {
                'success': True,
                'delegate': delegate['name'],
                'instructions': instructions
            }
            
        except Exception as e:
            logger.error(f"Ошибка делегирования задачи: {e}")
            return {'error': str(e)}
    
    def generate_delegation_instructions(self, task: Dict[str, Any], delegate: Dict[str, Any]) -> str:
        """Генерировать инструкции для делегата"""
        instructions = f"Задача для {delegate['name']}:\n\n"
        instructions += f"📋 {task['title']}\n\n"
        
        if task.get('description'):
            instructions += f"Описание: {task['description']}\n\n"
        
        if task.get('due_date'):
            instructions += f"⏰ Срок: {task['due_date'].strftime('%d.%m.%Y %H:%M')}\n\n"
        
        if task.get('steps'):
            instructions += "📝 План действий:\n"
            for i, step in enumerate(task['steps'], 1):
                instructions += f"{i}. {step}\n"
            instructions += "\n"
        
        # Специфичные инструкции в зависимости от типа делегата
        if delegate['type'] == 'personal':
            instructions += "💡 Рекомендации:\n"
            instructions += "• Уточни детали, если что-то непонятно\n"
            instructions += "• Сообщи о завершении\n"
        elif delegate['type'] == 'marketing_creative':
            instructions += "🎨 Креативные требования:\n"
            instructions += "• Следуй брендбуку\n"
            instructions += "• Покажи варианты перед финализацией\n"
        elif delegate['type'] == 'marketing_strategy':
            instructions += "📊 Стратегические моменты:\n"
            instructions += "• Проанализируй эффективность\n"
            instructions += "• Предложи оптимизации\n"
        
        return instructions
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Получить активные задачи"""
        tasks = self.load_tasks()
        return [t for t in tasks if t.get('status') in ['pending', 'in_progress']]
    
    def get_delegated_tasks(self) -> Dict[str, List[Dict[str, Any]]]:
        """Получить делегированные задачи по исполнителям"""
        tasks = self.load_tasks()
        delegated = {}
        
        for delegate_key in self.delegates.keys():
            delegated[delegate_key] = [
                t for t in tasks 
                if t.get('delegated_to') == delegate_key and t.get('status') == 'delegated'
            ]
        
        return delegated
    
    async def sync_with_ticktick(self) -> Dict[str, Any]:
        """Синхронизация с TickTick"""
        try:
            # Проверяем подключение
            if not await self.ticktick.test_connection():
                return {
                    'success': False,
                    'error': 'Не удается подключиться к TickTick'
                }
            
            # Получаем задачи из TickTick
            ticktick_tasks = await self.ticktick.get_all_tasks()
            local_tasks = self.load_tasks()
            
            synced_count = 0
            new_tasks = 0
            
            # Синхронизируем задачи из TickTick в локальную базу
            for tt_task in ticktick_tasks:
                tt_id = tt_task.get('id')
                
                # Ищем задачу в локальной базе
                local_task = None
                for lt in local_tasks:
                    if lt.get('external_id') == tt_id:
                        local_task = lt
                        break
                
                if local_task:
                    # Обновляем существующую задачу
                    if tt_task.get('status') == 2:  # completed
                        local_task['status'] = 'completed'
                        synced_count += 1
                else:
                    # Создаем новую задачу из TickTick
                    new_task = await self.ticktick.sync_task_to_bot(tt_task)
                    if new_task:
                        new_task['id'] = len(local_tasks) + new_tasks + 1
                        local_tasks.append(new_task)
                        new_tasks += 1
            
            # Сохраняем обновленные задачи
            self.save_tasks(local_tasks)
            
            return {
                'success': True,
                'synced_count': synced_count,
                'new_tasks': new_tasks,
                'total_ticktick_tasks': len(ticktick_tasks)
            }
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации с TickTick: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_task_summary(self, task_id: int) -> str:
        """Получить подробную сводку по задаче"""
        try:
            tasks = self.load_tasks()
            task = None
            
            for t in tasks:
                if t['id'] == task_id:
                    task = t
                    break
            
            if not task:
                return "❌ Задача не найдена"
            
            summary = f"📋 **{task['title']}**\n\n"
            
            if task.get('description'):
                summary += f"📝 **Описание:** {task['description']}\n\n"
            
            summary += f"📊 **Статус:** {task.get('status', 'неизвестно')}\n"
            summary += f"🎯 **Приоритет:** {task.get('priority', 'средний')}\n"
            summary += f"⏱️ **Время:** {task.get('estimated_time', 'не определено')}\n"
            
            if task.get('due_date'):
                summary += f"📅 **Срок:** {task['due_date'].strftime('%d.%m.%Y %H:%M')}\n"
            
            if task.get('delegated_to'):
                delegate_name = self.delegates[task['delegated_to']]['name']
                summary += f"👥 **Делегировано:** {delegate_name}\n"
            
            if task.get('external_id'):
                summary += f"🔄 **TickTick ID:** {task['external_id']}\n"
            
            if task.get('steps'):
                summary += f"\n📝 **План действий:**\n"
                for i, step in enumerate(task['steps'], 1):
                    summary += f"{i}. {step}\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Ошибка получения сводки задачи: {e}")
            return f"❌ Ошибка: {str(e)}"

