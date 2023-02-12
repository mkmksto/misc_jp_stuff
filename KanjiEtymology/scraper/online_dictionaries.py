# -*- coding: utf-8 -*-
# Copyright: Tanaka Aiko (https://github.com/aiko-tanaka)
# License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html

"""
Online dictionaries and their respective JSON cache methods (if there are any)
"""

import json
import os
import time
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup

from .config import config
from .offline_dictionaries import kanjidic2_info, offline_kanji_info
from .utils import calculate_time, speed_logger, try_access_site


@calculate_time
def tangorin_kanji_info(kanji: str) -> str:
    """
    Usage:
        To be used inside okjiten_etymology
    Args:
        Takes in a single kanji ONLY, not a list
    Returns:
        str: The english definition for the specified Kanji
    """
    response = try_access_site(
        site="https://tangorin.com/kanji?search={}".format(
            urllib.parse.quote(kanji.encode("utf-8"))
        ),
        num_retries=1,
        wait_time=4.0,
        timeout=1.5,
    )
    if response:
        soup = BeautifulSoup(response, features="html.parser")
    else:
        return ""
    if soup:
        en_definitions = soup.find("p", attrs={"class": "k-meanings"})
    else:
        return ""
    if en_definitions:
        en_definitions = en_definitions.get_text().strip()
    else:
        return ""

    try:
        en_definitions = en_definitions.split("; ")
        # limit num of definitions to only 3 definitions
        if len(en_definitions) > 3:
            en_definitions = en_definitions[:3]
            en_definitions = "; ".join(en_definitions)
        else:
            en_definitions = "; ".join(en_definitions)
    except:
        pass

    return en_definitions if en_definitions else ""


@calculate_time
def dong_etymology(kanji_set):
    """
    Usage: dong_etymology(extract_kanji(sample_vocab))
    Returns a Single string separated by break lines of all etymologies of the kanji set it is fed

    Args:
        List/Set of Kanji
    Returns:
        String of Etymologies per Kanji
    """
    full_etymology_list = ""
    for kanji in kanji_set:
        site = f'https://www.dong-chinese.com/dictionary/{urllib.parse.quote(kanji.encode("utf-8"))}'

        # try waiting for a while if website returns an error
        response = ""
        response = try_access_site(site=site, sleep_time=0.05)

        soup = BeautifulSoup(response, features="html.parser")
        soup_text = str(soup)

        # get only the relevant JS part of dong-chinese which is formatted as a JSON
        soup_text = (
            soup_text.split('<script>window["')[-1]
            .split("__sink__charData_")[-1]
            .split("]=")[-1]
        )
        # returns a pure JSON object
        soup_text = soup_text.split(";</script>")[0]

        dong_text_not_found = '"error":"Word not found"'

        # not and error, i.e. something was actually found inside dong
        if not (dong_text_not_found in soup_text):
            # turn into JSON and parse
            soup_json = json.loads(soup_text)

            try:
                etymology = soup_json["hint"]
            # usually KeyError
            except Exception as e:
                etymology = ""

            try:
                # <div class="MuiGrid-root MuiGrid-item MuiGrid-grid-xs-12" style="padding:8px">
                definition = soup.find(
                    "div",
                    attrs={
                        "class": "MuiGrid-root MuiGrid-item MuiGrid-grid-xs-12",
                        "style": "padding:8px",
                    },
                )
                definition = (
                    str(definition)
                    .split("<span><span><span>")[-1]
                    .split("</span></span><a href=")[0]
                )

                # get only one keyword from the many keywords separated by ; and or ,
                if ";" in definition:
                    definition = definition.split("; ")[0]
                    if "," in definition:
                        definition = definition.split(", ")[0]
                elif "," in definition:
                    definition = definition.split(", ")[0]

            except Exception as e:
                definition = ""

            try:
                decomposition = soup_json["components"]
            except Exception as e:
                decomposition = ""

            # concatenate the strings
            concat_str = "<b>{}</b>".format(kanji)
            full_etymology_list += concat_str

            if definition:
                add_str = "({}): ".format(definition)
                full_etymology_list += add_str
            else:
                full_etymology_list += ": "

            if etymology:
                full_etymology_list += etymology

            # decomposition is a list of DICT objects
            # e.g. "components":[  {"character":"木","type":["iconic"],"hint":null},
            # {"character":"◎","type":["iconic"],"hint":"Depicts roots."}   ]
            if decomposition:
                # decom_json_list = [json.loads(decom) for decom in decomposition]
                for decom in decomposition:
                    try:
                        char = str(decom["character"])
                    except Exception as e:
                        char = ""

                    try:
                        func = str(decom["type"])
                    except Exception as e:
                        func = ""

                    try:
                        hint = str(decom["hint"])
                    except:
                        hint = ""

                    add_str_decom = " [{}-{}-{}]".format(char, func, hint)
                    full_etymology_list += add_str_decom

            # \n when testing inside pycharm, <br> when inside Anki

            full_etymology_list += "<br>"
            if __name__ == "__main__":
                full_etymology_list += "\n"

    # print(full_etymology_list)
    return full_etymology_list


@calculate_time
def okjiten_cache(
    kanji: str = None, kanji_info_to_save: dict = None, save_to_dict=False
) -> dict or None:
    """
    JSON dict cache

    File formatting:
    The key is the okjiten site index (NOT ANYMORE)

    Just use the kanji itself as the key, they're unique anyway
    {
        '夢':     {
                    'kanji': '夢',
                    'definition': 'dream',
                    'online_img_url': ....
                  },
        '本':     {'kanji': '本', 'definition': 'book', 'online_img_url': ....}
        .....
    }

    checks if a certain kanji's okjiten formatting is already inside the JSON dict
    If there is, then return it

    If there isn't then, wait for the querying to finish and sive it inside the JSON
    Args:
        kanji
        kanji_info_to_save: dict of the kanji info to save
        mode:               (mode 1 = check, mode 2 = write)
    Returns:
        if mode 1:      JSON-formatted okjiten definition
        if mode 2:      none (only saves the JSON to the dictionary)
    """
    kanji_cache_path = config.get("kanji_cache_path")
    okjiten_cache_filename = config.get("okjiten_cache_filename")

    # TODO: overwrite specific kanji info if update is set to true
    force_update = config.get("force_update")
    full_path = os.path.join(kanji_cache_path, okjiten_cache_filename)

    # create a JSON file if it doesn't exist
    if not os.path.isfile(full_path):
        with open(full_path, "w") as fh:
            json.dump({}, fh)

    # (mode 2)
    if save_to_dict:
        json_formatted_info = {kanji: kanji_info_to_save}

        # https://stackoverflow.com/questions/18980039/how-to-append-in-a-json-file-in-python
        with open(full_path, "r", encoding="utf8") as fh:
            data: dict = json.load(fh)

        # https://www.programiz.com/python-programming/methods/dictionary/update
        # https://stackoverflow.com/questions/29694826/updating-a-dictionary-in-python
        # you can use a tuple to update a dict with key-val pairs
        try:
            data.pop(kanji)
        except KeyError:
            pass
        data.update(json_formatted_info)

        # https://stackoverflow.com/questions/18337407/saving-utf-8-texts-with-json-dumps-as-utf8-not-as-u-escape-sequence
        with open(full_path, "w", encoding="utf8") as fh:
            json.dump(data, fh, indent=4, ensure_ascii=False, separators=(",", ": "))

    # (mode 1)
    else:
        # check cache if the kanji exists, if it does, return it

        # the return is none, pass 'True' inside okjiten_cache(save_to_dict)
        # from where it is called
        try:
            with open(full_path, "r", encoding="utf8") as fh:
                try:
                    cache: dict = json.load(fh)

                    result = cache.get(kanji)
                    if result:
                        return result
                    else:
                        return None

                except json.decoder.JSONDecodeError:
                    return None
        except:
            raise


@calculate_time
def okjiten_etymology(kanji_set: list) -> list:
    """
    Usage: okjiten_etymology(extract_kanji(sample_vocab))

    Note: this won't return the image itself, only the online source and its anki src format
    You'll have to use download_image() wherever your main funciton is

    Also, won't return a neat string, you have to format it yourself to turn it into a string
    why? because the return can be neatly stored in a JSON file for chaching/querying

    you then loop through the result like:

    for res in result_list:
        kanji       = res['kanji']
        etymology   = res['etymology_text']
        etc...

    Args:
        List/Set of Kanji

    Returns:
        LIST of JSONs/Dicts
        each JSON/dict containing: (as dict properties)
            name/kanji itself       :   kanji
            definition              :   kanji definition
            online image URL        :   online_img_url
            anki image src URL      :   anki_img_url
            etymology_text          :   etymology_text
            src                     :   okijiten (constant) - for use when searching JSON files
            onyomi
            kunyomi
            bushu
    """

    result_list = []

    for kanji in kanji_set:
        initial_time = time.time()
        speed_logger.info(f"--- (1) START K:{kanji} initial time : 0 ---")

        indiv_kanji_info = dict()

        cache: dict = okjiten_cache(kanji, save_to_dict=False)
        # checks that cache isn't empty and that all cache items have a value
        # if at least one key doesn't have a value, the program will continue in order
        # for the cache to be updated

        # if len != 9, then some info might be missing so update the missing info
        if cache is not None and all(cache.values()) and len(cache) == 9:
            result_list.append(cache)
            continue
        speed_logger.info(f"--- after cache : {time.time() - initial_time} ---")

        sites = [
            "https://okjiten.jp/10-jyouyoukanjiitiran.html",
            "https://okjiten.jp/8-jouyoukanjigai.html",  # (kanken pre-1 and 1)
            "https://okjiten.jp/9-jinmeiyoukanji.html",
        ]

        for site in sites:
            original_site = site
            try:
                site = cache.get("scraped_from") if cache else original_site
            except AttributeError:
                site = original_site

            response = ""
            response = try_access_site(site)
            if not response:
                continue
            speed_logger.info(
                f"--- (2) K:{kanji} after response = try_access_site({site})"
                f" : {round(time.time() - initial_time, 5)} ---"
            )

            soup = BeautifulSoup(response, features="html.parser")
            if kanji in str(soup) and soup:
                indiv_kanji_info["kanji"] = kanji

                definition_cache = ""
                try:
                    definition_cache = cache.get("definition") if cache else ""
                except AttributeError:
                    definition_cache = ""
                if not definition_cache:
                    definition_cache = kanjidic2_info(kanji)
                if not definition_cache:
                    definition_cache = tangorin_kanji_info(kanji)
                if not definition_cache:
                    definition_cache = offline_kanji_info(kanji) or ""
                    if definition_cache:
                        definition_cache = definition_cache.get("meaning", "")

                indiv_kanji_info["definition"] = definition_cache or ""

                # very important: add the site if it matched, this way, the next time this func runs
                # we won't have to run through all 3 sites just to get to the kanji
                indiv_kanji_info["scraped_from"] = site

                speed_logger.info(
                    f"--- (3) K: {kanji} after indiv_kanji_info['scraped_from']"
                    f" : {round(time.time() - initial_time, 5)} ---"
                )
                # for some stupid reason, it can't match for kanji like 参, but will match its kyuujitai 參
                # TODO, if exception, try searching for its kyuujitai counterpart, look for a website that does that
                # or might be nvm because for some reason it werks now

                found = None
                try:
                    href = cache.get("actual_page")
                except AttributeError:
                    found = soup.find("a", text=kanji)
                    if found:
                        href = found.get("href")  # returns a str
                if not href:
                    continue

                href = "https://okjiten.jp/{}".format(href)
                indiv_kanji_info["actual_page"] = href

                kanji_page = try_access_site(href)
                if kanji_page:
                    kanji_soup = BeautifulSoup(kanji_page, features="html.parser")
                else:
                    continue

                speed_logger.info(
                    f"--- (4) K: {kanji} after kanji_page = try_access_site({href})"
                    f" : {round(time.time() - initial_time, 5)} ---"
                )

                tables = kanji_soup.find_all("td", attrs={"colspan": 12})
                if not tables:
                    continue

                ### ------------------------ START (1) ------------------------
                ### (1) scrape the 成り立ち image table

                # https://github.com/rgamici/anki_plugin_jaja_definitions/blob/master/__init__.py#L86
                # https://beautiful-soup-4.readthedocs.io/en/latest/
                # tables will be reused in the other scrapers

                # len(TABLES) == 3 ALWAYS!
                for table in tables:
                    kanji_soup = table.find("td", attrs={"height": 100})
                    if kanji_soup:
                        break

                etymology_image_src = kanji_soup.find("img")
                try:
                    etymology_image_src = etymology_image_src.get("src")
                except AttributeError:
                    etymology_image_src = ""

                if etymology_image_src:
                    etymology_image_url = "https://okjiten.jp/{}".format(
                        etymology_image_src
                    )

                    # use image_filename for downloading and storing the media
                    # add _ before img filename before anki keeps deleting these GIFs
                    # could be because I use them inside a JS script
                    image_filename = "_okijiten-{}".format(etymology_image_src)
                    anki_image_src = '<img src = "{}">'.format(image_filename)

                    indiv_kanji_info["image_filename"] = image_filename
                    indiv_kanji_info["online_img_url"] = etymology_image_url
                    indiv_kanji_info["anki_img_url"] = anki_image_src

                speed_logger.info(
                    f"--- (5) K: {kanji} after scrape the 成り立ち image table"
                    f" : {round(time.time() - initial_time, 5)} ---"
                )
                ### ------------------------ END (1) ------------------------
                # TODO: scrape the image and put it inside the media folder, try to resize it if u can

                ### ------------------------ START (2) ------------------------
                ### (2) scrape the 成り立ち text table / usually https://okjiten.jp/{}#a
                # do a findall and the etym text is always the 3rd table row from the top, etc., this is always the same
                # the 3rd table - TABLES[2] always contains the main content

                def_text = ""

                etymology_text_cache = ""
                try:
                    etymology_text_cache = cache.get("etymology_text")
                except AttributeError:
                    etymology_text_cache = ""

                if not etymology_text_cache:
                    main_body = tables[2]
                    th = main_body.find("th", attrs={"align": "left"})

                    if th:
                        th = BeautifulSoup(str(th), features="html.parser")
                        etymology = th.get_text().strip()
                        etymology = "".join(etymology.split())
                        etymology = etymology.replace("※", "<br>")  # for anki

                        def_text += etymology

                    else:
                        # there are cases where len(th)==0, usually it uses a td instead of a th
                        # sample: https://okjiten.jp/kanji1408.html(脅)
                        # in such cases, just go through every tr, and find what is relevant

                        # http://nihongo.monash.edu/kanjitypes.html (6 kanji types) (only 4 are on the site)
                        kanji_class = [
                            "象形文字",  # pictographs/hieroglyphs
                            "指事文字",  # "logograms", "simple ideographs", representation of abstract ideas
                            "会意文字",  # compound ideograph e.g. 休 (rest) from 人 (person) and 木 (tree
                            "会意兼形声文字",  # compound ideo + phono-semantic at the same time
                            "形声文字",  # semasio-phonetic"
                            "国字",
                        ]  # check last, not usually found at the start of the sentence, but inside

                        tr = main_body.find_all("tr")
                        # tr[7] is usually the .gif for the etymology image, tr[8] is etymology text

                        if tr:
                            etymology = tr[8]

                            etymology = BeautifulSoup(
                                str(etymology), features="html.parser"
                            )
                            etymology = etymology.get_text().strip()

                            if etymology and any(
                                class_ in etymology for class_ in kanji_class
                            ):
                                etymology = "".join(etymology.split())
                                etymology = etymology.replace("※", "<br>")  # for anki
                                def_text += etymology

                indiv_kanji_info["etymology_text"] = def_text or etymology_text_cache
                indiv_kanji_info["src"] = "okijiten"

                speed_logger.info(
                    f"--- (6) after scrape the 成り立ち TEXT table"
                    f" : {round(time.time() - initial_time, 5)} ---"
                )
                ### ------------------------ END (2) ------------------------

                # TODO
                ### (3) scrape the 読み table / usually https://okjiten.jp/{}#b
                # TODO
                ### (4) scrape the 部首 table / usually https://okjiten.jp/{}#c

                result_list.append(indiv_kanji_info)

                log_bool2 = log_bool3 = False
                if cache is None:
                    okjiten_cache(
                        kanji=kanji,
                        kanji_info_to_save=indiv_kanji_info,
                        save_to_dict=True,
                    )
                elif cache and len(cache) != len(indiv_kanji_info):
                    log_bool2 = True
                    okjiten_cache(
                        kanji=kanji,
                        kanji_info_to_save=indiv_kanji_info,
                        save_to_dict=True,
                    )
                elif cache and any(
                    cache[key] != indiv_kanji_info[key] for key, value in cache.items()
                ):
                    log_bool3 = True
                    okjiten_cache(
                        kanji=kanji,
                        kanji_info_to_save=indiv_kanji_info,
                        save_to_dict=True,
                    )

                speed_logger.info(
                    f"--- (7) END: after adding to cache if needed"
                    f"-- cache exists? : {bool(cache)} --"
                    f" len(cache) != len(indiv_kanji_info)? : {log_bool2} --"
                    f" any(cache[key] != indiv_kanji_info[key]?: {log_bool3} --"
                    f" : {round(time.time() - initial_time, 5)} ---"
                )

                # break out for site for sites loop -> if kanji in str(soup) and soup:
                # because if the kanji is inside the site, no need to go over the other sites
                # as such this for loop only runs one if the kanji is within the site at first try
                break

    # print(result_dict['online_img_url'])
    return result_list


if __name__ == "__main__":
    sample_vocab = (
        "参夢紋脅"  # 統參参夢紋泥恢疎姿勢'  # 自得だと思わないか' #！夢この前、あの姿勢のまま寝てるの見ましたよ固執流河麻薬所持容疑'
    )
    from pprint import pprint

    # fids = [{'vocab_field': '参夢'},{'vocab_field': '紋脅'}]
    # regen = Regen(fids=fids)
    # res = regen.generate()
    # pprint(res)

# okjiten_cache(save_to_dict=False)
