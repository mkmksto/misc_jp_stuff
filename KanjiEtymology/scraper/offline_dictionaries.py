# -*- coding: utf-8 -*-
# Copyright: Tanaka Aiko (https://github.com/aiko-tanaka)
# License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html

"""
Offline dictionaries
Methods to query cross-profile Kanji Decks and poll them for info
Use these methods before querying tangorin for definitions because tangorin
takes forever at times

IMPORTANT!
This module requires KanjiEater's GoldenDict add-on
This module uses monkey patched AnkiConnect methods from said addon
"""

import json
import os
import urllib.request

from .config import config
from .utils import calculate_time


# from foosoft's AnkiConnect sample code
def request(action, **params):
    return {"action": action, "params": params, "version": 6}


def invoke(action, **params):
    requestJson = json.dumps(request(action, **params)).encode("utf-8")
    response = json.load(
        urllib.request.urlopen(
            urllib.request.Request("http://localhost:8765", requestJson)
        )
    )
    if len(response) != 2:
        raise Exception("response has an unexpected number of fields")
    if "error" not in response:
        raise Exception("response is missing required error field")
    if "result" not in response:
        raise Exception("response is missing required result field")
    if response["error"] is not None:
        # return response['error']
        raise Exception(response["error"])
    return response["result"]


decks = [
    "全集Deck::01_All_in_One_Kanji",
    "全集Deck::02_KanjiKentei",
    "全集Deck::03_KanjiDamage",
]

lookalikes = "全集Deck::04_Kanji_lookalikes"


@calculate_time
def offline_kanji_info(kanji: str) -> dict:
    """
    Cross-Profile query for Kanji Info

    Returns:
        All kanji will have all four keys, but some may have empty values
        so as not to break dict.get() method when the key does not exist
        dict of kanji info containing:
        {
            'kanji':  '夢',
            'meaning': 'dream',
            'components': 'individual bushu' OR empty string/None,
            'lookalikes': polled from Memrise_Look_Alike_Kanji ('' or None),
            'examples': ''
        }
    """

    kanji_info = dict()
    for deck in decks:
        query = f"deck:{deck} kanji:*{kanji}*"
        result = invoke(
            "goldenCardsInfo",
            query=query,
            desiredFields="Kanji Meaning Components Examples",
        )
        if result:
            for res in result:
                fields: dict = res["fields"]
                kanji_info["kanji"] = kanji
                kanji_info["meaning"] = fields["Meaning"]["value"]
                try:
                    kanji_info["components"] = fields["Components"]["value"]
                except KeyError:
                    kanji_info["components"] = ""
                try:
                    kanji_info["examples"] = fields["Examples"]["value"]
                except KeyError:
                    kanji_info["examples"] = ""
            break

    query = f"deck:{lookalikes} kanji:*{kanji}*"
    lookalikes_query = invoke(
        "goldenCardsInfo", query=query, desiredFields="Kanji Memrise_Look_Alike_Kanji"
    )

    kanji_info["lookalikes"] = ""
    if lookalikes_query:
        for res in lookalikes_query:
            fields: dict = res["fields"]
            try:
                kanji_info["lookalikes"] = fields["Memrise_Look_Alike_Kanji"]["value"]
            except KeyError:
                kanji_info["lookalikes"] = ""

    return kanji_info


@calculate_time
def kanjidic2_info(kanji: str) -> str or None:
    """
    Only return a single-line English definition str
    """
    complete_path = os.path.join(
        config.get("kanjidic_folder"), config.get("kanjidic_filename")
    )
    # complete_path = r'D:\Libraries\Documents\GitHub\KanjiEtymology\scraper\kanji_bank_complete-dict-format.json'
    if os.path.isfile(complete_path):
        with open(complete_path, "r", encoding="utf8") as fh:
            data: dict = json.load(fh)

            result = data.get(kanji, "")
            if result:
                return result
    else:
        return None


# TODO: query the kanjigen JSON file if the kanji isn't listed on okjiten
@calculate_time
def kanjigen_info(kanji: str) -> str:
    pass


if __name__ == "__main__":
    # sample_vocab = '蛆' #紋脅' #統參参夢紋泥恢疎姿勢'  # 自得だと思わないか' #！夢この前、あの姿勢のまま寝てるの見ましたよ固執流河麻薬所持容疑'
    vocab = "蛆結相遭遇刹那"
    from pprint import pprint

    # result = invoke('goldenCardsInfo', query=f'deck:{deck} kanji:*{sample_vocab}*', desiredFields='kanji meaning')
    # for v in vocab:
    # pprint(offline_kanji_info(v).get('meaning'))
    # pprint(kanjidic2_info(v))
    #     print(type(v))
    # offline_kanji_info(sample_vocab)
