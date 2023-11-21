from telebot.types import File
from telebot import TeleBot

from tempfile import TemporaryDirectory
import shutil
import os

from ..data.user import Resume, User


class FileDownloader:
    MAX_SIZE = 50  # in MB
    MAXIMUM_FILE_SIZE = 5  # in MB
    TEMP_FOLDER_PREFIX: str

    user_list: list  # List[User]

    def __init__(self, bot: TeleBot, user_list, admin: User, temp_prefix="hack_bot_"):
        self.bot = bot
        self.admin = admin

        self.user_list = user_list
        self.TEMP_FOLDER_PREFIX = temp_prefix

    def get_resume_chunks(self):
        max_size_chunk = list()
        current_size = 0
        chunk_no = 0

        for user in self.user_list:
            resume_size = user.resume.size_mb
            if resume_size > self.MAXIMUM_FILE_SIZE:
                error_text = f"[FileDownloader] User {user.name} @{user.username} has invalid resume size {str(user.resume)}"
                print(error_text)
                self.bot.send_document(
                    self.admin.chat_id, data=user.resume.file_id, caption=error_text
                )
                continue

            if current_size + resume_size < self.MAX_SIZE:
                current_size += resume_size
                max_size_chunk.append(user)
            else:
                chunk_no += 1
                print(f"[FileDownloader] Chunk #{chunk_no} size = {current_size}")
                yield max_size_chunk
                max_size_chunk = list()
                current_size = 0

                max_size_chunk.append(user)
                current_size += resume_size

        yield max_size_chunk

    def download_user_resume_archive(self):
        for index, chunk in enumerate(self.get_resume_chunks()):
            temp_archive_path = self._get_temp_archive_path(chunk, index)

            # show sending document
            self.bot.send_chat_action(self.admin.chat_id, action="upload_document")

            # send archive
            with open(temp_archive_path, "rb") as archive:
                message = self.bot.send_document(self.admin.chat_id, archive)

            # update db info
            # ejf.cv_archive_file_id_list += [message.document.file_id]

            # delete archive
            os.remove(temp_archive_path)

    def _get_temp_archive_path(self, user_chunk: "List[User]", chunk_index: int):
        with TemporaryDirectory(prefix=self.TEMP_FOLDER_PREFIX) as temp_dir_path:

            for user in user_chunk:
                self._save_file_to_directory(user, temp_dir_path)

            archive_path = shutil.make_archive(
                f"CV_database_{chunk_index}", "zip", temp_dir_path
            )
            return archive_path

    def _save_file_to_directory(self, user: User, dir_path: str):
        resume: Resume = user.resume
        downloaded_file = resume.download_file(self.bot)

        # save file to temp directory
        file_name = f"{user.team.name}__{user.username}__{resume.file_name}"
        temp_file_path = os.path.join(dir_path, file_name)

        try:
            with open(temp_file_path, "wb") as new_file:
                new_file.write(downloaded_file)
        except:
            file_name = f"{user.username}__{resume.file_name}"
            temp_file_path = os.path.join(dir_path, file_name)
            with open(temp_file_path, "wb") as new_file:
                new_file.write(downloaded_file)
