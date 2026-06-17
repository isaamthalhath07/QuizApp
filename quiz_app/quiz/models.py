from django.db import models
from django.conf import settings
import json
import re

from io import BytesIO
from urllib.parse import urlparse, parse_qs
from PIL import Image
from django.core.files import File

VIDEO_EXT = ('.mp4', '.webm', '.ogv', '.mov', '.m4v')
AUDIO_EXT = ('.mp3', '.wav', '.m4a', '.aac', '.oga', '.flac', '.ogg')


def compress(image):
    im = Image.open(image)
    # create a BytesIO object
    im_io = BytesIO()
    if im.mode != 'RGB':
        img = im .convert('RGB')
    # save image to BytesIO object
    im.save(im_io, format='PNG', quality=60)
    # create a django-friendly Files object
    new_image = File(im_io, name=image.name)
    return new_image
class Question(models.Model):
    question_text = models.CharField(max_length=2000)
    pub_date = models.DateTimeField()
    answer_text = models.CharField(max_length=2000)
    explanation_text = models.CharField(max_length=2000)
    category = models.CharField(max_length=2000)

    def __str__(self):
        return self.question_text


class MCQ(models.Model):
    question_text = models.CharField(max_length=2000)
    pub_date = models.DateTimeField()
    option1 = models.CharField(max_length=2000)
    option2 = models.CharField(max_length=2000)
    multiple = models.BooleanField()
    option3 = models.CharField(max_length=2000)
    option4 = models.CharField(max_length=2000)
    answer_text = models.CharField(max_length=2000)
    explanation_text = models.CharField(max_length=2000)
    category = models.CharField(max_length=2000)

    def __str__(self):
        return self.question_text
class Written(models.Model):
    question_text = models.CharField(max_length=2000)
    pub_date = models.DateTimeField()
    answer_text = models.CharField(max_length=2000)
    explanation_text = models.CharField(max_length=2000)
    category = models.CharField(max_length=2000)
    display_answer = models.CharField(max_length=2000)
    def __str__(self):
        return self.question_text
    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)
class Connect(models.Model):
    question_text = models.CharField(max_length=2000)
    pub_date = models.DateTimeField()
    answer_text = models.CharField(max_length=2000)
    explanation_text = models.CharField(max_length=2000)
    hint_text= models.CharField(max_length=2000)
    category = models.CharField(max_length=2000)
    display_answer = models.CharField(max_length=2000)
    isTimed = models.BooleanField()
    image_1 = models.ImageField()
    image_2 = models.ImageField()
    image_3 = models.ImageField()
    image_4 = models.ImageField()
    def __str__(self):
        return self.question_text

    def save(self, *args, **kwargs):
        # Compress each image, but only if one is actually set — so a Connect can
        # be created with its text first and the images uploaded later.
        for field in ('image_1', 'image_2', 'image_3', 'image_4'):
            img = getattr(self, field)
            if img:
                try:
                    setattr(self, field, compress(img))
                except Exception:
                    pass

        # save
        super().save(*args, **kwargs)


class AudioVisual(models.Model):
    question_text = models.CharField(max_length=2000)
    pub_date = models.DateTimeField()
    answer_text = models.CharField(max_length=2000)
    explanation_text = models.CharField(max_length=2000)
    hint_text = models.CharField(max_length=2000)
    category = models.CharField(max_length=2000)
    display_answer = models.CharField(max_length=2000)
    is_Audio = models.BooleanField()
    is_Video = models.BooleanField()
    video = models.FileField(upload_to='videos/', null=True, verbose_name="", blank=True)
    audio = models.FileField(upload_to='audios/', null=True, verbose_name="", blank=True)

    def __str__(self):
        return self.question_text
class Facts(models.Model):
    pub_date = models.DateTimeField()
    answer_text = models.CharField(max_length=2000)
    category = models.CharField(max_length=2000)
    def __str__(self):
        return self.answer_text
class Score(models.Model):
    """Running point total per user (drives the leaderboard)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='quiz_score')
    points = models.IntegerField(default=0)
    correct = models.IntegerField(default=0)
    answered = models.IntegerField(default=0)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-points', '-correct']

    def __str__(self):
        return "%s — %d pts" % (self.user, self.points)


class AnswerLog(models.Model):
    """One row per (user, mode, question). Lets each question score only once."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='quiz_answers')
    mode = models.CharField(max_length=20)
    question_id = models.IntegerField()
    correct = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'mode', 'question_id')

    def __str__(self):
        return "%s %s#%s %s" % (self.user, self.mode, self.question_id,
                                "✓" if self.correct else "✗")


class Archive(models.Model):
    pub_date = models.DateTimeField()
    event = models.CharField(max_length=2000)
    title = models.CharField(max_length=2000)
    video_file = models.FileField(upload_to='videos/', null=True, verbose_name="", blank=True)
    audio_file = models.FileField(upload_to='audios/', null=True, verbose_name="", blank=True)
    image_file = models.ImageField(blank=True)
    # An external link (Mega, YouTube, Vimeo, or a direct media URL). When set,
    # the archive plays from this instead of an uploaded file.
    media_url = models.URLField(max_length=1000, blank=True, default="",
                                help_text="Mega / YouTube / Vimeo / direct media link. "
                                          "If set, it plays from here instead of an upload.")
    is_Image = models.BooleanField(default=False)
    is_Audio = models.BooleanField(default=False)
    is_Video = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def embed_info(self):
        """Work out how to play `media_url`. Returns a dict
        {kind: 'iframe'|'video'|'audio', url: <playable>, src: <original>} or
        None when there's no link (the template then falls back to the file)."""
        url = (self.media_url or "").strip()
        if not url:
            return None
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url
        parts = urlparse(url)
        host = parts.netloc.lower()
        path = parts.path

        # YouTube -> /embed/<id>
        if "youtube.com" in host or "youtu.be" in host:
            vid = None
            if "youtu.be" in host:
                vid = path.lstrip("/").split("/")[0]
            else:
                vid = (parse_qs(parts.query).get("v") or [None])[0]
                if not vid and "/embed/" in path:
                    vid = path.split("/embed/")[1].split("/")[0]
                if not vid and "/shorts/" in path:
                    vid = path.split("/shorts/")[1].split("/")[0]
            if vid:
                return {"kind": "iframe", "url": "https://www.youtube.com/embed/%s" % vid, "src": url}

        # Vimeo -> player.vimeo.com/video/<id>
        if "vimeo.com" in host:
            m = re.search(r"vimeo\.com/(?:video/)?(\d+)", url)
            if m:
                return {"kind": "iframe", "url": "https://player.vimeo.com/video/%s" % m.group(1), "src": url}

        # Mega -> /embed/<id>#<key>
        if "mega.nz" in host or "mega.co.nz" in host:
            emb = url
            m = re.search(r"/file/([^#?/]+)(#[^?]*)?", path + ("#" + parts.fragment if parts.fragment else ""))
            if "/embed/" in path:
                emb = url
            elif m:
                emb = "https://mega.nz/embed/%s%s" % (m.group(1), m.group(2) or "")
            else:
                m2 = re.search(r"#!([^!]+)!(.+)", url)   # legacy /#!<id>!<key>
                if m2:
                    emb = "https://mega.nz/embed/%s#%s" % (m2.group(1), m2.group(2))
            return {"kind": "iframe", "url": emb, "src": url}

        # Direct media file by extension
        low_path = path.lower()
        if low_path.endswith(VIDEO_EXT):
            return {"kind": "video", "url": url, "src": url}
        if low_path.endswith(AUDIO_EXT):
            return {"kind": "audio", "url": url, "src": url}

        # Fall back to the explicit flags, then a best-effort iframe.
        if self.is_Audio and not self.is_Video:
            return {"kind": "audio", "url": url, "src": url}
        if self.is_Video:
            return {"kind": "video", "url": url, "src": url}
        return {"kind": "iframe", "url": url, "src": url}

    def save(self, *args, **kwargs):
        # A link-only entry with no media flag set: infer one so the title list
        # still shows the right icon.
        if self.media_url and not (self.is_Image or self.is_Audio or self.is_Video):
            info = self.embed_info()
            if info and info["kind"] == "audio":
                self.is_Audio = True
            else:
                self.is_Video = True
        super().save(*args, **kwargs)

