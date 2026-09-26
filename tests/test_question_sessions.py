"""A live chat should not see the same tossup twice within its session."""
import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("TELEGRAM_TOKEN", "test-token")

from trivia_oracle import round as rnd


def _tossup(question):
    return SimpleNamespace(question_sanitized=question, answer_sanitized="Answer", answer="Answer")


class QuestionSessionTest(unittest.TestCase):
    def setUp(self):
        self.bot = mock.Mock(username="TriviaOracleBot")
        self.chat_data = {}
        self.update = SimpleNamespace(effective_chat=SimpleNamespace(id=-100))
        self.context = SimpleNamespace(bot=self.bot, chat_data=self.chat_data)

    def tearDown(self):
        if rnd.round_lock.locked():
            rnd.round_lock.release()
        rnd.current_round["active"] = False

    def _next(self, at, *questions, context=None):
        fetch = mock.AsyncMock(side_effect=[_tossup(q) for q in questions])
        with mock.patch.object(rnd, "_fetch_tossup", fetch), \
             mock.patch.object(rnd.time, "monotonic", return_value=at), \
             mock.patch.object(rnd.threading, "Thread") as thread:
            rnd.start_round(self.update, context or self.context)
        if rnd.round_lock.locked():
            rnd.round_lock.release()  # the mocked round thread did not run
        return fetch.await_count, thread.call_count

    def test_retries_seen_question_then_resets_after_inactivity(self):
        self.assertEqual(self._next(0, "First clue."), (1, 1))
        self.assertEqual(self._next(60, "First clue.", "Second clue."), (2, 1))
        self.assertEqual(self.chat_data["seen_tossups"], {"First clue.", "Second clue."})

        self.assertEqual(self._next(60 + rnd.SESSION_TIMEOUT, "First clue."), (1, 1))
        self.assertEqual(self.chat_data["seen_tossups"], {"First clue."})

    def test_sessions_are_per_chat_and_exhausted_retries_do_not_repeat(self):
        self._next(0, "First clue.")
        other_chat = SimpleNamespace(bot=self.bot, chat_data={})
        self.assertEqual(self._next(10, "First clue.", context=other_chat), (1, 1))

        attempts = ("First clue.",) * rnd.QUESTION_FETCH_ATTEMPTS
        self.assertEqual(self._next(20, *attempts), (rnd.QUESTION_FETCH_ATTEMPTS, 0))
        self.assertEqual(self.chat_data["last_next"], 0)
        self.assertEqual(self.chat_data["seen_tossups"], {"First clue."})
        self.assertIn("Could not find a new question", self.bot.send_message.call_args.kwargs["text"])
        self.assertEqual(self._next(rnd.SESSION_TIMEOUT, "First clue."), (1, 1))

    def test_next_during_a_round_does_not_refresh_the_session(self):
        self._next(0, "First clue.")
        rnd.round_lock.acquire()
        try:
            with mock.patch.object(rnd.time, "monotonic", return_value=rnd.SESSION_TIMEOUT - 1):
                rnd.start_round(self.update, self.context)
        finally:
            rnd.round_lock.release()

        self.assertEqual(self.chat_data["last_next"], 0)
        self.assertEqual(self._next(rnd.SESSION_TIMEOUT + 1, "First clue."), (1, 1))

    def test_failed_fetch_after_expiry_keeps_old_session_until_a_round_starts(self):
        self._next(0, "First clue.")
        with mock.patch.object(rnd, "_fetch_tossup", mock.AsyncMock(side_effect=RuntimeError("QBReader unavailable"))), \
             mock.patch.object(rnd.time, "monotonic", return_value=rnd.SESSION_TIMEOUT + 1):
            rnd.start_round(self.update, self.context)

        self.assertEqual(self.chat_data["last_next"], 0)
        self.assertEqual(self.chat_data["seen_tossups"], {"First clue."})
        self.assertEqual(self._next(rnd.SESSION_TIMEOUT + 2, "First clue."), (1, 1))

    def test_failed_duplicate_notice_releases_round_lock(self):
        self._next(0, "First clue.")
        self.bot.send_message.side_effect = RuntimeError("Telegram unavailable")

        with self.assertRaises(RuntimeError):
            self._next(20, *(("First clue.",) * rnd.QUESTION_FETCH_ATTEMPTS))

        self.assertFalse(rnd.round_lock.locked())
        self.bot.send_message.side_effect = None
        self.assertEqual(self._next(21, "Second clue."), (1, 1))

    def test_slow_fetch_has_total_deadline_and_releases_round_lock(self):
        async def slow_fetch():
            await asyncio.sleep(1)

        with mock.patch.object(rnd, "_fetch_tossup", side_effect=slow_fetch) as fetch, \
             mock.patch.object(rnd, "QUESTION_FETCH_TIMEOUT", 0.01):
            rnd.start_round(self.update, self.context)

        self.assertEqual(fetch.call_count, 1)
        self.assertFalse(rnd.round_lock.locked())
        self.assertNotIn("last_next", self.chat_data)
        self.assertIn("Failed to fetch a question", self.bot.send_message.call_args.kwargs["text"])
        self.assertEqual(self._next(1, "Second clue."), (1, 1))


if __name__ == "__main__":
    unittest.main()
