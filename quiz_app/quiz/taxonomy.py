"""Universal category taxonomy + classifier.

The whole site routes by a fixed set of MAIN_CATEGORIES (these are what the
category picker shows when you click a mode). A question's `category` field is a
comma-separated string; a question shows up under a main category if that main
appears in the list. So any arbitrary topic the user types (e.g. "FIFA World
Cup") must be mapped to one or more MAIN_CATEGORIES (e.g. "Sports") before the
questions are stored — otherwise they'd never appear in the UI.

`classify_category` does that deterministically (exact / sub-category / keyword
match) and can fall back to a Gemini classification for novel topics, with the
catch-all "GK" as a last resort.
"""

# Sub-categories per main category (mirrors the routing table in views.abc).
SUBCATEGORIES = {
    "Science": ["Biology", "Maths", "Physics", "Chemistry"],
    "Literature": ["Famous Authors", "Famous Novels"],
    "History": ["Indian History", "Historic events"],
    "Math": ["Logic", "Arithmetic", "Laws and Theorems"],
    "GK": ["Famous Personalities", "Logos"],
    "Sports": ["Famous Personalities"],
    "Film": ["All"],
}

# The universal categories every question maps to (and that the UI routes by).
MAIN_CATEGORIES = list(SUBCATEGORIES.keys())  # Science, Literature, History, Math, GK, Sports, Film
CATCH_ALL = "GK"  # General Knowledge — anything that doesn't fit elsewhere

# Keyword hints for fast, free, deterministic mapping.
_KEYWORDS = {
    "Sports": ["sport", "football", "soccer", "fifa", "world cup", "olympic", "cricket",
               "tennis", "nba", "basketball", "athlete", "league", "tournament", "messi",
               "ronaldo", "rugby", "hockey", "baseball", "boxing", "formula 1", "f1"],
    "Film": ["film", "movie", "cinema", "hollywood", "bollywood", "actor", "actress",
             "oscar", "tv show", "series", "netflix", "director", "anime", "sitcom"],
    "Science": ["science", "physics", "chemistry", "biology", "astronomy", "space", "nasa",
                "atom", "cell", "quantum", "element", "planet", "genetics", "ecology", "molecule"],
    "Math": ["math", "maths", "mathematics", "algebra", "geometry", "calculus", "arithmetic",
             "number theory", "equation", "theorem", "probability", "statistics"],
    "History": ["history", "historical", "ancient", "war", "empire", "dynasty", "revolution",
                "medieval", "civilization", "world war", "wwii", "wwi", "colonial", "pharaoh"],
    "Literature": ["literature", "author", "novel", "book", "poem", "poetry", "poet",
                   "shakespeare", "writer", "fiction", "drama", "playwright"],
    "GK": ["general knowledge", "gk", "trivia", "current affairs", "geography", "capital",
           "politics", "economics", "technology", "music", "art", "food", "language", "religion"],
}


def _dedupe(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x); out.append(x)
    return out


def classify_category(user_category, gemini_classify=None):
    """Map an arbitrary topic to 1-2 MAIN_CATEGORIES.

    gemini_classify, if given, is called as gemini_classify(user_category,
    MAIN_CATEGORIES) -> list[str] for novel topics that don't match locally.
    """
    norm = (user_category or "").strip().lower()
    if not norm:
        return [CATCH_ALL]

    # 1. exact main category
    for c in MAIN_CATEGORIES:
        if norm == c.lower():
            return [c]

    # 2. a known sub-category -> its parent main
    for main, subs in SUBCATEGORIES.items():
        if any(norm == s.lower() for s in subs):
            return [main]

    # 3. keyword / phrase match (either direction)
    hits = [main for main, kws in _KEYWORDS.items()
            if any(k in norm or norm in k for k in kws)]
    if hits:
        return _dedupe(hits)[:2]

    # 4. optional Gemini classification for genuinely novel topics
    if gemini_classify is not None:
        try:
            result = [c for c in (gemini_classify(user_category, MAIN_CATEGORIES) or [])
                      if c in MAIN_CATEGORIES]
            if result:
                return _dedupe(result)[:2]
        except Exception:
            pass

    # 5. last resort
    return [CATCH_ALL]


def storage_category(user_category, gemini_classify=None):
    """The comma-joined `category` string to store: mapped main(s) + the
    specific topic label, so the question both indexes in the UI and keeps its
    original topic. e.g. "Sports,FIFA World Cup"."""
    mains = classify_category(user_category, gemini_classify=gemini_classify)
    label = (user_category or "").strip()
    parts = list(mains)
    if label and label not in parts:
        parts.append(label)
    return ",".join(parts), mains
