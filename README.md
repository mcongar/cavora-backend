# Cavora Backend

Smart pantry manager API built with Django REST Framework.

## Stack
- Python 3.12
- Django 5 + Django REST Framework
- PostgreSQL (SQLite for development)
- JWT Authentication

## Setup
```bash
git clone ...
cd cavora
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your values
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Environment variables

| Variable | Description |
|----------|-------------|
| SECRET_KEY | Django secret key |
| DEBUG | True/False |
| DATABASE_URL | Database connection string |
| ANTHROPIC_API_KEY | Claude API key |
| CORS_ALLOWED_ORIGINS | Allowed origins for CORS |

## Apps

- **users** — Auth, JWT, user preferences
- **catalog** — Product catalog, OFF integration, multilanguage
- **pantry** — User pantry, scan sessions, bulk add
- **alerts** — Expiry notifications

## API docs

Import `docs/cavora.postman_collection.json` in Postman.

## Pending

See `docs/backlog.md` for planned features.