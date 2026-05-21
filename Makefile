.PHONY: dev next backend frontend frontend-next install install-next fmt

PY ?= python3
PORT_BACKEND ?= 8000
PORT_FRONTEND ?= 3000
PORT_NEXT ?= 3001

install:
	$(PY) -m venv backend/.venv
	./backend/.venv/bin/pip install -U pip
	./backend/.venv/bin/pip install -r backend/requirements.txt

install-next:
	cd frontend-next && npm install

backend:
	cd backend && ../backend/.venv/bin/uvicorn app.main:app --reload --port $(PORT_BACKEND)

frontend:
	cd frontend/public && $(PY) -m http.server $(PORT_FRONTEND)

frontend-next:
	cd frontend-next && npm run dev

dev: ## 后端 :8000 + 老静态前端 :3000
	@echo "→ Backend       http://localhost:$(PORT_BACKEND)/docs"
	@echo "→ Frontend (静态) http://localhost:$(PORT_FRONTEND)"
	@trap 'kill 0' INT; \
	  $(MAKE) backend & \
	  $(MAKE) frontend & \
	  wait

next: ## 后端 :8000 + Next.js :3001（推荐）
	@echo "→ Backend         http://localhost:$(PORT_BACKEND)/docs"
	@echo "→ Frontend (Next) http://localhost:$(PORT_NEXT)"
	@trap 'kill 0' INT; \
	  $(MAKE) backend & \
	  $(MAKE) frontend-next & \
	  wait
