import re
import unicodedata


SPELLING_STRICTNESS = 2


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _damerau_levenshtein(left: str, right: str) -> int:
    distances = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
    for index in range(len(left) + 1):
        distances[index][0] = index
    for index in range(len(right) + 1):
        distances[0][index] = index

    for left_index, left_char in enumerate(left, start=1):
        for right_index, right_char in enumerate(right, start=1):
            cost = left_char != right_char
            distances[left_index][right_index] = min(
                distances[left_index - 1][right_index] + 1,
                distances[left_index][right_index - 1] + 1,
                distances[left_index - 1][right_index - 1] + cost,
            )
            if (
                left_index > 1
                and right_index > 1
                and left_char == right[right_index - 2]
                and left[left_index - 2] == right_char
            ):
                distances[left_index][right_index] = min(
                    distances[left_index][right_index],
                    distances[left_index - 2][right_index - 2] + cost,
                )
    return distances[-1][-1]


def _explicitly_rejects(answerline: str, answer: str) -> bool:
    patterns = re.findall(
        r'(?:reject|do not accept(?: or prompt)?(?: on)?)\s+["“]([^"”]+)["”]',
        answerline,
        re.IGNORECASE,
    )
    return any(_normalize(pattern) == answer for pattern in patterns)


def _normalized_words(value: str) -> list[str]:
    value = unicodedata.normalize("NFD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]+", value.lower())


_ROMAN_NUMERALS = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6"}


def _title_tokens(value: str) -> list[str]:
    tokens = _normalized_words(value)
    return [_ROMAN_NUMERALS.get(token, token) for token in tokens]


def _matches_title_abbreviation(reference: str, given: str) -> bool:
    reference_tokens = _title_tokens(reference)
    answer_tokens = _title_tokens(given)
    if len(reference_tokens) < 3 or not answer_tokens:
        return False
    return all(
        (
            token in reference_tokens
            if token.isdigit()
            else len(token) >= 3
            and any(
                len(reference_token) >= 6 and reference_token.startswith(token)
                for reference_token in reference_tokens
            )
        )
        for token in answer_tokens
    )


def _matches_distinctive_title_word(reference: str, answer: str) -> bool:
    words = _normalized_words(reference)
    if len(words) < 3 or len(_normalized_words(answer)) != 1 or len(answer) < 6:
        return False
    return any(
        len(word) >= 6 and _damerau_levenshtein(word, answer) <= 1
        for word in words
    )


def is_lenient_spelling_match(answerline: str, given: str) -> bool:
    primary_answer = re.sub(r"<[^>]+>", "", answerline.split("[", 1)[0])
    reference = _normalize(primary_answer)
    answer = _normalize(given)
    if not reference or not answer or _explicitly_rejects(answerline, answer):
        return False
    return _matches_title_abbreviation(primary_answer, given) or _matches_distinctive_title_word(
        primary_answer, answer
    ) or (
        SPELLING_STRICTNESS * _damerau_levenshtein(reference, answer) <= len(reference)
    )
