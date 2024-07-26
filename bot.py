import telebot
from telebot import types
import sqlite3
import datetime

# Настройка бота
API_TOKEN = '7187174773:AAF-3yyj0MLC3fc1_1gw7dap86JLxtMBq3M'
bot = telebot.TeleBot(API_TOKEN)

# Подключение к базе данных
conn = sqlite3.connect('health_bot.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE,
    name TEXT,
    weight REAL,
    water_norm REAL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS food (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    food TEXT,
    timestamp TEXT,
    date TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS water (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    amount INTEGER,
    timestamp TEXT,
    date TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS weight_history (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    weight REAL,
    timestamp TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)
''')

conn.commit()

# Словарь для хранения состояния пользователя
user_states = {}

# Стартовая команда
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Бот активирован. Используйте /help для получения списка команд.")

# Команда помощи
@bot.message_handler(commands=['help'])
def help_command(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("/register"),
        types.KeyboardButton("/add_food"),
        types.KeyboardButton("/add_water"),
        types.KeyboardButton("/stats"),
        types.KeyboardButton("/change_weight"),
        types.KeyboardButton("/calculate_glasses")
    )
    help_text = (
        "/register - отвечает за твою регистрацию\nЭту кнопку нужно нажать в первую очередь и заполнить нужные поля 🥰\n\n"
        "/add\_food - нажав на эту кнопку или команду можно добавить запись о еде (а именно что ты кушал и пил в формате записки)\n\n"
        "Пример:\n\n _Покушал бутеры и выпил чаю_ \n\n 👇Записи о количестве выпитой воды заполняется ниже в пункте Вода\n\n"
        "/add\_water - нажав на эту кнопку или команду можно добавить запись о выпитой за сегодня воде\n\n"
        "/stats - получить статистику себя и меня 😘\n\n"
        "/change\_weight - с помощью этой функции можно обновить свой вес и бот автоматически пересчитает сколько воды тебе нужно пить в день и занесёт твой результат в статистику веса, которую ты сможешь смотреть в stats\n\n"
        "/calculate\_glasses - с помощью этой функции ты сможешь поститать количество оставшихся на сегодня стаканов воды ❤️"
    )
    bot.send_message(message.chat.id, help_text, reply_markup=keyboard, parse_mode="Markdown")

# Команда регистрации
@bot.message_handler(commands=['register'])
def register(message):
    user_states[message.from_user.id] = {'state': 'REGISTER_NAME'}
    bot.reply_to(message, 'Введите ваше имя:')

def handle_registration(message):
    user_id = message.from_user.id
    if user_states[user_id]['state'] == 'REGISTER_NAME':
        user_states[user_id]['name'] = message.text
        user_states[user_id]['state'] = 'REGISTER_WEIGHT'
        bot.reply_to(message, 'Введите ваш вес (кг):')
    elif user_states[user_id]['state'] == 'REGISTER_WEIGHT':
        name = user_states[user_id]['name']
        weight = float(message.text)
        water_norm = weight * 30

        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        if user:
            bot.reply_to(message, 'Вы уже зарегистрированы.')
        else:
            cursor.execute('INSERT INTO users (user_id, name, weight, water_norm) VALUES (?, ?, ?, ?)', (user_id, name, weight, water_norm))
            conn.commit()
            bot.reply_to(message, f'Регистрация завершена. Ваша норма воды: {water_norm} мл в день.')
        del user_states[user_id]

# Команда добавления еды
@bot.message_handler(commands=['add_food'])
def add_food(message):
    user_states[message.from_user.id] = {'state': 'ADD_FOOD'}
    bot.reply_to(message, 'Что вы скушали?')

def handle_food(message):
    user_id = message.from_user.id
    food = message.text
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    date = datetime.datetime.now().strftime('%Y-%m-%d')

    cursor.execute('INSERT INTO food (user_id, food, timestamp, date) VALUES (?, ?, ?, ?)', (user_id, food, timestamp, date))
    conn.commit()
    bot.reply_to(message, 'Запись добавлена.')
    del user_states[user_id]

# Команда добавления воды
@bot.message_handler(commands=['add_water'])
def add_water(message):
    user_states[message.from_user.id] = {'state': 'ADD_WATER'}
    bot.reply_to(message, 'Сколько миллилитров воды вы выпили?')

def handle_water(message):
    user_id = message.from_user.id
    amount = int(message.text)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    date = datetime.datetime.now().strftime('%Y-%m-%d')

    cursor.execute('INSERT INTO water (user_id, amount, timestamp, date) VALUES (?, ?, ?, ?)', (user_id, amount, timestamp, date))
    conn.commit()

    cursor.execute('SELECT SUM(amount) FROM water WHERE user_id = ? AND date = ?', (user_id, date))
    total_water = cursor.fetchone()[0]

    cursor.execute('SELECT water_norm FROM users WHERE user_id = ?', (user_id,))
    water_norm = cursor.fetchone()[0]

    remaining = water_norm - total_water

    bot.reply_to(message, f'Запись добавлена. Остаток от нормы: {remaining} мл.')
    del user_states[user_id]

# Команда смены веса
@bot.message_handler(commands=['change_weight'])
def change_weight(message):
    user_states[message.from_user.id] = {'state': 'CHANGE_WEIGHT'}
    bot.reply_to(message, 'Введите новый вес (кг):')

def handle_change_weight(message):
    user_id = message.from_user.id
    if user_states[user_id]['state'] == 'CHANGE_WEIGHT':
        new_weight = float(message.text)
        new_water_norm = new_weight * 30

        # Добавляем запись в историю веса
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('INSERT INTO weight_history (user_id, weight, timestamp) VALUES (?, ?, ?)', (user_id, new_weight, timestamp))
        conn.commit()

        # Получаем уже выпитую воду за сегодня
        date = datetime.datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT SUM(amount) FROM water WHERE user_id = ? AND date = ?', (user_id, date))
        total_water = cursor.fetchone()[0] or 0

        # Пересчитываем оставшуюся норму воды
        remaining_water = new_water_norm - total_water

        cursor.execute('UPDATE users SET weight = ?, water_norm = ? WHERE user_id = ?', (new_weight, new_water_norm, user_id))
        conn.commit()
        bot.reply_to(message, f'Ваш вес обновлен. Новая норма воды: {new_water_norm} мл в день. Остаток от нормы: {remaining_water} мл.')
        del user_states[user_id]

# Команда подсчета стаканов воды
@bot.message_handler(commands=['calculate_glasses'])
def calculate_glasses(message):
    user_states[message.from_user.id] = {'state': 'CALCULATE_GLASSES'}
    bot.reply_to(message, 'Введите объем вашего стакана (мл):')

def handle_calculate_glasses(message):
    user_id = message.from_user.id
    if user_states[user_id]['state'] == 'CALCULATE_GLASSES':
        glass_volume = float(message.text)

        # Получаем норму воды и оставшийся объем воды на сегодня
        date = datetime.datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT SUM(amount) FROM water WHERE user_id = ? AND date = ?', (user_id, date))
        total_water = cursor.fetchone()[0] or 0

        cursor.execute('SELECT water_norm FROM users WHERE user_id = ?', (user_id,))
        water_norm = cursor.fetchone()[0]

        remaining_water = water_norm - total_water

        # Подсчитываем количество стаканов
        if remaining_water > 0:
            number_of_glasses = remaining_water / glass_volume
            bot.reply_to(message, f'Вам нужно выпить {number_of_glasses:.2f} стаканов воды по {glass_volume} мл.')
        else:
            bot.reply_to(message, 'Вы уже достигли своей нормы воды на сегодня.')

        del user_states[user_id]

# Команда статистики
@bot.message_handler(commands=['stats'])
def stats(message):
    cursor.execute('SELECT name FROM users')
    users = cursor.fetchall()

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for user in users:
        keyboard.add(types.InlineKeyboardButton(text=user[0], callback_data=f'stats_{user[0]}'))
    bot.send_message(message.chat.id, 'Выберите пользователя для просмотра статистики:', reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stats_'))
def stats_user(call):
    stats_name = call.data[len('stats_'):]
    user_id = call.from_user.id
    user_states[user_id] = {'state': 'STATS_PERIOD', 'stats_name': stats_name}

    keyboard = types.InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        types.InlineKeyboardButton(text="День", callback_data='day'),
        types.InlineKeyboardButton(text="Неделя", callback_data='week'),
        types.InlineKeyboardButton(text="Месяц", callback_data='month')
    )
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f'Вы выбрали пользователя {stats_name}. За какой период вывести статистику?', reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data in ['day', 'week', 'month'])
def stats_period(call):
    period = call.data
    user_id = call.from_user.id
    stats_name = user_states[user_id]['stats_name']

    cursor.execute('SELECT user_id FROM users WHERE name = ?', (stats_name,))
    stats_user_id = cursor.fetchone()[0]

    now = datetime.datetime.now()
    if period == 'day':
        start_date = now.strftime('%Y-%m-%d')
    elif period == 'week':
        start_date = (now - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
    elif period == 'month':
        start_date = (now - datetime.timedelta(days=30)).strftime('%Y-%m-%d')

    cursor.execute(f'''
        SELECT food, timestamp FROM food WHERE user_id = ? AND date >= ?
    ''', (stats_user_id, start_date))
    food_stats = cursor.fetchall()

    cursor.execute(f'''
        SELECT amount, timestamp FROM water WHERE user_id = ? AND date >= ?
    ''', (stats_user_id, start_date))
    water_stats = cursor.fetchall()

    # Получение текущего веса и нормы воды
    cursor.execute('SELECT weight, water_norm FROM users WHERE user_id = ?', (stats_user_id,))
    weight, water_norm = cursor.fetchone()

    # Получение уже выпитой воды за сегодня
    today_date = datetime.datetime.now().strftime('%Y-%m-%d')
    cursor.execute('SELECT SUM(amount) FROM water WHERE user_id = ? AND date = ?', (stats_user_id, today_date))
    total_water_today = cursor.fetchone()[0] or 0

    remaining_water_today = water_norm - total_water_today

    food_entries = '\n'.join([f'{timestamp}: {food}' for food, timestamp in food_stats])
    water_entries = '\n'.join([f'{timestamp}: {amount} мл' for amount, timestamp in water_stats])
    food_count = len(food_stats)
    water_count = len(water_stats)
    total_water_amount = sum([amount for amount, timestamp in water_stats])

    # Получение истории веса
    cursor.execute(f'''
        SELECT weight, timestamp FROM weight_history WHERE user_id = ? AND timestamp >= ?
    ''', (stats_user_id, start_date))
    weight_history = cursor.fetchall()
    weight_history_entries = '\n'.join([f'{timestamp}: {weight} кг' for weight, timestamp in weight_history])

    stats_text = (f'Статистика для {stats_name} за период {period}:\n\n'
                  f'Еда {food_count} прием(а/ов):\n{food_entries}\n\n'
                  f'Вода {water_count} прием(а/ов):\n{water_entries}\n\n'
                  f'Всего воды выпито: {total_water_amount} мл\n'
                  f'Остаток воды на сегодня: {remaining_water_today} мл\n\n'
                  f'Текущий вес: {weight} кг\n\n'
                  f'История веса:\n{weight_history_entries}')

    bot.send_message(call.message.chat.id, stats_text)

# Обработчик сообщений
@bot.message_handler(func=lambda message: message.from_user.id in user_states)
def handle_state(message):
    user_id = message.from_user.id
    if 'state' in user_states[user_id]:
        state = user_states[user_id]['state']
        if state == 'REGISTER_NAME' or state == 'REGISTER_WEIGHT':
            handle_registration(message)
        elif state == 'ADD_FOOD':
            handle_food(message)
        elif state == 'ADD_WATER':
            handle_water(message)
        elif state == 'CHANGE_WEIGHT':
            handle_change_weight(message)
        elif state == 'CALCULATE_GLASSES':
            handle_calculate_glasses(message)

# Запуск бота
bot.infinity_polling()
