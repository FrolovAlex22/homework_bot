import logging
import time
import os
import sys

import telegram
import requests

from dotenv import load_dotenv
from exceptions import ExceptionWithIncorrectStatus


load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Функция для проверки переменных окружения."""
    if not(PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        logging.critical(
            'Отсутствует какая то из переменных окружения'
        )
        raise NameError


def send_message(bot, message):
    """Функция для отправки сообщений"""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправленно в Telegram.')
    except Exception as error:
        logging.error(
            f'Неудачная попытка отправить сообщение в Telegram{error}'
        )
    else:
        logging.debug('Сообщение НЕ отправленно в Telegram.')


def get_api_answer(timestamp):
    """Делает запрос к эндпойнту."""
    payload = {'from_date': 0}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        message = f'Сбои при запросе к эндпоинту.{error}'
        send_message(message)
    if response.status_code != 200:
        logging.error('Недоступность эндпоинта')
        message = 'Недоступность эндпоинта.'
        send_message(message)
        raise ExceptionWithIncorrectStatus(
            'Неудачная попытка связи с сервером'
        )
    return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if type(response) == dict:
        if 'homeworks' and 'current_date' in response:
            homework = response.get('homeworks')
            if type(homework) != list:
                raise TypeError(
                    'В ответе API домашней работв под ключом `homeworks`'
                    ' данные приходят не в виде списка.'
                )
            return homework[0]
        else:
            logging.error('Нужных ключей в списке нет')
            message = 'Нужных ключей в списке нет'
            send_message(message)
    else:
        logging.info('В ответе нет словаря, что то пошло не так')
        raise TypeError(
            'В ответе API структура данных не соответствует ожиданиям.'
        )


def parse_status(homework):
    """Извлекает статус домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    previous_status = ''
    if not homework_name:
        logging.error('В домашней работе нет ключа "homework_name"')
        message = 'В домашней работе нет ключа "homework_name"'
        send_message(message)
        raise Exception('В домашней работе нет ключа "homework_name"')

    if homework_status == 'approved':
        verdict = HOMEWORK_VERDICTS['approved']
    elif homework_status == 'reviewing':
        verdict = HOMEWORK_VERDICTS['reviewing']
    elif homework_status == 'rejected':
        verdict = HOMEWORK_VERDICTS['rejected']

    if homework_status not in HOMEWORK_VERDICTS:
        logging.error('Статуса работы нет в списке допустимых.')

    if homework_status != previous_status:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    previous_status = homework_status


def main():
    """Основная логика работы бота."""

    try:
        check_tokens()
    except Exception:
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
