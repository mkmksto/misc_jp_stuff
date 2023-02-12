import random
import time
import urllib.request
from html.parser import HTMLParser
from io import StringIO

import jaconv
from bs4 import BeautifulSoup
from css_parser import parseStyle
from sudachipy import dictionary, tokenizer

mode = tokenizer.Tokenizer.SplitMode.C
tokenizer_obj = dictionary.Dictionary().create()


def generate_reading(text):
    """
    Generate reading of a particular japanese text
    to import: from sudachi_wrapper import generate_reading
    """
    m = tokenizer_obj.tokenize(text, mode)

    aggr = ""
    for z in m:
        aggr += jaconv.kata2hira(z.reading_form())

    return aggr


def try_access_site(site, sleep_time=0.08, num_retries=3, wait_time=15.0, timeout=5):
    initial_time = time.time()
    time_margin = 0.02

    response = None
    try:
        response = urllib.request.urlopen(site, timeout=timeout)

    except:
        for i in range(num_retries):
            lapsed_time = time.time()
            if lapsed_time - initial_time > wait_time:
                return None

            try:
                response = urllib.request.urlopen(site, timeout=timeout)
            except:
                # does something like random.uniform(0.06, 0.10)
                sleep_time = random.uniform(
                    sleep_time - time_margin, sleep_time + time_margin
                )
                time.sleep(sleep_time)
    finally:
        return response


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


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def get_markup_structure(soup):
    content = []
    # node = {}
    for child in soup.children:
        if child.name is None:
            if child != "":
                content.append(child)
        else:
            content.append(get_markup_structure(child))
    if str(soup.name) in ["table", "tr", "td", "th"]:
        node = {"tag": soup.name}
    else:
        node = {"tag": "div"}

    attributes = get_attributes(soup.attrs)
    for key, val in attributes.items():
        node[key] = val
    if len(content) == 1:
        node["content"] = content[0]
    else:
        node["content"] = content
    return node


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
    if parsedStyle.verticalAlign != "":
        style["verticalAlign"] = parsedStyle.verticalAlign
    if parsedStyle.textDecoration != "":
        style["textDecorationLine"] = parsedStyle.textDecoration
    return


def unwrap_divs(text: str) -> str:
    soup = BeautifulSoup(text, features="html.parser")
    # for class_name in ['kijiWrp', 'kiji', 'Wrugj', 'Wrigo']:
    x = soup.find_all("div")
    for i in range(len(x)):
        soup.div.unwrap()

    return str(soup)


if __name__ == "__main__":
    # に忍びない
    print(generate_reading("と相まって"))
    print(generate_reading("に忍びない"))
    print(generate_reading("に即して"))
    print(generate_reading("に限ったことではない"))
    print(generate_reading("ないではおかない"))
