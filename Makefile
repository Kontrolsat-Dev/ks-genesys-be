# -------- Virtualenv & tooling (cross-platform) --------
VENV ?= .venv

ifeq ($(OS),Windows_NT)
PYTHON  := $(VENV)/Scripts/python.exe
PIP     := $(VENV)/Scripts/pip.exe
else
PYTHON  := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip
endif

UVICORN := $(PYTHON) -m uvicorn

# Se quiseres usar uv pip, chama:  make dev UV=uv
UV ?=

# -------- App config --------
APP       ?= apps.api_main:app
HOST      ?= 127.0.0.1
HOST_LIVE ?= 0.0.0.0
PORT      ?= 8000
LOG_LEVEL ?= debug

.PHONY: venv install dev prod clean worker

## Cria o virtualenv (se não existir)
ifeq ($(OS),Windows_NT)
venv:
	@if not exist "$(VENV)" ( py -3 -m venv "$(VENV)" || python -m venv "$(VENV)" )
else
venv:
	@test -d "$(VENV)" || python3 -m venv "$(VENV)"
endif

## Instala dependências
# - Se UV=uv, usa uv pip
# - Caso contrário, usa python -m pip (evita o erro de atualizar pip via pip.exe)
install: venv
ifdef UV
	$(UV) pip install -r requirements.txt
else
	$(PYTHON) -m pip install --upgrade pip wheel
	$(PYTHON) -m pip install -r requirements.txt
endif

## Arranca o servidor em modo dev (reload)
dev: install
	$(UVICORN) $(APP) --host $(HOST) --port $(PORT) --reload --log-level $(LOG_LEVEL)

## Arranca o servidor em modo "prod simples" (sem debug host)
prod: install
	$(UVICORN) $(APP) --host $(HOST_LIVE) --port $(PORT) --reload --log-level $(LOG_LEVEL)

## Limpa artefactos básicos
clean:
	@rm -rf __pycache__ .pytest_cache .mypy_cache || true

## Workers (entrypoint oficial dos jobs)
worker: install
	$(PYTHON) -m apps.worker_main
