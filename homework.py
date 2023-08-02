import logging
import time
import os
import sys
from http import HTTPStatus

import telegram
import requests
from dotenv import load_dotenv

from exceptions import ExceptionWithIncorrectStatus, ExceptionApiAnswer


load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TRY_API_ANSWER = 0
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
    return (PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)


def send_message(bot, message):
    """Функция для отправки сообщений."""
    logging.debug('Запуск отправки сообщения в Telegram.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправленно в Telegram.')
    except Exception as error:
        message = f'Неудачная попытка отправить сообщение в Telegram{error}'
        logging.error(message)


def get_api_answer(timestamp):
    """Делает запрос к эндпойнту."""
    payload = {'from_date': 0}
    logging.debug('Начало запроса к API.')
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except Exception:
        raise ExceptionApiAnswer('Неудачная попытка запроса к API.')
    if response.status_code != HTTPStatus.OK:
        raise ExceptionWithIncorrectStatus(
            'Неудачная попытка связи с сервером'
        )
    return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('"response" не являеться словарем.')
    if 'homeworks' not in response:
        raise KeyError('Нет ключа "homeworks" в словаре.')
    if 'current_date' not in response:
        raise KeyError('Нет ключа "current_date" в словаре.')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('"homeworks" не являеться списком.')
    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError(
            'Ключ "homework_name" отсутствует в словаре "homework".'
        )
    if 'status' not in homework:
        raise KeyError(
            'Ключ "status" отсутствует в словаре "homework".'
        )
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError('Статуса работы нет в списке допустимых.')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует какая то из переменных окружения')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_status = ''
    message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'

        finally:
            if message != last_status:
                send_message(bot, message)
                last_status = message
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
