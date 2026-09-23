import json
import os

# Repository root (parent of this package). In Docker this is /app.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_secrets() -> dict:
    path = os.path.join(ROOT_DIR, "secrets.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


# Environment variables win (used by Docker); secrets.json is the local fallback.
_secrets = _load_secrets()


def _setting(name: str, default=None):
    return os.environ.get(name) or _secrets.get(name, default)


TOKEN: str = _setting("TELEGRAM_TOKEN")
if not TOKEN:
    raise SystemExit("TELEGRAM_TOKEN is not set. Export it or add it to secrets.json (see secrets.example.json).")

# Telegram username (without @) allowed into /configure → Admin Settings.
# Unset = nobody has admin access.
ADMIN_USERNAME = (_setting("ADMIN_USERNAME") or "").lstrip("@") or None

SCORES_FILE = _setting("SCORES_FILE") or os.path.join(ROOT_DIR, "data", "scores.md")
POINTS_PER_CORRECT = 10       # per correct answer; ×hourglasses left with "hourglass" on
POINTS_PER_WRONG = 1          # "wrong_penalty" mode
POINTS_PER_MEDAL_WRONG = 3    # "medal_penalty" mode, top-3 players only
MOCK_COST = 2

# ── Scoring modes: key → checkbox label (/configure → Scoring Mode) ─────────────
# Modes are independent toggles and can be combined. None on = plain
# +POINTS_PER_CORRECT per correct answer with no penalties.
SCORING_MODES = {
    "wrong_penalty": "Wrong answers -1pt",
    "hourglass":     "Hourglass bonus",
    "medal_penalty": "Medals get penalty",
}
SCORING_MODE_DESCRIPTIONS = {
    "wrong_penalty": f"every wrong answer is -{POINTS_PER_WRONG} pt.",
    "hourglass":     f"a correct answer scores {POINTS_PER_CORRECT} pts per ⏳ still showing (⏳⏳⏳⏳⏳ = {5 * POINTS_PER_CORRECT} pts).",
    "medal_penalty": f"players holding 🥇🥈🥉 when the round starts lose {POINTS_PER_MEDAL_WRONG} pts per wrong answer.",
}
DEFAULT_SCORING_LABEL = f"Default (+{POINTS_PER_CORRECT} per correct, no penalties)"

# ── qbreader category/subcategory lists ───────────────────────────────────────
# All entries are valid qbreader Subcategory or AlternateSubcategory string values.
# They are split at query time into the correct API parameters (see round.py).

CATEGORIES = [
    # Literature — Subcategory + AlternateSubcategory
    "American Literature", "British Literature", "Classical Literature",
    "European Literature", "World Literature", "Other Literature",
    "Drama", "Long Fiction", "Poetry", "Short Fiction", "Misc Literature",
    # History — Subcategory
    "American History", "Ancient History", "European History",
    "World History", "Other History",
    # Science — Subcategory
    "Biology", "Chemistry", "Physics", "Other Science",
    # Science — AlternateSubcategory
    "Math", "Astronomy", "Computer Science", "Earth Science", "Engineering", "Misc Science",
    # Fine Arts — Subcategory
    "Visual Fine Arts", "Auditory Fine Arts", "Other Fine Arts",
    # Fine Arts — AlternateSubcategory
    "Architecture", "Dance", "Film", "Jazz", "Musicals", "Opera", "Photography", "Misc Arts",
    # Religion — Subcategory + AlternateSubcategory
    "Religion", "Beliefs", "Practices",
    # Standalone Subcategories (no further breakdown in qbreader)
    "Mythology", "Philosophy", "Current Events", "Geography", "Other Academic",
    # Social Science — Subcategory + AlternateSubcategory
    "Social Science", "Anthropology", "Economics", "Linguistics",
    "Psychology", "Sociology", "Other Social Science",
    # Pop Culture — Subcategory
    "Movies", "Music", "Sports", "Television", "Video Games", "Other Pop Culture",
]

# These are valid qbreader AlternateSubcategory values.
# At query time, selected entries from this set go to alternate_subcategories=;
# everything else goes to subcategories=. (See round.py: _build_api_filters)
ALL_ALT_SUBCATEGORIES = {
    "Drama", "Long Fiction", "Poetry", "Short Fiction", "Misc Literature",
    "Math", "Astronomy", "Computer Science", "Earth Science", "Engineering", "Misc Science",
    "Architecture", "Dance", "Film", "Jazz", "Musicals", "Opera", "Photography", "Misc Arts",
    "Beliefs", "Practices",
    "Anthropology", "Economics", "Linguistics", "Psychology", "Sociology", "Other Social Science",
}

# Convenience sets used by the category keyboard bulk-toggle buttons
ALL_SCIENCE = {
    "Biology", "Chemistry", "Physics", "Other Science",
    "Math", "Astronomy", "Computer Science", "Earth Science", "Engineering", "Misc Science",
}

ALL_ARTS = {
    "Visual Fine Arts", "Auditory Fine Arts", "Other Fine Arts",
    "Architecture", "Dance", "Film", "Jazz", "Musicals", "Opera", "Photography", "Misc Arts",
}

# ── Difficulty map: display label → qbreader numeric string ───────────────────
DIFFICULTIES = {
    "Unrated (0)":          "0",
    "Middle School (1)":    "1",
    "HS Easy (2)":          "2",
    "HS Regular (3)":       "3",
    "HS Hard (4)":          "4",
    "HS Nationals (5)":     "5",
    "College ⭐ (6)":       "6",
    "College ⭐⭐ (7)":     "7",
    "College ⭐⭐⭐ (8)":   "8",
    "College ⭐⭐⭐⭐ (9)": "9",
    "Open (10)":            "10",
}

# ── ConversationHandler state IDs ─────────────────────────────────────────────
(
    SELECT_OPTION, SELECT_TIME_FIELD, INPUT_VALUE, SELECT_CATEGORIES,
    SELECT_DIFFICULTIES, SELECT_ADMIN, SELECT_SCORING,
) = range(7)
