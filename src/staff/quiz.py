from ..data import Data
from ..data.user import User
from ..data.quiz import Quiz, Question
from ..staff import utils

from telebot import TeleBot
from telebot.types import (
    Message,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from typing import Iterator, Callable
from time import sleep

import re

CANCEL_BUTTON_TEXT = "Скасувати"
MAXIMUM_FILE_SIZE = 5 * 1024 ** 2


class InputException(Exception):
    pass


# TODO: remove this function
def start_starting_quiz(user: User, bot: TeleBot, final_func: Callable):
    start_quiz = Quiz.objects.filter(name="StartQuiz").first()
    start_quiz_questions = start_quiz.questions

    quiz_iterator = iter(start_quiz_questions)
    question = next(quiz_iterator)

    sleep(1)

    send_question(
        user,
        bot,
        question,
        quiz_iterator,
        save_func=_save_answers_to_user,
        final_func=final_func,
        container={},
        is_required=start_quiz.is_required,
    )


def start_quiz(
    user: User,
    bot: TeleBot,
    quiz: Quiz,
    save_func: Callable,
    final_func: Callable,
    wait=0,
):
    quiz_questions = quiz.questions

    quiz_iterator = iter(quiz_questions)
    question = next(quiz_iterator)

    sleep(wait)

    send_question(
        user,
        bot,
        question,
        quiz_iterator,
        save_func=save_func,
        final_func=final_func,
        container={},
        is_required=quiz.is_required,
    )


def send_question(
    user: User,
    bot: TeleBot,
    question: Question,
    quiz_iterator: Iterator,
    save_func: Callable = None,
    final_func: Callable = None,
    container=None,
    is_first_try=True,
    is_required=True,
):
    """
    :param user: user from DB
    :param bot: telebot instance
    :param question: question to send and process
    :param quiz_iterator: iterator on questions
    :param save_func: function that will save all data from quiz
        It must receive 2 params user: User and container: dict
    :param final_func: function that will be called after the quiz
        It must receive 1 param user: User
    :param container: temp dictionary where all the data will be stored
    :param is_first_try: show if it is first time to answer a question.
        After wrong answer we do not need to repeat a question
    :param is_required: is quiz can be canceled
    """
    chat_id = user.chat_id
    text = question.message

    # form markup
    answer_markup = _create_answer_markup(question, is_required=is_required)

    # do not send it if answer was wrong
    if is_first_try:
        bot.send_message(chat_id, text, reply_markup=answer_markup)

    bot.register_next_step_handler_by_chat_id(
        chat_id,
        process_message,
        user=user,
        bot=bot,
        question=question,
        quiz_iterator=quiz_iterator,
        save_func=save_func,
        final_func=final_func,
        container=container,
        is_first_try=is_first_try,
        is_required=is_required,
    )


def process_message(message: Message, **kwargs):
    """
    :param user: user from DB
    :param bot: telebot instance
    :param question: question to send and process
    :param quiz_iterator: iterator on questions
    :param save_func: function that will save all data from quiz
    :param final_func: function that will be called after the quiz
    :param container: temp dictionary where all the data will be stored
    :param is_first_try: show if it is first time to answer a question.
        After wrong answer we do not need to repeat a question
    """
    user = kwargs["user"]
    bot = kwargs["bot"]
    question = kwargs["question"]
    quiz_iterator = kwargs["quiz_iterator"]
    save_func = kwargs["save_func"]
    final_func = kwargs["final_func"]
    container = kwargs["container"]
    is_first_try = kwargs["is_first_try"]
    is_required = kwargs["is_required"]

    content_type = message.content_type

    try:
        # handle command input
        if _handle_commands(message) is True:
            return

        if content_type == "text":
            # cancel quiz if it the CANCEL button was pressed
            if is_required is False and message.text == CANCEL_BUTTON_TEXT:
                bot.send_message(
                    user.chat_id,
                    text="Я скасував усі твої дії :)\nНажимай /start щоб продовжити",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return False

        if content_type == question.input_type:

            if content_type == "text":
                if (
                    _process_text_messages(
                        message, question, bot, user, is_required_quiz=is_required
                    )
                    is False
                ):
                    return
                else:
                    container[question.name] = message.text

            elif content_type == "contact":
                contact = message.contact

                phone = contact.phone_number
                user_id = contact.user_id

                container["phone"] = phone
                container["user_id"] = user_id

            elif content_type == "photo":
                container[question.name] = message.photo[-1].file_id

            elif content_type == "document":
                if message.document.file_size >= MAXIMUM_FILE_SIZE:
                    raise InputException

                container["file_id"] = message.document.file_id
                container["file_name"] = message.document.file_name
                container["file_size"] = message.document.file_size

            else:
                raise InputException

            # if answer was valid - send message about it
            if question.correct_answer_message:
                bot.send_message(
                    user.chat_id,
                    text=question.correct_answer_message,
                    reply_markup=ReplyKeyboardRemove(),
                )
                sleep(0.5)

            # next question
            question = next(quiz_iterator, None)
            is_first_try = True

        # Wrong input type
        else:
            raise InputException

    except InputException:
        is_first_try = False
        bot.send_message(user.chat_id, text=question.wrong_answer_message)
        sleep(0.5)

    # do the next step
    if question:
        send_question(
            user=user,
            bot=bot,
            question=question,
            quiz_iterator=quiz_iterator,
            save_func=save_func,
            final_func=final_func,
            container=container,
            is_first_try=is_first_try,
            is_required=is_required,
        )
    # if questions ended
    else:
        # save data if needed
        if save_func:
            save_func(user, container)

        # send step after finish
        if final_func:
            final_func(user)


def _process_text_messages(
    message: Message,
    question: Question,
    bot: TeleBot,
    user: User,
    is_required_quiz: bool,
):
    input_text = message.text

    # cancel quiz if it the CANCEL button was pressed
    if is_required_quiz is False and input_text == CANCEL_BUTTON_TEXT:
        bot.send_message(
            user.chat_id,
            text="Я скасував усі твої дії :)\nНажимай /start щоб продовжити",
            reply_markup=ReplyKeyboardRemove(),
        )
        return False

    if question.allow_user_input:
        # if there is a specific text input
        if question.regex:
            pattern = re.compile(question.regex)
            if not pattern.search(input_text):
                raise InputException

    # if text input allowed only from keyboard
    else:
        if input_text not in question.buttons:
            raise InputException

    # if the answer was too long
    if question.max_text_size is not None:
        if len(input_text) > question.max_text_size:
            raise InputException

    return True


def _create_answer_markup(question: Question, is_required: bool) -> ReplyKeyboardMarkup:
    answer_markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)

    if question.input_type == "text":
        columns = 2 if len(question.buttons) < 8 else 3
        for row in utils.reply_keyboard_columns_generator(
            list(question.buttons), col=columns
        ):
            answer_markup.add(*row)

    elif question.input_type == "contact":
        answer_btn = KeyboardButton(text=question.buttons[0], request_contact=True)
        answer_markup.add(answer_btn)

    elif question.input_type == "location":
        answer_btn = KeyboardButton(text=question.buttons[0], request_location=True)
        answer_markup.add(answer_btn)

    # cancel button
    if is_required is False:
        cancel_btn = KeyboardButton(text=CANCEL_BUTTON_TEXT)
        answer_markup.add(cancel_btn)

    return answer_markup


def _handle_commands(message: Message) -> bool:
    """
    return True if need to interrupt current quiz
    """
    # TODO handle every command and check if quiz is interruptable

    if message.content_type == "text":
        command_text = message.text

        if command_text[0] == "/":
            raise InputException

    return False


def _save_answers_to_user(user: User, container):
    user.additional_info = container
    user.save()
