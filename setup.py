""""This script creat config file, and u must run this script first of all"""
import sys
import argparse
import configparser
from os import path


def create_parser():
    """Creat parameters passing from console"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-token', '--token')
    parser.add_argument('-db', '--database')
    return parser


def createConfig(path):
    """Using parser to output parameters from console"""
    config = configparser.ConfigParser()
    parser = create_parser()
    args = parser.parse_args(sys.argv[1:])

    config.add_section('TG')
    config["TG"]["token"] = '6403021795:AAFfsg3loLzjIUCRtRsmz1tiCUPfr1Flm_g'

    config.add_section('Mongo')

    config["Mongo"]["db"] = 'mongodb+srv://zakhar:GoFarEst@hackathon-bot.uzugzsg.mongodb.net/bot-database'

    with open(path, "w") as config_file:
        config.write(config_file)


if __name__ == '__main__':
    if path.isfile('Settings.ini'):
        key = input("Do you really wanna change your settings?(y/n) ")
        if key == "y":
            createConfig('Settings.ini')
        else:
            sys.exit("Script is terminated")
    else:
        createConfig('Settings.ini')