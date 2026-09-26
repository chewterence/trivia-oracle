"""
Two players send a correct answer at the same moment: both must be scored.

Drives the real python-telegram-bot Dispatcher with the bot's real handler
registration. Only the network is faked: qbreader is replaced with stubs and
the Telegram bot is a Mock that records send_message calls.

Run from the repo root:  python -m unittest discover tests
"""
import asyncio
import datetime
import os
import queue
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("TELEGRAM_TOKEN", "test-token")

from telegram import Chat, Message, Update, User
from telegram.ext import Dispatcher

from trivia_oracle import round as rnd
from trivia_oracle.__main__ import register_handlers
from trivia_oracle.config import POINTS_PER_CORRECT
from trivia_oracle.scores import scores
from trivia_oracle.settings import settings

CHAT = Chat(id=-100, type="group")
# qbreader round-trip time per submitted text. Real latency varies, so a
# simultaneous answer can easily be judged after the first one.
CHECK_LATENCY = {"Paris": 0.1, "paris": 0.5}
DEFAULT_LATENCY = 0.1

_in_flight = {"now": 0, "max": 0}
_in_flight_lock = threading.Lock()


async def _fake_fetch_tossup():
    return SimpleNamespace(
        question_sanitized="First clue. Second clue. Third clue.",
        answer_sanitized="Paris",
        answer="Paris",
    )


async def _fake_check_answer(answerline, given):
    with _in_flight_lock:
        _in_flight["now"] += 1
        _in_flight["max"] = max(_in_flight["max"], _in_flight["now"])
    try:
        await asyncio.sleep(CHECK_LATENCY.get(given, DEFAULT_LATENCY))
    finally:
        with _in_flight_lock:
            _in_flight["now"] -= 1
    if given == "Paris?":
        return SimpleNamespace(directive="prompt", directed_prompt="France")
    return SimpleNamespace(directive="accept" if given.lower() == answerline.lower() else "reject")


def _text_update(update_id: int, user: User, text: str) -> Update:
    message = Message(
        message_id=update_id,
        date=datetime.datetime.now(),
        chat=CHAT,
        from_user=user,
        text=text,
    )
    return Update(update_id=update_id, message=message)


class ConcurrentCorrectAnswersTest(unittest.TestCase):
    def setUp(self):
        # defaults=None: a bare Mock's truthy `defaults.run_async` would make
        # every handler async and hide the production behaviour.
        self.bot = mock.Mock(username="TriviaOracleBot", defaults=None)
        self.chat_data = {}
        self.updates = queue.Queue()
        self.dp = Dispatcher(self.bot, self.updates, workers=4, use_context=True)
        register_handlers(self.dp)
        # Same dispatch loop Updater.start_polling runs; it pulls from self.updates.
        threading.Thread(target=self.dp.start, daemon=True).start()

        # Long clue timers: only a correct answer should end the round.
        self._saved_timing = (settings.sentence_interval, settings.answer_wait, settings.scoring_modes)
        settings.sentence_interval, settings.answer_wait, settings.scoring_modes = 30.0, 30.0, set()

        scores.clear()
        _in_flight.update(now=0, max=0)
        self.patches = [
            mock.patch.object(rnd, "_fetch_tossup", _fake_fetch_tossup),
            mock.patch.object(rnd, "_check_answer", _fake_check_answer),
            mock.patch.object(rnd, "save_scores", lambda: None),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        settings.sentence_interval, settings.answer_wait, settings.scoring_modes = self._saved_timing
        scores.clear()
        self.dp.stop()
        # Never leave a round (and its lock) running into the next test.
        if rnd.round_lock.acquire(timeout=5):
            rnd.round_lock.release()

    def _start_round(self):
        update = SimpleNamespace(effective_chat=CHAT)
        rnd.start_round(update, SimpleNamespace(bot=self.bot, chat_data=self.chat_data))
        self.assertTrue(rnd.current_round["active"])

    def _wait_for_round_end(self):
        self.assertTrue(rnd.round_lock.acquire(timeout=10), "round never ended")
        rnd.round_lock.release()

    def _round_end_text(self) -> str:
        texts = [c.kwargs["text"] for c in self.bot.send_message.call_args_list]
        return next(t for t in texts if "[ROUND END]" in t)

    def test_simultaneous_correct_answers_both_score(self):
        alice = User(id=1, first_name="Alice", is_bot=False)
        bob = User(id=2, first_name="Bob", is_bot=False)
        self._start_round()

        # Both arrive in the same poll, as when two players hit send together.
        # Alice's check returns first and ends the round; Bob's is still in flight.
        self.updates.put(_text_update(1, alice, "Paris"))
        self.updates.put(_text_update(2, bob, "paris"))
        self._wait_for_round_end()

        self.assertEqual(_in_flight["max"], 2, "answers were checked one at a time, not in parallel")
        self.assertEqual(scores.get(1, {}).get("score"), POINTS_PER_CORRECT, "Alice not scored")
        self.assertEqual(scores.get(2, {}).get("score"), POINTS_PER_CORRECT, "Bob not scored")
        end_text = self._round_end_text()
        self.assertIn("Alice", end_text)
        self.assertIn("Bob", end_text)

    def test_wrong_answer_does_not_end_round_or_block_correct_one(self):
        alice = User(id=1, first_name="Alice", is_bot=False)
        bob = User(id=2, first_name="Bob", is_bot=False)
        self._start_round()

        self.updates.put(_text_update(1, alice, "London"))
        self.updates.put(_text_update(2, bob, "Paris"))
        self._wait_for_round_end()

        self.assertEqual(scores[1]["score"], 0)
        self.assertEqual(scores[2]["score"], POINTS_PER_CORRECT)
        self.assertNotIn("Alice", self._round_end_text())

    def test_directed_prompt_replies_without_scoring_or_ending_round(self):
        alice = User(id=1, first_name="Alice", is_bot=False)
        self._start_round()

        self.updates.put(_text_update(1, alice, "Paris?"))
        for _ in range(50):
            if any("Prompt on: France" in call.kwargs.get("text", "") for call in self.bot.send_message.call_args_list):
                break
            threading.Event().wait(0.05)

        prompts = [call.kwargs for call in self.bot.send_message.call_args_list if "Prompt on: France" in call.kwargs.get("text", "")]
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0]["chat_id"], CHAT.id)
        self.assertEqual(prompts[0]["reply_to_message_id"], 1)
        self.assertEqual(scores[1]["score"], 0)
        self.assertTrue(rnd.current_round["active"])

        rnd.current_round["event"].set()
        self._wait_for_round_end()


if __name__ == "__main__":
    unittest.main()
