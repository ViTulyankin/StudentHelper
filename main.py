import telebot
from telebot import types
import pymorphy2
import sqlite3
import os
from PIL import Image, ImageDraw, ImageFont

TOKEN = '5132155261:AAGX5L4hFzVhjPxoe3j0NEpClXqDPX_cvqg'
bot = telebot.TeleBot(TOKEN)

conn = sqlite3.connect('db/database.db', check_same_thread=False)
cursor = conn.cursor()

morph = pymorphy2.MorphAnalyzer()

days = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']

directory = f"""{os.getcwd()}\\files\\"""


def update_account(user_id, info, clear=False):
    if get_state(user_id):
        if clear:
            cursor.execute(f'DELETE FROM timetable WHERE user_id = {user_id}')
        cursor.execute('UPDATE state SET {}'.format(', '.join([f'{key} = ?' for key in info.keys()])),
                       list(info.values()))
    else:
        cursor.execute(f'INSERT INTO state (user_id, is_created, day) VALUES (?, ?, ?)', info)
    conn.commit()


def get_state(user_id, state=None):
    states = cursor.execute(f"""SELECT * FROM state WHERE user_id = {user_id}""").fetchall()
    if not states:
        return False
    if not state:
        return states
    return cursor.execute(f"""SELECT {state} FROM state WHERE user_id = {user_id}""").fetchall()[0]


def create_markup(text_list, count=1):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i in range(count):
        list_items = []
        for elem in text_list:
            list_items.append(types.KeyboardButton(elem))
        markup.add(*list_items)
    return markup


@bot.message_handler(commands=["start"])
def start(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.first_name

        bot.send_message(message.chat.id, f'> Привет, {username}')
        if not get_state(user_id):
            update_account(user_id, [user_id, False, -1])
        day = int(get_state(user_id, 'day')[0])
        if get_state(user_id, 'is_created')[0]:
            markup = create_markup(['Посмотреть расписание', 'Изменить расписание', 'Записать новое'])
            sent = bot.send_message(message.chat.id, '> Рад снова увидеть вас!', reply_markup=markup)
            bot.register_next_step_handler(sent, after_end)
        elif day != -1:
            markup = create_markup(['Продолжить запись', 'Закончить запись', 'Записать новое'])
            sent = bot.send_message(message.chat.id, '> Рад снова увидеть вас! Вы остановились на {}'.format(
                morph.parse(days[day])[0].inflect({'loct'}).word), reply_markup=markup)
            bot.register_next_step_handler(sent, old_record)
        elif not get_state(user_id, 'is_created')[0]:
            markup = create_markup(['Записать расписание'])
            sent = bot.send_message(message.chat.id,
                                    '> Нажмите "Записать расписание" для создания нового расписания',
                                    reply_markup=markup)
            bot.register_next_step_handler(sent, start_record)
    except Exception as e:
        print(e)
        sent = bot.send_message(message.chat.id, f'> Хммм... Что-то пошло не так')
        bot.register_next_step_handler(sent, start)


def old_record(message):
    try:
        user_id = message.from_user.id
        if message.text == 'Продолжить запись':
            day = int(get_state(user_id, 'day')[0]) - 1
            update_account(user_id, {'day': day})
            bot.send_message(message.chat.id, '> Хорошо', reply_markup=create_markup(['Следующий день',
                                                                                      'Закончить запись']))
            next_day(message)
        elif message.text == 'Записать новое':
            update_account(user_id, {'user_id': user_id, 'is_created': False, 'day': -1})
            start_record(message)
        elif message.text == 'Закончить запись':
            end_record(message)
        else:
            sent = bot.send_message(message.chat.id, '> Введите действительную комманду или выберите его из списка',
                                    reply_markup=create_markup(['Посмотреть расписание',
                                                                'Изменить расписание', 'Записать новое']))
            bot.register_next_step_handler(sent, old_record)
    except Exception as e:
        print(e)
        sent = bot.send_message(message.chat.id, f'> Хммм... Что-то пошло не так')
        bot.register_next_step_handler(sent, start)


def start_record(message):
    try:
        if message.text in ('Записать расписание', 'Записать новое'):
            markup = create_markup(['Следующий день', 'Закончить запись'])
            bot.send_message(message.chat.id, '> Чтобы записать расписание, введите названия уроков '
                                              'на отдельных строках или отдельными сообщениями.\n')
            bot.send_message(message.chat.id, '> Чтобы перейти на следующий день, нажмите кнопу "Следующий день"\n'
                                              '> Чтобы закончить запись, нажмите кнопку "Закончить запись"',
                             reply_markup=markup)
            next_day(message)
        else:
            sent = bot.send_message(message.chat.id, '> Введите действительную комманду или выберите его из списка',
                                    reply_markup=create_markup(['Записать расписание']))
            bot.register_next_step_handler(sent, start_record)
    except Exception as e:
        print(e)
        sent = bot.send_message(message.chat.id, f'> Хммм... Что-то пошло не так')
        bot.register_next_step_handler(sent, start)


def next_day(message):
    try:
        user_id = message.from_user.id
        day = int(get_state(user_id, 'day')[0]) + 1
        update_account(user_id, {'day': day})
        now_day = days[day]
        text = '> Уроки на {}'.format(morph.parse(now_day)[0].inflect({'accs'}).word)
        if day != 6:
            markup = create_markup(['Следующий день', 'Закончить запись'])
        else:
            markup = create_markup(['Закончить запись'])
        sent = bot.send_message(message.chat.id, text, reply_markup=markup)
        bot.register_next_step_handler(sent, record_day)
    except Exception as e:
        print(e)
        sent = bot.send_message(message.chat.id, f'> Хммм... Что-то пошло не так')
        bot.register_next_step_handler(sent, start)


def record_day(message):
    try:
        if message.text == 'Следующий день':
            next_day(message)
        elif message.text == 'Закончить запись':
            end_record(message)
        else:
            sent = record_day_2(message)
            bot.register_next_step_handler(sent, record_day)
    except Exception as e:
        print(e)
        sent = bot.send_message(message.chat.id, f'> Хммм... Что-то пошло не так')
        bot.register_next_step_handler(sent, start)


def record_day_2(message):
    user_id = message.from_user.id
    day = int(get_state(user_id, 'day')[0]) + 1
    if '\n' in message.text:
        lessons = message.text.split('\n')
        sent = bot.send_message(message.chat.id,
                                '> Уроки {} записаны'.format(', '.join([f'"{elem}"' for elem in lessons])))
        text = ";".join(lessons)
    else:
        sent = bot.send_message(message.chat.id, f'> Урок "{message.text}" записан')
        text = message.text
    bot.delete_message(message.chat.id, message.message_id)
    if not cursor.execute(f'SELECT * from timetable WHERE user_id = {user_id}').fetchall():
        cursor.execute(f'INSERT INTO timetable (user_id) VALUES (?)', (user_id,))
        conn.commit()
    lessons = cursor.execute(f'SELECT {days[day - 1]} from timetable WHERE user_id = {user_id}').fetchall()[0][0]
    if lessons:
        cursor.execute(f'UPDATE timetable SET {days[day - 1]} = ? WHERE user_id = {user_id}',
                       (lessons + text + ';',))
    else:
        cursor.execute(f'UPDATE timetable SET {days[day - 1]} = ? WHERE user_id = {user_id}', (text + ';',))
    conn.commit()
    return sent


def end_record(message):
    try:
        user_id = message.from_user.id
        lessons = cursor.execute(f'SELECT * from timetable WHERE user_id = {user_id}').fetchall()
        if lessons:
            update_account(user_id, {'is_created': True})
            markup = create_markup(['Посмотреть расписание', 'Изменить расписание', 'Записать новое'])
            sent = bot.send_message(message.chat.id, '> Расписание записано. '
                                                     'Теперь вы его можете посмотреть в любое время — '
                                                     'просто нажмите на кнопку "Посмотреть расписание"',
                                    reply_markup=markup)
            bot.register_next_step_handler(sent, after_end)
        else:
            update_account(user_id, {'day': -1})
            markup = create_markup(['Записать расписание'])
            sent = bot.send_message(message.chat.id, '> В расписании должен быть записан как минимум один день',
                                    reply_markup=markup)
            bot.register_next_step_handler(sent, start_record)
    except Exception as e:
        print(e)
        sent = bot.send_message(message.chat.id, f'> Хммм... Что-то пошло не так')
        bot.register_next_step_handler(sent, start)


def after_end(message):
    try:
        user_id = message.from_user.id
        if message.text == 'Посмотреть расписание':
            my_list = []
            for elem in days:
                lessons = cursor.execute(f'SELECT {elem} from timetable WHERE user_id = {user_id}').fetchall()[0][0]
                if lessons:
                    my_list.append(elem)
            markup = create_markup(my_list)
            sent = bot.send_message(message.chat.id, '> Какой день вы бы хотели посмотреть?', reply_markup=markup)
            bot.register_next_step_handler(sent, text_to_image)
        elif message.text == 'Записать новое':
            update_account(user_id, {'user_id': user_id, 'is_created': False, 'day': -1}, True)
            start_record(message)
        elif message.text == 'Изменить расписание':
            markup = create_markup(days)
            sent = bot.send_message(message.chat.id, '> Какой день вы бы хотели изменить?', reply_markup=markup)
            bot.register_next_step_handler(sent, change_day)
        else:
            sent = bot.send_message(message.chat.id, '> Введите действительную комманду или выберите его из списка',
                                    reply_markup=create_markup(['Посмотреть расписание',
                                                                'Изменить расписание', 'Записать новое']))
            bot.register_next_step_handler(sent, after_end)
    except Exception as e:
        print(e)
        sent = bot.send_message(message.chat.id, f'> Хммм... Что-то пошло не так')
        bot.register_next_step_handler(sent, start)


def text_to_image(message):
    try:
        markup = create_markup(['Посмотреть расписание', 'Изменить расписание', 'Записать новое'])
        user_id = message.from_user.id
        if message.text in days:
            lessons = cursor.execute(f'SELECT {message.text} from timetable WHERE user_id = {user_id}').fetchall()[0][0]
            if lessons:
                lessons = lessons.split(';')
                lessons = [f'{lessons.index(les) + 1}. ' + les for les in lessons if les]
                max_len = str(max(lessons, key=len))

                font = ImageFont.truetype(f'{directory}\\font\\times.ttf', size=60)

                im = Image.new('RGB', (font.getsize(max_len)[0] + 20,
                                       (font.getsize(max_len)[1] + 5) * len(lessons) + 20),
                               color='white')
                draw_text = ImageDraw.Draw(im)
                position = (10, 10)

                draw_text.text(
                    position,
                    '\n'.join(lessons),
                    font=font,
                    fill='black')
                path = f'{directory}\\{user_id}.png'
                im.save(path)
                with open(path, 'rb') as photo:
                    sent = bot.send_photo(message.chat.id, photo, reply_markup=markup)
                    bot.register_next_step_handler(sent, after_end)
                os.remove(path)
            else:
                sent = bot.send_message(message.chat.id, '> У вас нет расписания на этот день', reply_markup=markup)
                bot.register_next_step_handler(sent, after_end)
        else:
            sent = bot.send_message(message.chat.id, '> Введите действительный день недели или выберите его из списка')
            bot.register_next_step_handler(sent, after_end)
    except Exception as e:
        print(e)
        sent = bot.send_message(message.chat.id, f'> Хммм... Что-то пошло не так')
        bot.register_next_step_handler(sent, start)


def change_day(message):
    user_id = message.from_user.id
    try:
        markup = create_markup(['Закончить запись'])
        if message.text in days:
            text = '> Уроки на {}'.format(morph.parse(message.text)[0].inflect({'accs'}).word)
            update_account(user_id, {'day': days.index(message.text)})
            cursor.execute(f'UPDATE timetable SET {message.text} = NULL WHERE user_id = {user_id}')
            sent = bot.send_message(message.chat.id, text, reply_markup=markup)
            bot.register_next_step_handler(sent, change_day_2)
    except Exception as e:
        print(e)
        sent = bot.send_message(message.chat.id, f'> Хммм... Что-то пошло не так')
        bot.register_next_step_handler(sent, start)


def change_day_2(message):
    if message.text == 'Закончить запись':
        end_record(message)
    else:
        sent = record_day_2(message)
        bot.register_next_step_handler(sent, change_day_2)


bot.polling(none_stop=True, interval=0)

# имя бота для тестирования - @my_student_helper_bot
