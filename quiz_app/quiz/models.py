from django.db import models
from django.conf import settings
import json

from io import BytesIO
from PIL import Image
from django.core.files import File


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
    is_Image = models.BooleanField()
    is_Audio = models.BooleanField()
    is_Video = models.BooleanField()

    def __str__(self):
        return self.title

