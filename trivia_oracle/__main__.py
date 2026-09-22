import logging

from telegram.ext import (
    CallbackQueryHandler, CommandHandler, ConversationHandler,
    Filters, MessageHandler, Updater,
)

from .config import (
    TOKEN,
    SELECT_OPTION, SELECT_TIME_FIELD, INPUT_VALUE,
    SELECT_CATEGORIES, SELECT_DIFFICULTIES, SELECT_ADMIN, SELECT_SCORING,
)
from .handlers import (
    configure,
    configure_admin,
    configure_input_value,
    configure_select_option,
    configure_select_scoring,
    configure_select_time_field,
    configure_toggle_category,
    configure_toggle_difficulty,
    error_handler,
    mock_answer,
    show_scores,
)
from .round import handle_round_answer, start_round
from .scores import load_scores

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def register_handlers(dp) -> None:
    dp.add_handler(CommandHandler("next", start_round))
    dp.add_handler(CommandHandler("scores", show_scores))
    dp.add_handler(CommandHandler("mock", mock_answer))
    dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler("configure", configure)],
        states={
            SELECT_OPTION:       [CallbackQueryHandler(configure_select_option)],
            SELECT_TIME_FIELD:   [CallbackQueryHandler(configure_select_time_field)],
            INPUT_VALUE:         [MessageHandler(Filters.text & ~Filters.command, configure_input_value)],
            SELECT_CATEGORIES:   [CallbackQueryHandler(configure_toggle_category)],
            SELECT_DIFFICULTIES: [CallbackQueryHandler(configure_toggle_difficulty)],
            SELECT_ADMIN:        [CallbackQueryHandler(configure_admin)],
            SELECT_SCORING:      [CallbackQueryHandler(configure_select_scoring)],
        },
        fallbacks=[],
    ))
    # run_async: the dispatcher otherwise handles updates one at a time, so a
    # second simultaneous answer would wait out the first one's qbreader check
    # and arrive after the round had already closed.
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_round_answer, run_async=True))
    dp.add_error_handler(error_handler)


def main() -> None:
    updater = Updater(TOKEN)
    register_handlers(updater.dispatcher)

    load_scores()
    updater.start_polling(allowed_updates=["message", "callback_query"])
    logging.info("TriviaOracleBot is running...")
    updater.idle()


if __name__ == "__main__":
    main()
