# -*- coding: utf-8 -*-
# Copyright: Tanaka Aiko (https://github.com/aiko-tanaka)
# License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html

import logging
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import OrderedDict
from functools import wraps

import requests
from aqt import mw
from bs4 import BeautifulSoup

from .config import config

FORMAT = logging.Formatter(
    "%(levelname)s \t| %(asctime)s: \t%(message)s", "%Y-%m-%d %I:%M:%S %p"
)


def setup_logger(name, log_file, _format=FORMAT, level=logging.DEBUG):
    """Create two or more loggers because writing to a CSV
    Causes the Characters to become messed up even with the
    correct encoding
    Note that the log files are always in UTF-8, never
    set by the user, i.e. even if the files read are in shift JIS
    the log files are still in UTF-8
    Args:
        name:           Name of the logger
        log_file:       Path to the log file
        _format:        String format
        level:          DEBUG by default
    """
    # https://stackoverflow.com/questions/52896485/python3-logger-unicodeencodeerror
    handler = logging.FileHandler(log_file, encoding="utf8")
    handler.setFormatter(_format)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


# TODO: (important) you might want to use requests instead of urllib.request for try_access_site
# so that download_image can use try_access_site instead of using its own try_acces

# TODO: not yet usable, you should still create a config.py and config.md that pulls things like log path,
# and other config settings
ADD_ON_PATH = os.path.dirname(__file__)
# # TODO: dynamically determine the name of the addon instead of r'\push_existing'
LOG_FOLDER_PATH = ADD_ON_PATH + r"\logging"

if not os.path.exists(LOG_FOLDER_PATH):
    os.makedirs(LOG_FOLDER_PATH)

NEW_PATH = os.path.join(ADD_ON_PATH, "logging")

LOG_FILE_PATH = os.path.join(NEW_PATH, "kanji_etym.log")
# CALL_LOG_PATH = os.path.join(NEW_PATH, 'debug_call_log.log')

# I don't know why, but if you set the name of the logger to main_logger (same as main.py)
# logging entries double up
speed_logger = setup_logger("speed_logger", LOG_FILE_PATH)


# https://stackoverflow.com/questions/11731136/python-class-method-decorator-w-self-arguments
# NOTE: if you wan't to use this decorator on a function, you must enclose the signal in a lambda
# That way, it passes the function itself as an argument instead of a flag (bool)
def calculate_time_class_method(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        before = time.time()
        result = f(*args, **kwargs)
        elapsed = time.time() - before
        speed_logger.info('function "{}" took {} seconds'.format(f.__name__, elapsed))
        return result

    return wrap


def calculate_time(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        before = time.time()
        result = f(*args, **kwargs)
        elapsed = time.time() - before

        result_for_log = ""
        if result:
            if isinstance(result, (str, list, dict)):
                result_for_log = str(result)
                if len(result_for_log) > 200:
                    result_for_log = result_for_log[:200]

        speed_logger.info(
            'function "{}" took {} seconds '
            "\t| args: {} "
            "\t| kwargs: {} "
            "\t| result: {}".format(
                f.__name__, elapsed, str(args), str(kwargs), result_for_log
            )
        )
        return result

    return wrap


# call_logger = setup_logger('call_logger', CALL_LOG_PATH)


# I'm not sure but just in case the decorated function has a return value, return result ensures that
# the value is passed?


# note to self: if the function passed is an object, 'self' would be part of *args
def trace_calls(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        result = f(*args, **kwargs)
        call_logger.info(
            'function: "{}" | args: {} | kwargs: {}'.format(f.__name__, args, kwargs)
        )
        return result

    return wrap


# https://stackoverflow.com/questions/11232230/logging-to-two-files-with-different-settings
def open_log_file(path):
    """Opens either the Report Log or the CSV container
    for vocabs without any matches
    The senders specify a different path depending on the button
    Args:
        path:       path to the log file (~\Documents\Anki\addons\push_existing)
    """
    if sys.version_info[0] == 3:
        from webbrowser import open

        open(path)

    elif sys.version_info[0] == 2:
        os.startfile(path)


def extract_kanji(text: str) -> list or None:
    """
    returns a unique set/list of Kanji extracted from the vocab
    also removes latin and hiragana text
    https://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-whilst-preserving-order
    https://stackoverflow.com/questions/34587346/python-check-if-a-string-contains-chinese-character
    """
    if text:
        kanji_only_set = re.findall(r"[\u4e00-\u9fff]+", text)
        kanji_only_set = "".join(kanji_only_set)
        return list(OrderedDict.fromkeys(kanji_only_set))
    else:
        return None


def try_access_site(site, sleep_time=0.08, num_retries=3, wait_time=15.0, timeout=5):
    initial_time = time.time()
    time_margin = 0.02

    response = None
    try:
        response = urllib.request.urlopen(site, timeout=timeout)

    except:
        for i in range(num_retries):
            lapsed_time = time.time()
            if lapsed_time - initial_time > wait_time:
                return None

            try:
                response = urllib.request.urlopen(site, timeout=timeout)
            except:
                # does something like random.uniform(0.06, 0.10)
                sleep_time = random.uniform(
                    sleep_time - time_margin, sleep_time + time_margin
                )
                time.sleep(sleep_time)
    finally:
        return response


def bs_remove_html(html):
    """
    https://www.geeksforgeeks.org/remove-all-style-scripts-and-html-tags-using-beautifulsoup/
    """
    soup = BeautifulSoup(html, "html.parser")

    for data in soup(["style", "script"]):
        # Remove tags
        data.decompose()

    # return data by retrieving the tag content
    return " ".join(soup.stripped_strings)


@calculate_time
def download_image(online_url, filename, use_inside_anki=True):
    """
    https://stackoverflow.com/questions/37158246/how-to-download-images-from-beautifulsoup
    Args:
        filename:           the name of the file to be saved as,
                            usually diff from the online_url because I added a string preceding it
        use_inside_anki:    default val= True
                            Set this to False for testing purposes, when not using inside Anki
    """

    # had to use mw.col.media.dir() inside a function because mw.col.media.dir() is called
    # at runtime when Anki starts, and since mw isn't loaded yet, it'll cause an error (not media method for NoneType)
    if use_inside_anki:
        current_col_media_path = (
            mw.col.media.dir()
            or r"C:\Users\Mi\AppData\Roaming\Anki2\User 1\collection.media"
        )
    else:
        current_col_media_path = config.get("media_debug_folder")

    complete_file_location = os.path.join(current_col_media_path, filename)

    time_margin = 0.02
    sleep_time = 0.08
    if not os.path.isfile(complete_file_location):
        try:
            with open(complete_file_location, "wb") as f:
                request = None
                try:
                    request = requests.get(online_url)

                except:
                    for i in range(15):
                        try:
                            request = requests.get(online_url)
                        except Exception as e:
                            sleep_time = random.uniform(
                                sleep_time - time_margin, sleep_time + time_margin
                            )
                            time.sleep(sleep_time)

                finally:
                    if request:
                        f.write(request.content)

        except Exception as e:
            # showInfo('Could not save image {} because {}'.format(filename, e) )
            pass

    else:
        print("file already exists")
        pass


if __name__ == "__main__":
    # from pprint import pprint
    # pprint(try_access_site(r'https://www.w3schools.com/python/module_random.asp'))
    print(os.path.dirname(__name__))
