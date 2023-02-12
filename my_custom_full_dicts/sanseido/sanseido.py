import csv
import json
import os
import pathlib
import re
import shutil

import util
from bs4 import BeautifulSoup

cleaned_input = []

with open("ssd-h-rmv.csv", "r", encoding="utf8") as f_in:
    csvreader = csv.reader(f_in)

    for line in csvreader:
        if line:
            cleaned_input.append(line)


pos_map = {
    "名": "n",
    "自五": "v5",
    "他五": "v5",
    "自上一": "v1",
    "他下一": "v1",
    "形": "adj-i",
    "自サ": "vs",
    "他サ": "vs",
    "自カ": "vk",
    "他カ": "vk",
}


def taigigo_haseigo(inp_str: str) -> str:
    """
    <span class=""対義語"">愛息</span>
    <span class=""派生語""><span class=""派生語見出"">愛くるしさ</span>
        to
    ［対義語］愛息
    ［派生語］愛くるしさ
    """
    out = re.sub(r'<span class="対義語">(.*?)</span>', r"［対義語］\1", inp_str)
    out = re.sub(r'<span class="派生語">(.*?)</span>', r"\n［派生語］\1", out)
    out = out.replace(r'<span class="派生語見出">', "")
    if out:
        out = f"\n{out}"
    return out


def get_pos(word_in_kanji: str, sanseido_pos: str) -> str:
    """
    Args:
        inp_str: the word in kanji form
    """
    yomi_pos = ""
    if word_in_kanji:
        if not word_in_kanji.endswith("ずる"):
            yomi_pos = pos_map.get(sanseido_pos.strip(), "")
        else:
            yomi_pos = "vz"
    else:
        yomi_pos = ""

    return yomi_pos


final_ouput = []

for i, entry in enumerate(cleaned_input):
    word_header: str = entry[0]
    raw_contents: str = entry[1]
    raw_contents = raw_contents.replace("\n", "")
    raw_contents = raw_contents.replace("<br>", "")

    entry = BeautifulSoup(raw_contents, features="html.parser")
    part_of_speech = entry.find("span", attrs={"class": "品詞"})
    if part_of_speech:
        part_of_speech = part_of_speech.contents[0]
    else:
        part_of_speech = ""

    ####################

    word_kanji_form = ""
    word_reading = ""
    if "【" in word_header:
        word_kanji_form = re.findall(r"【(.*?)】", word_header)
        if isinstance(word_kanji_form, list):
            word_kanji_form = word_kanji_form[0]

        word_reading = word_header.split("【")[0]
    else:
        word_kanji_form = word_header

    ####################

    part_of_speech = get_pos(word_kanji_form, part_of_speech)

    ####################

    try:
        raw_contents_split = re.split(r'（<span class="品詞">(.*?)</span>）', raw_contents)
        raw_contents_0 = raw_contents_split[0]
        kanren_tango = ""
        if raw_contents_0:
            raw_contents_0_soup = BeautifulSoup(raw_contents_0, features="html.parser")
            # a = container for related words(kanren)
            a_hrefs = raw_contents_0_soup.find_all("a")
            for href in a_hrefs:
                raw_contents_0 = raw_contents_0.replace(str(href).strip(), "")
                kanren_tango += str(href).strip()
                # print(href)

        raw_contents_1 = raw_contents_split[1]  # the 品詞 itself
        raw_contents_2 = raw_contents_split[2]
        raw_contents_2 = raw_contents_2.replace(r'<span class="語義番号">', "\n")

        if kanren_tango:
            kanren_tango = f"\n\n{kanren_tango}"

        remaining_items_collector = ""
        if len(raw_contents_split) > 3:
            for idx, other_contents in enumerate(raw_contents_split):
                if idx >= 3:
                    remaining_items_collector += str(other_contents)

        raw_contents = (
            f"{raw_contents_0.strip()}（{raw_contents_1.strip()}）\n"
            f"{raw_contents_2}{remaining_items_collector}{kanren_tango}"
        )

    except IndexError:
        # raw_contents_1 = raw_contents_split[1] # the 品詞 itself     IndexError: list index out of range
        pass

    ############ remove ruby               <span class=""ルビ"">センリョウ</span>
    raw_contents = re.sub(r'<span class="ルビ">(.*?)</span>', "", raw_contents)

    ############
    # further cleanup
    raw_contents = raw_contents.replace(r'<rect class="red">派生</rect>', "")

    ############
    # pick out the 対義語 and 派生語
    raw_contents = taigigo_haseigo(raw_contents)
    ############

    stripped_contents: str = util.strip_tags(raw_contents)
    stripped_contents = stripped_contents.strip()

    temp_list = [
        word_kanji_form,
        word_reading,
        None,
        part_of_speech,
        0,  # frequency info
        [stripped_contents],
        i,
        "",
    ]

    final_ouput.append(temp_list)

    # if i == 7000:
    #     break
    print(i)
    # print(temp_list)


def create_sanseido():
    build_version = "v_1.01"

    build_directory = "yomichan_dictionary_json_files"
    try:
        os.mkdir(build_directory)
    except FileExistsError:
        print("directory already exists")

    terms_per_file = 10000
    max_i = int(len(final_ouput) / terms_per_file) + 1
    for i in range(max_i):
        if pathlib.Path(f"{build_directory}/term_bank{i+1}.json").is_file():
            os.remove(f"{build_directory}/term_bank{i+1}.json")

        with open(
            f"{build_directory}/term_bank_{i+1}.json", "w", encoding="utf8"
        ) as f_out:
            start = terms_per_file * i
            end = terms_per_file * (i + 1)
            print(i)
            json.dump(final_ouput[start:end], f_out, indent=4, ensure_ascii=False)

    with open(f"{build_directory}/index.json", "w", encoding="utf8") as f:
        index = {
            "title": "三省堂国語辞典 第7版",
            "revision": f"sanseido7.{build_version}",
            "url": "https://github.com/aiko-tanaka/Grammar-Dictionaries/",
            "sequenced": True,
            "format": 3,
            "description": """生きのよい国語辞典『三国(サンコク)』の全面改訂版。\n\nカタカナ語から生活のことばまで約4千語を追加。\n
                            シンプルで平易な語釈によって現代語を活写する。\n類書にない項目(「スイスロール」等)や
                            最新の知見(新語・新用法の発生・普及年代を示す、「銀ぶら」の民間語源を正す)も満載。\n話しことばに〔話〕のラベルを新表示。
                            \n知らないと困る社会常識語約3千2百を新たに選定。\n新常用漢字表対応。並版を拡大し、文字サイズ約106%に。
                            \n項目数約8万2千。2色刷。""",
            "attribution": "https://www.monokakido.jp/ja/old_product/japanese/sankoku7/",
            "author": "nihongobongo",
        }
        json.dump(index, f, indent=4, ensure_ascii=False)

    zip_filename = "[Monolingual]三省堂国語辞典 第7版"
    if pathlib.Path(f"{zip_filename}_{build_version}.zip").is_file():
        os.remove(f"{zip_filename}.zip")
    shutil.make_archive(zip_filename, "zip", build_directory)


if __name__ == "__main__":
    if True:
        create_sanseido()
