import os
import logging
import questions
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (Updater,
                          CommandHandler,
                          MessageHandler,
                          Filters,
                          ConversationHandler)
import redis
from logger import MyLogsHandler

logger = logging.getLogger(__name__)

QUESTIONS, ANSWER = 1, 2


def get_keyboard():
    """Добавляет кнопки боту."""
    keyboard = ReplyKeyboardMarkup([
        ["Новый вопрос", "Сдаться"],
        ["Мои счет"]
    ])
    return keyboard


def handler_start(update: Update, _, db_counter):
    """Start the bot."""
    db_counter.set(update.message.from_user.id, 0)
    msg = ("Привет! Я бот для викторин! "
           "Для начала игры нажми кнопку «Новый вопрос»!")
    update.message.reply_text(
        msg,
        reply_markup=get_keyboard())
    return QUESTIONS


def handler_new_question_request(update: Update, context, db_user, quiz):
    question = quiz.get_random_question()
    db_user.set(update.message.from_user.id, question)
    update.message.reply_text(f"{question}")
    return ANSWER


def handler_solution(update, _, db_counter, db_user, quiz):
    """Проверяет правильность ответа на вопрос."""
    answer = quiz.get_question_answer(db_user.get(update.message.from_user.id))
    if update.message.text.lower() == answer.lower():
        db_counter.incr(update.message.from_user.id)
        msg = ("Правильно! Поздравляю! "
               "Для следующего вопроса нажми «Новый вопрос».")
        update.message.reply_text(
            msg,)
        return QUESTIONS
    update.message.reply_text("Неправильно… Попробуешь ещё раз?", )
    return ANSWER


def handler_give_up(update, context, db_user, quiz):
    """Показывает правильный ответ."""
    answer = quiz.get_question_answer(db_user.get(update.message.from_user.id))
    update.message.reply_text(
        f'Правильным было: "{answer}"\n Следующий вопрос',
        parse_mode="HTML",
    )
    question = quiz.get_random_question()
    db_user.set(update.message.from_user.id, question)
    update.message.reply_text(f"{question}")
    return ANSWER


def handler_count(update, context, db_counter):
    """Показывает счет."""
    count = str(db_counter.get(update.message.from_user.id), 'utf-8')
    update.message.reply_text(
        f"Счет: {count}",
        parse_mode="HTML",
    )
    return ANSWER


def handler_cancel(update, _, db_counter, db_user):
    count = db_counter.get(update.message.from_user.id)
    update.message.reply_text(
        f"Спасибо, за участие в Викторине! Ваш счет: {count}",
        parse_mode="HTML",
    )
    db_counter.delete(update.message.from_user.id)
    db_user.delete(update.message.from_user.id)
    return ConversationHandler.END


def main():
    load_dotenv()

    db_user = redis.Redis.from_url(os.getenv('REDIS_URL_DB_TG_USER'))
    db_counter = redis.Redis.from_url(os.getenv('REDIS_URL_DB_TG_COUNTER'))
    db_questions = redis.Redis.from_url(os.getenv('REDIS_URL_DB_QUESTIONS'))
    quiz = questions.Quiz(db_questions)
    tg_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    tg_log_chat_id = os.getenv('TELEGRAM_BOT_LOGS_CHAT_ID')
    start = lambda update, context: handler_start(update, context, db_counter)
    new_question_request = lambda update, context: handler_new_question_request(
        update, context, db_user, quiz
    )
    send_count = lambda update, context: handler_count(
        update, context, db_counter
    )
    give_up_question = lambda update, context: handler_give_up(
        update, context, db_user, quiz
    )
    solution = lambda update, context: handler_solution(
        update, context, db_counter, db_user, quiz
    )
    cancel = lambda update, context: handler_cancel(
        update, context, db_counter, db_user
    )
    updater = Updater(tg_bot_token)
    dispatcher = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            QUESTIONS: [
                MessageHandler(
                    Filters.text("Новый вопрос"), new_question_request
                ),
                MessageHandler(
                    Filters.text("Мои счет"), send_count
                ),
            ],
            ANSWER: [
                MessageHandler(
                    Filters.text("Новый вопрос"), give_up_question
                ),
                MessageHandler(
                    Filters.text("Сдаться"), give_up_question
                ),
                MessageHandler(
                    Filters.text("Мои счет"), send_count
                ),
                MessageHandler(
                    Filters.text, solution
                ),
            ],

        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dispatcher.add_handler(conv_handler)
    logger.addHandler(MyLogsHandler(tg_bot_token, tg_log_chat_id))
    try:
        updater.start_polling()
        updater.idle()
    except Exception as e:
        logger.error(
            "Бот Telegram перестал работать: " + str(e),
            exc_info=True)


if __name__ == '__main__':
    main()
