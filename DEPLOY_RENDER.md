# Deploying QuizApp to Render (with managed PostgreSQL)

This guide deploys the app to [Render](https://render.com) using a managed
PostgreSQL database and loads your existing quiz data into it.

The repo already contains everything needed:

- `render.yaml` — the Blueprint (web service + Postgres + env vars)
- `requirements.txt` — includes `gunicorn`, `psycopg2-binary`, `dj-database-url`, `whitenoise`
- `quiz_app/quiz_app/settings.py` — reads `DATABASE_URL`, `DJANGO_SECRET_KEY`,
  `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` from the environment

---

## 1. Create the stack from the Blueprint

1. Push the latest code to GitHub (already done if you're reading this in the repo).
2. In the Render dashboard: **New +  →  Blueprint**.
3. Select the **`Fantasticlegend1000/QuizApp`** repo and approve.
4. Render reads `render.yaml`, then creates:
   - a PostgreSQL database `quizapp-db`
   - a web service `quizapp`
   - a generated `DJANGO_SECRET_KEY`, and `DATABASE_URL` wired from the DB.
5. Click **Apply**. The first deploy runs the build command, which installs
   dependencies, runs `collectstatic`, and applies all migrations (creating the
   empty tables in Postgres).

When it finishes, the site is live at `https://quizapp-XXXX.onrender.com`
(empty — no questions/users yet; that's the next step).

> Note: on Render's **free** tier the web service sleeps after ~15 min idle
> (first request after that takes ~30s to wake), and free Postgres has storage
> limits and an expiry date. Upgrade either to a paid plan for production.

---

## 2. Load your existing data into the Render database

Your existing data (2 users, 211 written questions, MCQs, flashcards, connect,
audiovisual, facts, archive) was exported to **`render_data.json`**. This file
is **not** in the repo because it contains user password hashes — keep it
private. (If you don't have it, regenerate it from the local SQLite DB — see
section 4.)

Load it straight into the Render Postgres from your own machine:

1. In the Render dashboard open the **quizapp-db** database and copy its
   **External Database URL** (starts with `postgres://...`).
2. From the project root on your machine:

   ```bash
   # one-time: install the deps locally so manage.py can talk to Postgres
   pip install -r requirements.txt

   # point Django at the Render database (use the EXTERNAL url)
   #   Windows PowerShell:  $env:DATABASE_URL = "postgres://...."
   #   macOS/Linux:         export DATABASE_URL="postgres://...."
   export DATABASE_URL="postgres://USER:PASSWORD@HOST/DB"
   export DJANGO_SECRET_KEY="anything-nonempty"
   export DJANGO_DEBUG="False"

   cd quiz_app
   python manage.py migrate          # safe to re-run; tables already exist
   python manage.py loaddata ../render_data.json
   ```

   `loaddata` restores the rows, including the two users with their original
   passwords, so existing logins keep working.

3. Reload the site — your questions and accounts are now there.

---

## 3. Media files (images / audio / video)  ⚠️ follow-up needed

Postgres stores your **data**, but the ~458 MB of uploaded **media** (Connect
images, AudioVisual clips, Archive files) are real files. Render's default web
filesystem is ephemeral, so:

- the rows load fine, but their images/clips will 404 until media has a home, and
- any new uploads through the admin won't survive a redeploy.

Pick one of:

- **Render persistent disk** — attach a disk to the web service, mount it at the
  media root, and upload the existing `media/` folder to it (requires a paid
  instance).
- **External object storage** — e.g. Cloudinary or S3 via `django-storages`
  (Cloudinary has a usable free tier). This is the more cloud-native choice.

Ask and I can wire up either one (the Cloudinary route is a small settings +
requirements change).

---

## 4. Regenerating the data fixture (if needed)

From the project root, against your local SQLite DB:

```bash
cd quiz_app
python manage.py shell -c "
from django.core import serializers
from django.contrib.auth import get_user_model
from quiz.models import Question, MCQ, Written, Connect, AudioVisual, Facts, Archive
objs = list(get_user_model().objects.all())
for M in [Question, MCQ, Written, Connect, AudioVisual, Facts, Archive]:
    objs += list(M.objects.all())
open('../render_data.json','w',encoding='utf-8').write(serializers.serialize('json', objs, indent=2))
"
```

(The plain `manage.py dumpdata` command crashes on the local Python 3.9 / Django
3.2 / SQLite combo with a streaming-cursor bug, hence the materialized-list
approach above.)
