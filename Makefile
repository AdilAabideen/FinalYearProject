SHELL := /bin/zsh

.PHONY: install install-backend install-frontend run run-backend run-frontend build-frontend

install: install-backend install-frontend

install-backend:
	cd backend && python3 -m pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

run-backend:
	cd backend && python3 run.py

run-frontend:
	cd frontend && npm run dev

run:
	@set -e; \
	trap 'kill 0' INT TERM EXIT; \
	(cd backend && python3 run.py) & \
	(cd frontend && npm run dev) & \
	wait

build-frontend:
	cd frontend && npm run build
