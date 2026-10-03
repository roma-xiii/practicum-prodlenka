# Practicum-Prodlenka

## Структура

- `client/` — приложение на Next.js (App Router, TypeScript, Tailwind).
- `server/` — API-сервер на FastAPI.
- `source/` — материалы и данные проекта (скрипты, идеи, скиллы).

## Запуск

### Через make

```bash
make install   # установить зависимости server и client
make dev       # запустить server и client параллельно
```

Отдельно: `make server` (FastAPI, http://localhost:8000) и `make client`
(Next.js, http://localhost:3000). Список команд — `make help`.

### Server

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Проверка: http://localhost:8000/health

### Client

```bash
cd client
npm install
cp .env.local.example .env.local
npm run dev
```

Приложение: http://localhost:3000

Клиент обращается к серверу по адресу из `NEXT_PUBLIC_API_URL` (по умолчанию
`http://localhost:8000`). Убедитесь, что сервер запущен, иначе кнопка проверки
покажет ошибку подключения.
