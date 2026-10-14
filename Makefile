# Pintasan pengembangan. Jalankan `make` untuk daftar target.
.DEFAULT_GOAL := bantuan
COMPOSE ?= docker compose
PG_URL   = postgresql+asyncpg://$$(grep ^POSTGRES_USER ../.env | cut -d= -f2):$$(grep ^POSTGRES_PASSWORD ../.env | cut -d= -f2)@localhost:5432

bantuan: ## Tampilkan daftar target
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

env: ## Buat .env dari contoh dengan rahasia acak
	@test -f .env || (cp .env.example .env && python3 scripts/buat_rahasia.py .env && echo ".env dibuat")

naik: env ## Bangun dan jalankan semua layanan (http://localhost:8088)
	$(COMPOSE) up -d --build

turun: ## Hentikan semua layanan (data tetap)
	$(COMPOSE) down

reset: ## Hentikan dan HAPUS seluruh data (volume)
	$(COMPOSE) down -v

log: ## Ikuti log api dan worker
	$(COMPOSE) logs -f api worker

seed-demo: ## Data contoh (akun semua peran, instrumen demo). Sandi acak, atau: make seed-demo DEMO_PASSWORD='...'
	$(COMPOSE) exec -T $(if $(DEMO_PASSWORD),-e DEMO_PASSWORD='$(DEMO_PASSWORD)') api python -m app.cli seed-demo

buat-dekan: ## Buat akun Dekan awal: make buat-dekan EMAIL=dekan@kampus.ac.id NAMA="Prof. X"
	$(COMPOSE) exec api python -m app.cli buat-pengguna --email $(EMAIL) --nama "$(NAMA)" --peran dekan

psql: ## Konsol PostgreSQL
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-simak} -d $${POSTGRES_DB:-simak}

migrasi: ## Jalankan migrasi Alembic di kontainer api
	$(COMPOSE) exec api alembic upgrade head

uji: ## Uji backend (unit + API; butuh Postgres dari compose)
	$(COMPOSE) up -d postgres
	$(COMPOSE) exec -T postgres psql -U $${POSTGRES_USER:-simak} -d postgres -c "DROP DATABASE IF EXISTS simak_test" -c "CREATE DATABASE simak_test"
	cd backend && TEST_DATABASE_URL="$(PG_URL)/simak_test" uv run pytest -q

uji-unit: ## Uji unit saja (tanpa basis data)
	cd backend && uv run pytest tests/unit -q

lint: ## Ruff (backend)
	cd backend && uv run ruff check . && uv run ruff format --check .

tipe-fe: ## Pemeriksaan tipe frontend (lewat Docker)
	docker run --rm -v "$$PWD/frontend":/app -w /app node:22-alpine sh -c "npm install --no-audit --no-fund >/dev/null && npx tsc --noEmit"

.PHONY: bantuan env naik turun reset log seed-demo buat-dekan psql migrasi uji uji-unit lint tipe-fe
