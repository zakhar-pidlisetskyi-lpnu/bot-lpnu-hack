from telebot import TeleBot
from telegraph import Telegraph
import mongoengine as me
from pymongo.ssl_support import CERT_NONE
from datetime import datetime, timezone, date

import string
import random

from src.data.user import Team


from .quiz import Question, Quiz
from ..data import hackathon as hack_db


class Data:

    TEST_PHOTO = "https://i.ibb.co/0Gv4JyW/photo-2021-04-16-12-48-15.jpg"

    def __init__(self, conn_string: str, bot: TeleBot):
        self.bot = bot

        me.connect(host=conn_string, ssl_cert_reqs=CERT_NONE)
        print("connection success ")

        self.create_system_tables()

        self.hackathon: hack_db.Hackathon = self.get_hackathon()

    @property
    def start_quiz(self) -> Quiz:
        return Quiz.objects.filter(name="StartQuiz").first()

    @property
    def register_team_quiz(self) -> Quiz:
        return Quiz.objects.filter(name="RegisterTeamQuiz").first()

    @property
    def login_team_quiz(self) -> Quiz:
        return Quiz.objects.filter(name="LoginTeamQuiz").first()

    @property
    def cv_request_quiz(self) -> Quiz:
        return Quiz.objects.filter(name="CvQuiz").first()

    @property
    def org_questions_quiz(self) -> Quiz:
        return Quiz.objects.filter(name="OrqQuestionsQuiz").first()

    @property
    def admin_team(self) -> Team:
        return Team.objects.filter(name="Admins").first()

    def create_system_tables(self):
        self._create_quizes()

        self._create_hackathon()

    def _create_quizes(self):
        if self.start_quiz is None:
            self._create_start_quiz()

        if self.register_team_quiz is None:
            self._create_register_team_quiz()

        if self.login_team_quiz is None:
            self._create_login_team_quiz()

        if self.cv_request_quiz is None:
            self._create_cv_request_quiz()

        if self.org_questions_quiz is None:
            self._create_org_questions_quiz()

    def _create_start_quiz(self):

        quiz = Quiz(name="StartQuiz", is_required=True)

        q_name_surname = Question(
            name="name_surname",
            message="Як мені до тебе звертатися?",
            correct_answer_message="Гарно звучить 🥰",
            wrong_answer_message="Введи ім’я текстом 🤡",
        )

        q_age = Question(
            name="age",
            message="Скільки тобі років?",
            regex="[1-9][0-9]",
            correct_answer_message="Ого, ми однолітки 🥰",
            wrong_answer_message="Вкажи свій справжній вік 🤡",
        )

        q_school = Question(
            name="school",
            message="Де вчишся? Вибери або введи.",
            buttons=[
                "НУЛП",
                "ЛНУ",
                "УКУ",
                "КПІ",
                "КНУ",
                "Ще в школі",
                "Вже закінчив(-ла)",
            ],
            correct_answer_message="Клас 🥰",
            wrong_answer_message="Введи назву текстом 🤡",
        )

        q_study_term = Question(
            name="study_term",
            message="Який ти курс?",
            buttons=[
                "Перший",
                "Другий",
                "Третій",
                "Четвертий",
                "На магістартурі",
                "Нічого з переліченого",
            ],
            allow_user_input=False,
            correct_answer_message="Ідеальний час, щоб будувати кар'єру 🥰",
            wrong_answer_message="Вибери, будь ласка, один з варіантів 🤡",
        )

        q_tech = Question(
            name="tech_used",
            message="Які технології збираєшся використовувати на проекті?",
            allow_user_input=True,
            correct_answer_message="Те що треба!",
            wrong_answer_message="Відповідь треба записувати текстом",
        )
        q_source = Question(
            name="registration_source",
            message="Звідки дізнався про Hackathon?",
            allow_user_input=True,
            correct_answer_message="Дякую за відповідь, для мене це дуже користно)",
            wrong_answer_message="Відповідь треба записувати текстом",
        )
        q_work = Question(
            name="work_info",
            message="Вже працюєш в айті сфері?",
            buttons=[
                "Taк",
                "Ні",
                "Планую",
            ],
            allow_user_input=False,
            correct_answer_message="Дякую за інформацію)",
            wrong_answer_message="Відповідь треба записувати текстом",
        )

        ##############
        q_city = Question(
            name="city",
            message="Звідки ти? Вибери зі списку або введи назву.",
            buttons=["Львів", "Київ", "Новояворівськ", "Донецьк", "Стамбул"],
            correct_answer_message="Був-був там!",
            wrong_answer_message="Введи назву текстом :)",
        )

        q_contact = Question(
            name="contact",
            message="Обміняємося контактами?",
            buttons=["Тримай!"],
            input_type="contact",
            correct_answer_message="Дякую. А я залишаю тобі контакт головного організатора: @Slavkoooo 🥰",
            wrong_answer_message="Надішли, будь ласка, свій контакт 🤡",
        )

        q_email = Question(
            name="email",
            message="Наостанок, вкажи адресу своєї поштової скриньки.",
            regex="^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$",
            correct_answer_message="Дякую 🥰",
            wrong_answer_message="Введи, будь ласка, електронну адресу 🤡",
        )

        q_agree = Question(
            name="user_agreements",
            message="Залишилося тільки дати згоду на обробку даних.",
            buttons=["Я погоджуюсь."],
            allow_user_input=False,
        )

        quiz.questions = [
            q_name_surname,
            q_age,
            q_school,
            q_study_term,
            # q_city,
            q_tech,
            q_source,
            q_work,
            q_contact,
            q_email,
            q_agree,
        ]

        quiz.save()
        print("StartQuiz has been added")

    def _create_register_team_quiz(self):
        quiz = Quiz(name="RegisterTeamQuiz", is_required=False)

        q_team_name = Question(
            name="team_name",
            message="Напиши мені назву своєї команди",
            correct_answer_message="It is fucking amazing!",
            wrong_answer_message="Введи назву текстом 🤡",
        )

        q_password = Question(
            name="password",
            message="Придумай пароль для входу в твою команду",
            correct_answer_message="It is fucking amazing!",
            wrong_answer_message="Введи пароль текстом 🤡",
        )

        quiz.questions = [q_team_name, q_password]
        quiz.save()

        print("RegisterTeamQuiz has been added")

    def _create_login_team_quiz(self):
        quiz = Quiz(name="LoginTeamQuiz", is_required=False)

        q_login = Question(
            name="login",
            message="Введи логін",
            correct_answer_message="It is fucking amazing!",
            wrong_answer_message="Такий логін не зареєстрований у системі.",
        )

        q_password = Question(
            name="password",
            message="Введи пароль",
            correct_answer_message="It is fucking amazing!",
            wrong_answer_message="Пароль невірний. Спробуй ще раз",
        )

        quiz.questions = [q_login, q_password]
        quiz.save()

        print("LoginTeamQuiz has been added")

    def _create_cv_request_quiz(self):
        quiz = Quiz(name="CvQuiz", is_required=False)

        q_file_request = Question(
            name="file_request",
            message="Надішли своє резюме файлом.",
            input_type="document",
            allow_user_input=True,
            correct_answer_message="It is fucking amazing!",
            wrong_answer_message="Я очікував від тебе файл, а ти...",
        )

        quiz.questions = [q_file_request]
        quiz.save()

        print("CvQuiz has been added")

    def _create_org_questions_quiz(self):
        quiz = Quiz(name="OrqQuestionsQuiz", is_required=False)

        q_tshirt_size = Question(
            name="tshirt_size",
            message="Який у тебе розмір футболки?",
            input_type="text",
            correct_answer_message="В мене також🔥",
            wrong_answer_message="ERROR: Відповідь має бути щось з цього S, M, L, XL, XXL, XXXL👾",
        )

        q_np_number = Question(
            name="new_post_number",
            message="З якого відділення Нової пошти тобі зручно забрати посилку?",
            input_type="text",
            correct_answer_message="Супер🔥",
            wrong_answer_message="ERROR: Напиши номер відділення👾",
        )

        q_pib = Question(
            name="pib",
            message="ПІБ",
            input_type="text",
            correct_answer_message="Дякую💚",
            wrong_answer_message="ERROR: Відповідь має бути текстом👾",
        )

        q_is_discord = Question(
            name="discord",
            message="Маєш аккаунт в Discord?\nЯкщо ні, тоді створи його🔥\nhttps://discord.com/",
            input_type="text",
            buttons=["Так", "Ні"],
            allow_user_input=False,
            correct_answer_message="Супер🔥",
            wrong_answer_message="ERROR: Вибери один з поданих варіантів👾",
        )

        q_comments = Question(
            name="comments",
            message="Маєш якісь коментарі?",
            input_type="text",
            correct_answer_message="Супер🔥",
            wrong_answer_message="ERROR: Відповідь має бути текстом👾",
        )

        q_city = Question(
            name="city",
            message="Місто проживання",
            input_type="text",
            correct_answer_message="Круто🔥",
            wrong_answer_message="ERROR: Відповідь має бути текстом👾",
        )

        q_is_cv = Question(
            name="is_cv",
            message="Надіслав CV?\nЯкщо ні, тоді поспіши, адже часу не так багато🔥",
            input_type="text",
            buttons=["Так", "Ні"],
            allow_user_input=False,
            correct_answer_message="Супер🔥",
            wrong_answer_message="ERROR: Вибери один з поданих варіантів👾",
        )

        q_final = Question(
            name="data_processing",
            message="Залишилося тільки дати згоду на обробку даних.",
            input_type="text",
            buttons=["Даю дозвіл"],
            allow_user_input=False,
            correct_answer_message="Супер🔥",
            wrong_answer_message="ERROR: Неправильний формат👾",
        )

        quiz.questions = [
            q_tshirt_size,
            q_np_number,
            q_pib,
            q_is_discord,
            q_comments,
            q_city,
            q_is_cv,
            q_final,
        ]
        quiz.save()

        print("OrqQuestionsQuiz has been added")

    def _create_hackathon(self):

        if hack_db.Hackathon.objects.first():
            print("Hack table is already exists")
            return

        hack_db.add_test_data()

    def update_quiz_table(self):
        quizes = Quiz.objects

        # form paragraphs in questions
        for quiz in quizes:
            for question in quiz.questions:
                question.message = question.message.replace("\\n", "\n")

            quiz.save()

    def get_hackathon(self) -> hack_db.Hackathon:
        return hack_db.Hackathon.objects.first()


class Content(me.Document):
    start_text = me.StringField()
    start_photo = me.StringField()
    user_start_text = me.StringField()
    user_start_photo = me.StringField()
    hack_start_text = me.StringField()
    hack_start_photo = me.StringField()
