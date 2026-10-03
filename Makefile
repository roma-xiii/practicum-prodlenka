.PHONY: help install server client dev

help:
	@echo "make install  - установить зависимости server и client"
	@echo "make server   - запустить FastAPI в dev-режиме (http://localhost:8000)"
	@echo "make client   - запустить Next.js в dev-режиме (http://localhost:3000)"
	@echo "make dev      - запустить server и client параллельно"

install:
	cd server && python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
	cd client && npm install

server:
	cd server && ./.venv/bin/uvicorn app.main:app --reload --port 8000

client:
	cd client && npm run dev

dev:
	$(MAKE) -j2 server client
