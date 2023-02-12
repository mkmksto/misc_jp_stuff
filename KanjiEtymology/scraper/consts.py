# -*- coding: utf-8 -*-
# Copyright: Tanaka Aiko (https://github.com/aiko-tanaka)
# License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html

# parts of this code are copied from tatsumoto-ren/Ajatt-tools
# https://github.com/Ajatt-Tools/PasteImagesAsWebP/blob/main/config.py

import os

ADDON_PATH = os.path.dirname(__file__)
ADDON_NAME = "Kanji Etymology"

# text shown while processing cards
LABEL_PROGRESS_UPDATE = "Scraping Kanji Etymologies"
# text shown on menu to run the functions
LABEL_MENU = "Extract Kanji from Vocab, and fetch etymologies into Kanji_Etym field"

if __name__ == "__main__":
    print(ADDON_PATH)
