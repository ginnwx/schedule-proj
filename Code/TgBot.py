import telebot
from telebot import types
import psycopg2
import select
import smtplib
import ssl
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread

# Настройки подключения к базе данных PostgreSQL
DB_HOST = "localhost"
DB_NAME = "schedule_Tk"
DB_USER = "postgres"
DB_PASSWORD = "1111111"
DB_PORT = "5432"

# Настройки почты
SENDER_EMAIL = "nananaaan@gmail.com"  # Ваш email
SENDER_PASSWORD = "121212121211"      # Ваш пароль от почты
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# Подключение к базе данных PostgreSQL
def connect_db():
    conn = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    return conn.cursor(), conn

# Хэширование пароля (для безопасности)
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# Функция для регистрации пользователя
def register_user(email, password, message):
    cursor, conn = connect_db()
    password_hash = hash_password(password)
    try:
        cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, password_hash))
        conn.commit()
        chat_id = message.chat.id
        bot.send_message(chat_id, f"Пользователь {email} успешно зарегистрирован! Теперь вы можете авторизоваться.")
    except psycopg2.IntegrityError as e:
        # Ловим ошибку целостности, которая может быть связана с нарушением ограничения
        print(f"Ошибка при регистрации пользователя: {e}")
        conn.rollback()
        # Проверяем, что ошибка связана с форматом email
        if 'email_format' in str(e):  # Проверяем, что ошибка связана с форматом email
            bot.send_message(message.chat.id, "Ошибка: Неверный формат email. Пожалуйста, используйте правильный формат email (например, user@example.com).")
            
        else:
            bot.send_message(message.chat.id, "Ошибка при регистрации. Попробуйте снова.")
    except Exception as e:
        print(f"Ошибка при регистрации пользователя: {e}")
        conn.rollback()
        bot.send_message(message.chat.id, "Произошла ошибка при регистрации. Попробуйте позже.")

# Функция для авторизации пользователя
def authenticate_user(email, password):
    cursor, conn = connect_db()
    password_hash = hash_password(password)
    cursor.execute("SELECT id FROM users WHERE email = %s AND password = %s", (email, password_hash))
    user = cursor.fetchone()
    return user is not None


bot = telebot.TeleBot('7618142838:AAEGMMRO4wEozpgnb6yvw4fIDjXwMufoUqc')

user_groups = {}
# Храним подписчиков на уведомления
subscribers = set()
authenticated_users = set()


# Команда для регистрации пользователя
@bot.message_handler(commands=['register'])
def register(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "Введите ваш email для регистрации:")
    bot.register_next_step_handler(msg, process_email_for_registration, message)

def process_email_for_registration(message, chat_message):
    chat_id = message.chat.id
    email = message.text
    msg = bot.send_message(chat_id, "Введите ваш пароль:")
    bot.register_next_step_handler(msg, process_password_for_registration, email, chat_message)

def process_password_for_registration(message, email, chat_message):
    chat_id = message.chat.id
    password = message.text
    # Регистрация пользователя с передачей объекта message
    register_user(email, password, chat_message)

# Команда для авторизации пользователя
@bot.message_handler(commands=['login'])
def login(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "Введите ваш email:")
    bot.register_next_step_handler(msg, process_email_for_login)

def process_email_for_login(message):
    chat_id = message.chat.id
    email = message.text
    msg = bot.send_message(chat_id, "Введите ваш пароль:")
    bot.register_next_step_handler(msg, process_password_for_login, email)

def process_password_for_login(message, email):
    chat_id = message.chat.id
    password = message.text
    if authenticate_user(email, password):
        authenticated_users.add(chat_id)
        bot.send_message(chat_id, f"Вы успешно авторизованы, {email}. Теперь вы можете получать уведомления.")
    else:
        bot.send_message(chat_id, "Неверный email или пароль. Попробуйте снова.")

# Уведомления только для авторизованных пользователей
@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    chat_id = message.chat.id
    if chat_id not in authenticated_users:
        bot.send_message(chat_id, "Пожалуйста, авторизуйтесь, чтобы подписаться на уведомления.")
        return

    if chat_id not in subscribers:
        subscribers.add(chat_id)
        bot.send_message(chat_id, "Вы подписались на уведомления о изменениях в расписании.")
    else:
        bot.send_message(chat_id, "Вы уже подписаны на уведомления.")

# Отписка от уведомлений
@bot.message_handler(commands=['unsubscribe'])
def unsubscribe(message):
    chat_id = message.chat.id
    if chat_id in subscribers:
        subscribers.remove(chat_id)
        bot.send_message(chat_id, "Вы отписались от уведомлений.")
    else:
        bot.send_message(chat_id, "Вы не подписаны на уведомления.")

# Функция для отправки email
def send_email(subject, body, recipient_email):
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            
            message = MIMEMultipart()
            message["From"] = SENDER_EMAIL
            message["To"] = recipient_email
            message["Subject"] = subject
            
            message.attach(MIMEText(body, "plain"))
            server.sendmail(SENDER_EMAIL, recipient_email, message.as_string())
            print(f"Email отправлен на {recipient_email}")
    except Exception as e:
        print(f"Ошибка при отправке email: {e}")

# Функция для получения уведомлений из базы данных PostgreSQL
def listen_for_notifications():
    cursor, conn = connect_db()
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cursor.execute("LISTEN schedule_change;")  # Подписка на уведомления
    print("Ожидание уведомлений...")

    while True:
        if select.select([conn], [], [], 5) == ([], [], []):
            print("Нет новых уведомлений")
        else:
            conn.poll()
            while conn.notifies:
                notify = conn.notifies.pop()
                group_change_message = notify.payload

                # Отправка уведомлений по email всем пользователям
                cursor.execute("SELECT email FROM users")  # Получаем email всех пользователей
                users = cursor.fetchall()
                for user in users:
                    email_recipient = user[0]  # Извлекаем email из результата запроса
                    send_email("Изменение в расписании", group_change_message, email_recipient)

                # Отправка уведомлений по Telegram
                for subscriber in subscribers:
                    if subscriber in authenticated_users:
                        bot.send_message(subscriber, f"Изменение в расписании: {group_change_message}")

# Функция получения расписания из базы данных
def get_schedule(group, day):
    cursor, conn = connect_db()
    query = """
    SELECT s.pair, d.name, t.name, c.name
    FROM schedule s
    JOIN disciplines d ON s.discipline_id = d.id
    JOIN teachers t ON s.teacher_id = t.id
    JOIN classrooms c ON s.classroom_id = c.id
    WHERE s.group_name = %s AND s.day_of_week = %s
    ORDER BY s.pair
    """
    cursor.execute(query, (group, day))
    results = cursor.fetchall()
    conn.close()

    if results:
        schedule_message = f"Расписание для группы {group} на {day}:\n"
        for row in results:
            pair, discipline, teacher, classroom = row
            schedule_message += f"{pair} пара: {discipline} - {teacher} в {classroom}\n"
        return schedule_message
    else:
        return "Расписание не найдено для этого дня."

# Функция получения списка групп
def get_groups():
    cursor, conn = connect_db()
    cursor.execute("SELECT DISTINCT group_name FROM schedule")
    groups = cursor.fetchall()
    conn.close()
    return [group[0] for group in groups]

# Стартовая команда
@bot.message_handler(commands=['start'])
def start(message):
    # Приветственное сообщение
    welcome_message = '''
    Привет! Я бот для работы с расписанием.

    Вот список команд, которые доступны:
    /start - Приветствие и описание бота.
    /register - Зарегистрироваться.
    /login - авторизация
    /subscribe - подписаться на уведомление(только после авторизации)
    '''
    
    # Создаем клавиатуру для выбора группы
    groups = get_groups()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for group in groups:
        markup.add(types.KeyboardButton(f"Группа {group}"))
    btn_schedule = types.KeyboardButton("Расписание звонков")
    markup.add(btn_schedule)
    
    # Кнопка для сайта колледжа
    markup.add(types.KeyboardButton("Сайт колледжа"))
    
    # Кнопка для графика учебного процесса
    markup.add(types.KeyboardButton("График учебного процесса"))
    
    bot.send_message(message.chat.id, welcome_message, reply_markup=markup)

# Обработка выбора группы
@bot.message_handler(func=lambda message: message.text.startswith("Группа"))
def send_group_schedule(message):
    group = message.text.split(" ")[1]  # Получаем номер группы из сообщения
    user_groups[message.chat.id] = group  # Сохраняем группу для последующего использования

    # Создаем клавиатуру для выбора дня недели
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    days_of_week = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница']
    for day in days_of_week:
        markup.add(types.KeyboardButton(day))
    
    # Добавляем кнопку для возврата в главное меню
    btn_back = types.KeyboardButton("Главное меню")
    markup.add(btn_back)
    
    bot.send_message(message.chat.id, "Выберите день недели:", reply_markup=markup)

# Обработка выбора дня недели
@bot.message_handler(func=lambda message: message.text in ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница'])
def send_schedule(message):
    group = user_groups.get(message.chat.id, None)
    if group:
        day = message.text
        schedule = get_schedule(group, day)
        bot.send_message(message.chat.id, schedule)
        
        # После показа расписания возвращаем в главное меню
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        groups = get_groups()
        for group in groups:
            markup.add(types.KeyboardButton(f"Группа {group}"))
        btn_schedule = types.KeyboardButton("Расписание звонков")
        markup.add(btn_schedule)
        markup.add(types.KeyboardButton("Сайт колледжа"))
        markup.add(types.KeyboardButton("График учебного процесса"))
        
        bot.send_message(message.chat.id, "Чтобы выбрать другую группу или команду, используйте кнопки ниже.", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите группу сначала.")

# Обработка кнопки "Расписание звонков"
@bot.message_handler(func=lambda message: message.text == "Расписание звонков")
def send_call_schedule(message):
    call_schedule = '''
    🕰️ Расписание звонков:

    🔹 0 пара: Онлайн
    🔹 1 пара: 13:30 - 15:00
    🔹 2 пара: 15:20 - 16:50
    🔹 3 пара: 17:00 - 18:30
    '''
    bot.send_message(message.chat.id, call_schedule)

# Обработка кнопки "Сайт колледжа" с красивой кнопкой-ссылкой
@bot.message_handler(func=lambda message: message.text == "Сайт колледжа")
def send_site_link(message):
    # Создаем инлайн-кнопку с URL
    markup = types.InlineKeyboardMarkup()
    btn_site = types.InlineKeyboardButton(text="Перейти на сайт колледжа", url="https://admission.astanait.edu.kz/college#rec807871314")
    markup.add(btn_site)
    
    bot.send_message(message.chat.id, "Перейдите на сайт нашего колледжа, нажав на кнопку ниже:", reply_markup=markup)

# Обработка кнопки "График учебного процесса"
@bot.message_handler(func=lambda message: message.text == "График учебного процесса")
def send_academic_schedule(message):
    # Замените путь на фактический путь к файлу с графиком учебного процесса
    file_path = r"C:\Users\aruzh\Downloads\ГРАФИК_УЧЕБНОГО_ПРОЦЕССА_НА_2024_2025_учебный_год.pdf"

    # Отправляем файл
    with open(file_path, 'rb') as file:
        bot.send_document(message.chat.id, file)

# Обработка кнопки "Главное меню"
@bot.message_handler(func=lambda message: message.text == "Главное меню")
def go_to_main_menu(message):
    start(message)

# Запуск слушателя
if __name__ == "__main__":
    notification_thread = Thread(target=listen_for_notifications)
    notification_thread.start()
    
    bot.polling(none_stop=True)

