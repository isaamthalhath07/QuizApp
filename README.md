# Quizite

A playful, multi-mode quiz web app built with Django. Pick a mode and a category, then test yourself with multiple-choice, written, flashcard, "connect the images", and audiovisual questions — with lenient, typo-tolerant answer checking and a glassmorphism UI.

<!-- Add a screenshot here, e.g.: ![Quizite home](docs/home.png) -->

---

## Features

- **Five quiz modes**
  - **MCQ** — single- and multiple-answer questions with instant feedback and explanations.
  - **Written** — free-text answers, a lenient countdown timer, and forgiving matching.
  - **Flashcards** — tap to flip question/answer cards.
  - **Connect** — guess the link between a 2×2 grid of images.
  - **Audiovisual** — answer from an audio or video clip.
- **Categories & sub-categories** (Science, Literature, History, Math, GK, Sports, Film, …) plus "All" and "Random".
- **Lenient answer matching, no LLM required** — deterministic normalization + edit-distance + word-order tolerance, so typos, casing, punctuation and reordering still count as correct. Authors can also define accepted variants with a small command syntax.
- **Archive** — browse past event media (images / audio / video).
- **Responsive** — works on mobile and desktop; **glassmorphism / bento** visual design.
- **Production-ready** — environment-driven settings, HTTPS hardening, WhiteNoise static serving with content-hashed cache-busting, Postgres + object-storage support.

## Tech stack

- **Backend:** Django 4.2 (Python)
- **Database:** SQLite (local) / PostgreSQL (production, e.g. Supabase)
- **Static files:** WhiteNoise (compressed + manifest/hashed in production)
- **Media storage:** local filesystem (local) / Cloudflare R2 or any S3-compatible store via `django-storages` (production)
- **Server:** Gunicorn
- **Frontend:** Django templates + vanilla JS + a single hand-written CSS design layer (no build step)

## Project structure

```
QuizApp/
├── requirements.txt
├── render.yaml              # Render deployment blueprint
├── DEPLOY_RENDER.md         # full deployment guide
└── quiz_app/                # Django project (run manage.py here)
    ├── manage.py
    └── quiz/                # the quiz app: models, views, templates, static
```

## Getting started (local)

Requirements: Python 3.9+ and `pip`.

```bash
git clone https://github.com/isaamthalhath07/QuizApp.git
cd QuizApp
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cd quiz_app
# DEBUG=True is required locally (so localhost is an allowed host)
export DJANGO_DEBUG=True
export DJANGO_SECRET_KEY=dev-only-secret                # Windows PowerShell: $env:DJANGO_DEBUG="True" etc.
python manage.py migrate
python manage.py createsuperuser                        # to add questions via the admin
python manage.py runserver
```

Open **http://127.0.0.1:8000/quiz/login/** (the site lives under `/quiz/`; `/` redirects there). Add content at **/admin/**.

### Configuration (environment variables)

| Variable | Purpose | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret key | random (set a stable one in prod) |
| `DJANGO_DEBUG` | `True`/`False` | `False` |
| `DJANGO_ALLOWED_HOSTS` | comma-separated hosts | localhost in DEBUG; `.onrender.com` etc. in prod |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | comma-separated origins | — |
| `DATABASE_URL` | Postgres URL (`dj-database-url`) | SQLite if unset |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | object-storage credentials | media on local FS if unset |
| `AWS_STORAGE_BUCKET_NAME` / `AWS_S3_ENDPOINT_URL` / `AWS_S3_CUSTOM_DOMAIN` | bucket + endpoint + public domain | — |

## Deployment

This repo ships a Render Blueprint (`render.yaml`) and a step-by-step guide in **[DEPLOY_RENDER.md](DEPLOY_RENDER.md)** covering Render (web), Supabase (Postgres), and Cloudflare R2 (media), including how to migrate existing data and media. The same Django app deploys to any host that can run Gunicorn with a Postgres database and S3-compatible media storage.

## Answer syntax (for question authors)

The written / connect / audiovisual rounds match answers leniently, and the stored answer can encode accepted variants:

- `;` separates independent accepted answers; `:` separates OR-alternatives.
- `/answer` — fuzzy match (typos/case/spacing/word-order tolerant). Example: `/mont blanc:/montblanc`.
- `/#answer` — spelling-tolerant (soundex). `/?answer` — exact, case-sensitive.

## Generating questions with Gemini

A management command can auto-author high-quality questions with Google's Gemini
API and insert them straight into the database in the correct format.

```bash
export GEMINI_API_KEY="...your key..."        # Windows PowerShell: $env:GEMINI_API_KEY="..."
cd quiz_app

# 10 challenging MCQs about Physics
python manage.py generate_questions --mode mcq --category Physics --count 10

# preview without saving
python manage.py generate_questions --mode written --category History --count 8 --dry-run
```

- **Modes:** `mcq`, `written`, `flashcard`, `facts`. (Connect / Audiovisual need
  media, so they are added via the admin.)
- **Options:** `--count`, `--model` (default `gemini-2.0-flash`, or `$GEMINI_MODEL`),
  `--temperature`, `--prompt-file`, `--dry-run`.
- **The prompts are editable.** Each mode's instructions live in
  `quiz/management/commands/prompts/<mode>.txt` — tweak them to change tone,
  difficulty, or focus, or pass your own with `--prompt-file`.
- Gemini returns clean JSON; the command validates it (e.g. an MCQ's correct
  answer must be one of its options) and formats it into the DB fields,
  including the written-answer matching syntax.

## License

No license specified yet — add one (e.g. MIT) if you intend others to reuse it.
