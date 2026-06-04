# Navigator AI Assistant API

API-сервис AI-ассистента для программного комплекса «Навигатор». Система принимает запрос пользователя из OpenWebUI, определяет тип вопроса и запускает агентный пайплайн.

Ассистент работает с двумя источниками данных:

* **Neo4j** — структура приложения «Навигатор»: вкладки, разделы, описания элементов интерфейса и связи между ними.
* **PostgreSQL** — геологические материалы, разбитые на смысловые блоки.

---

## Что делает проект

Система помогает пользователю:

* найти нужную вкладку или раздел в ПК «Навигатор»;
* получить краткое описание элемента интерфейса;
* получить пояснение по геологическим терминам;
* обработать смешанный запрос, где нужен и маршрут в интерфейсе, и предметное объяснение.


---

## Что нужно кроме кода

Перед запуском должны быть установлены и настроены:

1. **Python 3.11+**
2. **Ollama**
3. **OpenWebUI в Docker**
4. **Neo4j**
5. **PostgreSQL**
6. **pgvector для PostgreSQL**

---

## Установка проекта

Склонировать репозиторий:

```bash
git clone https://github.com/ArinaVinar/navigator-ai-api.git
cd navigator-ai-api
```

Создать виртуальное окружение:

```bash
python -m venv .venv
```

Активировать окружение на Windows:

```bash
.venv\Scripts\activate
```

Установить зависимости:

```bash
pip install -r requirements.txt
```

---

## Настройка `.env`

Создать файл `.env` на основе `.env.example`.

Пример:

```env
APP_HOST=0.0.0.0
APP_PORT=7777

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=navigator_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

POSTGRES_TOP_K=5
NEO4J_TOP_K=5

MAX_RETRIES=2
MIN_CONFIDENCE=0.65
```


---

## Подготовка внешних сервисов

### Ollama

Скачать модель:

```bash
ollama pull qwen2.5:7b
```

Проверить список моделей:

```bash
ollama list
```

---

### PostgreSQL

В PostgreSQL должна быть база данных `navigator_db`.

В базе должна быть таблица:

```sql
CREATE TABLE IF NOT EXISTS geology_blocks (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    embedding vector(384)
);
```

Также должно быть включено расширение:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

### Neo4j

В Neo4j должна быть загружена структура приложения «Навигатор».

Узлы должны иметь поля:

```text
id
name
description
embedding
```

Для семантического поиска нужно создать общий label:

```cypher
MATCH (n)
WHERE any(label IN labels(n) WHERE label IN [
  'Element',
  'InfoAdditional',
  'Item',
  'SubElement',
  'SubItem',
  'SubSubElement',
  'SubSubItem',
  'SubSubSubElement'
])
SET n:NavigatorNode;
```

Создать vector index:

```cypher
CREATE VECTOR INDEX navigator_node_embedding_index IF NOT EXISTS
FOR (n:NavigatorNode)
ON (n.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 384,
    `vector.similarity_function`: 'cosine'
  }
};
```

---

### OpenWebUI в Docker

Запуск OpenWebUI:

```bash
docker run -d ^
  -p 3001:8080 ^
  -v open-webui:/app/backend/data ^
  --name open-webui ^
  --restart always ^
  ghcr.io/open-webui/open-webui:main
```

OpenWebUI будет доступен по адресу:

```text
http://localhost:3001
```

---

## Запуск API

Запустить FastAPI-сервис:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 7777 --reload
```

Проверить работу API:

```bash
curl http://127.0.0.1:7777/api/health
```

---

## Подключение к OpenWebUI

В OpenWebUI добавить OpenAI-compatible connection.

Если OpenWebUI запущен локально:

```text
Base URL: http://127.0.0.1:7777/v1
API Key: navigator-key
Model ID: navigator-assistant
```

Если OpenWebUI запущен в Docker:

```text
Base URL: http://host.docker.internal:7777/v1
API Key: navigator-key
Model ID: navigator-assistant
```

