# -*- coding: utf-8 -*-
# Copyright: Tanaka Aiko (https://github.com/aiko-tanaka)
# License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html

import os
import sys

# from pathlib import Path
# print(os.path.abspath('..'))
# ppp = Path(os.path.abspath('..'))
# parent = ppp.parent.absolute()
# ajt = os.path.join(parent, r'1344485230\mecab_controller')

# sys.path.append(ajt)
# print(ajt)
if __name__ == "__main__":
    sys.path.append("../1344485230/mecab_controller")
else:
    sys.path.append("./mecab_controller")
ajt_furigana = __import__("mecab_controller")

mecab = ajt_furigana.MecabController()


def generate_furigana(text: str, skip_words=None) -> str:
    res = mecab.reading(text, skip_words)
    if res:
        return res
    else:
        return ""


if __name__ == "__main__":
    print(generate_furigana("昨日すき焼きを食べました"))
    print(os.path.abspath("../1344485230/mecab_controller"))
