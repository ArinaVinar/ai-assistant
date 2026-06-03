# Navigator AI API

API-сервис AI-ассистента для программного комплекса «Навигатор».

## Основная логика

Сервис принимает запрос пользователя через OpenAI-compatible endpoint, определяет тип запроса и запускает агентный пайплайн:

- вопросы по навигации обрабатываются через Neo4j;
- вопросы по геологическим знаниям обрабатываются через PostgreSQL;
- генерация ответа выполняется через Ollama;
- оркестрация пайплайна реализована через LangGraph.

## Стек

- Python
- FastAPI
- LangGraph
- Neo4j
- PostgreSQL + pgvector
- Ollama
- sentence-transformers

## Запуск

1. Установить зависимости:

```bash
pip install -r requirements.txt
```

2. Создать .env по примеру .env.example.
3. Запустить API:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
4. Проверить сервис:
```bash
curl http://127.0.0.1:8000/api/health
```
Base URL OpenWebUI:
```bash
http://127.0.0.1:8000/v1
```