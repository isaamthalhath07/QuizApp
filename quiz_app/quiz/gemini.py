"""Shared Gemini question-generation service.

Used by both the admin page (quiz/admin.py) and the management command
(generate_questions). Talks to the Gemini REST API with the standard library
only (no extra dependency). Gemini returns clean JSON content which we validate
and map into the database models, including the written-answer command syntax.
"""

import json
import os
import urllib.error
import urllib.request

from django.utils import timezone

from quiz.models import MCQ, Written, Question, Facts

MODES = ("mcq", "written", "flashcard", "facts")
MODE_LABELS = {"mcq": "MCQ", "written": "Written", "flashcard": "Flashcard", "facts": "Facts"}
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


class GeminiError(Exception):
    """Any user-facing failure (missing key, API error, bad output)."""


def has_api_key():
    return bool(os.environ.get("GEMINI_API_KEY"))


def load_default_prompt(mode):
    with open(os.path.join(PROMPTS_DIR, mode + ".txt"), encoding="utf-8") as fh:
        return fh.read()


def render_prompt(template, category, count):
    return template.replace("{category}", category).replace("{count}", str(count))


def call_gemini(model, prompt, temperature, api_key=None):
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise GeminiError("GEMINI_API_KEY is not set on the server.")
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": temperature},
    }).encode("utf-8")
    req = urllib.request.Request(
        GEMINI_URL.format(model=model, key=key),
        data=body, headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise GeminiError("Gemini API error %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:300]))
    except urllib.error.URLError as e:
        raise GeminiError("Could not reach the Gemini API: %s" % e)
    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError):
        raise GeminiError("Unexpected Gemini response: %s" % str(payload)[:300])
    if isinstance(data, dict) and "questions" in data:
        data = data["questions"]
    if not isinstance(data, list):
        raise GeminiError("Expected a JSON array of questions.")
    return data


def build_record(mode, item, category):
    """Map one clean JSON item to an unsaved model instance. Raises on bad data."""
    now = timezone.now()
    if mode == "flashcard":
        return Question(question_text=item["question"], answer_text=item["answer"],
                        explanation_text=item.get("explanation", ""), category=category, pub_date=now)
    if mode == "facts":
        return Facts(answer_text=item["fact"], category=category, pub_date=now)
    if mode == "mcq":
        opts = item["options"]
        if len(opts) != 4:
            raise ValueError("MCQ needs exactly 4 options")
        correct = item["correct"] if isinstance(item["correct"], list) else [item["correct"]]
        for c in correct:
            if c not in opts:
                raise ValueError("correct answer %r is not one of the options" % c)
        return MCQ(question_text=item["question"], option1=opts[0], option2=opts[1],
                   option3=opts[2], option4=opts[3], answer_text=",".join(correct),
                   multiple=bool(item.get("multiple", len(correct) > 1)),
                   explanation_text=item.get("explanation", ""), category=category, pub_date=now)
    if mode == "written":
        answer = item["answer"].strip()
        seen, variants = set(), []
        for a in [answer] + [x.strip() for x in item.get("accepted", []) if x and x.strip()]:
            if a.lower() not in seen:
                seen.add(a.lower()); variants.append("/" + a)
        return Written(question_text=item["question"], answer_text=":".join(variants),
                       display_answer=answer, explanation_text=item.get("explanation", ""),
                       category=category, pub_date=now)
    raise ValueError("unknown mode %r" % mode)


def generate(mode, category, count, prompt_template, model=None, temperature=0.9, api_key=None):
    """Call Gemini and build (unsaved) records.

    Returns (records, errors) where records is a list of (raw_item, model_obj)
    and errors is a list of human-readable skip messages.
    """
    model = model or DEFAULT_MODEL
    prompt = render_prompt(prompt_template, category, count)
    data = call_gemini(model, prompt, temperature, api_key)
    records, errors = [], []
    for i, item in enumerate(data, 1):
        try:
            records.append((item, build_record(mode, item, category)))
        except (KeyError, ValueError, TypeError) as e:
            errors.append("#%d: %s" % (i, e))
    return records, errors
