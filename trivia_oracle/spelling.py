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


def is_lenient_spelling_match(answerline: str, given: str) -> bool:
    primary_answer = re.sub(r"<[^>]+>", "", answerline.split("[", 1)[0])
    reference = _normalize(primary_answer)
    answer = _normalize(given)
    if not reference or not answer or _explicitly_rejects(answerline, answer):
        return False
    return SPELLING_STRICTNESS * _damerau_levenshtein(reference, answer) <= len(reference)
