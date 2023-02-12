import csv
import glob
import json
import os
import pathlib
import shutil
from collections import OrderedDict

import util

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


def create_jmdict_pos_map():
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

    jmdict_endings = tuple(jmdict_endings)
    # print(jmdict_endings)


def main():
    final_dictionary_list = []

    with open(cleaned_csv_path, "r", encoding="utf8") as f_in:
        csvreader = csv.reader(f_in)
        for idx, line in enumerate(csvreader):
            assert len(line) <= 3

            vocab: str = str(line[0])

            ## if len(line) == 3, line[2] equals its pronunciation in hiragana
            reading = ""
            if len(line) == 3:
                reading = str(line[2])

            definition = line[1]
            definition = util.strip_tags(definition)

            get_deinflection_endings()

            yomi_pos = ""
            if vocab.endswith(inflections):
                yomi_pos = get_pos(vocab)

            if not yomi_pos:
                if vocab.endswith(jmdict_endings):
                    # print(True)
                    yomi_pos = get_jmdict_pos(vocab)

                    # print(f'{vocab}\n{yomi_pos}\n{reading}\n{definition}')
                    # print('\n')
            # if idx >= 500:
            #     break

            specific_site_link = f"https://thesaurus.weblio.jp/content/{vocab}"
            link_string = {"tag": "a", "href": specific_site_link, "content": "weblio"}

            struct_cont = [{"type": "structured-content", "content": [link_string]}]
            temp_list = [vocab, reading, "", yomi_pos, 0, struct_cont, idx, ""]

            print(idx)
            final_dictionary_list.append(temp_list)

    create_weblio_external(final_dictionary_list)


def get_deinflection_endings() -> None:
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
    # print(inflections)
    inflections = tuple(inflection_endings)


# https://stackoverflow.com/questions/48774616/return-the-value-of-a-matching-item-in-a-python-list
def _check_if_in_lookup(word, lookup):
    """
    lookup = deinflection endings tuple

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


def create_weblio_external(final_list):
    build_version = "v_1.00"

    build_directory = "yomichan_dictionary_json_files"
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
                "revision": f"weblio-ruigi-jisho.{build_version}",
                "url": "https://github.com/aiko-tanaka/Grammar-Dictionaries/",
                "sequenced": True,
                "format": 3,
                "description": """様々な同義語や同意語の日本語表現を約40万語を収録。\n 使う場面やニュアンスごとに、類語とシソーラスを分類・整理。
リンクによって「類語の類語」を簡単に検索。\n 名詞や形容詞、感嘆符など、品詞の区別にとらわれず類語を紹介。 \n 通俗表現やセリフも多数収録。""",
                "attribution": "https://thesaurus.weblio.jp/",
                "author": "nihongobongo",
            }
            json.dump(index, f, indent=4, ensure_ascii=False)

        zip_filename = "Weblio類語辞書"
        if pathlib.Path(f"{zip_filename}_{build_version}.zip").is_file():
            os.remove(f"{zip_filename}_{build_version}.zip")
        shutil.make_archive(f"{zip_filename}_{build_version}", "zip", build_directory)


if __name__ == "__main__":
    create_jmdict_pos_map()
    main()
