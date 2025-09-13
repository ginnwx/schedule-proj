import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2

# Подключение к базе данных PostgreSQL
def connect_db():
    try:
        conn = psycopg2.connect(
            dbname="schedule_Tk",  # Название вашей базы данных
            user="postgres",  # Ваше имя пользователя
            password="Almas0711",  # Ваш пароль
            host="localhost",  # или IP-адрес вашего сервера
            port="5432"  # Порт PostgreSQL
        )
        return conn
    except Exception as e:
        messagebox.showerror("Ошибка подключения", f"Не удалось подключиться к базе данных: {e}")
        return None

# Функция для извлечения всех групп из базы данных
def get_groups():
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT group_name FROM schedule;")
            return [row[0] for row in cursor.fetchall()]

# Кешированные данные (для дисциплин, преподавателей и кабинетов)
cached_disciplines = {}
cached_teachers = {}
cached_classrooms = {}

# Функции для извлечения данных с кешированием
def get_disciplines():
    if not cached_disciplines:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, name FROM disciplines;")
                cached_disciplines.update({row[0]: row[1] for row in cursor.fetchall()})
    return cached_disciplines

def get_teachers():
    if not cached_teachers:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, name FROM teachers;")
                cached_teachers.update({row[0]: row[1] for row in cursor.fetchall()})
    return cached_teachers

def get_classrooms():
    if not cached_classrooms:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, name FROM classrooms;")
                cached_classrooms.update({row[0]: row[1] for row in cursor.fetchall()})
    return cached_classrooms

# Функция для загрузки расписания
def load_schedule(group_name):
    for item in tree.get_children():
        tree.delete(item)

    with connect_db() as conn:
        with conn.cursor() as cursor:
            days_of_week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            cursor.execute("""
                SELECT id, day_of_week, pair, time, discipline_id, teacher_id, classroom_id
                FROM schedule
                WHERE group_name = %s
                ORDER BY CASE day_of_week
                    WHEN 'Понедельник' THEN 1
                    WHEN 'Вторник' THEN 2
                    WHEN 'Среда' THEN 3
                    WHEN 'Четверг' THEN 4
                    WHEN 'Пятница' THEN 5
                    WHEN 'Суббота' THEN 6
                    WHEN 'Воскресенье' THEN 7
                END, pair;
            """, (group_name,))

            rows = cursor.fetchall()
            current_day = None
            for row in rows:
                day_of_week = row[1]
                
                if day_of_week != current_day:
                    current_day = day_of_week
                    tree.insert("", "end", values=(day_of_week, '', '', '', '', ''), tags="day_header")
                    tree.tag_configure("day_header", font=("Arial", 12, "bold"), background="#cce5ff", anchor="center")
                
                discipline_name = get_disciplines().get(row[4], "Неизвестно")
                teacher_name = get_teachers().get(row[5], "Неизвестно")
                classroom_name = get_classrooms().get(row[6], "Неизвестно")
                
                tree.insert("", "end", iid=row[0], values=("", row[2], row[3], discipline_name, teacher_name, classroom_name))

# Функция для редактирования расписания
def edit_schedule():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Ошибка", "Выберите запись для редактирования.")
        return

    item_id = selected_item[0]
    values = tree.item(item_id, "values")
    
    # Открыть окно для редактирования
    edit_window = tk.Toplevel(root)
    edit_window.title("Редактирование записи")

    # Извлечь текущие данные из базы для выбранной пары
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT day_of_week, pair, time, discipline_id, teacher_id, classroom_id
                FROM schedule
                WHERE id = %s;
            """, (item_id,))
            record = cursor.fetchone()
    
    if record:
        day_of_week, pair, time, discipline_id, teacher_id, classroom_id = record

        # Создание переменных для редактируемых значений
        day_of_week_var = tk.StringVar(value=day_of_week)
        pair_var = tk.StringVar(value=pair)
        time_var = tk.StringVar(value=time)

        # Список дней недели для Combobox
        days_of_week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        day_of_week_combobox = ttk.Combobox(edit_window, values=days_of_week, state="readonly")
        day_of_week_combobox.set(day_of_week)

        # Список номеров пар
        pair_combobox = ttk.Combobox(edit_window, values=["I", "II", "III", "IV", "V"], state="readonly")
        pair_combobox.set(pair)

        # Список времени с дополнительным расчетом для 4 и 5 пар
        time_combobox = ttk.Combobox(edit_window, values=[
            "08:00 - 09:30", "09:40 - 11:10", "11:20 - 12:50", "13:00 - 14:30", "14:40 - 16:10", "16:20 - 17:50", 
            "13:30 - 15:00", "15:20 - 16:50", "17:00 - 18:30", "18:40 - 20:10", "20:20 - 21:50"], state="readonly")
        time_combobox.set(time)

        discipline_combobox = ttk.Combobox(edit_window, values=list(get_disciplines().values()), state="readonly")
        discipline_combobox.set(get_disciplines().get(discipline_id))
        
        teacher_combobox = ttk.Combobox(edit_window, values=list(get_teachers().values()), state="readonly")
        teacher_combobox.set(get_teachers().get(teacher_id))
        
        classroom_combobox = ttk.Combobox(edit_window, values=list(get_classrooms().values()), state="readonly")
        classroom_combobox.set(get_classrooms().get(classroom_id))

        # Размещение элементов на экране
        tk.Label(edit_window, text="День недели:").grid(row=0, column=0, padx=10, pady=5)
        day_of_week_combobox.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(edit_window, text="Пара:").grid(row=1, column=0, padx=10, pady=5)
        pair_combobox.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(edit_window, text="Время:").grid(row=2, column=0, padx=10, pady=5)
        time_combobox.grid(row=2, column=1, padx=10, pady=5)

        tk.Label(edit_window, text="Дисциплина:").grid(row=3, column=0, padx=10, pady=5)
        discipline_combobox.grid(row=3, column=1, padx=10, pady=5)

        tk.Label(edit_window, text="Преподаватель:").grid(row=4, column=0, padx=10, pady=5)
        teacher_combobox.grid(row=4, column=1, padx=10, pady=5)

        tk.Label(edit_window, text="Аудитория:").grid(row=5, column=0, padx=10, pady=5)
        classroom_combobox.grid(row=5, column=1, padx=10, pady=5)

        # Кнопка для сохранения изменений
        def save_changes():
            new_day_of_week = day_of_week_combobox.get()
            new_pair = pair_combobox.get()
            new_time = time_combobox.get()
            new_discipline = list(get_disciplines().keys())[list(get_disciplines().values()).index(discipline_combobox.get())]
            new_teacher = list(get_teachers().keys())[list(get_teachers().values()).index(teacher_combobox.get())]
            new_classroom = list(get_classrooms().keys())[list(get_classrooms().values()).index(classroom_combobox.get())]

            if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите сохранить изменения?"):
            # Сохранение изменений в базу данных
             with connect_db() as conn:
                 with conn.cursor() as cursor:
                     cursor.execute("""
                         UPDATE schedule
                         SET day_of_week = %s, pair = %s, time = %s, discipline_id = %s, teacher_id = %s, classroom_id = %s
                         WHERE id = %s;
                     """, (new_day_of_week, new_pair, new_time, new_discipline, new_teacher, new_classroom, item_id))
                     conn.commit()

            edit_window.destroy()
            load_schedule('Группа 1')

        tk.Button(edit_window, text="Сохранить", command=save_changes).grid(row=6, column=0, columnspan=2, pady=10)

# Создание главного окна
root = tk.Tk()
root.title("Расписание")

# Вкладки и таблица
tree = ttk.Treeview(root, columns=("day", "pair", "time", "discipline", "teacher", "classroom"), show="headings")
tree.heading("day", text="День недели")
tree.heading("pair", text="Пара")
tree.heading("time", text="Время")
tree.heading("discipline", text="Дисциплина")
tree.heading("teacher", text="Преподаватель")
tree.heading("classroom", text="Аудитория")
tree.grid(row=0, column=0, padx=10, pady=10)

# Выбор группы
group_label = tk.Label(root, text="Группа:")
group_label.grid(row=1, column=0, padx=10, pady=5)

group_combobox = ttk.Combobox(root, values=get_groups(), state="readonly")
group_combobox.grid(row=1, column=1, padx=10, pady=5)

# Кнопка для загрузки расписания
def load_selected_group():
    load_schedule(group_combobox.get())

tk.Button(root, text="Загрузить", command=load_selected_group).grid(row=1, column=2, padx=10, pady=5)

# Кнопка для редактирования записи
tk.Button(root, text="Редактировать", command=edit_schedule).grid(row=2, column=0, padx=10, pady=5)

def add_schedule():
    # Открытие окна для добавления пары
    add_window = tk.Toplevel(root)
    add_window.title("Добавить пару")

    # Элементы интерфейса для ввода данных
    group_combobox = ttk.Combobox(add_window, values=get_groups(), state="readonly")
    group_combobox.grid(row=0, column=1, padx=10, pady=5)
    group_combobox.set(get_groups()[0])  # Установить первую группу по умолчанию

    day_of_week_combobox = ttk.Combobox(add_window, values=["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"], state="readonly")
    day_of_week_combobox.grid(row=1, column=1, padx=10, pady=5)
    day_of_week_combobox.set("Понедельник")

    pair_combobox = ttk.Combobox(add_window, values=["I", "II", "III", "IV", "V"], state="readonly")
    pair_combobox.grid(row=2, column=1, padx=10, pady=5)
    pair_combobox.set("I")

    time_combobox = ttk.Combobox(add_window, values=[ 
        "08:00 - 08:45, 8:50 - 9:35", "09:45 - 10:30, 10:35 - 11:20", "11:40 - 12:25, 12:30 - 13:15", 
        "13:30 - 15:00", "15:20 - 16:50", "17:00 - 18:30", "18:40 - 20:10", "20:20 - 21:50"], state="readonly")
    time_combobox.grid(row=3, column=1, padx=10, pady=5)

    discipline_combobox = ttk.Combobox(add_window, values=list(get_disciplines().values()), state="readonly")
    discipline_combobox.grid(row=4, column=1, padx=10, pady=5)

    teacher_combobox = ttk.Combobox(add_window, values=list(get_teachers().values()), state="readonly")
    teacher_combobox.grid(row=5, column=1, padx=10, pady=5)

    classroom_combobox = ttk.Combobox(add_window, values=list(get_classrooms().values()), state="readonly")
    classroom_combobox.grid(row=6, column=1, padx=10, pady=5)

    # Функция для сохранения новой пары
    def save_new_pair():
        group_name = group_combobox.get()  # Получаем выбранную группу
        day_of_week = day_of_week_combobox.get()
        pair = pair_combobox.get()
        time = time_combobox.get()
        discipline = list(get_disciplines().keys())[list(get_disciplines().values()).index(discipline_combobox.get())]
        teacher = list(get_teachers().keys())[list(get_teachers().values()).index(teacher_combobox.get())]
        classroom = list(get_classrooms().keys())[list(get_classrooms().values()).index(classroom_combobox.get())]

        # Подтверждение перед добавлением
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите добавить эту пару?"):
            # Сохранение в базе данных
            with connect_db() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(""" 
                        INSERT INTO schedule (group_name, day_of_week, pair, time, discipline_id, teacher_id, classroom_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (group_name, day_of_week, pair, time, discipline, teacher, classroom))
                    conn.commit()

            add_window.destroy()
            load_schedule(group_name)  # Загружаем расписание для выбранной группы

    tk.Button(add_window, text="Сохранить", command=save_new_pair).grid(row=7, column=0, columnspan=2, pady=10)



# Кнопка для добавления новой записи
tk.Button(root, text="Добавить пару", command=add_schedule).grid(row=2, column=2, padx=10, pady=5)

#удаление записи
def delete_schedule():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Ошибка", "Выберите запись для удаления.")
        return

    item_id = selected_item[0]
    # Запрос подтверждения удаления
    if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить эту запись?"):
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM schedule WHERE id = %s;", (item_id,))
                conn.commit()

        tree.delete(item_id)


tk.Button(root, text="Удалить", command=delete_schedule).grid(row=2, column=1, padx=10, pady=5)

root.mainloop()

