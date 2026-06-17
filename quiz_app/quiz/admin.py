from django.contrib import admin
from django.contrib import messages
from django.template.response import TemplateResponse
from django.urls import path

from . import gemini
from . import taxonomy
from .models import Question, MCQ, Written, Connect, AudioVisual, Facts, Archive, Score, AnswerLog

admin.site.register(Question)
admin.site.register(MCQ)
admin.site.register(Written)
admin.site.register(Connect)
admin.site.register(AudioVisual)
admin.site.register(Facts)


@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    list_display = ("title", "event", "media_kind", "has_link", "pub_date")
    list_filter = ("event", "is_Video", "is_Audio", "is_Image")
    search_fields = ("title", "event")
    fields = ("event", "title", "pub_date", "media_url",
              "video_file", "audio_file", "image_file",
              "is_Video", "is_Audio", "is_Image")

    @admin.display(description="Type")
    def media_kind(self, obj):
        info = obj.embed_info()
        if info:
            return "link (%s)" % info["kind"]
        for label, flag in (("video", obj.is_Video), ("audio", obj.is_Audio), ("image", obj.is_Image)):
            if flag:
                return "file (%s)" % label
        return "—"

    @admin.display(boolean=True, description="Link?")
    def has_link(self, obj):
        return bool(obj.media_url)


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ("user", "points", "correct", "answered", "updated")
    ordering = ("-points",)


@admin.register(AnswerLog)
class AnswerLogAdmin(admin.ModelAdmin):
    list_display = ("user", "mode", "question_id", "correct", "created")
    list_filter = ("mode", "correct")


admin.site.site_header = "Quizite admin"
admin.site.site_title = "Quizite admin"


def _preview_entry(mode, raw):
    """Shape one raw Gemini item for the preview template."""
    entry = {"mode": mode}
    if mode == "mcq":
        correct = raw.get("correct", [])
        if not isinstance(correct, list):
            correct = [correct]
        entry["question"] = raw.get("question", "")
        entry["options"] = [{"text": o, "correct": o in correct} for o in raw.get("options", [])]
        entry["explanation"] = raw.get("explanation", "")
    elif mode == "written":
        entry["question"] = raw.get("question", "")
        entry["answer"] = raw.get("answer", "")
        entry["accepted"] = raw.get("accepted", [])
        entry["explanation"] = raw.get("explanation", "")
    elif mode == "flashcard":
        entry["question"] = raw.get("question", "")
        entry["answer"] = raw.get("answer", "")
        entry["explanation"] = raw.get("explanation", "")
    elif mode == "facts":
        entry["fact"] = raw.get("fact", "")
    elif mode == "connect":
        entry["question"] = raw.get("question", "")
        entry["answer"] = raw.get("answer", "")
        entry["accepted"] = raw.get("accepted", [])
        entry["images"] = raw.get("images", [])
        entry["hint"] = raw.get("hint", "")
        entry["explanation"] = raw.get("explanation", "")
    elif mode == "av":
        entry["question"] = raw.get("question", "")
        entry["answer"] = raw.get("answer", "")
        entry["accepted"] = raw.get("accepted", [])
        entry["media_type"] = raw.get("media_type", "")
        entry["source"] = raw.get("source_suggestion", "")
        entry["timestamp"] = raw.get("timestamp", "")
        entry["hint"] = raw.get("hint", "")
        entry["explanation"] = raw.get("explanation", "")
    return entry


def generate_questions_view(request):
    """Admin page: generate questions with Gemini (preview, then save)."""
    context = dict(admin.site.each_context(request))
    context.update({
        "title": "Generate questions with Gemini",
        "modes": [(m, gemini.MODE_LABELS[m]) for m in gemini.MODES],
        "default_prompts": {m: gemini.load_default_prompt(m) for m in gemini.MODES},
        "default_model": gemini.DEFAULT_MODEL,
        "has_api_key": gemini.has_api_key(),
        # form defaults
        "mode": "mcq", "category": "", "count": 10,
        "model": gemini.DEFAULT_MODEL, "temperature": "0.9",
        "prompt": gemini.load_default_prompt("mcq"),
        "preview": None,
    })

    if request.method == "POST":
        mode = request.POST.get("mode", "mcq")
        if mode not in gemini.MODES:
            mode = "mcq"
        category = (request.POST.get("category") or "").strip()
        try:
            count = max(1, min(50, int(request.POST.get("count") or 10)))
        except (TypeError, ValueError):
            count = 10
        model = (request.POST.get("model") or gemini.DEFAULT_MODEL).strip()
        try:
            temperature = float(request.POST.get("temperature") or 0.9)
        except (TypeError, ValueError):
            temperature = 0.9
        prompt = request.POST.get("prompt") or gemini.load_default_prompt(mode)
        action = request.POST.get("action", "preview")

        context.update({"mode": mode, "category": category, "count": count,
                        "model": model, "temperature": temperature, "prompt": prompt})

        if not category:
            messages.error(request, "Please enter a category / topic.")
        else:
            # Map the typed topic to the universal routing categories so the
            # questions index in the UI even if the topic isn't a main category.
            classify_cb = (lambda uc, cats: gemini.gemini_classify(uc, cats)) if gemini.has_api_key() else None
            store_cat, mapped = taxonomy.storage_category(category, gemini_classify=classify_cb)
            context["mapped"] = mapped
            context["store_cat"] = store_cat
            try:
                records, errors = gemini.generate(mode, category, count, prompt,
                                                  model=model, temperature=temperature,
                                                  store_category=store_cat)
                messages.info(request, "“%s” mapped to: %s  (stored as %s)"
                              % (category, ", ".join(mapped), store_cat))
                for e in errors:
                    messages.warning(request, "Skipped " + e)
                if action == "save":
                    saved = 0
                    for _raw, obj in records:
                        obj.save()
                        saved += 1
                    messages.success(request, "Saved %d %s question(s) to the database."
                                     % (saved, gemini.MODE_LABELS[mode]))
                else:
                    context["preview"] = [_preview_entry(mode, raw) for raw, _obj in records]
                    if records:
                        messages.info(request, "Previewed %d question(s) — review them, then click "
                                      "“Generate & save”." % len(records))
                    else:
                        messages.warning(request, "Gemini returned no usable questions.")
            except gemini.GeminiError as e:
                messages.error(request, str(e))

    return TemplateResponse(request, "admin/generate_questions.html", context)


# Register the custom page under /admin/generate-questions/ (named admin:generate_questions)
_orig_get_urls = admin.site.get_urls


def _get_urls():
    return [
        path("generate-questions/", admin.site.admin_view(generate_questions_view),
             name="generate_questions"),
    ] + _orig_get_urls()


admin.site.get_urls = _get_urls
