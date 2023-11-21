from telebot.types import Message, KeyboardButton, CallbackQuery
from telebot import TeleBot

from ..data.user import User

import requests
import tempfile
import shutil
import os
import time
from datetime import datetime, timezone


def form_and_send_new_cv_archive(bot: TeleBot, user: User):
    UPDATE_INTERVAL = 1  # minutes
    ejf = JobFair.objects.first()
    chat_id = user.chat_id

    # update archive only once in 10 min
    archive_last_update = ejf.cv_archive_last_update
    if archive_last_update:
        date_diff = (
            user.last_interaction_date - archive_last_update
        ).total_seconds() / 60.0
        if date_diff < UPDATE_INTERVAL:
            bot.send_message(
                chat_id,
                text=f"Почекай ще {UPDATE_INTERVAL-date_diff:.2f} хвилин...",
            )
            return

    # clear archives list
    ejf.cv_archive_file_id_list = list()

    for temp_archive_path in _form_max_size_archive(bot):
        # show sending document
        bot.send_chat_action(chat_id, action="upload_document")

        # send archive
        with open(temp_archive_path, "rb") as archive:
            message = bot.send_document(chat_id, archive)

        # update db info
        ejf.cv_archive_file_id_list += [message.document.file_id]

        # delete archive
        os.remove(temp_archive_path)

    # update db info
    ejf.cv_archive_size = User.objects.filter(cv_file_id__ne=None).count()
    ejf.cv_archive_last_update = user.last_interaction_date
    ejf.save()


def _form_max_size_archive(bot: TeleBot, max_size=40) -> str:
    MAXIMUM_FILE_SIZE = 5 * 1024 ** 2
    max_size *= 1024 ** 2
    cv_users = User.objects.filter(cv_file_id__ne=None)
    cv_users_size = cv_users.count()
    index = 0
    archive_index = 0

    is_continue = True
    while index < cv_users_size:
        current_size = 0
        archive_index += 1
        # make temp directory
        with tempfile.TemporaryDirectory(prefix="ejf_bot_") as temp_dir_path:
            while index < cv_users_size:
                if current_size + MAXIMUM_FILE_SIZE >= max_size:
                    break

                # get current user
                cv_user = cv_users[index]

                # get file from telegram servers
                file_info = bot.get_file(file_id=cv_user.cv_file_id)
                file_name = cv_user.cv_file_name
                file_size = file_info.file_size
                downloaded_file = bot.download_file(file_info.file_path)

                # save file to temp directory
                temp_file_path = os.path.join(temp_dir_path, file_name)
                if os.path.exists(temp_file_path):
                    file_name = f"{file_name.split('.')[0]}{index}.pdf"
                    temp_file_path = os.path.join(temp_dir_path, file_name)
                with open(temp_file_path, "wb") as new_file:
                    new_file.write(downloaded_file)

                # count overall size
                current_size += file_size

                # go to next user
                index += 1

            # make archive
            archive_path = shutil.make_archive(
                f"CV_database_{archive_index}", "zip", temp_dir_path
            )
            yield archive_path


def reply_keyboard_columns_generator(btn_names_list: list, col=2):
    row = []

    for index, btn_name in enumerate(btn_names_list, 1):
        row += [KeyboardButton(btn_name)]

        if index % col == 0:
            yield row
            row = []

    if row:
        yield row


def delete_message(bot: TeleBot, call: CallbackQuery):
    chat_id = call.message.chat_id
    message_id = call.message.message_id

    try:
        bot.delete_message(chat_id, message_id)

    except:
        bot.answer_callback_query(call.id, text="Щоб продовжити натискай на /start")


def time_check(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        rest = func(*args, **kwargs)
        end = time.time()
        print(f"Час виконання {(end - start):.4} секунд")
        return rest

    return wrapper


def get_now() -> datetime:
    return datetime.now(tz=timezone.utc)
