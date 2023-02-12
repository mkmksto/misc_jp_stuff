# -*- coding: utf-8 -*-
# Copyright: Tanaka Aiko (https://github.com/aiko-tanaka)
# License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html

# parts of the code are copied from renato's work (https://github.com/rgamici)
# Description: Just a stupidly simple program that extracts a word wrapped in <b></b>
# and puts it into a dst field, yeah I'm lazy

# Note to self: I use if False: because I haven't cloned the Anki repo yet
# so pycharm doesn't recognize aqt, anki, etc.

# TODO: only deconjugate/search net if the vocab contains some furigana (check KanjiEtym for furigana checker)

import json
import os
import re
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from io import StringIO

from bs4 import BeautifulSoup

test_in_anki = True

dir_path = os.path.dirname(os.path.realpath(__file__)).split("\\")[-1]

from anki.hooks import addHook
from aqt import mw
from aqt.utils import showInfo
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

try:
    config = mw.addonManager.getConfig(dir_path)
    expression_field = config["expressionField"]
    vocab_field = config["vocabField"]
    keybinding = config["keybinding"]  # nothing by default
except Exception as e:
    # expression_field = 'Expression'
    expression_field = "Reading"
    vocab_field = "Vocab"
    keybinding = ""  # nothing by default
    force_update = "no"

# text shown while processing cards
label_progress_update = "Extracting <b>Vocab</b> in deconjugated form from JISHO"
# text shown on menu to run the functions
label_menu = "Extract Vocab wrapped in <b></b> from Sentence field"

## TO DO's
# fix how anki can't fucking find the config file
# understand what mw.progress.finish() does
# try actually catching errors from try: f.flush()
# handle cases where the sentence is empty (implemented but not yet tested)
# create a utils.py and use it to trace calls, also create a .log file
# use showInfo() to provide a summary of what happened after running the program


# https://stackoverflow.com/questions/753052/strip-html-from-strings-in-python
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


def _strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def get_vocab(sentence):
    """
    return the bolded word from the sentence
    """
    # return an empty string if sentence is empty
    # return an HTML-stripped vocab just to be sure an clean
    try:
        sentence = str(sentence)
        if sentence != "" and len(sentence.split("<b>")) == 2:
            return _strip_tags(sentence.split("<b>")[1].split("</b>")[0])
        elif sentence == "":
            return ""
    except Exception as e:
        showInfo(
            "failed to extract vocab from a specific card, because - {}".format(str(e))
        )
        raise


def remove_furigana(sentence):
    """
    Only use this function if expression_field = 'Reading' (i.e. the sentence field with furigana)
    AND
    if the '[' or ']' in expression_field
    https://stackoverflow.com/questions/14596884/remove-text-between-and
    """
    try:
        return re.sub("[\(\[].*?[\)\]]", "", sentence)
    except Exception as e:
        showInfo("failed to remove furigana - {}".format(str(e)))


def remove_ruby(sentence):
    """
    Only use this if expression_field = 'Reading'
    AND
    if <rt> in expression_field
    """
    try:
        sentence = (
            sentence.replace("<ruby>", "")
            .replace("</ruby>", "")
            .replace("<rb>", "")
            .replace("</rb>", "")
        )
        return re.sub("<rt>.*?</rt>", "", sentence)
    except Exception as e:
        showInfo("failed to remove furigana - {}".format(str(e)))


def jisho_deconjugate(vocab: str) -> str or None:
    """
    https://github.com/lsrdg/jisho-karini/blob/master/jisho-karini.py
    https://jisho.org/forum/54fefc1f6e73340b1f160000-is-there-any-kind-of-search-api
    """

    # to prevent Attribute error (NoneType has no attribute encode)
    # prob when the sentence doesn't have anything in bold
    if vocab:
        url = "https://jisho.org/api/v1/search/words?keyword={}".format(
            urllib.parse.quote(vocab.encode("utf-8"))
        )

        num_retries = 10
        response = None
        try:
            response = urllib.request.urlopen(url)
        except Exception as e:
            for i in range(num_retries):
                try:
                    response = urllib.request.urlopen(url)
                except Exception as e:
                    time.sleep(0.03)

        if response:
            response = BeautifulSoup(response, features="html.parser")
            response_json: dict = json.loads(str(response))
            try:
                # jisho returns nothing inside its 'data' key
                response_data: dict = response_json.get("data")[0]
            except IndexError:
                return None
            try:
                deconjugated = response_data.get("slug")
            except Exception as e:
                showInfo(f"error from ->response_data.get(slug)-<: {e}")
                raise

            return deconjugated
        else:
            return None

    else:
        return None


class Regen:
    """Used to organize the work flow to update the selected cards
    Attributes
    ----------
    ed :
        Anki Card browser object
    fids :
        List of selected cards
    completed : int
        Track how many cards were already processed
    """

    def __init__(self, ed, fids):
        self.ed = ed
        # ed.selectedNotes
        self.fids = fids
        self.completed = 0
        # self.config     = mw.addonManager.getConfig(__name__)
        if len(self.fids) == 1:
            # Single card selected, need to deselect it before updating
            self.row = self.ed.currentRow()
            self.ed.form.tableView.selectionModel().clear()
        mw.progress.start(max=len(self.fids), immediate=True)
        mw.progress.update(label=label_progress_update, value=0)

    def _update_progress(self):
        self.completed += 1
        mw.progress.update(label=label_progress_update, value=self.completed)
        if self.completed >= len(self.fids):
            mw.progress.finish()
            return

    def generate(self):
        fs = [mw.col.getNote(id=fid) for fid in self.fids]

        for f in fs:
            # empty sentence field (probably very rare)
            if not f[expression_field]:
                self._update_progress()
                continue

            sent = str(f[expression_field])
            if "[" in sent and expression_field == "Reading":
                sent = remove_furigana(sent)
            elif "<rt>" in sent and expression_field == "Reading":
                sent = remove_ruby(sent)

            plain_vocab = get_vocab(sent)
            # probably nothing enclosed in <b> (usually happens when I review the entire sentence)
            if plain_vocab is None:
                self._update_progress()
                continue

            deconjugated_vocab = jisho_deconjugate(plain_vocab)
            if deconjugated_vocab is None:
                self._update_progress()
                continue

            deconjugated_vocab = (
                deconjugated_vocab if deconjugated_vocab else plain_vocab
            )

            try:
                # vocab field already contains something
                if force_update == "no" and f[vocab_field]:
                    # do nothing, count it as progress
                    self._update_progress()
                    mw.progress.finish()
                    continue

                elif not f[vocab_field] and r"<b>" in sent:
                    # vocab_field is empty, fill it
                    f[vocab_field] = deconjugated_vocab
                    self._update_progress()
                    mw.progress.finish()

                elif force_update == "yes" and f[vocab_field] and r"<b>" in sent:
                    f[vocab_field] += deconjugated_vocab
                    self._update_progress()
                    mw.progress.finish()

                else:
                    pass

            except Exception as e:
                showInfo("error from generate() function, - {}".format(str(e)))

            try:
                f.flush()
            except Exception as e:
                pass

            # just a fail-safe
            if self.completed >= len(self.fids):
                mw.progress.finish()
                showInfo(
                    "Extraction done for {} out of {} notes done".format(
                        self.completed, len(self.fids)
                    )
                )

                return


def setup_menu(ed):
    """
    Add entry in Edit menu
    """
    a = QAction(label_menu, ed)
    a.triggered.connect(lambda _, e=ed: on_regen_vocab(e))
    ed.form.menuEdit.addAction(a)
    a.setShortcut(QKeySequence(keybinding))


def add_to_context_menu(view, menu):
    """
    Add entry to context menu (right click)
    """
    menu.addSeparator()
    a = menu.addAction(label_menu)
    a.triggered.connect(lambda _, e=view: on_regen_vocab(e))
    a.setShortcut(QKeySequence(keybinding))


def on_regen_vocab(ed):
    """
    main function
    """
    regen = Regen(ed, ed.selectedNotes())
    regen.generate()
    mw.reset()
    mw.requireReset()


addHook("browser.setupMenus", setup_menu)
addHook("browser.onContextMenu", add_to_context_menu)

# testing inside pycharm
sample_word = "食べちゃった"
if __name__ == "__main__":
    print(jisho_deconjugate(sample_word))
