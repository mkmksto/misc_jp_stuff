import glob
import json
import os
import pathlib
import re
import shutil
from collections import OrderedDict

import util
from bs4 import BeautifulSoup

DEBUG = False

# TODO: put tsukaiwake at the end, put the list of vocabs after the shared definition
# TODO: check if <table> in string, then return its struct cont equiv, otherwise, return the str


def main(raw_json):
    final_dictionary = []

    with open(raw_json, "r", encoding="utf8") as f_in:
        data_in: dict = json.load(f_in, object_pairs_hook=OrderedDict)

    ctr = 0
    for idx, (key, val) in enumerate(data_in.items()):
        key: str

        list_of_vocabs = get_vocabs_from_header(text=key)
        vocab_pos_dict, contents = get_pos_and_contents(str(val))
        # print(f'idx:{idx}, cont:{contents}')

        # raw vocab still has parentheses
        for raw_vocab in list_of_vocabs:
            vocab, reading = get_reading_vocab_pair(raw_vocab)
            yomi_pos = vocab_pos_dict.get(vocab, "")
            if not yomi_pos:
                yomi_pos = get_foosoft_pos(vocab)

            # print(f'ctr:{ctr}, {vocab}:{yomi_pos}\n{contents}')
            print(f"ctr:{ctr}, {vocab}:{yomi_pos}")
            temp_list = [vocab, reading, "", yomi_pos, 0, contents, ctr, ""]

            final_dictionary.append(temp_list)
            ctr += 1

        if ctr >= 100 and DEBUG:
            break

    ################################################
    if not DEBUG:
        create_dictionary(final_dictionary)
    ################################################


def get_pos_and_contents(text) -> tuple:
    """
    Returns:
         ({vocab1: pos1, vocab2: pos2}, contents) as a tuple
    """
    pos_dict = dict()

    soup = BeautifulSoup(text, features="html.parser")
    section_containing_pos = soup.find("section", attrs={"id": "sec_thsrs"})

    ########################################################
    # get pos
    if section_containing_pos:
        children = section_containing_pos.findChildren(
            "div", attrs={"class": "content-parts f-16"}
        )
        if children:
            child_containing_pos = get_matching_item_from_list(
                children,
                text_to_match="【",
            )

            if child_containing_pos:
                dt_container = child_containing_pos.findChildren("dt")
                if dt_container:
                    for vocab in dt_container:
                        try:
                            vocab_and_pos: str = vocab.text
                            word = vocab_and_pos.split("【")[0]
                            pos = (
                                vocab_and_pos.replace(word, "")
                                .replace("【", "")
                                .replace("】", "")
                            )
                            if pos:
                                pos_dict[word.strip()] = POS_MAP.get(pos.strip(), "")
                            else:
                                pos_dict[word.strip()] = get_jmdict_pos(word.strip())
                        except Exception:
                            raise

    ########################################################
    # get contents
    soup_text = str(soup)
    soup_text = get_word_from_li_html(soup_text)
    soup_text = clean_paragraphs_html(soup_text)
    soup_text = clean_headings_html(soup_text)
    soup_text = clean_unnecessary(soup_text)
    soup_text = final_cleanup(soup_text)
    contents = convert_tables(soup_text)
    if isinstance(contents, str):
        contents = contents.replace("\n\n", "", 1)
        contents = util.strip_tags(contents)
    contents = [contents]

    return pos_dict, contents


def convert_tables(text) -> str or dict:
    if "table" in text:
        full_text = "<body>" + text + "</body>"
        soup = BeautifulSoup(full_text, features="html.parser")
        body_structure = util.get_markup_structure(soup.body)
        if body_structure:
            content = body_structure["content"]
        else:
            return text

        if not isinstance(content, str):
            content = [content[0].replace("\n\n", "", 1), content[1:]]
            return {"type": "structured-content", "content": content}
        else:
            raise ValueError("Failed somewhere at converting tables")
    else:
        return text


def final_cleanup(text: str) -> str:
    """
    Remove extra \n's
    Better formatting for の使い方

    Usage:
        place at the end of cleanup
    """
    cleaned = re.sub(r"[\n]{1,2}[\s]{0,100}[\n]{1,2}", r"\n\n", text)
    cleaned = re.sub(r"[\s\n]{0,5}(.*?【.*?】)[\s\n]{0,5}", r"\n\n\1\n  ", cleaned)
    # remove giant space after main definition
    # cleaned = re.sub(r'(\\n){0,2}(\\xa0){1,5}(\\n){1,2}', r'\n\n', cleaned)
    return cleaned.strip()


def get_word_from_li_html(text: str) -> str:
    """
    list of words at the end (based on ruigo)
    The original format was one word per line, which was too long, just concat them into one line
    """
    cleaned_text = re.sub(
        r"<ul.*?>", r"\n&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;→", text
    )
    cleaned_text = cleaned_text.replace(r"</ul>", "")
    return re.sub(r'<li><a\shref="(.*?)">(.*?)<\/a><\/li>', r"・\2  ", cleaned_text)


def clean_paragraphs_html(text: str) -> str:
    # emphasize first definition
    cleaned_text = re.sub(
        r"<p>(.*?)<\/p>", r"&nbsp;&nbsp;&nbsp;&nbsp;➞\1", text, count=1
    )
    cleaned_text = re.sub(
        r"<p.*?>(.*?)<\/p>", r"\n\n&nbsp;&nbsp;&nbsp;\1", cleaned_text
    )
    return cleaned_text


def clean_headings_html(text: str) -> str:
    """
    h3 = prob tsukaikata and tsukaiwake
    """
    cleaned_text = re.sub(r"<h1.*?>(.*?)<\/h1>", r"", text)
    cleaned_text = re.sub(r"<h2.*?>(.*?)<\/h2>", r"\n\1\n", cleaned_text)
    cleaned_text = re.sub(
        r'<h3 class="bar-title gray except-hover-underline"><a\shref=.*?>(.*?)<\/a>(.*?)<\/h3>',
        r"\n\n［\1\2］",
        cleaned_text,
    )
    cleaned_text = re.sub(r"<h3.*?>(.*?)<\/h3>", r"\n\n\1\n", cleaned_text)
    cleaned_text = re.sub(r"<h4.*?>(.*?)<\/h4>", r"\n\1\n", cleaned_text)

    return cleaned_text


def clean_unnecessary(text: str) -> str:
    cleaned_text = text.replace("<br>", "\n")
    cleaned_text = re.sub(
        r"<span\sclass=\"sub\-item\">(.*?)<\/span>", r"\n", cleaned_text
    )
    cleaned_text = re.sub(
        r"<span\sclass=\"sub\-items\">(.*?)<\/span>", r"\n", cleaned_text
    )
    cleaned_text = re.sub(
        r"<p\sclass=\"wordnet\-cite\">([^a])(.*?)<\/p>", r"", cleaned_text
    )
    cleaned_text = re.sub(
        r'<div class="section cx anchor-hover-underline"><div class="basic_title except-hover-underline">([^a])*<a.*\/a>([^a])*<\/div>',
        r"",
        cleaned_text,
    )
    cleaned_text = re.sub(
        r'<dt><a href="bword:.*?">(.*?)<\/a>(.*?)<\/dt>', r"\n\1\2", cleaned_text
    )
    cleaned_text = re.sub(
        r"<dd>(.*?)<\/dd>", r"\n&nbsp;&nbsp;&nbsp;&nbsp;\1", cleaned_text
    )
    cleaned_text = cleaned_text.replace("英語表現", "")
    cleaned_text = cleaned_text.replace("カテゴリ", "\n")
    cleaned_text = cleaned_text.replace("国語辞書で調べる", "")

    # TODO: tsukaiwake and tsukaikata (if needed)
    cleaned_text = re.sub(
        r'<dl class="float-left"><dt>([０-９]{1,2})<\/dt><dd>(.*?)<\/dd><\/dl>',
        r"\1\n&nbsp;&nbsp;&nbsp;\2\n",
        cleaned_text,
    )
    cleaned_text = re.sub(r"<\/?strong.*?>", r"", cleaned_text)
    cleaned_text = re.sub(r"([０-９]{1,2})", r"\n\1", cleaned_text)
    cleaned_text = re.sub(r"<\/?div.*?>", r"", cleaned_text)
    cleaned_text = re.sub(r"<\/?dl.*?>", r"", cleaned_text)
    cleaned_text = re.sub(r"<\/?dt.*?>", r"", cleaned_text)
    cleaned_text = re.sub(r"<\/?dd.*?>", r"", cleaned_text)
    cleaned_text = re.sub(r"<\/?i.*?>", r"", cleaned_text)
    cleaned_text = re.sub(r"<\/?span.*?>", r"", cleaned_text)
    cleaned_text = re.sub(r"<\/?section.*?>", r"", cleaned_text)
    cleaned_text = re.sub(r"<\/?li.*?>", r"", cleaned_text)
    cleaned_text = re.sub(r"<\/?yomi.*?>", r"", cleaned_text)
    # cleaned_text = re.sub(r'[^.]{0,1}(.*?[^.]{0,5}の使い分け)[^.]{0,1}', r'\n\1', cleaned_text)

    # remove things attached to [英]
    cleaned_text = re.sub(
        r"[\s]?\[英\].*?[<]?[^ぁ-んァ-ン！：／一-龯【】０-９Ａ-ｚぁ-ゞァ-ヶｦ-ﾟ]*[\n]?", r"", cleaned_text
    )
    cleaned_text = re.sub(r"<\/?a.*?>", r"", cleaned_text)

    # idk why but regex couldn't catch the footer
    cleaned_text = cleaned_text.split("\n")
    cleaned_text = "\n".join(cleaned_text[:-1])
    cleaned_text = cleaned_text.replace("▽", "\n&nbsp;&nbsp;&nbsp;▽")
    return cleaned_text


def get_matching_item_from_list(iterable, text_to_match: str):
    """
    https://stackoverflow.com/questions/48774616/return-the-value-of-a-matching-item-in-a-python-list
    Returns:
        The member of the list where 'text' has been found
    """
    return next((member for member in iterable if text_to_match in member.text), None)


def get_vocabs_from_header(text: str) -> list:
    """
    Removes everything beyond '|' (which is basically a rehashing of the terms)

    Returns:
        a list of strings as the parsed vocab from the header
    """
    pattern = re.compile(r"^(.*?)\|")
    cleaned_text = pattern.match(text)
    if cleaned_text:
        cleaned_text = cleaned_text.groups()[0]
    else:
        cleaned_text = str(text)

    if "_" in cleaned_text:
        cleaned_text = cleaned_text.split("_")[1]

    return [vocab for vocab in cleaned_text.split("／")]


def get_reading_vocab_pair(text: str) -> tuple:
    """
    Returns:
         (vocab, reading) pair
    """
    pattern = re.compile(r"(.*?)\((.*?)\)")
    if "(" in text:
        reading = pattern.search(text)
        return reading.groups()[0], reading.groups()[1]
    else:
        return text, util.generate_reading(text)


def __create_unique_list_of_raw_pos():
    # raw pos = 形動, 形, etc. (not yet v1, v5, vk, etc.)
    global _TEMP_POS_LIST
    _TEMP_POS_LIST = list(set(_TEMP_POS_LIST))
    with open("raw_pos_list.txt", "w", encoding="utf8") as f:
        json.dump(_TEMP_POS_LIST, f, indent=4, ensure_ascii=False)


def set_global_pos_map() -> None:
    global POS_MAP
    POS_MAP = {
        "ナ下一": "v1",
        "バ下一": "v1",
        "カ上一": "v1",
        "サ下一": "v1",
        "ナ上一": "v1",
        "ザ上一": "v1",
        "ダ下一": "v1",
        "ガ上一": "v1",
        "ハ下一": "v1",
        "ラ上一": "v1",
        "ザ下一": "v1",
        "タ上一": "v1",
        "カ下一": "v1",
        "マ上一": "v1",
        "バ上一": "v1",
        "タ下一": "v1",
        "ラ下一": "v1",
        "マ下一": "v1",
        "ア上一": "v1",
        "ア下一": "v1",
        "ガ下一": "v1",
        "バ五": "v5",
        "ラ五": "v5",
        "カ五": "v5",
        "ナ五": "v5",
        "ガ五": "v5",
        "サ五": "v5",
        "ワ五": "v5",
        "タ五": "v5",
        "マ五": "v5",
        "形": "adj-i",
        "サ変": "vs",
        "カ変": "vk",
    }


def create_jmdict_pos_map() -> None:
    """
    sets the values of three global variables based on values form JMDict/Shin Kanji Tsukai
    i.e. creates a P.O.S and reading map
    """
    shin_jmdict_path = (
        r"D:\1.Michael\JP\Dictionaries\shoui\stephenmk\jmdict_orthographic_variants"
    )
    json_file_pattern = os.path.join(shin_jmdict_path, "term_bank_*.json")
    json_files = glob.glob(json_file_pattern)

    global JMDICT_ENDINGS

    for file_path in json_files:
        with open(file_path, "r", encoding="utf8") as fh:
            data: list = json.load(fh)

        # create tuple for checking with endswith
        # vocab : pos mapping
        for entry in data:
            if entry[3]:
                JMDICT_ENDINGS.append(entry[0])
                JMDICT_POS_MAP[entry[0]] = entry[3]

    JMDICT_ENDINGS = tuple(JMDICT_ENDINGS)


def _return_item_that_endswith(word, lookup):
    """
    https://stackoverflow.com/questions/48774616/return-the-value-of-a-matching-item-in-a-python-list
    Args:
        lookup: deinflection endings tuple

    Returns:
        the ending of the word (that matched)
    """
    return next((s for s in lookup if word.endswith(s)), None)


def get_jmdict_pos(word) -> str:
    ending = _return_item_that_endswith(word, JMDICT_ENDINGS)
    return JMDICT_POS_MAP.get(ending, "")


def create_foosoft_pos_map() -> None:
    """
    based on foosoft's deinflect.json
    """
    inflection_endings = []
    with open("deinflect.json", "r", encoding="utf8") as ff:
        deinflect = json.load(ff)

    global POS_MAP
    POS_MAP = OrderedDict()

    for rule in deinflect:
        inflection_endings.append(rule["kanaIn"])
        POS_MAP[rule["kanaIn"]] = rule["rulesIn"]

    with open("deinflect2.json", "r", encoding="utf8") as fh:
        deinflect2 = json.load(fh)

    for rule in deinflect2:
        inflection_endings.append(rule["kanaOut"])
        POS_MAP[rule["kanaOut"]] = rule["rulesOut"]

    global INFLECTIONS
    INFLECTIONS = tuple(inflection_endings)


def get_foosoft_pos(word) -> str:
    """
    Returns:
         yomichan pos (e.g. v1, vk)
    """
    ending = _return_item_that_endswith(word, INFLECTIONS)

    yomi_pos = POS_MAP.get(ending, "")
    if yomi_pos:
        yomi_pos = yomi_pos[0]

    return yomi_pos


def create_dictionary(final_list: list) -> None:
    """
    Create yomichan json files and zip them to an archive

    """
    print("creating dictionary")
    build_version = "v_1.00"
    test_name = ""
    if DEBUG:
        test_name = "TEST0"

    build_directory = f"yomichan_dictionary_json_files_{build_version}{test_name}"
    try:
        os.mkdir(build_directory)
    except FileExistsError:
        print("directory already exists")

    terms_per_file = 6000
    max_i = int(len(final_list) / terms_per_file) + 1
    for i in range(max_i):
        if pathlib.Path(f"{build_directory}/term_bank{i+1}.json").is_file():
            os.remove(f"{build_directory}/term_bank{i+1}.json")

        with open(
            f"{build_directory}/term_bank_{i+1}.json", "w", encoding="utf8"
        ) as f_out:
            start = terms_per_file * i
            end = terms_per_file * (i + 1)
            print(i)
            json.dump(final_list[start:end], f_out, indent=4, ensure_ascii=False)

        with open(f"{build_directory}/index.json", "w", encoding="utf8") as f:
            index = {
                "title": f"使い方の分かる 類語例解辞典{test_name}",
                "revision": f"tsukai-ruigo.{build_version}",
                "url": "https://github.com/aiko-tanaka/Grammar-Dictionaries/",
                "sequenced": True,
                "format": 3,
                "description": """２万５千語の基本的な言葉を６千のグループに分類し、共通する意味、実例、
                使い分けなどについて記述。特に、言葉の微妙なニュアンスの違いや使い方の差異は、
                豊富な例文と類語対比表を用いて丁寧に解説した。""",
                "attribution": "https://www.shogakukan.co.jp/books/09505522",
                "author": "nihongobongo",
            }
            json.dump(index, f, indent=4, ensure_ascii=False)

        zip_filename = f"使い方の分かる 類語例解辞典{test_name}"
        if pathlib.Path(f"{zip_filename}_{build_version}.zip").is_file():
            os.remove(f"{zip_filename}_{build_version}.zip")
        shutil.make_archive(f"{zip_filename}_{build_version}", "zip", build_directory)


if __name__ == "__main__":
    raw_dict_data = "tsukaikata.json"
    _TEMP_POS_LIST = []
    POS_MAP = OrderedDict()
    JMDICT_ENDINGS = []
    JMDICT_POS_MAP = OrderedDict()
    FOOSOFT_POS_MAP = OrderedDict()

    set_global_pos_map()
    create_jmdict_pos_map()
    create_foosoft_pos_map()
    main(raw_dict_data)
