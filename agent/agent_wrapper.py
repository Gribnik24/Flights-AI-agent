import os
import time
import json
import logging
from langchain_core.messages import HumanMessage

from agent.flights_agent import agent


logging.basicConfig(level=logging.INFO, filename="../logs/chat_logs.log", filemode="a", encoding='utf-8')

async def run_and_trace(agent, config, query: str) -> str:
    """
    Функция для показа логов TAO цикла у ReAct агентов
    
    Args:
        agent: CompiledStateGraph агента
        config: Конфигурация с session_id и другими параметрами
        query: Запрос пользователя
        
    Returns:
        str: Отформатированные логи TAO цикла
    """
    logging.info('Запуск функции agent_wrapper.run_and_trace()')
    tao_logs = ''
    start_time = time.time()
    
    dialog_len = 0
    try:
        if hasattr(agent, 'memory') and agent.memory:
            if hasattr(agent.memory, 'chat_memory'):
                dialog_len = len(agent.memory.chat_memory.messages)
        elif hasattr(agent.memory, 'messages'):
            dialog_len = len(agent.memory.messages)
        session_id = config.get('configurable', {}).get('session_id', 'default')
        logging.info(f'Текущая длина истории для сессии {session_id}: {dialog_len}')
        
    except Exception as e:
        logging.warning(f'Не удалось получить длину истории: {e}')
        dialog_len = 0
    
    
    result = None
    try:
        logging.info(f'Старт передачи сообщения пользователя: {query[:200]}...' if len(query) > 200 else f'Старт передачи сообщения пользователя: {query}')
        result = await agent.ainvoke({'messages': [HumanMessage(content=query)]}, config=config)
        logging.info('Передача сообщения и получения ответа от агента завершилась успешно')
    except Exception as e:
        logging.error(f'Передача сообщения и получения ответа от агента завершилась ошибкой: {e}', exc_info=True)
        return f"Произошла ошибка при выполнении запроса агента: {e}"

    if result is None:
        return "Ошибка: агент не вернул результат."

    elapsed = time.time() - start_time

    tool_count = 0
    step_num = 0
    for msg in range(len(result['messages']) - 1): #doalog_len
        cur_msg = result['messages'][msg]
        msg_type = type(cur_msg).__name__

        if msg_type == 'HumanMessage':
            logging.info(f'Обработка сообщения {msg} (HumanMessage)')
            tao_logs = f'USER QUERY: {cur_msg.content}\n'
        
        elif msg_type == 'AIMessage' and hasattr(cur_msg, 'tool_calls') and cur_msg.tool_calls:
            logging.info(f'Обработка сообщения {msg} (AIMessage - Think/Act)')
            step_num += 1
            for tao_step, tc in enumerate(iterable=cur_msg.tool_calls, start=1):
                tool_count += 1
                tao_logs = f'--- TAO Step {step_num} ---\n'
                if cur_msg.content:
                    logging.info(f'Обработка шага {tao_step} сообщения {msg} (AIMessage - Think)')
                    tao_logs += f'THOUGHT: {cur_msg.content}\n'
                logging.info(f'Обработка шага {tao_step} сообщения {msg} (AIMessage - Act)')
                tao_logs += f'ACTION: {tc["name"]}({json.dumps(tc["args"], indent=2, ensure_ascii=False)})\n'

        elif msg_type == 'ToolMessage':
            content_preview = cur_msg.content
            logging.info(f'Обработка шага сообщения {msg} (ToolMessage - Observe)')
            tao_logs += f'OBSERVE: {content_preview}\n'

        elif msg_type == 'AIMessage' and not getattr(cur_msg, 'tool_calls', None):
            logging.info(f'Обработка финального ответа (AIMessage)')
            if cur_msg.content and cur_msg != result['messages'][0]:
                tao_logs += '\n--- Final Answer ---\n'
                tao_logs += f'{cur_msg.content}\n'

    logging.info(f'Обработка статистики по ответу')
    tao_logs += f'Statistics:\nTAO cycles: {step_num}\nTool calls: {tool_count}\nTime: {elapsed:.2f} s'
    return tao_logs


async def process_message(user_message: str, user_id: int, show_tao_logs: bool = False) -> str:
    try:
        config = {"configurable": {"thread_id": str(user_id)}}
        
        if show_tao_logs:
            tao_logs = await run_and_trace(agent=agent, config=config, query=user_message)
            return tao_logs
        
        logging.info(f'Старт передачи сообщения пользователя: {user_message[:50]}')
        response = await agent.ainvoke({"messages": [HumanMessage(content=user_message)]}, config=config)
        last_message = response["messages"][-1]
        logging.info('Успешное завершение асинхронного вызова агента')
        return last_message.content
    
    except Exception as e:
        logging.error(f'Асинхронный вызов агента завершился ошибкой: {e}', exc_info=True)
        raise