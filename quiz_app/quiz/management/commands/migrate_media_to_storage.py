"""One-time migration of existing local media files to the configured storage.

After switching media storage to a remote backend (Cloudflare R2 / any
S3-compatible store), the database still references files by name but the files
themselves only exist in the local ``media/`` folder. This command reads each
referenced file from a local media root, uploads it through the field's storage
backend (R2 when the AWS_* env vars are set), and rewrites the database
reference to the stored name so the URLs resolve.

Typical use — run from a machine that still has the local ``media/`` folder,
pointed at the target database and bucket:

    # macOS/Linux
    export DATABASE_URL="postgres://...(Supabase session pooler url)..."
    export AWS_ACCESS_KEY_ID="...r2 access key..."
    export AWS_SECRET_ACCESS_KEY="...r2 secret..."
    export AWS_STORAGE_BUCKET_NAME="quizapp-media"
    export AWS_S3_ENDPOINT_URL="https://<account>.r2.cloudflarestorage.com"
    export AWS_S3_CUSTOM_DOMAIN="pub-xxxx.r2.dev"   # or your custom domain
    export DJANGO_SECRET_KEY="anything-nonempty"
    export DJANGO_DEBUG="False"
    cd quiz_app
    python manage.py migrate_media_to_storage --dry-run   # preview
    python manage.py migrate_media_to_storage             # upload + fix refs

Use --media-root to read from a media folder other than settings.MEDIA_ROOT.
"""

import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from quiz.models import Archive, AudioVisual, Connect

# Each media-bearing model and the file/image fields to migrate.
MEDIA_FIELDS = [
    (Connect, ['image_1', 'image_2', 'image_3', 'image_4']),
    (AudioVisual, ['video', 'audio']),
    (Archive, ['video_file', 'audio_file', 'image_file']),
]


class Command(BaseCommand):
    help = "Upload existing local media to the configured storage (Cloudflare R2) and fix DB references."

    def add_arguments(self, parser):
        parser.add_argument(
            '--media-root',
            default=str(settings.MEDIA_ROOT),
            help='Local folder to read existing files from (default: settings.MEDIA_ROOT).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be uploaded without uploading or writing to the DB.',
        )

    def handle(self, *args, **options):
        media_root = options['media_root']
        dry_run = options['dry_run']

        if not dry_run and not getattr(settings, 'USE_S3_MEDIA', False):
            self.stderr.write(self.style.WARNING(
                'Remote media storage is not configured (AWS_STORAGE_BUCKET_NAME / '
                'AWS_S3_ENDPOINT_URL unset) — files would be saved with the local '
                'filesystem storage. Set the R2 env vars first, or use --dry-run.'
            ))

        uploaded = 0
        missing = 0

        for model, fields in MEDIA_FIELDS:
            for obj in model.objects.all():
                updates = {}
                for field_name in fields:
                    file_field = getattr(obj, field_name)
                    name = getattr(file_field, 'name', '') or ''
                    if not name:
                        continue

                    local_path = os.path.join(media_root, name)
                    if not os.path.exists(local_path):
                        self.stderr.write(
                            f'  MISSING  {model.__name__}#{obj.pk}.{field_name}: {local_path}'
                        )
                        missing += 1
                        continue

                    if dry_run:
                        self.stdout.write(
                            f'  would upload {model.__name__}#{obj.pk}.{field_name}: {name}'
                        )
                        continue

                    with open(local_path, 'rb') as fh:
                        content = ContentFile(fh.read())
                    new_name = file_field.storage.save(name, content)
                    updates[field_name] = new_name
                    uploaded += 1
                    self.stdout.write(
                        f'  {model.__name__}#{obj.pk}.{field_name}: {name} -> {new_name}'
                    )

                if updates:
                    # Persist with update() to bypass Connect.save()'s image
                    # re-compression (and any other custom save side effects).
                    model.objects.filter(pk=obj.pk).update(**updates)

        if dry_run:
            self.stdout.write(self.style.SUCCESS('Dry run complete (no changes made).'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Done. uploaded={uploaded} missing={missing}'))
