import json
from collections import OrderedDict

import jaconv
from sudachipy import dictionary, tokenizer


def generate_reading(text: str) -> str:
    """
    Generate reading of a particular japanese text
    """
    mode = tokenizer.Tokenizer.SplitMode.C
    tokenizer_obj = dictionary.Dictionary().create()
    m = tokenizer_obj.tokenize(text, mode)

    aggr = ""
    for z in m:
        aggr += jaconv.kata2hira(z.reading_form())

    return aggr


def _return_item_that_endswith(word: str, lookup):
    """
    https://stackoverflow.com/questions/48774616/return-the-value-of-a-matching-item-in-a-python-list
    Args:
        word    : word to check if it's somewhere inside the lookup tuple
        lookup  : deinflection endings tuple
    Returns:
        the ending of the word (that matched)
    """
    return next((s for s in lookup if word.endswith(s)), None)


def get_matching_item_from_list(iterable, text_to_match: str):
    """
    https://stackoverflow.com/questions/48774616/return-the-value-of-a-matching-item-in-a-python-list
    Returns:
        The member of the list where 'text' has been found
    """
    return next((member for member in iterable if text_to_match in member.text), None)


def create_foosoft_pos_map() -> None:
    """
    based on foosoft's deinflect.json
    """
    inflection_endings = []
    with open("deinflect.json", "r", encoding="utf8") as ff:
        deinflect = json.load(ff)

    global FOOSOFT_POS_MAP
    FOOSOFT_POS_MAP = OrderedDict()

    for rule in deinflect:
        inflection_endings.append(rule["kanaIn"])
        FOOSOFT_POS_MAP[rule["kanaIn"]] = rule["rulesIn"]

    with open("deinflect2.json", "r", encoding="utf8") as fh:
        deinflect2 = json.load(fh)

    for rule in deinflect2:
        inflection_endings.append(rule["kanaOut"])
        FOOSOFT_POS_MAP[rule["kanaOut"]] = rule["rulesOut"]

    global INFLECTIONS
    INFLECTIONS = tuple(inflection_endings)


def get_foosoft_pos(word) -> str:
    """
    Returns:
         yomichan pos (e.g. v1, vk)
    """
    ending = _return_item_that_endswith(word, INFLECTIONS)

    yomi_pos = FOOSOFT_POS_MAP.get(ending, "")
    if yomi_pos:
        yomi_pos = yomi_pos[0]

    return yomi_pos


if __name__ == "__main__":
    # に忍びない
    print(generate_reading("と相まって"))
    print(generate_reading("に忍びない"))
    print(generate_reading("に即して"))
    print(generate_reading("に限ったことではない"))
    print(generate_reading("ないではおかない"))
