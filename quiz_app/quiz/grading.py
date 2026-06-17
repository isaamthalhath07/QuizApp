"""Authoritative server-side answer grading.

A faithful port of the deterministic matcher in `static/assets/test.js` /
`connect.js` (normalize -> Levenshtein -> sorted-token -> token-bag) plus the
legacy command syntax stored in each model's `answer_text`:

    ;  separates independent answer keys (any may match)
    :  OR inside one key
    /word    fuzzy match (the common case, via loose_match)
    /=word   STRICT: normalized-exact, no fuzz/soundex (chemical names, formulae)
    /#word   soundex (spelling-tolerant)
    /?word   exact, case-sensitive
    ,# / ,$ / ,? / ,% / ,@ words   word-bag variants

Used by the scoring endpoint so points can't be awarded for a wrong answer.
"""

import re

_NONWORD = re.compile(r"[^a-z0-9\s]")
_WS = re.compile(r"\s+")
_STOP = {"a", "an", "the", "of", "is", "are", "and", "to", "in", "on", "by",
         "for", "with"}


def _norm(s):
    s = (s or "").lower()
    s = _NONWORD.sub(" ", s)
    return _WS.sub(" ", s).strip()


def _lev(a, b):
    m, n = len(a), len(b)
    if not m:
        return n
    if not n:
        return m
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[n]


def _sim(a, b):
    ml = max(len(a), len(b))
    return 1.0 if ml == 0 else (1 - _lev(a, b) / ml)


def loose_match(user_raw, correct_raw):
    u, c = _norm(user_raw), _norm(correct_raw)
    if not u or not c:
        return False
    if u == c:
        return True
    ml = max(len(u), len(c))
    threshold = 0.75 if ml <= 4 else (0.80 if ml <= 8 else 0.82)
    if _sim(u, c) >= threshold:
        return True
    if _sim(" ".join(sorted(u.split(" "))), " ".join(sorted(c.split(" ")))) >= threshold:
        return True
    cw = [w for w in c.split(" ") if w and w not in _STOP]
    uw = [w for w in u.split(" ") if w]
    if cw and all(any(y == x or _sim(y, x) >= 0.8 for y in uw) for x in cw):
        return True
    return False


def strict_match(user_raw, correct_raw):
    """Normalized exact: case-insensitive, punctuation/whitespace folded, but NO
    fuzzy distance and NO soundex — so 'sodium bicarbonate' != 'sodium carbonate'."""
    return _norm(user_raw) == _norm(correct_raw)


def soundex(s):
    s = (s or "").lower()
    if not s:
        return "0000"
    codes = {"b": "1", "f": "1", "p": "1", "v": "1",
             "c": "2", "g": "2", "j": "2", "k": "2", "q": "2", "s": "2", "x": "2", "z": "2",
             "d": "3", "t": "3", "l": "4", "m": "5", "n": "5", "r": "6"}
    first = s[0]
    out = first
    prev = codes.get(first, "")
    for ch in s[1:]:
        code = codes.get(ch, "")
        if code and code != prev:
            out += code
        if ch not in "hw":
            prev = code if ch in codes else ""
    return (out + "000")[:4].upper()


def grade_text(answer, answer_text):
    """True if `answer` satisfies the stored `answer_text` command key."""
    answer = answer or ""
    for command in (answer_text or "").split(";"):
        if not command:
            continue
        or_commands = command.split(":") if ":" in command else [command]
        for cmd in or_commands:
            if not cmd:
                continue
            if cmd[0] == "/":
                flag = cmd[1] if len(cmd) > 1 else ""
                if flag == "#":
                    if soundex(answer) == soundex(cmd.replace("#", "").replace("/", "")):
                        return True
                elif flag == "?":
                    if answer == cmd.replace("?", "").replace("/", ""):
                        return True
                elif flag == "=":
                    if strict_match(answer, cmd.replace("=", "", 1).replace("/", "", 1)):
                        return True
                else:
                    if loose_match(answer, cmd.replace("/", "", 1)):
                        return True
            elif cmd[0] == ",":
                body = cmd[2:].lower()
                aw = answer.lower().split(" ")
                cwds = body.split(" ")
                if len(cmd) > 1 and cmd[1] == "#":
                    if ",".join(map(soundex, cwds)) in ",".join(map(soundex, aw)):
                        return True
                else:
                    if all(w in aw for w in cwds):
                        return True
    return False


def grade_mcq(selected, answer_text, multiple):
    """`selected` is the list of option texts the user chose; `answer_text` is the
    comma-joined correct option(s). All correct and no wrong -> True."""
    correct = [c for c in (answer_text or "").split(",") if c]
    chosen = [s for s in (selected or []) if s]
    if not chosen or not correct:
        return False
    if multiple:
        return set(chosen) == set(correct)
    return len(chosen) == 1 and chosen[0] in correct
