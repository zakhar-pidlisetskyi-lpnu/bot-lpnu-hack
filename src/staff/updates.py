from datetime import datetime, timezone, date
import threading
from time import sleep, time

from telebot.types import Message, Chat

from ..data import User, Hackathon, Data
from src.staff import utils


class Updater:

    UPDATE_HOUR = 10  # 8:00 every morning

    def __init__(self, data: Data):
        super().__init__()

        self.data = data

    def update_user_interaction_time(self, message: Message) -> User:
        user_chat_id = message.chat.id
        date = utils.get_now()

        user = User.objects.filter(chat_id=user_chat_id)

        # add user if it does not exist
        if user.count() == 0:
            hack = Hackathon.objects.first()

            username = (
                message.chat.username
                if message.chat.username is not None
                else "No Nickname"
            )
            name = (
                message.chat.first_name
                if message.chat.first_name is not None
                else "No Name"
            )
            surname = (
                message.chat.last_name
                if message.chat.last_name is not None
                else "No Surname"
            )
            register_source = (
                message.text.split()[1] if len(message.text.split()) > 1 else "Unknown"
            )

            user = User(
                chat_id=user_chat_id,
                name=name,
                surname=surname,
                username=username,
                register_source=register_source,
                registration_date=date,
                last_update_date=date,
                last_interaction_date=date,
            )

            user.save()

        # update user if exists
        else:
            user = user.first()
            date = utils.get_now()
            user.update(last_interaction_date=date)

        return user

    def start_update_threads(self):

        update_thread = threading.Thread(
            name="EverydayUpdater", target=self._start_everyday_updates
        )
        update_thread.start()

    def update_menu_from_db(self):
        print("[Updater] Started silent refresh of DB")
        # not_blocked_users = User.objects.filter(is_blocked=False)
        self.data.hackathon.silent_refresh_menu_data()
        print("[Updater] Finished silent refresh of DB")

    def _start_everyday_updates(self):
        try:
            while True:
                self._wait_till_update()

                update_started = time()

                self._update_blocked_users()
                self._update_active_users_info()
                # self._update_current_menu() TODO: auto update every day

                print(
                    f"[Updater] Everyday updates have been finished. "
                    f"Time passed - {time()-update_started:.2f} seconds"
                )

                self._sleep_one_day()

        except Exception as e:
            print(f"(Updater exception) Promote thread - {e}")
            self.start_update_threads()

    def _update_active_users_info(self):
        not_blocked_users = User.objects.filter(is_blocked=False)

        for user in not_blocked_users:
            try:
                message = self.data.bot.send_message(user.chat_id, text="🤖")
                self.data.bot.delete_message(message.chat.id, message.message_id)

                chat = message.chat
                is_changed = False

                if chat.first_name != user.name:
                    user.name = chat.first_name
                    is_changed = True

                if chat.last_name != user.surname:
                    user.surname = chat.last_name
                    is_changed = True

                if chat.username != user.username:
                    user.username = chat.username
                    is_changed = True

                if is_changed:
                    user.save()
                    print(
                        f"[Updater] User {user.username} has been successfuly updated!"
                    )

            except Exception as e:
                print(f"[Updater] User {user.username} has been blocked yesterday.")
                user.blocked_date = utils.get_now()
                user.is_blocked = True
                user.save()

        print(f"[Updater] Checked data for {len(not_blocked_users)} active users.")

    def _update_blocked_users(self):
        blocked_users = User.objects.filter(is_blocked=True)

        for user in blocked_users:
            try:
                message = self.data.bot.send_message(user.chat_id, text="🤖")
                self.data.bot.delete_message(message.chat.id, message.message_id)

                user.is_blocked = False
                user.save()
                print(f"[Updater] User {user.username} is unblocked now!")

            except Exception as e:
                print(f"[Updater] User {user.username} is still blocked.")

    def _update_current_menu(self):

        user_list = User.objects.filter(is_blocked=False)

        if self.data.hackathon.current_menu.end_date != date.today():
            days_left = self.data.hackathon.current_menu.end_date - date.today()
            print(f"[Updater] Menu will be updated in {days_left.days} days.")
            return

        self.data.hackathon.switch_to_next_menu()

        for user in user_list:
            try:
                self.data.hackathon.current_menu.send_menu(self.data.bot, user)
            except Exception as e:
                print(f"[Updater] ERROR while menu update for {user.username} - {e}")

        print(
            (
                f"[Updater] Menu is updated to '{self.data.hackathon.current_menu.name}'"
                f" for {len(user_list)} users"
            )
        )

    def _wait_till_update(self):
        current_hour = datetime.now().hour
        if current_hour != self.UPDATE_HOUR:
            hours_left = (
                self.UPDATE_HOUR - current_hour
                if current_hour < self.UPDATE_HOUR
                else 24 % current_hour + self.UPDATE_HOUR
            )

            print(f"[Updater] Time left till update - {hours_left} hours")

            current_hour = 1 if current_hour == 0 else current_hour
            seconds_left = current_hour * 60 * 60
            sleep(seconds_left)

    def _sleep_one_day(self):
        sleep(24 * 60 * 60)
