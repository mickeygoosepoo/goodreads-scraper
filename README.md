# Goodreads Scraper

A Python web scraper that collects book data from Goodreads and stores it in a normalized SQLite database. Built as a learning project covering core CS and software engineering concepts.

## Project Files

| File | Purpose |
|------|---------|
| `fetcher.py` | HTTP requests — fetches raw HTML from Goodreads |
| `parsers.py` | HTML parsing — extracts structured data from raw HTML |
| `db.py` | Database layer — normalized schema, SQL queries, transactions |
| `pipeline.py` | Orchestration — combines fetcher + parser + db into one flow |
| `tasks.py` | Background jobs — Celery tasks for async scraping |
| `celery_config.py` | Celery + Redis configuration |
| `app.py` | Flask web server — routes and dashboard |
| `templates/index.html` | Dashboard UI |
| `main.py` | Command-line entry point |
| `migrate_db.py` | One-time migration from old flat schema to normalized schema |
| `health_check.py` | Verify Redis, DB schema, and Flask are all running correctly |

## Database Schema

Four normalized tables linked by foreign keys:

```
authors     → books (one-to-many, via author_id FK)
books       ↔ genres (many-to-many, via book_genres junction table)
```

## How to Run

**1. Set up the virtual environment:**
```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

**2. Scrape books from the command line:**
```bash
./venv/bin/python3 main.py
```

**3. Run the web dashboard (requires Redis + Celery for background scraping):**
```bash
# Terminal 1 — Redis (install via: brew install redis)
brew services start redis

# Terminal 2 — Celery worker
./venv/bin/celery -A tasks worker --loglevel=info

# Terminal 3 — Flask web server
./venv/bin/python3 app.py
# Open http://127.0.0.1:5000
```

## CS Concepts Covered

- **Database Normalization** (1NF, 2NF, 3NF) — `db.py`
- **Foreign Keys & Referential Integrity** — `db.py`
- **Many-to-Many Relationships & Junction Tables** — `db.py`, `migrate_db.py`
- **SQL JOINs** (INNER, LEFT, chained multi-table) — `db.py`
- **ACID Transactions** — `db.py`
- **Async / Concurrent Programming** — `fetcher.py`, `pipeline.py`, `tasks.py`
- **Message Queues & Distributed Systems** — `celery_config.py`, `tasks.py`
- **HTML Parsing** — `parsers.py`
- **Data Migration** — `migrate_db.py`
- **REST-style Routing** — `app.py`
