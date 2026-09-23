import random
import unittest

from trivia_oracle.roasts import ROAST_COUNT, roast


class TriviaRoastsTest(unittest.TestCase):
    def test_roasts_include_the_answer_and_have_thousands_of_combinations(self):
        self.assertGreaterEqual(ROAST_COUNT, 5_000)
        self.assertIn("Migration", roast("Migration", random.Random(1)))

    def test_seeded_roasts_vary(self):
        roasts = {roast("Migration", random.Random(seed)) for seed in range(100)}
        self.assertGreaterEqual(len(roasts), 50)


if __name__ == "__main__":
    unittest.main()
