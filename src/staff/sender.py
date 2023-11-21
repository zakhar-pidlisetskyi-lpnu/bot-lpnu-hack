from enum import Enum
from typing import Union
import re

from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Video,
    File,
    Poll,
    Sticker,
)
from telebot import TeleBot
from mongoengine.queryset.queryset import QuerySet

from ..data import Data
from ..data.user import User, Team


class DestinationEnum(Enum):
    ALL = "msg ALL"
    ALL_REGISTERED = "msg ALL_REGISTERED"
    ALL_UNREGISTERED = "msg ALL UNREGISTERED"
    ALL_WITH_TEAMS = "msg ALL WITH TEAMS"
    ALL_PARTICIPANTS = "msg ALL PARTICIPANTS"  # those who participate in hack
    TEAM = "msg TEAM"
    USER = "msg USER"
    ME = "msg ME"

    @classmethod
    def common_destinations(cls):
        return [
            cls.ALL.value,
            cls.ALL_REGISTERED.value,
            cls.ALL_UNREGISTERED.value,
            cls.ALL_WITH_TEAMS.value,
            cls.ALL_PARTICIPANTS.value,
            cls.ME.value,
        ]


class CustomMessage:
    text: str = None
    photo: str
    markup: InlineKeyboardMarkup
    content_type: str
    video: Video
    file: File
    sticker: Sticker
    poll: Poll
    poll_temp_message: Message = None  # contents original poll inside

    def __init__(self, content_type: str, admin: User):
        self.photo = None
        self.markup = InlineKeyboardMarkup()
        self.content_type = content_type
        self.admin = admin

    def format(self):
        self._extract_buttons()

    def send(self, bot: TeleBot, user: User):

        if self.content_type == "photo":
            bot.send_photo(
                user.chat_id,
                photo=self.photo[0].file_id,
                caption=self.text,
                reply_markup=self.markup,
            )

        elif self.content_type == "text":
            bot.send_message(user.chat_id, text=self.text, reply_markup=self.markup)

        elif self.content_type == "video":
            bot.send_video(
                user.chat_id,
                data=self.video.file_id,
                caption=self.text,
                reply_markup=self.markup,
            )

        elif self.content_type == "document":
            bot.send_document(
                user.chat_id,
                data=self.file.file_id,
                caption=self.text,
                reply_markup=self.markup,
            )

        elif self.content_type == "poll":
            self._send_poll_message(bot, user)

        elif self.content_type == "sticker":
            bot.send_sticker(user.chat_id, data=self.sticker.file_id)

    def _send_poll_message(self, bot: TeleBot, user: User):
        poll = self.poll

        if self.poll_temp_message is None:
            options = [q.text for q in poll.options]
            self.poll_temp_message = bot.send_poll(
                chat_id=self.admin.chat_id,
                question=poll.question,
                options=options,
                is_anonymous=poll.is_anonymous,
                type=poll.type,
                allows_multiple_answers=poll.allows_multiple_answers,
                correct_option_id=poll.correct_option_id,
                explanation=poll.explanation,
                close_date=poll.close_date,
                is_closed=poll.is_closed,
            )

        bot.forward_message(
            user.chat_id,
            from_chat_id=self.poll_temp_message.chat.id,
            message_id=self.poll_temp_message.message_id,
        )

    def _extract_buttons(self):
        if self.text is None:
            return

        split_text = self.text.split("[btn]")

        self.text = split_text[0]
        buttons = split_text[1:]

        for btn in buttons:
            custom_btn = CustomButton()

            custom_btn.name = re.search(r"name=(.*?)]", btn).group(1)
            custom_btn.link = re.search(r"link=(.*?)]", btn).group(1)

            self.markup.add(custom_btn.form_btn())


class CustomButton:
    name: str
    link: str

    def form_btn(self) -> InlineKeyboardButton:
        return InlineKeyboardButton(text=self.name, url=self.link)


class Sender:
    custom_message: CustomMessage
    custom_message_input_rule = (
        "Надішли мені повідомлення текстом або текст+картинку\n\n"
        "Щоб вставити <i>кнопки-посилання</i> до повідомлення, то потрібно дотриматись наступного формату:\n"
        "\t\t*Основний текст*\n"
        "\t\t[btn][name=Кнопка1][link=https://google.com]\n"
        "\t\t[btn][name=Кнопка2][link=https://nestor.com]\n\n"
        "В результаті, ти отримаєш повідомлення з двома кнопками."
    )
    progress_text = "Користувачів оброблено {}/{}\nКориситувачів заблоковано {}"
    CANCEL_BUTTON_TEXT = "Скасувати"

    def __init__(
        self,
        data: Data,
        admin: User,
        destination: str,
        team_id: str = None,
        prev_admin_menu: "Callable" = None,
    ):
        self.data = data
        self.admin = admin
        self.prev_admin_menu = prev_admin_menu
        self.team_id = team_id

        self.receiver_list: QuerySet = self._get_receiver_list(destination)

    def send_custom_message(self):
        bot = self.data.bot

        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        cancel_btn = KeyboardButton(text=self.CANCEL_BUTTON_TEXT)
        markup.add(cancel_btn)

        bot.send_message(
            self.admin.chat_id,
            text=self.custom_message_input_rule,
            disable_web_page_preview=True,
            reply_markup=markup,
        )

        bot.register_next_step_handler_by_chat_id(
            self.admin.chat_id, self._process_input
        )

    def _process_input(self, message: Message):
        content_type = message.content_type
        self.custom_message = CustomMessage(content_type, self.admin)

        if content_type == "text":
            if message.text == self.CANCEL_BUTTON_TEXT:
                self.data.bot.send_message(
                    self.admin.chat_id,
                    text="Скасовано!",
                    reply_markup=ReplyKeyboardRemove(),
                )
                self._return_to_prev_admin_menu()
                return

            self.custom_message.text = message.text

        elif content_type == "photo":
            self.custom_message.text = message.caption
            self.custom_message.photo = message.photo

        elif content_type == "video":
            self.custom_message.video = message.video
            self.custom_message.text = message.caption

        elif content_type == "document":
            self.custom_message.file = message.document
            self.custom_message.text = message.caption

        elif content_type == "poll":
            self.custom_message.poll = message.poll

        elif content_type == "sticker":
            self.custom_message.sticker = message.sticker

        else:
            self.data.bot.send_message(
                self.admin.chat_id,
                text="Підтримується розсилка тексту, фото, відео, файлів та голосувань.",
            )
            return

        self._send_messages()

    def _send_messages(self):
        try:
            self.custom_message.format()
        except Exception as e:
            print(f"[Sender] Error - {e}")
            self.data.bot.send_message(self.admin.chat_id, text=f"{e}")
            return

        receivers_count = len(self.receiver_list)
        progress_message = self.data.bot.send_message(
            self.admin.chat_id,
            text=self.progress_text.format(0, receivers_count, 0),
        )

        blocked_users = 0
        for _id, user in enumerate(self.receiver_list, 1):
            try:
                self.custom_message.send(self.data.bot, user)
            except Exception as e:
                print(f"[Sender] Error - {e}")
                self.data.bot.send_message(self.admin.chat_id, text=f"{e}")
                blocked_users += 1

            if _id % 10 == 0:
                self.data.bot.edit_message_text(
                    text=self.progress_text.format(_id, receivers_count, blocked_users),
                    chat_id=self.admin.chat_id,
                    message_id=progress_message.message_id,
                )

        self.data.bot.edit_message_text(
            text=self.progress_text.format(
                receivers_count, receivers_count, blocked_users
            ),
            chat_id=self.admin.chat_id,
            message_id=progress_message.message_id,
        )

        self._return_to_prev_admin_menu()

    def _get_receiver_list(self, destination: str) -> Union[QuerySet, list]:

        if destination == DestinationEnum.ALL.value:
            return User.objects.filter(is_blocked=False)

        elif destination == DestinationEnum.ALL_WITH_TEAMS.value:
            return User.objects.filter(team__ne=None)

        elif destination == DestinationEnum.ALL_PARTICIPANTS.value:
            users = User.objects
            participants = filter(lambda user: user.is_participant, users)
            return list(participants)

        elif destination == DestinationEnum.ALL_REGISTERED.value:
            return User.objects.filter(additional_info__ne=None)

        elif destination == DestinationEnum.ALL_UNREGISTERED.value:
            return User.objects.filter(additional_info=None)

        elif destination == DestinationEnum.TEAM.value:
            team = Team.objects.get(id=self.team_id)
            return User.objects.filter(team=team)

        elif destination == DestinationEnum.USER.value:
            pass

        elif destination == DestinationEnum.ME.value:
            return User.objects.filter(chat_id=self.admin.chat_id)

    def _return_to_prev_admin_menu(self):
        if self.prev_admin_menu:
            self.prev_admin_menu(self.admin)