# Демонстрация

В этой папке собраны материалы, сессии-демонстрации работы AI-агента.

## Содержание

| Папка / Файл | Описание |
|--------------|----------|
| `dialog_screenshots/` | Скриншоты переписки с ботом |
| `logs_examples/` | Примеры логов работы агента |
| `presentation/` | Презентации, созданные ботом |

## Логи

Директория `logs_examples/` содержит примеры реальных логов:

### Chat logs (`chat_logs.log`)

Содержит события Telegram-бота:
- Запуск команд (`/start`, `/about`, `/CreatePresentation`, `/restart`)
- Обработка входящих сообщений
- Запросы к внешним API (Yandex Travel, OpenRouter, Presenton)
- Ошибки и предупреждения

Пример:
```
[CHAT LOGS]: INFO | Передача команды `/start` в бота
[CHAT LOGS]: INFO | Успешное завершение команды `/start`
[AGENT LOGS]: INFO | Старт передачи сообщения пользователя: Какие аэропорты есть в Москве?
[AGENT LOGS]: INFO | Передача сообщения и получения ответа от агента завершилась успешно
```

### TAO logs (`tao_logs.log`)

Содержит полный цикл мыслей AI-агента (Think, Act, Observe):

- `HUMAN MESSAGE` — сообщения пользователя
- `THOUGHT` — рассуждения агента перед действием
- `ACTION` — вызовы инструментов с параметрами
- `OBSERVATION` — результаты выполнения инструментов
- `FINAL ANSWER` — финальный ответ пользователю
- `Statistics` — количество TAO-циклов, вызовов инструментов и время ответа

Пример:
```
[TAO LOGS]: INFO | HUMAN MESSAGE: Какие аэропорты есть в Москве?
[TAO LOGS]: INFO | Обработка (AIMessage - Think/Act)
[TAO LOGS]: INFO | --- TAO Step 1 ---
[TAO LOGS]: INFO | Обработка шага сообщения (AIMessage - Think)
[TAO LOGS]: INFO | THOUGHT: User asks: which airports are in Moscow. Need get_airport_data mode city ru_name "Москва".
[TAO LOGS]: INFO | Обработка сообщения (AIMessage - Act)
[TAO LOGS]: INFO | ACTION: get_airport_data({"mode": "city", "ru_name": "Москва"})
[TAO LOGS]: INFO | Обработка сообщения (ToolMessage - Observe)
[TAO LOGS]: INFO | OBSERVATION: {...}
[TAO LOGS]: INFO | FINAL ANSWER: В Москве находятся следующие аэропорты: Шереметьево (IATA SVO), Внуково (IATA VKO), Домодедово (IATA DME), Быково (IATA BKA) и Остафьево (IATA OSF).
[TAO LOGS]: INFO | Обработка статистики по ответу
[TAO LOGS]: INFO | Statistics: TAO cycles: 1 | Tool calls: 1 | Time: 7.18 s
```