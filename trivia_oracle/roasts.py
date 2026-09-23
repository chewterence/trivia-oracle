import random


OPENERS = (
    "the clue just filed a formal complaint because",
    "somewhere, a quizbowl packet quietly closed itself after",
    "the answer checker is opening a support ticket because of",
    "the buzzer would like to clarify that it did not endorse",
    "the hourglass saw this answer and asked for a transfer",
    "the study guide has entered witness protection after",
    "a professor has paused mid-lecture to process",
    "the bibliography is now mostly redacted because of",
    "the clue gave you every chance before receiving",
    "the scoreboard has classified this as a weather event after",
    "the packet is requesting hazard pay for",
    "Wikipedia opened a new tab and immediately regretted",
    "the quiz gods have placed a hold on",
    "the answerline is checking its legal options after",
    "the library lights flickered when it detected",
    "a historian just added an asterisk next to",
    "the facts are currently buffering around",
    "the clue is asking its union representative about",
    "a research assistant has been assigned to investigate",
    "the textbook has started a group chat about",
    "the academic decathlon has issued a weather advisory for",
    "a citation has gone missing in response to",
    "the packet has marked this for peer review:",
    "the buzzer heard a noise complaint about",
)

MIDDLES = (
    "that answer",
    "that detour from the prompt",
    "that leap of interpretive freedom",
    "that alternate-universe fact pattern",
    "that aggressively independent research result",
    "that answer-shaped object",
    "that confidence-first methodology",
    "that bold use of nearby vocabulary",
    "that unusually creative reading of the clue",
    "that answer arriving without adult supervision",
    "that category-defying moment",
    "that attempt to negotiate with the answerline",
    "that speedrun through every wrong subcategory",
    "that evidence-optional conclusion",
    "that unlicensed remix of the question",
    "that rogue scholarly intervention",
    "that guess from a parallel packet",
    "that enthusiastic departure from the facts",
    "that freestyle interpretation of history",
    "that unexpected plot twist in the response",
    "that answer attempting a hostile takeover of the clue",
    "that beautiful disaster of a buzz",
    "that answer with absolutely no fear of consequences",
    "that academic jump scare",
)

CLOSERS = (
    "Bold strategy.",
    "The confidence is doing most of the work here.",
    "Ten points if we were playing something else.",
    "The clue did not consent to this interpretation.",
    "A strong effort from an entirely different question.",
    "Somehow, this has become a geography problem.",
    "We appreciate the commitment to originality.",
    "The facts will be arriving in a later update.",
    "This answer has been forwarded to quality assurance.",
    "The packet has requested a moment of silence.",
    "No further questions from the answer checker.",
    "The vibes are immaculate; the accuracy is negotiating.",
    "A daring move in the field of being elsewhere.",
    "The next clue was going to explain it, but never mind.",
    "That was a power, just not a power answer.",
    "The scoreboard will remember this with great professionalism.",
    "A citation would improve this situation dramatically.",
    "The clue is considering a restraining order.",
    "This has been logged as an educational event.",
    "The answerline has muted the conversation.",
)

ROAST_COUNT = len(OPENERS) * len(MIDDLES) * len(CLOSERS)


def roast(answer: str, rng=None) -> str:
    picker = rng or random
    return f"🤣 “{answer}” — {picker.choice(OPENERS)} {picker.choice(MIDDLES)} {picker.choice(CLOSERS)}"
