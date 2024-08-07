import os
import random
import logging
import questions

from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
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

def start(update: Update, context: CallbackContext):
    """Start the bot."""
    db_counter.set(update.message.from_user.id, 0)
    update.message.reply_text("Привет! Я бот для викторин! Для начала игры нажми кнопку «Новый вопрос»!",
                              reply_markup=get_keyboard())
    return QUESTIONS


def handler_new_question_request(update: Update, context: CallbackContext):
    question = questions.get_random_question()
    db_user.set(update.message.from_user.id, question)
    update.message.reply_text(f"{question}")
    return ANSWER


def handler_solution(update, Context):
    """Проверяет правильность ответа на вопрос."""
    answer = questions.get_question_answer(db_user.get(update.message.from_user.id))
    if update.message.text.lower() == answer.lower():
        db_counter.incr(update.message.from_user.id)
        update.message.reply_text(
            "Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос».",)
        return QUESTIONS
    update.message.reply_text("Неправильно… Попробуешь ещё раз?", )
    return ANSWER


def handler_give_up(update, context):
    """Показывает правильный ответ."""
    answer = questions.get_question_answer(db_user.get(update.message.from_user.id))
    update.message.reply_text(
        f'Правильным было: "{answer}"\n Следующий вопрос',
        parse_mode="HTML",
    )
    question = questions.get_random_question()
    db_user.set(update.message.from_user.id, question)
    update.message.reply_text(f"{question}")
    return ANSWER


def handler_count(update, context):
    """Показывает счет."""
    count = str(db_counter.get(update.message.from_user.id), 'utf-8')
    update.message.reply_text(
        f"Счет: {count}",
        parse_mode="HTML",
    )
    return ANSWER


def cancel(update, context):
    count = db_counter.get(update.message.from_user.id)
    update.message.reply_text(
        f"Спасибо, за участие в Викторине! Ваш счет: {count}",
        parse_mode="HTML",
    )
    db_counter.delete(update.message.from_user.id)
    db_user.delete(update.message.from_user.id)
    return ConversationHandler.END


def main():
    # Load environment variables
    tg_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    tg_log_chat_id = os.getenv('TELEGRAM_BOT_LOGS_CHAT_ID')
    # Create the Updater and pass it your bot's token.
    updater = Updater(tg_bot_token)
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    # Handlers

    # on different commands - answer in Telegram
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

    # Add conversation handler
    dispatcher.add_handler(conv_handler)
    logger.addHandler(MyLogsHandler(tg_bot_token, tg_log_chat_id))
    # Start the Bot
    try:
        updater.start_polling()
        updater.idle()
    except Exception as e:
        logger.error(
            "Бот Telegram перестал работать: " + str(e),
            exc_info=True)


if __name__ == '__main__':
    load_dotenv()
    # Connect to DB
    db_user = redis.Redis.from_url(os.getenv('REDIS_URL_DB_TG_USER'))
    db_counter = redis.Redis.from_url(os.getenv('REDIS_URL_DB_TG_COUNTER'))
    db_questions = redis.Redis.from_url(os.getenv('REDIS_URL_DB_QUESTIONS'))
    questions = questions.Quiz(db_questions)
    #
    QUESTIONS = 1
    ANSWER = 2
    main()
