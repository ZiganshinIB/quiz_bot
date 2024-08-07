import logging
import random
import os
import redis
import questions

import vk_api as vk
from dotenv import load_dotenv
from vk_api.keyboard import VkKeyboard
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id


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


def send_question(event, questions):
    """Возвращает рандомный вопрос и выдает его пользователю."""
    question = random.choice(list(questions.keys()))
    db_user.set(event.user_id, question)
    return vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=get_keyboard(),
        message=f"{question}",
    )


def check_answer(event, questions):
    """Проверяет данный пользователем ответ на правильность."""

    if event.text.lower() == questions[str(db_user.get(event.user_id), 'utf-8')].lower():
        db_counter.incr(event.user_id)
        return vk_api.messages.send(
            user_id=event.user_id,
            random_id=get_random_id(),
            keyboard=get_keyboard(),
            message="Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос».",
        )
    return vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=get_keyboard(),
        message="Неправильно… Попробуешь ещё раз?",
    )


def report_correct_answer(event, vk_api, questions):
    """Сообщает пользователю правильный ответ при нажатии на кнопку 'Сдаться'."""
    answer = questions[str(db_user.get(event.user_id), 'utf-8')]
    vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        message=f"Правильным было: {answer}",
    )
    send_question(event, questions)


def get_number_points(event):
    """Выдает количетсво правильных ответов в текущей викторине."""
    return vk_api.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        keyboard=get_keyboard(),
        message=f"Количество правильных ответов:{str(db_counter.get(event.user_id), 'utf-8')}",
    )


if __name__ == "__main__":
    load_dotenv()
    # Connect to DB
    db_user = redis.Redis.from_url(os.getenv('REDIS_URL_DB_VK_USER'))
    db_counter = redis.Redis.from_url(os.getenv('REDIS_URL_DB_VK_COUNTER'))
    questions.init_all_questions()
    quizes = questions.quizes

    vk_session = vk.VkApi(token=os.getenv("VK_BOT_TOKEN"))
    vk_api = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            try:
                if event.text == "Начать":
                    start(event)
                elif event.text == "Новый вопрос":
                    send_question(event, quizes)
                elif event.text == "Сдаться":
                    report_correct_answer(event, vk_api, quizes)
                elif event.text == "Мой счёт":
                    get_number_points(event)
                else:
                    check_answer(event, quizes)
            except Exception as err:
                print(err)
