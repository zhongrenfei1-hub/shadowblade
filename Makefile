.PHONY: dev backend frontend install fmt

PY ?= python3
PORT_BACKEND ?= 8000
PORT_FRONTEND ?= 3000

install:
	$(PY) -m venv backend/.venv
	./backend/.venv/bin/pip install -U pip
	./backend/.venv/bin/pip install -r backend/requirements.txt

backend:
	cd backend && ../backend/.venv/bin/uvicorn app.main:app --reload --port $(PORT_BACKEND)

frontend:
	cd frontend/public && $(PY) -m http.server $(PORT_FRONTEND)

dev:
	@echo "→ Backend  http://localhost:$(PORT_BACKEND)/docs"
	@echo "→ Frontend http://localhost:$(PORT_FRONTEND)"
	@trap 'kill 0' INT; \
	  $(MAKE) backend & \
	  $(MAKE) frontend & \
	  wait
