# FastAPI server

Минимальный API-сервер на FastAPI.

## Запуск

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Эндпоинты

- `GET /health` — проверка работоспособности.
- `GET /api/hello` — тестовый ответ.

Документация OpenAPI: http://localhost:8000/docs

## Переменные окружения

Скопируйте `.env.example` в `.env` и при необходимости измените значения:

- `APP_ENV` — окружение приложения.
- `CORS_ORIGINS` — список разрешённых origin через запятую.
