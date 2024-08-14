import logging
import os
import redis
import questions

import vk_api as vk
from dotenv import load_dotenv
from vk_api.keyboard import VkKeyboard
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from logger import MyLogsHandler

logger = logging.getLogger(__name__)


def get_keyboard():
    """Добавляет кнопки боту."""
    keyboard = VkKeyboard()

    keyboard.add_button("Новый вопрос")
    keyboard.add_button("Сдаться")

    keyboard.add_line()
    keyboard.add_button("Мой счёт")

    return keyboard.get_keyboard()


def start(event):
    """Запускает новую викторину.

    Обнуляет количество правильных ответов."""
    db_counter.set(event.user_id, 0)
    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=get_keyboard(),
        message="Для начала игры нажми кнопку «Новый вопрос»!",
    )


def send_question(event):
    """Возвращает рандомный вопрос и выдает его пользователю."""
    question = quiz.get_random_question()
    db_user.set(event.user_id, question)
    return vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=get_keyboard(),
        message=f"{question}",
    )


def check_answer(event):
    """Проверяет данный пользователем ответ на правильность."""

    if event.text.lower() == quiz.get_question_answer(
            str(db_user.get(event.user_id),
                'utf-8')).lower():
        db_counter.incr(event.user_id)
        msg = ("Правильно! Поздравляю! "
               "Для следующего вопроса нажми «Новый вопрос».")
        return vk_api.messages.send(
            user_id=event.user_id,
            random_id=get_random_id(),
            keyboard=get_keyboard(),
            message=msg,
        )
    return vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=get_keyboard(),
        message="Неправильно… Попробуешь ещё раз?",
    )


def report_correct_answer(event, vk_api):
    """
    Сообщает пользователю правильный ответ,
    при нажатии на кнопку 'Сдаться'.
    """
    answer = quiz.get_question_answer(str(db_user.get(event.user_id), 'utf-8'))
    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        message=f"Правильным было: {answer}",
    )
    send_question(event)


def get_number_points(event):
    """Выдает количетсво правильных ответов в текущей викторине."""
    return vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=get_keyboard(),
        message=f"Количество правильных ответов:"
                f"{str(db_counter.get(event.user_id), 'utf-8')}",
    )


if __name__ == "__main__":
    load_dotenv()
    db_user = redis.Redis.from_url(os.getenv('REDIS_URL_DB_VK_USER'))
    db_counter = redis.Redis.from_url(os.getenv('REDIS_URL_DB_VK_COUNTER'))
    db_questions = redis.Redis.from_url(os.getenv('REDIS_URL_DB_QUESTIONS'))
    quiz = questions.Quiz(db_questions)
    vk_session = vk.VkApi(token=os.getenv("VK_BOT_TOKEN"))
    vk_api = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)

    tg_logger_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    tg_logger_chat_id = os.getenv('TELEGRAM_BOT_LOGS_CHAT_ID')
    logger.addHandler(MyLogsHandler(tg_logger_bot_token, tg_logger_chat_id))

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            try:
                if event.text == "Начать":
                    start(event)
                elif event.text == "Новый вопрос":
                    send_question(event)
                elif event.text == "Сдаться":
                    report_correct_answer(event, vk_api)
                elif event.text == "Мой счёт":
                    get_number_points(event)
                else:
                    check_answer(event)
            except Exception as err:
                logger.error(
                    "Бот VK перестал работать: " + str(err),
                    exc_info=True)
