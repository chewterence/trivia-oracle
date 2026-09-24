import asyncio
import logging
import re
import threading
from typing import Optional

from qbreader.asynchronous import Async

from .config import (
    ALL_ALT_SUBCATEGORIES, CATEGORIES, DIFFICULTIES,
    POINTS_PER_CORRECT, POINTS_PER_MEDAL_WRONG, POINTS_PER_WRONG,
)
from .scores import format_scoreboard, medalist_ids, save_scores, scores, scores_lock
from .settings import settings
from .spelling import is_lenient_spelling_match

# ── Round state ───────────────────────────────────────────────────────────────

current_round: dict = {
    "active": False,
    "answer_sanitized": None,
    "answerline": None,
    "winners": [],       # [(first_name, points_awarded)] for everyone who answered correctly
    "winner_ids": set(), # user IDs already scored this round (one correct answer each)
    "penalties": {},     # {first_name: total_points_deducted} for wrong answers this round
    "sentences": [],
    "hourglasses": 0,    # ⏳ count on the latest clue message (hourglass scoring)
    "scoring_modes": frozenset(),  # snapshot of settings.scoring_modes at round start
    "medalists": set(),  # user IDs holding 🥇🥈🥉 at round start (medal_penalty scoring)
    "pending_checks": 0, # answers sent while active whose qbreader check hasn't returned yet
    "event": threading.Event(),
}
round_lock = threading.Lock()  # held for the duration of a round; prevents overlapping rounds
# Signalled whenever pending_checks drops, so the round can close once every
# answer sent before the buzzer has been judged. Shares scores_lock.
checks_settled = threading.Condition(scores_lock)
PENDING_CHECK_TIMEOUT = 15.0  # seconds; don't hold the round open forever if qbreader hangs


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_api_filters() -> tuple:
    """
    Split settings.selected_categories into the two qbreader API parameters.

    Returns (subcategories, alt_subcategories) — either can be None (= no filter).
    When all categories are selected we return (None, None) to avoid sending a
    redundant filter and to stay within URL-length limits.
    """
    if settings.selected_categories == set(CATEGORIES):
        return None, None

    subcategories = [c for c in settings.selected_categories if c not in ALL_ALT_SUBCATEGORIES] or None
    alt_subcategories = [c for c in settings.selected_categories if c in ALL_ALT_SUBCATEGORIES] or None
    return subcategories, alt_subcategories


async def _fetch_tossup():
    subcategories, alt_subcategories = _build_api_filters()
    difficulties = (
        [DIFFICULTIES[d] for d in settings.selected_difficulties]
        if settings.selected_difficulties != set(DIFFICULTIES)
        else None
    )
    async with await Async.create() as qb:
        tossups = await qb.random_tossup(
            number=1,
            subcategories=subcategories,
            alternate_subcategories=alt_subcategories,
            difficulties=difficulties,
        )
    return tossups[0]


def _points_for_correct() -> int:
    if "hourglass" in current_round["scoring_modes"]:
        return POINTS_PER_CORRECT * current_round["hourglasses"]
    return POINTS_PER_CORRECT


def _penalty_for_wrong(user_id: int) -> int:
    modes = current_round["scoring_modes"]
    penalty = 0
    if "wrong_penalty" in modes:
        penalty += POINTS_PER_WRONG
    if "medal_penalty" in modes and user_id in current_round["medalists"]:
        penalty += POINTS_PER_MEDAL_WRONG
    return penalty


async def _check_answer(answerline: str, given: str):
    async with await Async.create() as qb:
        return await qb.check_answer(answerline, given)


# ── Round execution ───────────────────────────────────────────────────────────

def _run_round(bot, chat_id: int) -> None:
    sentences = current_round["sentences"]
    total = len(sentences)

    for i, sentence in enumerate(sentences):
        if current_round["event"].is_set():
            break
        current_round["hourglasses"] = total - i
        bot.send_message(
            chat_id=chat_id,
            text=f"{'🎯' * (i + 1)}\n{sentence}\n{'⏳' * (total - i)}",
        )
        current_round["event"].wait(settings.sentence_interval)

    if not current_round["event"].is_set():
        current_round["event"].wait(settings.answer_wait)

    with checks_settled:
        current_round["active"] = False
        # Answers sent at the same moment as the first correct one are still
        # being checked; score them before announcing the result.
        if not checks_settled.wait_for(lambda: current_round["pending_checks"] == 0, PENDING_CHECK_TIMEOUT):
            logging.warning("Closing round with %d answer check(s) still pending", current_round["pending_checks"])
    _send_round_end(bot, chat_id)
    bot.send_message(chat_id=chat_id, text=format_scoreboard())
    round_lock.release()


def _send_round_end(bot, chat_id: int) -> None:
    next_prompt = f"\n\nNext question: /next@{bot.username}"
    winners = current_round["winners"]
    penalties = current_round["penalties"]

    if winners:
        if "hourglass" in current_round["scoring_modes"]:
            labels = [f"{name} (+{pts} pts)" for name, pts in winners]
        else:
            labels = [name for name, _ in winners]
        if len(labels) == 1:
            congrats = f"Congrats {labels[0]} answered correctly!"
        else:
            names = ", ".join(labels[:-1]) + f" & {labels[-1]}"
            congrats = f"Congrats {names} all answered correctly!"
        result = f"✅✅✅ [ROUND END] ✅✅✅\n {congrats}\n\n Answer: {current_round['answer_sanitized']}"
    else:
        result = f"❌❌❌ [ROUND END] ❌❌❌\n Sad to say, nobody answered correctly.\n\n The answer is actually: {current_round['answer_sanitized']}"

    if penalties:
        penalty_lines = "\n".join(f"  -{pts} pts — {name}" for name, pts in sorted(penalties.items()))
        result += f"\n\n❌ Wrong answer deductions:\n{penalty_lines}"

    result += next_prompt
    bot.send_message(chat_id=chat_id, text=result)


# ── Public Telegram handler functions ─────────────────────────────────────────

def handle_round_answer(update, _context) -> None:
    """Runs on a dispatcher worker thread (run_async) so simultaneous answers are checked in parallel."""
    given = update.message.text.strip()
    user = update.effective_user

    with scores_lock:
        if not current_round["active"] or user.id in current_round["winner_ids"]:
            return
        current_round["pending_checks"] += 1
        if user.id not in scores:
            scores[user.id] = {"name": user.first_name, "score": 0}
        else:
            scores[user.id]["name"] = user.first_name

    try:
        prompt = _judge_answer(user, given)
        if prompt:
            _context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🤔 {user.first_name}, Prompt on: {prompt}",
                reply_to_message_id=update.message.message_id,
            )
    finally:
        with checks_settled:
            current_round["pending_checks"] -= 1
            checks_settled.notify_all()


def _judge_answer(user, given: str) -> Optional[str]:
    try:
        judgement = asyncio.run(_check_answer(current_round["answerline"], given))
    except Exception as e:
        logging.error("Answer check failed: %s", e)
        return

    if judgement.directive == "accept" or (
        judgement.directive == "reject"
        and is_lenient_spelling_match(current_round["answerline"], given)
    ):
        with scores_lock:
            if user.id in current_round["winner_ids"]:
                return
            points = _points_for_correct()
            scores[user.id]["score"] += points
            save_scores()
            current_round["winner_ids"].add(user.id)
            current_round["winners"].append((user.first_name, points))
        current_round["event"].set()

    elif judgement.directive == "prompt":
        return judgement.directed_prompt or "be more specific"

    elif judgement.directive == "reject":
        penalty = _penalty_for_wrong(user.id)
        if not penalty:
            return
        with scores_lock:
            scores[user.id]["score"] -= penalty
            save_scores()
            name = user.first_name
            current_round["penalties"][name] = current_round["penalties"].get(name, 0) + penalty


def start_round(update, context) -> None:
    if not round_lock.acquire(blocking=False):
        return

    try:
        tossup = asyncio.run(_fetch_tossup())
    except Exception as e:
        logging.error("Failed to fetch question: %s", e)
        context.bot.send_message(chat_id=update.effective_chat.id, text="Failed to fetch a question. Try /next again.")
        round_lock.release()
        return

    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', tossup.question_sanitized) if s.strip()]
    with scores_lock:
        medalists = medalist_ids()
    current_round.update({
        "active": True,
        "answer_sanitized": tossup.answer_sanitized,
        "answerline": tossup.answer,
        "winners": [],
        "winner_ids": set(),
        "penalties": {},
        "sentences": sentences,
        "hourglasses": len(sentences),
        "scoring_modes": frozenset(settings.scoring_modes),
        "medalists": medalists,
        "pending_checks": 0,
    })
    current_round["event"].clear()
    logging.info("Answer: %s", tossup.answer_sanitized)

    threading.Thread(
        target=_run_round,
        args=(context.bot, update.effective_chat.id),
        daemon=True,
    ).start()
