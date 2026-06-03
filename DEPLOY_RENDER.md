# Deploying QuizApp

**Host:** Render (web service) · **Database:** Supabase PostgreSQL · **Media:** Cloudflare R2

Everything needed is already in the repo:

- `render.yaml` — the Blueprint (web service + env vars; secrets via `sync: false`)
- `requirements.txt` — `gunicorn`, `dj-database-url`, `psycopg2-binary`, `whitenoise`, `django-storages`, `boto3`
- `quiz_app/quiz_app/settings.py` — reads `DATABASE_URL` and the `AWS_*` R2 vars from the environment; falls back to SQLite + local media when they're absent (so local dev is unchanged)

Do the two prerequisites first (Supabase + R2) so their values exist when you
create the Render stack — the first deploy runs `migrate` against the database.

---

## 1. Supabase database

1. Create a project at <https://supabase.com> and set a database password.
2. **Project Settings → Database → Connection string → "Session pooler"** and
   copy the URI. It looks like:

   ```
   postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
   ```

   Use the **Session pooler** string (IPv4 + SSL) — Render's outbound is IPv4 and
   the direct `db.<ref>.supabase.co` host is often IPv6-only. The app already
   forces SSL (`sslmode=require`) when `DEBUG=False`.

   That URI is your **`DATABASE_URL`**.

> Free Supabase pauses after ~7 days of inactivity (one click to resume); it
> does **not** delete your data on a timer. Limits ~500 MB DB — plenty here.

---

## 2. Cloudflare R2 bucket (media)

1. In the Cloudflare dashboard open **R2** and **Create bucket** (e.g. `quizapp-media`).
2. **R2 → Manage API Tokens → Create API token** with *Object Read & Write* on
   that bucket. Copy the **Access Key ID** and **Secret Access Key**.
3. Note your S3 endpoint (shown in R2): `https://<account_id>.r2.cloudflarestorage.com`
4. Make objects publicly viewable: bucket → **Settings → Public access** →
   enable the **r2.dev** public URL (gives `pub-xxxx.r2.dev`) or attach a custom
   domain. That hostname (no `https://`) is your **`AWS_S3_CUSTOM_DOMAIN`**.

Values you now have:

| Env var | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | R2 token Access Key ID |
| `AWS_SECRET_ACCESS_KEY` | R2 token Secret Access Key |
| `AWS_STORAGE_BUCKET_NAME` | `quizapp-media` |
| `AWS_S3_ENDPOINT_URL` | `https://<account_id>.r2.cloudflarestorage.com` |
| `AWS_S3_CUSTOM_DOMAIN` | `pub-xxxx.r2.dev` (or your custom domain) |

> Free R2: 10 GB storage and **no egress fees**.

---

## 3. Create the Render stack

1. Push the latest code to GitHub (done if you're reading this in the repo).
2. Render dashboard: **New + → Blueprint → pick `Fantasticlegend1000/QuizApp`**.
3. Render reads `render.yaml` and prompts for the `sync: false` secrets — paste
   the `DATABASE_URL` from step 1 and the five R2 values from step 2.
4. **Apply.** The first deploy installs deps, runs `collectstatic`, and runs
   `migrate` against Supabase (creating the empty tables).

Live at `https://quizapp-XXXX.onrender.com` (empty until you load data next).

> Free Render web services sleep after ~15 min idle (~30 s cold start). Upgrade
> to keep it warm.

---

## 4. Load your existing data into Supabase

Your existing data was exported to **`render_data.json`** (2 users, 211 written
questions, MCQs, flashcards, connect, audiovisual, facts, archive). It is **not**
committed (it contains password hashes) — keep it private. Load it from your
machine straight into Supabase:

```bash
pip install -r requirements.txt

#   macOS/Linux:
export DATABASE_URL="postgresql://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres"
export DJANGO_SECRET_KEY="anything-nonempty"
export DJANGO_DEBUG="False"
#   Windows PowerShell:  $env:DATABASE_URL = "postgresql://..."  etc.

cd quiz_app
python manage.py migrate          # safe to re-run; tables already exist
python manage.py loaddata ../render_data.json
```

`loaddata` restores the two users with their original passwords, so existing
logins keep working.

---

## 5. Upload your existing media to R2

A management command copies the local `media/` files to R2 and rewrites the DB
references. Run it from your machine (which still has `media/`), pointed at the
**same** Supabase DB and R2 bucket:

```bash
export DATABASE_URL="postgresql://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres"
export AWS_ACCESS_KEY_ID="...r2 access key..."
export AWS_SECRET_ACCESS_KEY="...r2 secret..."
export AWS_STORAGE_BUCKET_NAME="quizapp-media"
export AWS_S3_ENDPOINT_URL="https://<account_id>.r2.cloudflarestorage.com"
export AWS_S3_CUSTOM_DOMAIN="pub-xxxx.r2.dev"
export DJANGO_SECRET_KEY="anything-nonempty"
export DJANGO_DEBUG="False"

cd quiz_app
python manage.py migrate_media_to_storage --dry-run   # preview (19 files)
python manage.py migrate_media_to_storage             # upload + fix references
```

Run this **after** step 4 (it updates the rows that `loaddata` created). New
uploads through the Django admin then go to R2 automatically.

---

## 6. Regenerating the data fixture (if needed)

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

(Plain `manage.py dumpdata` crashes on the local Python 3.9 / Django 3.2 / SQLite
combo with a streaming-cursor bug, hence the materialized-list approach.)
