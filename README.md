# placsp-browser

API + ETL para explorar datos de licitaciones de la [Plataforma de Contratación del Sector Público](https://contrataciondelestado.es).

Optimizada para consumo por agentes de IA: búsqueda unificada, respuestas densas, códigos CODICE resueltos a etiquetas legibles.

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/buscar` | Búsqueda unificada: texto libre + filtros + cursor |
| GET | `/api/v1/licitacion/{id}` | Detalle completo (criterios, solvencia, lotes, docs) |
| GET | `/api/v1/empresa/{nif}` | Perfil de empresa con stats agregadas |
| GET | `/api/v1/organo/{id}` | Perfil de órgano con stats |
| GET | `/api/v1/similares/{id}` | Licitaciones similares (CPV + importe) |
| GET | `/api/v1/catalogos/{tipo}` | Valores válidos para filtros |

## Stack

- **API**: FastAPI + asyncpg + PostgreSQL 16
- **ETL**: Ingestión de feeds ATOM CODICE (hourly cron)
- **Búsqueda**: tsvector español + pg_trgm para fuzzy
- **Deploy**: Docker Compose + Caddy (auto-HTTPS) en Hetzner

## Deploy rápido

```bash
# Rellenar variables en deploy/cloud-init.yml y pegar en Hetzner al crear servidor.
# Después del boot:
ssh user@<ip>
cd placsp-browser/deploy
docker compose exec etl-cron sh -c \
  "cd /app && PYTHONPATH=src uv run python -m etl.handlers.feed_reader --seed"
```

## Desarrollo local

```bash
cp .env.example .env
uv sync
PYTHONPATH=src uv run pytest tests/
PYTHONPATH=src uv run uvicorn api.main:app --reload
```
