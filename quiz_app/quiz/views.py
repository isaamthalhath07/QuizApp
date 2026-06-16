import random

from django.core.cache import cache
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.template import loader
from django.views.decorators.http import require_http_methods

from quiz.models import Archive
from quiz.models import AudioVisual
from quiz.models import Connect
from quiz.models import Facts
from quiz.models import MCQ
from quiz.models import Question
from quiz.models import Written

from .forms import UserForm

abc = {
    "Science": ["Biology", "Maths", "Physics", "Chemistry"],
    "Literature": ["Famous Authors", "Famous Novels"],
    "History": ["Indian History", "Historic events"],
    "Math": ["Logic", "Arithmetic", "Laws and Theorems"],
    "GK": ["Famous Personalities", "Logos"],
    "Sports": ["Famous Personalities"],
    "Film": ["All"],
}


def _shuffled_ids(model_cls, cat):
    if cat != "All":
        ids = [obj.pk for obj in model_cls.objects.all() if cat in getattr(obj, 'category').split(',')]
    else:
        ids = list(model_cls.objects.values_list('pk', flat=True))
    random.shuffle(ids)
    return ids


def _session_question_list(request, model_cls, cat, session_key):
    state = request.session.get(session_key, {})
    if state.get('cat') != cat or not state.get('ids'):
        state = {'cat': cat, 'ids': _shuffled_ids(model_cls, cat)}
        request.session[session_key] = state
    return state['ids']


# --- Login rate limiting (brute-force protection) ---
# Per-IP failed-attempt counter in the cache. After LOGIN_MAX_FAILS failures
# within LOGIN_FAIL_WINDOW seconds the IP is locked out for LOGIN_LOCKOUT
# seconds. Uses Django's cache (LocMemCache by default — effective on a single
# worker; use a shared cache like Redis for multi-instance deployments).
LOGIN_MAX_FAILS = 5
LOGIN_FAIL_WINDOW = 300      # 5 minutes
LOGIN_LOCKOUT = 900         # 15 minutes


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or 'unknown'


def loginl(request):
    ip = _client_ip(request)
    lock_key = 'login_lock:%s' % ip
    fail_key = 'login_fail:%s' % ip

    invalid = False
    locked = bool(cache.get(lock_key))
    form = UserForm(request.POST or None)

    if request.method == 'POST' and not locked:
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                django_login(request, user)
                cache.delete(fail_key)
                return HttpResponseRedirect('/quiz/')
        invalid = True
        # register the failed attempt; lock out once over the threshold
        fails = (cache.get(fail_key) or 0) + 1
        cache.set(fail_key, fails, LOGIN_FAIL_WINDOW)
        if fails >= LOGIN_MAX_FAILS:
            cache.set(lock_key, True, LOGIN_LOCKOUT)
            cache.delete(fail_key)
            locked = True

    context = {
        "form": form,
        "error": invalid and not locked,
        "locked": locked,
        "lockout_minutes": LOGIN_LOCKOUT // 60,
        "userboi": request.user.username if request.user.is_authenticated else "",
    }
    template = loader.get_template('quiz/login.html')
    response = HttpResponse(template.render(context, request))
    response['Cache-Control'] = 'no-store'   # don't cache the credentials page
    return response


@require_http_methods(["POST"])
def logoutl(request):
    django_logout(request)
    return HttpResponseRedirect('/quiz/login/')


@login_required(login_url='/quiz/login/')
def randomCat(request):
    random_cat = random.choice(list(abc))
    rand_cat = random.choice(abc[random_cat])
    template = loader.get_template('quiz/questions.html')

    if rand_cat != "All":
        query = [q for q in Question.objects.all() if rand_cat in getattr(q, 'category').split(',')]
        context = {"Questions": query, "userboi": request.user.username}
    else:
        context = {"Questions": Question.objects.all(), "userboi": request.user.username}

    return HttpResponse(template.render(context, request))


@login_required(login_url='/quiz/login/')
def mcqrandomCat(request):
    random_cat = random.choice(list(abc))
    rand_cat = random.choice(abc[random_cat])
    return HttpResponseRedirect(rand_cat + "/1")


@login_required(login_url='/quiz/login/')
def categories(request, cat):
    template = loader.get_template('quiz/questions.html')

    if cat != "All":
        query = [q for q in Question.objects.all() if cat in getattr(q, 'category').split(',')]
        context = {"Questions": query, "userboi": request.user.username}
    else:
        context = {"Questions": Question.objects.all(), "userboi": request.user.username}

    return HttpResponse(template.render(context, request))


@login_required(login_url='/quiz/login/')
def writtencategories(request, cat):
    return HttpResponseRedirect(cat + "/1")


@login_required(login_url='/quiz/login/')
def writtencategoriesstuff(request, cat, number):
    template = loader.get_template('quiz/written.html')
    ids = _session_question_list(request, Written, cat, 'written_state')
    try:
        idx = int(number) - 1
        question = Written.objects.get(pk=ids[idx])
    except (ValueError, IndexError, Written.DoesNotExist):
        return HttpResponseRedirect('/quiz/written/categories/')
    context = {"Questions": [question], "userboi": request.user.username, "Numberrr": len(ids) + 1}
    return HttpResponse(template.render(context, request))


@login_required(login_url='/quiz/login/')
def mcqcategories(request, cat):
    template = loader.get_template('quiz/mcq.html')

    if cat != "All":
        query = [q for q in MCQ.objects.all() if cat in getattr(q, 'category').split(',')]
        context = {"Questions": query, "userboi": request.user.username, "QuestionsList": list(MCQ.objects.all())}
    else:
        context = {"Questions": MCQ.objects.all(), "userboi": request.user.username, "QuestionsList": list(MCQ.objects.all())}

    return HttpResponse(template.render(context, request))


@login_required(login_url='/quiz/login/')
def subcats(request, maincat):
    template = loader.get_template('quiz/subcats.html')

    if maincat != "All":
        context = {"subcats": abc.get(maincat, []), "maincat": maincat, "userboi": request.user.username}
    else:
        context = {"e": "e", "userboi": request.user.username}
    return HttpResponse(template.render(context, request))


@login_required(login_url='/quiz/login/')
def connectcategories(request, cat):
    return HttpResponseRedirect(cat + "/1")


@login_required(login_url='/quiz/login/')
def connectcategoriesstuff(request, cat, number):
    template = loader.get_template('quiz/connect.html')
    ids = _session_question_list(request, Connect, cat, 'connect_state')
    try:
        idx = int(number) - 1
        question = Connect.objects.get(pk=ids[idx])
    except (ValueError, IndexError, Connect.DoesNotExist):
        return HttpResponseRedirect('/quiz/connect/categories/')
    context = {"q": question, "userboi": request.user.username, "Numberrr": len(ids) + 1}
    return HttpResponse(template.render(context, request))


@login_required(login_url='/quiz/login/')
def cats(request):
    template = loader.get_template('quiz/categories.html')
    context = {
        'Questions': Question.objects.all(),
        'Category': abc,
        "userboi": request.user.username,
    }
    return HttpResponse(template.render(context, request))


@login_required(login_url='/quiz/login/')
def archive_cats(request):
    all_events = list(set(Archive.objects.values_list('event', flat=True)))
    template = loader.get_template('quiz/archiveevents.html')
    context = {"events": all_events, "userboi": request.user.username}
    return HttpResponse(template.render(context, request))


@login_required(login_url='/quiz/login/')
def archive_cats_events(request, event):
    template = loader.get_template('quiz/archivetitles.html')
    all_events = Archive.objects.filter(event__iexact=event)
    context = {"titles": all_events, "userboi": request.user.username}
    return HttpResponse(template.render(context, request))


@login_required(login_url='/quiz/login/')
def archive_cats_events_title(request, event, title):
    template = loader.get_template('quiz/archiveeventtitles.html')
    all_events = Archive.objects.filter(title__iexact=title)
    context = {"titles": all_events, "userboi": request.user.username}
    return HttpResponse(template.render(context, request))


@login_required(login_url='/quiz/login/')
def about(request):
    template = loader.get_template('quiz/about.html')
    context = {" ": " ", "userboi": request.user.username}
    return HttpResponse(template.render(context, request))


@login_required(login_url='/quiz/login/')
def home(request):
    items = list(Facts.objects.all())
    random_item = random.choice(items) if items else None
    template = loader.get_template('quiz/home.html')

    User = get_user_model()
    users = list(User.objects.all()[:2])
    first_user = users[0] if len(users) > 0 else None
    second_user = users[1] if len(users) > 1 else None

    context = {
        'Questions': Question.objects.all(),
        "Facts": random_item,
        'Category': abc,
        "userboi": request.user.username,
        "FirstUser": first_user,
        "SecondUser": second_user,
    }
    return HttpResponse(template.render(context, request))


@login_required(login_url='/quiz/login/')
def audiovisualcategories(request, cat):
    return HttpResponseRedirect(cat + "/1")


@login_required(login_url='/quiz/login/')
def audiovisualcategoriesstuff(request, cat, number):
    template = loader.get_template('quiz/av.html')
    ids = _session_question_list(request, AudioVisual, cat, 'audiovisual_state')
    try:
        idx = int(number) - 1
        question = AudioVisual.objects.get(pk=ids[idx])
    except (ValueError, IndexError, AudioVisual.DoesNotExist):
        return HttpResponseRedirect('/quiz/audiovisual/categories/')
    context = {"q": question, "userboi": request.user.username, "Numberrr": len(ids) + 1}
    return HttpResponse(template.render(context, request))
