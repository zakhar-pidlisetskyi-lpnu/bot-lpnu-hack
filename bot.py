import configparser
import os

from telebot.types import Message

from src.data import Data, User
from src.sections.admin import AdminSection

from src.sections.main_menu import MainMenuSection
from src.sections.team_menu import TeamMenu

from src.staff.updates import Updater

# from src.staff import utils

# from src.objects import quiz

from telebot import TeleBot, logger

config = configparser.ConfigParser()
config.read("Settings.ini")

API_TOKEN = (
    os.environ.get("TOKEN", False)
    if os.environ.get("TOKEN", False)
    else config["TG"]["token"]
)
CONNECTION_STRING = (
    os.environ.get("DB", False)
    if os.environ.get("DB", False)
    else config["Mongo"]["db"]
)

bot = TeleBot(API_TOKEN, parse_mode="HTML")
data = Data(conn_string=CONNECTION_STRING, bot=bot)

main_menu_section = MainMenuSection(data=data)
team_section = TeamMenu(data=data)
admin_section = AdminSection(data=data)

updater = Updater(data=data)


@bot.message_handler(commands=["start"])
def start_bot(message):

    try:
        user = updater.update_user_interaction_time(message)
        main_menu_section.send_start_menu(user)

    except Exception as e:
        print(f"Exception during start - {e}")
        bot.send_message(message.chat_id, text="Упс, щось пішло не так. Спробуй знову!")


@bot.message_handler(content_types=["text"])
def handle_text_buttons(message):
    user = updater.update_user_interaction_time(message)
    message_text = message.text

    try:

        # import time
        # start = time.time()

        if message_text in data.hackathon.current_menu.buttons_list:
            if (
                data.hackathon.current_menu.get_btn_by_name(message_text).special_action
                == "team_info"
            ):
                team_section.send_team_info_menu(user)
            else:
                main_menu_section.process_button(user, message_text)

        elif message_text == "__next_menu":
            data.hackathon.switch_to_next_menu()
            main_menu_section.send_start_menu(user)

        elif message_text == "SilentUpdate":
            updater.update_menu_from_db()

        elif message_text == "__adminaccess":
            admin_section.send_admin_menu(user)

        # TEMP!!!
        elif message_text == "suka_force_back":
            registered_users = User.objects.filter(is_blocked=False)
        
            # data.hackathon.current_menu = data.hackathon.p_registration_menu
            data.hackathon.switch_to_prev_menu()
            # data.hackathon.save()
        
            counter = 0
            for user in registered_users:
                try:
                    data.hackathon.current_menu.send_menu(bot, user)
                    counter += 1
                except Exception as e:
                    print(
                        f"[Updater] ERROR while menu update for {user.username} - {e}"
                    )
        
            print(f"Updated - {counter}/{len(registered_users)}")
        
        elif message_text == "suka_force_forward":
            data.hackathon.switch_to_next_menu()
            # data.hackathon.save()
            main_menu_section.send_start_menu(user)
            # users = User.objects.filter(team__ne=None)
            users = User.objects.filter(is_blocked=False)
        
            # participants = filter(lambda user: user.is_participant, users)
            counter = 0
            for u in users:
                try:
                    data.hackathon.current_menu.send_menu(bot, u)
                    counter += 1
                except Exception as e:
                    print(
                        f"[Updater] ERROR while menu update for {user.username} - {e}"
                    )
        
            print(f"Updated - {counter}/{len(users)}")

    except Exception as e:
        print(e)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    user = updater.update_user_interaction_time(call.message)
    section = call.data.split(";")[0]

    try:
        if section == "Team":
            team_section.process_callback(user, call)
        elif section == "Admin":
            admin_section.process_callback(user, call)
        else:
            bot.answer_callback_query(call.id)

    except Exception as e:
        print(e)


if __name__ == "__main__":
    updater.start_update_threads()

    bot.polling(none_stop=True)
