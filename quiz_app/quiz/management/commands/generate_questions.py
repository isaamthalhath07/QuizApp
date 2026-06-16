"""Generate high-quality quiz questions with the Gemini API and insert them.

Examples
--------
    # set your key once
    export GEMINI_API_KEY="...your key..."

    # generate 10 hard MCQs about Physics
    python manage.py generate_questions --mode mcq --category Physics --count 10

    # preview without saving
    python manage.py generate_questions --mode written --category History --count 8 --dry-run

    # use a different model / your own edited prompt
    python manage.py generate_questions --mode flashcard --category Biology \
        --model gemini-2.0-flash --prompt-file my_prompt.txt

Modes: mcq, written, flashcard, facts. (Connect / Audiovisual need media, so
they are author-added via /admin/.)

The instructions sent to Gemini live in editable text files under
`quiz/management/commands/prompts/<mode>.txt` — tweak them freely, or pass
`--prompt-file` to use your own. Gemini returns clean JSON content; this command
formats it into the database's fields (including the written-answer command
syntax) so the prompt only has to focus on question quality.
"""

import json
import os
import urllib.error
import urllib.request

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from quiz.models import MCQ, Written, Question, Facts

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
MODES = ("mcq", "written", "flashcard", "facts")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"


class Command(BaseCommand):
    help = "Generate quiz questions via the Gemini API and insert them into the database."

    def add_arguments(self, parser):
        parser.add_argument("--mode", required=True, choices=MODES, help="Type of question to generate.")
        parser.add_argument("--category", required=True, help="Category/topic, e.g. 'Physics'. Stored on each question.")
        parser.add_argument("--count", type=int, default=10, help="How many questions to generate (default 10).")
        parser.add_argument("--model", default=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
                            help="Gemini model id (default gemini-2.0-flash, or $GEMINI_MODEL).")
        parser.add_argument("--temperature", type=float, default=0.9, help="Sampling temperature (default 0.9).")
        parser.add_argument("--prompt-file", default=None,
                            help="Path to a custom prompt template (defaults to prompts/<mode>.txt).")
        parser.add_argument("--dry-run", action="store_true", help="Print the generated questions without saving.")

    # ---- Gemini call ----
    def _call_gemini(self, model, prompt, temperature):
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise CommandError("GEMINI_API_KEY environment variable is not set.")
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
            raise CommandError("Gemini API error %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:500]))
        except urllib.error.URLError as e:
            raise CommandError("Could not reach the Gemini API: %s" % e)
        try:
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise CommandError("Unexpected Gemini response: %s" % str(payload)[:500])

    # ---- record builders (map clean JSON -> DB fields) ----
    def _build(self, mode, item, category):
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
            accepted = [answer] + [a.strip() for a in item.get("accepted", []) if a.strip()]
            # de-dupe, build the "/x:/y" fuzzy-match command syntax the grader expects
            seen, variants = set(), []
            for a in accepted:
                k = a.lower()
                if k not in seen:
                    seen.add(k); variants.append("/" + a)
            return Written(question_text=item["question"], answer_text=":".join(variants),
                           display_answer=answer, explanation_text=item.get("explanation", ""),
                           category=category, pub_date=now)
        raise ValueError("unknown mode")

    def handle(self, *args, **opts):
        mode = opts["mode"]
        prompt_path = opts["prompt_file"] or os.path.join(PROMPTS_DIR, mode + ".txt")
        if not os.path.exists(prompt_path):
            raise CommandError("Prompt file not found: %s" % prompt_path)
        with open(prompt_path, encoding="utf-8") as fh:
            template = fh.read()
        prompt = template.replace("{category}", opts["category"]).replace("{count}", str(opts["count"]))

        self.stdout.write("Asking %s for %d %s question(s) about '%s'..." % (
            opts["model"], opts["count"], mode, opts["category"]))
        data = self._call_gemini(opts["model"], prompt, opts["temperature"])
        if isinstance(data, dict) and "questions" in data:
            data = data["questions"]
        if not isinstance(data, list):
            raise CommandError("Expected a JSON array of questions, got: %s" % str(data)[:300])

        created = skipped = 0
        for i, item in enumerate(data, 1):
            try:
                obj = self._build(mode, item, opts["category"])
            except (KeyError, ValueError, TypeError) as e:
                self.stderr.write("  skip #%d: %s" % (i, e))
                skipped += 1
                continue
            if opts["dry_run"]:
                self.stdout.write("  [%d] %s" % (i, (item.get("question") or item.get("fact"))[:90]))
            else:
                obj.save()
                created += 1

        if opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry run: %d valid, %d skipped (nothing saved)." % (len(data) - skipped, skipped)))
        else:
            self.stdout.write(self.style.SUCCESS("Saved %d %s question(s); %d skipped." % (created, mode, skipped)))
