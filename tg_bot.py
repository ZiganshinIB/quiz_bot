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


def get_keyboard():
    """Добавляет кнопки боту."""
    keyboard = ReplyKeyboardMarkup([
        ["Новый вопрос", "Сдаться"],
        ["Мои счет"]
    ])
    return keyboard


def start(update: Update, _):
    """Start the bot."""
    db_counter.set(update.message.from_user.id, 0)
    msg = ("Привет! Я бот для викторин! "
           "Для начала игры нажми кнопку «Новый вопрос»!")
    update.message.reply_text(
        msg,
        reply_markup=get_keyboard())
    return QUESTIONS


def handler_new_question_request(update: Update, _):
    question = quiz.get_random_question()
    db_user.set(update.message.from_user.id, question)
    update.message.reply_text(f"{question}")
    return ANSWER


def handler_solution(update, _):
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


def handler_give_up(update, _):
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


def handler_count(update, _):
    """Показывает счет."""
    count = str(db_counter.get(update.message.from_user.id), 'utf-8')
    update.message.reply_text(
        f"Счет: {count}",
        parse_mode="HTML",
    )
    return ANSWER


def cancel(update, _):
    count = db_counter.get(update.message.from_user.id)
    update.message.reply_text(
        f"Спасибо, за участие в Викторине! Ваш счет: {count}",
        parse_mode="HTML",
    )
    db_counter.delete(update.message.from_user.id)
    db_user.delete(update.message.from_user.id)
    return ConversationHandler.END


def main():
    tg_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    tg_log_chat_id = os.getenv('TELEGRAM_BOT_LOGS_CHAT_ID')
    updater = Updater(tg_bot_token)
    dispatcher = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            QUESTIONS: [
                MessageHandler(
                    Filters.text("Новый вопрос"), handler_new_question_request
                ),
                MessageHandler(
                    Filters.text("Мои счет"), handler_count
                ),
            ],
            ANSWER: [
                MessageHandler(
                    Filters.text("Новый вопрос"), handler_give_up
                ),
                MessageHandler(
                    Filters.text("Сдаться"), handler_give_up
                ),
                MessageHandler(
                    Filters.text("Мои счет"), handler_count
                ),
                MessageHandler(
                    Filters.text, handler_solution
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
    load_dotenv()
    db_user = redis.Redis.from_url(os.getenv('REDIS_URL_DB_TG_USER'))
    db_counter = redis.Redis.from_url(os.getenv('REDIS_URL_DB_TG_COUNTER'))
    db_questions = redis.Redis.from_url(os.getenv('REDIS_URL_DB_QUESTIONS'))
    quiz = questions.Quiz(db_questions)
    QUESTIONS = 1
    ANSWER = 2
    main()
