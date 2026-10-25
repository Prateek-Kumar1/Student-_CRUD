# Students Database CRUD API

A Python backend for managing student records, built with **FastAPI** and **SQLite**.
Includes an **optional bonus**: a local-AI endpoint powered by **Ollama** that answers
natural-language questions about the stored data.

## Features
- Full CRUD: create, list/filter, view, update (PUT and PATCH) and delete students
- SQLite persistence (data survives restarts)
- Input validation (email format, phone format, DOB must be in the past, at least one contact method)
- Proper errors: `404` missing record, `409` duplicate email, `422` invalid input
- Filtering and pagination on the list endpoint
- Automated tests (pytest), dummy seed data, interactive Swagger docs
- Optional Ollama Q&A that is grounded in database records and never runs model-written SQL

## Project structure
```
students-crud/
├── app/
│   ├── main.py            # FastAPI app + startup (creates DB table)
│   ├── database.py        # SQLite connection + schema
│   ├── schemas.py         # Pydantic validation models
│   ├── crud.py            # All SQL (parameterised queries)
│   ├── ai_service.py      # Optional Ollama integration
│   └── routers/
│       ├── students.py    # CRUD endpoints
│       └── ai.py          # POST /ai/ask
├── tests/test_api.py      # 11 automated tests
├── seed.py                # Loads dummy sample students
├── requirements.txt
└── .env.example
```

## Prerequisites
- Python 3.10+
- (Optional, bonus only) [Ollama](https://ollama.com) installed

## Installation
```bash
git clone <your-repo-url>
cd students-crud
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```bash
python seed.py                     # optional: load 8 dummy students
uvicorn app.main:app --reload
```
Open **http://127.0.0.1:8000/docs** for interactive API docs. The database file
`students.db` is created automatically in the project folder.

## Run the tests
```bash
python -m pytest -q
```
Tests use a temporary database, so your `students.db` is never touched.

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/students` | Create a student |
| GET | `/students` | List / filter students |
| GET | `/students/{student_id}` | View one student |
| PUT | `/students/{student_id}` | Replace all details |
| PATCH | `/students/{student_id}` | Update only the fields sent |
| DELETE | `/students/{student_id}` | Delete a student |
| POST | `/ai/ask` | (Bonus) Ask a question about the data |

**Student fields:** `student_id` (auto), `name`*, `date_of_birth`* (YYYY-MM-DD), `email` and/or `phone`
(at least one required), `course`, `address`, `enrollment_date`.

**List filters (query params):** `name`, `course` (partial, case-insensitive), `email` (exact),
`born_after`, `born_before` (dates, inclusive), `skip`, `limit` (default 100, max 500).

### Example requests (curl)
```bash
# Create
curl -X POST http://127.0.0.1:8000/students -H "Content-Type: application/json" \
  -d '{"name":"Riya Mehta","date_of_birth":"2005-04-12","email":"riya@example.com","course":"Python Backend"}'

# List + filter
curl "http://127.0.0.1:8000/students"
curl "http://127.0.0.1:8000/students?course=data&born_after=2005-01-01"

# View one
curl http://127.0.0.1:8000/students/1

# Partial update
curl -X PATCH http://127.0.0.1:8000/students/1 -H "Content-Type: application/json" \
  -d '{"course":"Machine Learning"}'

# Full replace
curl -X PUT http://127.0.0.1:8000/students/1 -H "Content-Type: application/json" \
  -d '{"name":"Riya M.","date_of_birth":"2005-04-12","phone":"+91 98765 43210"}'

# Delete (returns 204 No Content)
curl -X DELETE http://127.0.0.1:8000/students/1
```

### Status codes
`200` OK · `201` Created · `204` Deleted · `400` empty PATCH · `404` not found ·
`409` duplicate email · `422` validation error

## Bonus: local AI with Ollama
The core app works without this. To enable it:
```bash
ollama pull llama3.2:1b
ollama serve                       # if not already running
```
Then:
```bash
curl -X POST http://127.0.0.1:8000/ai/ask -H "Content-Type: application/json" \
  -d '{"question":"List students born after 2005"}'
```
Supported question styles: *"How many students are there?"*, *"List students born after 2005"*,
*"born before 2004"*, *"born in 2006"*, *"How many students are in Data Science?"*, *"student named Aarav"*.

**How it stays safe and accurate**
1. The backend maps the question to a small set of fixed filters (course, birth year, name, count).
2. The backend runs parameterised queries itself and fetches the matching rows.
3. Only those rows (plus the exact total) are given to the model as context, with an instruction to answer from them only.
4. The response includes `records_used` and `filters_applied` so every answer can be verified.
5. The model never sees the schema and never executes SQL.

If Ollama isn't running, the endpoint still responds with a database-derived answer and `"ai_used": false`.
Change the model/host via `OLLAMA_MODEL` / `OLLAMA_URL` (see `.env.example`).

## Security notes
- All queries are parameterised (SQL-injection tested).
- Only dummy data is included; `*.db` and `.env` are git-ignored. Never commit real student data.
