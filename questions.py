import redis
import os
import re
import argparse
from abc import ABC, abstractmethod

from dotenv import load_dotenv


class BaseFormatStrategy(ABC):

    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def extract_question_answer(self,text) -> dict:
        pass


class FormatStrategy(BaseFormatStrategy):

    def __init__(self,
                 block_splitter,
                 start_question,
                 start_answer,
                 **kwargs):
        super().__init__(**kwargs)
        self.block_splitter = block_splitter
        self.start_question = start_question
        self.start_answer = start_answer

    def extract_question_answer(self, text) -> dict:
        block_splitter = self.block_splitter
        start_question = self.start_question
        start_answer = self.start_answer

        blocks = text.split(block_splitter)
        cd = {}
        for index, block in enumerate(blocks):
            if re.search(start_question, block):
                question = re.sub(start_question, '', block).strip()
                answer = re.sub(start_answer, '', blocks[index + 1]).strip()
                cd[question] = answer
        return cd


class Quiz:
    def __init__(self, redis_db: redis.Redis):
        self.redis_db = redis_db

    def add_question(self, question, answer):
        self.redis_db.set(question, answer)

    def add_questions(self, questions: dict):
        """
        Добавляет вопросы в БД
        :param questions: Словарь вопрос-ответ
        :return: None
        """
        self.redis_db.mset(questions)

    def add_questions_from_file(self,
                                file_name,
                                encoding='KOI8-R',
                                format_strategy: BaseFormatStrategy = None):
        """
        Добавляет вопросы из файла в БД
        :param file_name: Имя файла
        :param encoding: Кодировка
        :return: None
        """
        with open(file_name, 'r', encoding=encoding) as f:
            quizes = f.read()
        if not format_strategy:
            format_strategy = self.__get_default_format_strategy__()
        cd = format_strategy.extract_question_answer(quizes)
        if cd:
           self.redis_db.mset(cd)

    def add_questions_from_directory(self, directory_name, encoding='KOI8-R',
                                     format_strategy: BaseFormatStrategy = None):
        """
        Добавляет вопросы из директории в БД
        :param directory_name: Имя директории
        :param encoding: Кодировка
        :return: None
        """
        for file_name in os.listdir(directory_name):
            if not os.path.isfile(os.path.join(directory_name, file_name)):
                full_path = os.path.join(directory_name, file_name)
                self.add_questions_from_file(full_path, encoding=encoding, format_strategy=format_strategy)

    def get_question_answer(self, question):
        return str(self.redis_db.get(question), 'utf-8')

    def get_random_question(self) -> str:
        return str(self.redis_db.randomkey(), 'utf-8')

    def __get_default_format_strategy__(self):
        fs = FormatStrategy(block_splitter='\n\n', start_question='Вопрос \d+:', start_answer='Ответ:')
        return fs


if __name__ == '__main__':
    load_dotenv()
    # Connect to DB
    db = redis.Redis.from_url(os.getenv('REDIS_URL_DB_QUESTIONS'))
    questions = Quiz(db)
    parser = argparse.ArgumentParser(
        description='Работа с базой данных с вопросами. \n Добавляет вопросы из файла или директории.\n'
                    'Необходимо указать параметр -f (иммеет приоритет выше) или -d для запуска'
    )
    parser.add_argument('-f', '--file', type=str, help='Имя файла')
    parser.add_argument('-d', '--directory', type=str, help='Имя директории')
    args = parser.parse_args()
    if args.file:
        questions.add_questions_from_file(args.file)
        print("Вопросы добавлены.")
    elif args.directory:
        questions.add_questions_from_directory(args.directory)
        print("Вопросы добавлены.")
    else:
        print("Ошибка: Не указано ни имя файла, ни имя директории.")
        parser.print_help()


