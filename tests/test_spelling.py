import os
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("TELEGRAM_TOKEN", "test-token")

from trivia_oracle import round as rnd
from trivia_oracle.scores import scores
from trivia_oracle.spelling import is_lenient_spelling_match


ANSWERLINE = 'Cú Chulainn [accept "Setanta"]'


class LenientSpellingTest(unittest.TestCase):
    def test_accepts_close_cu_chulainn_spellings(self):
        for answer in ("Cu chulhaim", "chulcullain", "Cu chulain", "cul chulain", "Chuculan"):
            with self.subTest(answer=answer):
                self.assertTrue(is_lenient_spelling_match(ANSWERLINE, answer))

    def test_rejects_an_unrelated_joke_answer(self):
        self.assertFalse(is_lenient_spelling_match(ANSWERLINE, "Chuck norris"))

    def test_round_accepts_a_lenient_spelling_after_qbreader_rejects_it(self):
        scores.clear()
        scores[1] = {"name": "Alice", "score": 0}
        rnd.current_round.update(
            answerline=ANSWERLINE,
            winners=[],
            winner_ids=set(),
            scoring_modes=frozenset(),
            hourglasses=1,
            event=threading.Event(),
        )

        async def rejected_answer(_answerline, _given):
            return SimpleNamespace(directive="reject")

        with mock.patch.object(rnd, "_check_answer", rejected_answer), mock.patch.object(rnd, "save_scores"):
            rnd._judge_answer(SimpleNamespace(id=1, first_name="Alice"), "Cu chulain")

        self.assertEqual(scores[1]["score"], 10)
        self.assertTrue(rnd.current_round["event"].is_set())
        scores.clear()


if __name__ == "__main__":
    unittest.main()
