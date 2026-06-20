import time
import json
import logging
import asyncio
from langchain_core.messages import HumanMessage
from agent.flights_agent import agent

# Настройка двух отдельных логгеров
def setup_loggers():
    """
    Настройка двух логгеров для чата и TAO
    """
    # Логгер для чата
    agent_logger = logging.getLogger('agent_logs')
    agent_logger.setLevel(logging.INFO)
    agent_logger.propagate = False
    
    # Логгер для TAO
    tao_logger = logging.getLogger('tao_logs')
    tao_logger.setLevel(logging.INFO)
    tao_logger.propagate = False
    
    # Очищаем существующие обработчики
    agent_logger.handlers.clear()
    tao_logger.handlers.clear()
    
    # Создаем файловые обработчики
    agent_handler = logging.FileHandler(
        filename="../logs/chat_logs.log",
        mode="a",
        encoding='utf-8'
    )
    tao_handler = logging.FileHandler(
        filename="../logs/tao_logs.log",
        mode="a",
        encoding='utf-8'
    )
    
    agent_formatter = logging.Formatter('[AGENT LOGS]: %(levelname)s | %(message)s')
    tao_formatter = logging.Formatter('[TAO LOGS]: %(levelname)s | %(message)s')
    agent_handler.setFormatter(agent_formatter)
    tao_handler.setFormatter(tao_formatter)
    
    # Добавляем обработчики к логгерам
    agent_logger.addHandler(agent_handler)
    tao_logger.addHandler(tao_handler)
    
    return agent_logger, tao_logger

agent_logger, tao_logger = setup_loggers()

async def collect_tao_logs(result, start_time):
    """
    Фоновый сбор TAO логов в том же формате, что и у вас
    """
    try:
        agent_logger.info('Запуск фонового сбора TAO логов')
        
        elapsed = time.time() - start_time
        tool_count = 0
        step_num = 0
        all_messages = result['messages']
        
        last_human_idx = -1
        for i, msg in enumerate(all_messages):
            if type(msg).__name__ == 'HumanMessage':
                last_human_idx = i
        current_messages = all_messages[last_human_idx:]
        
        for msg in current_messages:
            msg_type = type(msg).__name__

            if msg_type == 'HumanMessage':
                tao_logger.info(f'Обработка сообщения (HumanMessage)')
                tao_logger.info(f'HUMAN MESSAGE: {msg.content}')
            
            elif msg_type == 'AIMessage' and hasattr(msg, 'tool_calls') and msg.tool_calls:
                tao_logger.info(f'Обработка (AIMessage - Think/Act)')
                step_num += 1
                for tc in msg.tool_calls:
                    tool_count += 1
                    tao_logger.info(f'--- TAO Step {step_num} ---')
                    if not msg.content and msg.additional_kwargs:
                        tao_logger.info(f'Обработка шага сообщения (AIMessage - Think)')
                        tao_logger.info(f'THOUGHT: {msg.additional_kwargs['reasoning_content']}')
                    tao_logger.info(f'Обработка сообщения (AIMessage - Act)')
                    tao_logger.info(f'ACTION: {tc["name"]}({json.dumps(tc["args"], ensure_ascii=False)})')
                        
            elif msg_type == 'ToolMessage':
                tao_logger.info(f'Обработка сообщения (ToolMessage - Observe)')
                tao_logger.info(f'OBSERVATION: {msg.content}') 
                
            elif msg_type == 'AIMessage' and not getattr(msg, 'tool_calls', None):
                if msg.content and msg != result['messages'][0]:
                    tao_logger.info(f'FINAL ANSWER: {msg.content}')         
        
        # Статистика
        tao_logger.info(f'Обработка статистики по ответу')
        tao_logger.info(f'Statistics: TAO cycles: {step_num} | Tool calls: {tool_count} | Time: {elapsed:.2f} s')
        agent_logger.info(f'Фоновый сбор TAO логов завершен')
        
    except Exception as e:
        agent_logger.error(f'Ошибка при сборе TAO логов: {e}', exc_info=True)

async def run_and_trace(agent, config, query: str):
    """
    Функция для запуска агента и сбора логов в фоне
    Возвращает ответ для пользователя и фоновую задачу
    """
    agent_logger.info('Запуск функции agent_wrapper.run_and_trace()')
    start_time = time.time()
    
    result = None
    try:
        result = await agent.ainvoke({'messages': [HumanMessage(content=query)]}, config=config)
        agent_logger.info('Передача сообщения и получения ответа от агента завершилась успешно')
    except Exception as e:
        agent_logger.error(f'Передача сообщения и получения ответа от агента завершилась ошибкой: {e}', exc_info=True)
        #return f"Произошла ошибка при выполнении запроса агента: {e}", None
        return f"Произошла ошибка при выполнении запроса агента: {e}"

    if result is None:
        #return "Ошибка: агент не вернул результат.", None
        return "Ошибка: агент не вернул результат."

    # Получаем финальный ответ для пользователя
    user_response = "Ошибка: нет сообщений в ответе"
    if 'messages' in result and len(result['messages']) > 0:
        last_message = result['messages'][-1]
        if hasattr(last_message, 'content') and last_message.content:
            user_response = last_message.content
    
    # Запускаем фоновый сбор TAO логов
    asyncio.create_task(collect_tao_logs(result, start_time))
    
    # Возвращаем ответ пользователю
    return user_response

async def process_message(user_message: str, user_id: int, collect_tao_logs: bool = True) -> str:
    """
    Обработка сообщения пользователя
    """
    try:
        config = {"configurable": {"thread_id": str(user_id)}}
        
        # Запускаем агента и собираем логи в фоне
        agent_logger.info(f'Старт передачи сообщения пользователя: {user_message}')
        if collect_tao_logs:
            response_content = await run_and_trace(agent, config, user_message)
            agent_logger.info(f'Ответ отправлен пользователю, фоновый сбор логов TAO цикла запущен')
        else:
            response_content = await agent.ainvoke({'messages': [HumanMessage(content=user_message)]}, config=config)
            agent_logger.info(f'Ответ отправлен пользователю, фоновый сбор логов TAO цикла отключен')
        
        return response_content
    
    except Exception as e:
        agent_logger.error(f'Асинхронный вызов агента завершился ошибкой: {e}', exc_info=True)
        raise