import platform
import datetime
import asyncio
import aiohttp
import sys
from pprint import pprint

# адреса для запиту з місцем підставлення дати
URL_TEMPLATE = "https://api.privatbank.ua/p24api/exchange_rates?json&date={}"
# формат дати
DATE_FORMAT = "%d.%m.%Y"
# дозволені валюти
ALLOWED = ['USD', 'EUR', 'CHF', 'GBP', 'PLN', 'CAD']


def get_date(days_ago: int) -> str:
    """ 
        Повертає рядкове значення дати яку було задано кількість днів тому
    """
    to_day = datetime.datetime.now()
    date = to_day - datetime.timedelta(days=days_ago)
    return date.strftime(DATE_FORMAT)


async def fetch_oneday(session: aiohttp.ClientSession, url: str):
    """ 
        Асинхронна функція яка обробляє один запит для заданої сесії та адреси
        Також обробляє помилки з'єднання
    """
    # намагаємось відправити запит
    try:
        async with session.get(url) as response:
            # обробляємо статус
            if response.status == 200:
                # отримуємо json представлення
                return await response.json()
            else:
                # якщо помилка
                return f'Error status: {response.status} for {url}'
    # якщо помилка з'єднання
    except aiohttp.ClientConnectorError as err:
        return f'Connection error: {err} '


async def fatch_data(period: int):
    """ 
        Асинхронна функція обробляє запити за заданий період
    """
    # створюємо сесію
    async with aiohttp.ClientSession() as session:
        # створюємо список завдань 
        # що складається з викликів асинхронних функцій
        # для кожного дня в періоді
        tasks = [
            fetch_oneday(session, URL_TEMPLATE.format(get_date(i))) for i in range(period)
        ]
        # отримуємо результат всих запитів
        responses = await asyncio.gather(*tasks)

    # повертаємо
    return responses

def handle_args():
    """ 
        Обробляє аргументи командного рядка.
        Враховує варіанти вибору назв валют.
        По замовчуванню повертає список валют ['EUR', 'USD']
    """
    # якщо аргументи не задані
    if len(sys.argv) < 2:
        print("Arguments error!")
        exit()

    # Обробляємо параметр періоду
    try:
        period = int(sys.argv[1])
    except ValueError:
        print("Arguments error! Argument must be a number!")
        exit()

    # якщо період виходить за рамки дозволеного
    if  period > 10 or period < 1:
        print("Arguments error! Argument must be between 1 and 10")
        exit()
    
    # варіант по замовчуванню
    if len(sys.argv) == 2: 
        return period, ['USD', 'EUR']

    # обробка вказаних валют на правильність
    if len(sys.argv) > 2:
        values = sys.argv[2:]
        values = [v.upper() for v in values]
        for value in values:
            if value not in ALLOWED:
                print(f"Arguments error! Currency name is unknown {value}")
                exit()
        return period, values

def parse_data(data: list[dict], currencies:list[str]) -> list[dict]:
    """ 
        Парсить вхідні дані.
        Тобто фільтрує лише потрібні валюти
    """
    result = []
    # Обходимо словник даних
    for day_data in data:
        # якщо елемент рядок - то це повідомлення про помилку
        # інкше це список словників
        if not isinstance(day_data, str):
            parsed_data = {}
            parsed_data['date'] = day_data['date']
            # фільтруємо задані валюти
            for currency in currencies:
                for rates in day_data['exchangeRate']:
                    if rates['currency'] == currency:
                        parsed_data[currency] = {}
                        
                        # в першу чергу отримуємо готівковий курс
                        # якщо його не має, то отримуємо курс НацБанку
                        rate = rates.get('saleRate', None)
                        rateNB = rates.get('saleRate', None)
                        # якщо і такий відлсутній то значення 0.0
                        parsed_data[currency]['sale'] = rate if rate else rateNB if rateNB else 0.0
                        
                        rate = rates.get('purchaseRate', None)
                        rateNB = rates.get('purchaseRateNB', None)
                        parsed_data[currency]['purchase'] = rate if rate else rateNB if rateNB else 0.0
            # кладемо в список результатів
            result.append(parsed_data)
        else:
            # кладемо помилку
            result.append(day_data)
    # повертаємо
    return result
        
                    

if __name__ == "__main__":
    # обробляєм аргументи
    period, currencies = handle_args()

    # перевірка платформи на якій запуститься скріпт
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # отримуємо дані від приват банку
    data = asyncio.run(fatch_data(period))
    # фільтруємо дані
    parsed = parse_data(data, currencies)

    # виводимо на консоль
    pprint(parsed, sort_dicts=False, compact=True, indent=2)
    
    

