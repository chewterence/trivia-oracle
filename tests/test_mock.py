import os
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("TELEGRAM_TOKEN", "test-token")

from trivia_oracle.handlers import mock_answer
from trivia_oracle.scores import scores


class MockAnswerTest(unittest.TestCase):
    def setUp(self):
        scores.clear()
        scores[1] = {"name": "Alice", "score": 10}
        self.alice = SimpleNamespace(id=1, first_name="Alice")
        self.target = SimpleNamespace(
            message_id=22,
            text="Migration",
            caption=None,
            from_user=SimpleNamespace(first_name="Bob"),
        )
        self.command = SimpleNamespace(reply_to_message=self.target, reply_text=mock.Mock())
        self.update = SimpleNamespace(message=self.command, effective_user=self.alice, effective_chat=SimpleNamespace(id=-100))
        self.context = SimpleNamespace(bot=mock.Mock())

    def tearDown(self):
        scores.clear()

    def test_mock_spends_two_points_and_replies_to_the_target(self):
        with mock.patch("trivia_oracle.handlers.save_scores"), mock.patch(
            "trivia_oracle.handlers.roast", return_value="🤣 custom roast"
        ):
            mock_answer(self.update, self.context)

        self.assertEqual(scores[1]["score"], 8)
        self.context.bot.send_message.assert_called_once_with(
            chat_id=-100,
            text="🤣 custom roast",
            reply_to_message_id=22,
        )

    def test_mock_requires_two_points(self):
        scores[1]["score"] = 1
        with mock.patch("trivia_oracle.handlers.save_scores"):
            mock_answer(self.update, self.context)

        self.assertEqual(scores[1]["score"], 1)
        self.command.reply_text.assert_called_once_with("You need 2 points to /mock.")
        self.context.bot.send_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
