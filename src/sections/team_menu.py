from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
)
from telebot import TeleBot

from .section import Section
from ..data.user import User, Team
from ..data import Data
from ..data.quiz import Quiz, Question
from ..staff import quiz, utils


class TeamMenu(Section):

    MENU_PHOTO: str = "https://i.ibb.co/zFmfFVC/Frame-56.jpg"

    def __init__(self, data: Data):
        super().__init__(data)

    @property
    def menu_action(self):
        return {
            "TeamInfo": self.send_team_info_menu,
            "RegisterTeam": self._register_team,
            "LoginTeam": self._login_team,
            "LogoutTeam": self._logout_team,
            "EditTeam": self._send_edit_team_menu,
            "SendTask": self._send_test_task,
            "CV": self._send_cv,
            "OrgQuestions": self._send_org_questions_quiz,
        }

    def process_callback(self, user: User, call: CallbackQuery):
        self.bot.clear_step_handler_by_chat_id(user.chat_id)

        action = call.data.split(";")[1]

        try:
            self.menu_action[action](user, call)
        except:
            self.bot.answer_callback_query(call.id, text="Wrong callback_data")

    def send_team_info_menu(self, user: User, call: CallbackQuery = None):

        if user.team is None:
            text = "У тебе ще немає команди!"
            photo = self.MENU_PHOTO

        else:
            text = str(user.team)
            photo = self.MENU_PHOTO  # user.team.photo

        markup = self._create_team_info_markup(user)

        if call:
            self.send_message(call, text, photo, markup)
        else:
            self.bot.send_photo(
                chat_id=user.chat_id, caption=text, photo=photo, reply_markup=markup
            )

    def _send_test_task(self, user: User, call: CallbackQuery = None):
        def process_test_task_send(message: Message, **kwargs):
            user: User = kwargs["user"]
            back_step = kwargs["back_step"]
            cancel_markup = self.create_cancel_markup()

            if message.content_type == "text":
                text = message.text
                if text.startswith("https://"):
                    task_link = text.split(" ")[0]
                    user.update_github_repo(task_link)

                    self.bot.send_message(
                        user.chat_id, text="Дякую!", reply_markup=ReplyKeyboardRemove()
                    )
                    self.data.hackathon.current_menu.send_menu(self.bot, user)
                    return

                elif text == self.CANCEL_BUTTON_TEXT:
                    self.bot.send_message(user.chat_id, text="Скасовано!")
                    self.data.hackathon.current_menu.send_menu(self.bot, user)
                    return

                else:
                    self.bot.send_message(
                        user.chat_id,
                        text="Посилання має починатись на https://",
                        reply_markup=cancel_markup,
                    )
                    back_step(user)
                    return
            else:
                self.bot.send_message(
                    user.chat_id,
                    text="Посилання має бути у вигляді тексту.",
                    reply_markup=cancel_markup,
                )
                back_step(user)
                return

        text = "Надішли мені посилання на гіт репозиторій."
        markup = self.create_cancel_markup()

        self.bot.send_message(user.chat_id, text=text, reply_markup=markup)

        self.bot.register_next_step_handler_by_chat_id(
            user.chat_id,
            process_test_task_send,
            user=user,
            back_step=self._send_test_task,
        )

    def _send_edit_team_menu(self, user: User, call: CallbackQuery):
        self.send_message(call, text="Меню редагування команди")

    def _register_team(self, user: User, call: CallbackQuery):

        if user.team:
            self.bot.send_message(
                user.chat_id, f"Ти вже є учасником команди {user.team.name}"
            )
            return

        if self.data.hackathon.current_menu != self.data.hackathon.p_registration_menu:
            self.bot.send_message(user.chat_id, f"Реєстрація вже закінчилась.")
            return

        quiz.start_quiz(
            user=user,
            bot=self.bot,
            quiz=self.data.register_team_quiz,
            save_func=self._save_new_team,
            final_func=self.send_team_info_menu,
        )

    def _save_new_team(self, user: User, container):
        team_name = container["team_name"]

        if Team.objects.filter(name=team_name).first():
            self.data.bot.send_message(
                user.chat_id,
                text=f"Команда з назвою {team_name} вже зареєстрована.",
            )
            return

        team = Team(
            name=team_name,
            password=container["password"],
            registration_datetime=utils.get_now(),
        )
        team.save()

        user.team = team
        user.save()

        self.bot.send_message(
            user.chat_id,
            text=f"Команда {user.team.name} успішно добавлена!",
            reply_markup=self.data.hackathon.current_menu.markup,
        )

    def _login_team(self, user: User, call: CallbackQuery):

        if user.team:
            self.bot.send_message(
                user.chat_id, f"Ти вже є учасником команди {user.team.name}"
            )
            return

        team_login = TeamLogin(self.data, self.send_team_info_menu)
        team_login.login(user)

    def _logout_team(self, user: User, call: CallbackQuery):

        if user.team is None:
            self.bot.send_message(user.chat_id, f"Ти вже покинув команду.")
            return

        user.leave_team()
        self.bot.send_message(user.chat_id, f"Ти успішно покинув команду.")
        self.send_team_info_menu(user, call)

    def _send_cv(self, user: User, call: CallbackQuery):
        cv_request_quiz = self.data.cv_request_quiz

        quiz.start_quiz(
            user,
            self.bot,
            quiz=cv_request_quiz,
            save_func=user.update_resume,
            final_func=self.send_team_info_menu,
        )

    def _send_org_questions_quiz(self, user: User, call: CallbackQuery):
        cv_request_quiz = self.data.org_questions_quiz

        quiz.start_quiz(
            user,
            self.bot,
            quiz=cv_request_quiz,
            save_func=user.update_org_questions,
            final_func=self.send_team_info_menu,
        )

    def _create_team_info_markup(self, user: User) -> InlineKeyboardMarkup:

        register_team_btn = InlineKeyboardButton(
            text="Зереєструвати команду",
            callback_data=self.form_team_callback(action="RegisterTeam", edit=True),
        )

        login_team_btn = InlineKeyboardButton(
            text="Увійти в команду",
            callback_data=self.form_team_callback(action="LoginTeam", edit=True),
        )

        logout_team_btn = InlineKeyboardButton(
            text="Покинути команду",
            callback_data=self.form_team_callback(action="LogoutTeam", edit=True),
        )

        git_link_btn = InlineKeyboardButton(
            text="Надіслати посилання на гіт",
            callback_data=self.form_team_callback(action="SendTask", edit=True),
        )

        cv_btn = InlineKeyboardButton(
            text="Здати резюме",
            callback_data=self.form_team_callback(action="CV", edit=True),
        )

        org_quiz_btn = InlineKeyboardButton(
            text="Організаційна форма",
            callback_data=self.form_team_callback(action="OrgQuestions", edit=True),
        )

        markup = InlineKeyboardMarkup()

        if user.team is None:
            if (
                self.data.hackathon.current_menu
                == self.data.hackathon.p_registration_menu
            ):
                markup.add(login_team_btn)
                markup.add(register_team_btn)
            else:
                markup.add(login_team_btn)
                markup.add(register_team_btn)
        else:
            markup.add(git_link_btn)
            markup.add(cv_btn)
            # markup.add(org_quiz_btn)  TODO: add after selection
            markup.add(logout_team_btn)

        return markup


class TeamLogin:

    team: Team
    CANCEL = "Скасувати"

    def __init__(self, data: Data, final_func):
        super().__init__()

        self.data: Data = data
        self.final_func = final_func

        self.q_login: Question = self.data.login_team_quiz.questions[0]
        self.q_password: Question = self.data.login_team_quiz.questions[1]

        self.cancel_markup = self._create_cancel_markup()

    def login(self, user: User):
        self._request_login(user)

    def _request_login(self, user: User, first_time=True):

        if first_time:
            self.data.bot.send_message(
                user.chat_id, text=self.q_login.message, reply_markup=self.cancel_markup
            )

        self.data.bot.register_next_step_handler_by_chat_id(
            user.chat_id,
            callback=self._process_request,
            user=user,
            question=self.q_login,
            retry_func=self._request_login,
            next_func=self._check_login,
        )

    def _check_login(self, user: User, login: str):

        team = Team.objects.filter(name=login).first()

        if team is None:
            self.data.bot.send_message(
                chat_id=user.chat_id, text=self.q_login.wrong_answer_message
            )
            self._request_login(user, False)
            return

        self.team = team
        self._request_password(user)

    def _request_password(self, user: User, first_time=True):

        if first_time:
            self.data.bot.send_message(
                user.chat_id,
                text=self.q_password.message,
                reply_markup=self.cancel_markup,
            )

        self.data.bot.register_next_step_handler_by_chat_id(
            user.chat_id,
            callback=self._process_request,
            user=user,
            question=self.q_password,
            retry_func=self._request_password,
            next_func=self._check_password,
        )

    def _check_password(self, user: User, password: str):

        if self.team.password != password:
            self.data.bot.send_message(
                chat_id=user.chat_id, text=self.q_password.wrong_answer_message
            )
            self._request_password(user, False)
            return

        self._login(user)

    def _login(self, user: User):
        user.team = self.team

        self.data.bot.send_message(
            user.chat_id,
            text=f"Ти успішно увійшов в команду {self.team.name}!",
            reply_markup=self.data.hackathon.current_menu.markup,
        )

        user.save()
        self.final_func(user)

    def _process_request(self, message: Message, **kwargs):

        user: User = kwargs["user"]
        question: Question = kwargs["question"]
        retry_func = kwargs["retry_func"]
        next_func = kwargs["next_func"]

        if message.content_type == "text":
            text = message.text

            if text == self.CANCEL:
                self.data.bot.send_message(
                    user.chat_id,
                    text="Відміняю...",
                    reply_markup=self.data.hackathon.current_menu.markup,
                )
                self.final_func(user)
                return

            next_func(user, text)

        else:
            self.data.bot.send_message(
                user.chat_id, text="Допускається тільки текстова відповідь."
            )
            retry_func(user, False)
            return

    def _create_cancel_markup(self) -> ReplyKeyboardMarkup:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        cancel_btn = KeyboardButton(text=self.CANCEL)
        markup.add(cancel_btn)

        return markup
