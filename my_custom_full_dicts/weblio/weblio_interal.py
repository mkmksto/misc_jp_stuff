import csv
import glob
import json
import os
import pathlib
import re
import shutil
from collections import OrderedDict

import util
from bs4 import BeautifulSoup
from css_parser import parseStyle

# TODO: instead of using struct content, just split it along 意義素類語, then format using tabs/spaces
# TODO: improve clean_definition regex so that it doesn't catch entries beyond thesaurus as bold

csv_path = "../weblio_ruigigo_jiten"
cleaned_csv_path = os.path.join(csv_path, "weblio_cleaned.csv")
shin_jmdict_path = (
    r"D:\1.Michael\JP\Dictionaries\shoui\stephenmk\jmdict_orthographic_variants"
)

inflections = tuple()
pos_map = OrderedDict()

# jmdict inflections
jmdict_endings = []
jmdict_pos_map = OrderedDict()
jmdict_reading_map = OrderedDict()


def create_jmdict_pos_map() -> None:
    """
    sets the values of three global variables based on values form JMDict/Shin Kanji Tsukai
    i.e. creates a P.O.S and reading map
    """
    json_file_pattern = os.path.join(shin_jmdict_path, "term_bank_*.json")
    json_files = glob.glob(json_file_pattern)

    global jmdict_endings

    for file_path in json_files:
        with open(file_path, "r", encoding="utf8") as fh:
            data: list = json.load(fh)

        # create tuple for checking with endswith
        # vocab : pos mapping
        for entry in data:
            if entry[3]:
                jmdict_endings.append(entry[0])
                jmdict_pos_map[entry[0]] = entry[3]

            if entry[1]:
                jmdict_reading_map[entry[0]] = entry[1]

    jmdict_endings = tuple(jmdict_endings)


def main() -> None:
    final_dictionary_list = []

    create_deinflection_endings()

    with open(cleaned_csv_path, "r", encoding="utf8") as f_in:
        csvreader = csv.reader(f_in)
        for idx, line in enumerate(csvreader):
            assert len(line) <= 3

            vocab: str = str(line[0])

            reading = ""
            if len(line) == 3:
                reading = str(line[2])

            if not reading:
                reading = get_jmdict_reading(vocab)

            if not reading:
                reading = util.generate_reading(vocab)

            definition = str(line[1])
            definition = return_first_two_defs(definition, terms_limit=10)

            yomi_pos = ""
            if vocab.endswith(inflections):
                yomi_pos = get_pos(vocab)

            if not yomi_pos:
                if vocab.endswith(jmdict_endings):
                    yomi_pos = get_jmdict_pos(vocab)

            if isinstance(definition, list):
                definition = [e for e in definition if e]

            # check for あばずれ女
            # if idx == 3860 or idx == 0:
            #     print(f'{vocab}\n{reading}\n{definition}')
            #     print('\n')

            if isinstance(definition, str):
                content = [definition]
            else:
                content = [{"type": "structured-content", "content": definition}]

            temp_list = [vocab, reading, "", yomi_pos, 0, content, idx, ""]

            # if idx >= 600:
            #     print(f'{definition}')
            #     break

            print(idx)
            final_dictionary_list.append(temp_list)

    #################################################
    if True:
        create_weblio_external(final_dictionary_list)
    #################################################


def return_first_two_defs(defn, terms_limit=10) -> str:
    """
    Return the first two dictionaries
    and limit num of entries of each dict to only 7 entries(customizable)
    """
    # frst_two = split_but_keep_separator(defn, '<table>')
    frst_two = split_but_keep_separator(defn, '<h2 class="dictNm">')
    # 3, not 2 because [0] pertains to the info before <h2 class....>
    frst_two = frst_two[:3]
    frst_two = "".join(frst_two)
    frst_two = "<body>" + frst_two + "</body>"
    frst_two = clean_definition(frst_two)

    soup = BeautifulSoup(frst_two, features="html.parser")
    frst_two = get_markup_structure(soup.body)
    frst_two = frst_two["content"]
    frst_two = simplify_content_if_possible(frst_two)

    return frst_two


def clean_definition(defn) -> str:
    cln_defn = re.sub(r"<!--.{0,40}?-->", "", defn)
    cln_defn = re.sub(
        r'<table\sclass="wrp"><tr>(.{0,30})<h2\sclass="dictNm"><a\s>(.{0,30})<\/a><\/h2><\/td><\/tr><\/table>',
        r"\n→\2",
        cln_defn,
    )
    cln_defn = _unwrap_divs(cln_defn)
    cln_defn = re.sub(r"<a(.*?)>", "", cln_defn)

    # <table class=""wrp""> (wraps the dictionary title)
    cln_defn = cln_defn.replace("</a>", "")
    cln_defn = re.sub(r'<div\sclass="kijiWrp">(.*?)<\/div>', r"\1", cln_defn)
    cln_defn = re.sub(r'<div\sclass="kiji">(.*?)<\/div>', r"\1", cln_defn)

    cln_defn = re.sub(r'<div\sclass="Nwnts">(.*?)<\/div>', r"\1", cln_defn)  # wordnet
    cln_defn = re.sub(
        r'<div\sclass="Wrugj">(.*?)<\/div>', r"\1", cln_defn
    )  # (weblio ruigo)
    cln_defn = re.sub(r'<div\sclass="Wrigo">(.*?)<\/div>', r"\1", cln_defn)  # Thesaurus

    cln_defn = re.sub(
        r'<h2\sclass="midashigo"(.{0,60}?)>(.{0,50}?)<\/h2>', r"\n【\2】\n", cln_defn
    )
    cln_defn = cln_defn.replace("\n", "", 1)
    cln_defn = cln_defn.strip()

    return cln_defn


def simplify_content_if_possible(cont):
    """
    Try to concatenate the contents if the content contains no dict
    Typing the contents will usually give something like this
        [<class 'bs4.element.NavigableString'>
        <class 'bs4.element.NavigableString'>
        <class 'dict'>
        <class 'bs4.element.NavigableString'>
        <class 'bs4.element.NavigableString'>]
    Returns:
        A string if the content can be simplfied
        Otherwise, simply returns the list as is
    """

    if cont:
        if not any(isinstance(c, dict) for c in cont):
            try:
                aggr = "".join(cont)
                return aggr

            except Exception as e:
                raise
        else:
            return cont
    else:
        return cont


def _unwrap_divs(text: str) -> str:
    soup = BeautifulSoup(text, features="html.parser")
    # for class_name in ['kijiWrp', 'kiji', 'Wrugj', 'Wrigo']:
    x = soup.find_all("div")
    for i in range(len(x)):
        soup.div.unwrap()

    return str(soup)


def split_but_keep_separator(text, separator) -> list:
    """
    Splits a string into a list but keeps its separator/delimiter
    """
    s = [e + separator for e in text.split(separator) if e]
    return s


def remove_none(obj):
    """
    https://stackoverflow.com/questions/20558699/python-how-recursively-remove-none-values-from-a-nested-data-structure-lists-a
    """
    if isinstance(obj, (list, tuple, set)):
        return type(obj)(remove_none(x) for x in obj if x is not None)
    elif isinstance(obj, dict):
        return type(obj)(
            (remove_none(k), remove_none(v))
            for k, v in obj.items()
            if k is not None and v is not None
        )
    else:
        return obj


def get_markup_structure(soup):
    content = []
    node = {"tag": "span"}
    if soup:
        for child in soup.children:
            if child.name is None:
                if child != "":
                    content.append(child)
            else:
                content.append(get_markup_structure(child))

        if str(soup.name) == "h2":
            node = {"tag": "span"}
        if str(soup.name) in [
            "table",
            "tbody",
            "tfoot",
            "tr",
            "td",
            "div",
            "span",
            "th",
            "br",
        ]:
            node = {"tag": soup.name}

        if node and content:
            if None in content:
                content.remove(None)
            elif "" in content:
                content.remove("")
            attributes = get_attributes(soup.attrs)
            for key, val in attributes.items():
                node[key] = val
            if len(content) == 1:
                if content[0]:
                    if isinstance(content[0], dict):
                        node["content"] = remove_none(content[0])
                    else:
                        node["content"] = content[0]
            else:
                if isinstance(content, dict):
                    node["content"] = remove_none(content)
                else:
                    node["content"] = content
        else:
            return

        return remove_none(node)

    else:
        return remove_none(node)


def get_attributes(attrs):
    attributes = {}
    if "colspan" in attrs:
        attributes["colSpan"] = int(attrs["colspan"])
    if "style" in attrs:
        attributes["style"] = get_style(attrs["style"])
    if "lang" in attrs:
        attributes["lang"] = attrs["lang"]
    return attributes


def get_style(inline_style_string):
    style = {}
    parsedStyle = parseStyle(inline_style_string)
    if parsedStyle.fontSize != "":
        style["fontSize"] = parsedStyle.fontSize
    if parsedStyle.fontWeight != "":
        style["fontWeight"] = parsedStyle.fontWeight
    return style


def create_deinflection_endings() -> None:
    """
    sets the values of the global suffix inflections table
    also sets a pos map (ending : pos) dictionary
    """
    inflection_endings = []
    with open("deinflect.json", "r", encoding="utf8") as ff:
        deinflect = json.load(ff)

    global pos_map
    pos_map = OrderedDict()

    for rule in deinflect:
        inflection_endings.append(rule["kanaIn"])
        pos_map[rule["kanaIn"]] = rule["rulesIn"]

    with open("deinflect2.json", "r", encoding="utf8") as fh:
        deinflect2 = json.load(fh)

    for rule in deinflect2:
        inflection_endings.append(rule["kanaOut"])
        pos_map[rule["kanaOut"]] = rule["rulesOut"]

    global inflections
    inflections = tuple(inflection_endings)


# https://stackoverflow.com/questions/48774616/return-the-value-of-a-matching-item-in-a-python-list
def _check_if_in_lookup(word, lookup):
    """
    Args:
        lookup: deinflection endings tuple

    Returns:
        the ending of the word (that matched)
    """
    return next((s for s in lookup if word.endswith(s)), None)


def get_pos(word) -> str:
    """
    Returns:
        its yomichan part of speech
        e.g. v1, v5, adj-i, etc.
    """
    ending = _check_if_in_lookup(word, inflections)

    yomi_pos = pos_map.get(ending, "")
    if yomi_pos:
        yomi_pos = yomi_pos[0]

    return yomi_pos


def get_jmdict_pos(word) -> str:
    ending = _check_if_in_lookup(word, jmdict_endings)
    return jmdict_pos_map.get(ending, "")


def get_jmdict_reading(word) -> str:
    return jmdict_reading_map.get(word, "")


def create_weblio_external(final_list):
    """
    Create yomichan json files and zip them to an archive
    """
    build_version = "v_1.02"
    # v_1.02, simplify overly-complex divs, remove <b>, simplified list of strings to a single string

    build_directory = f"yomichan_dictionary_json_files_{build_version}"
    try:
        os.mkdir(build_directory)
    except FileExistsError:
        print("directory already exists")

    terms_per_file = 40000
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
                "title": "Weblio類語辞書",
                "revision": f"weblio-ruigi-jisho-int.{build_version}",
                "url": "https://github.com/aiko-tanaka/Grammar-Dictionaries/",
                "sequenced": True,
                "format": 3,
                "description": """様々な同義語や同意語の日本語表現を約40万語を収録。\n 使う場面やニュアンスごとに、類語とシソーラスを分類・整理。
リンクによって「類語の類語」を簡単に検索。\n 名詞や形容詞、感嘆符など、品詞の区別にとらわれず類語を紹介。 \n 通俗表現やセリフも多数収録。""",
                "attribution": "https://thesaurus.weblio.jp/",
                "author": "nihongobongo",
            }
            json.dump(index, f, indent=4, ensure_ascii=False)

        zip_filename = "Weblio類語辞書_internal"
        if pathlib.Path(f"{zip_filename}_{build_version}.zip").is_file():
            os.remove(f"{zip_filename}_{build_version}.zip")
        shutil.make_archive(f"{zip_filename}_{build_version}", "zip", build_directory)


if __name__ == "__main__":
    create_jmdict_pos_map()
    main()
