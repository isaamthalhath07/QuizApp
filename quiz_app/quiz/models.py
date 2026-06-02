import os

from django.db import models
import json

from io import BytesIO
from PIL import Image
from django.core.files import File


def video_storage():
    """Per-field storage for video/audio uploads.

    Cloudinary serves video and audio under its ``video`` resource type, which
    differs from images. When CLOUDINARY_URL is configured we return Cloudinary's
    video storage; otherwise we fall back to Django's default (filesystem) storage
    so local development is unchanged. A *callable* is used so Django does not
    serialize a concrete storage into migrations (keeps the schema untouched).
    """
    if os.environ.get('CLOUDINARY_URL'):
        from cloudinary_storage.storage import VideoMediaCloudinaryStorage
        return VideoMediaCloudinaryStorage()
    from django.core.files.storage import default_storage
    return default_storage


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
        # call the compress function
        self.image_1= compress(self.image_1)
        self.image_2= compress(self.image_2)
        self.image_3= compress(self.image_3)
        self.image_4= compress(self.image_4)

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
    video = models.FileField(upload_to='videos/', null=True, verbose_name="", blank=True, storage=video_storage)
    audio = models.FileField(upload_to='audios/', null=True, verbose_name="", blank=True, storage=video_storage)

    def __str__(self):
        return self.question_text
class Facts(models.Model):
    pub_date = models.DateTimeField()
    answer_text = models.CharField(max_length=2000)
    category = models.CharField(max_length=2000)
    def __str__(self):
        return self.answer_text
class Archive(models.Model):
    pub_date = models.DateTimeField()
    event = models.CharField(max_length=2000)
    title = models.CharField(max_length=2000)
    video_file = models.FileField(upload_to='videos/', null=True, verbose_name="", blank=True, storage=video_storage)
    audio_file = models.FileField(upload_to='audios/', null=True, verbose_name="", blank=True, storage=video_storage)
    image_file = models.ImageField(blank=True)
    is_Image = models.BooleanField()
    is_Audio = models.BooleanField()
    is_Video = models.BooleanField()

    def __str__(self):
        return self.title

