import json
import os
import re
from collections import defaultdict
from os import path
from pathlib import Path
from subprocess import Popen, call

from bs4 import BeautifulSoup

try:
    from tqdm.auto import tqdm
except ImportError:

    def tqdm(x, *arg, **kwargs):
        return x


word = re.compile("[\s\n]*")
re_nl = re.compile("[ \n\t]+")

zhtml_dir = "./zhtml"
html_dir = "./html"
txt_dir = "./txt"
parse_dir = "./parse"
freq_dic_dir = "./freq_dict"
dic_dir = "./dictionary"
extract_dic_dir = "./extract_dic_dir"
text_dic_dir = "./text_dic_dir"
dict_parse_text_dir = "./dict_parse_text_dir"
for i in [
    txt_dir,
    zhtml_dir,
    html_dir,
    parse_dir,
    freq_dic_dir,
    extract_dic_dir,
    text_dic_dir,
    dict_parse_text_dir,
]:
    i = Path(i)
    i.mkdir(exist_ok=True)


def read_jumanpp(fn):
    res = []
    originals = []
    acc = []
    original = []
    with open(fn) as fd:
        for i in map(str.strip, fd):
            if i == "EOS":
                if len(acc) > 0:
                    res.append(acc)
                    originals.append(original)
                    original = []
                    acc = []
            elif i == "*":
                continue
            else:
                i = [j for j in i.split() if len(j) > 0]

                acc.append(i[2])
                original.append(i[0])
    return res, originals


class yomi_dict:
    def __init__(self, filename, dir=dic_dir):
        filename = path.splitext(filename)[0]
        self.file = path.join(dir, filename)
        self.filename = filename
        self.extract_dir = path.join(extract_dic_dir, filename)
        self.dict_text = path.join(text_dic_dir, filename)
        self.dict_parse_text = path.join(dict_parse_text_dir, filename)

    def extract(self):
        if path.exists(self.extract_dir):
            return
        call(["unzip", self.file, "-d", self.extract_dir])

    def convert_to_text(self):
        if path.exists(self.dict_text):
            return
        self.extract()
        words = []
        with open(self.dict_text, "w") as fd:
            for i in os.listdir(self.extract_dir):
                if re.match("term_bank_\d+\.json", i) is None:
                    continue
                with open(path.join(self.extract_dir, i)) as dict_part:
                    part = json.load(dict_part)
                for i in part:
                    words.append(i[0])
                    if len(i[1].strip()) > 0:
                        words.append(i[1])
            words = set(words)
            for w in words:
                fd.write(w)
                fd.write("\n")

    def pare_text(self):
        if path.exists(self.dict_parse_text):
            return
        self.convert_to_text()
        with open(self.dict_parse_text, "w") as output:
            with open(self.dict_text) as input:
                call("jumanpp", stdin=input, stdout=output)

    def load_words(self):
        self.pare_text()
        self.words, self.originals = read_jumanpp(self.dict_parse_text)
        return self


with open(path.join(freq_dic_dir, "index.json"), "w") as fd:
    fd.write('{"title":"Freq","format":3,"revision":"frequency1"}')


class book:
    def __init__(self, filename, dir="."):
        self.file = path.join(dir, filename)
        self.filename = filename[:-5]
        self.zhtml_file = path.join(zhtml_dir, self.filename + ".htmlz")
        self.html_dir = path.join(html_dir, self.filename)
        self.txt_file = path.join(txt_dir, self.filename + ".txt")
        self.clean_html_file = path.join(self.html_dir, "clean-index.html")
        self.parse_file = path.join(parse_dir, self.filename + ".parse")

    def htmlz(self):
        if not path.exists(self.zhtml_file):
            call(["ebook-convert", self.file, self.zhtml_file])

    def html(self):
        if path.exists(self.html_dir):
            return
        self.htmlz()
        call(["unzip", self.zhtml_file, "-d", self.html_dir])

    def clean_html(self):
        if path.exists(self.clean_html_file):
            return

        self.html()
        with open(path.join(self.html_dir, "index.html")) as fd:
            soup = BeautifulSoup(fd.read())
        for rt in soup.find_all("rt"):
            rt.extract()
        for ruby in soup.find_all("ruby"):
            if ruby.string is None:
                s = "".join(ruby.strings)
            else:
                s = ruby.string
            s = word.sub("", s)
            ruby.replace_with(s)
        with open(self.clean_html_file, "w") as file:
            file.write(str(soup))

    def txt(self):
        if path.exists(self.txt_file):
            return
        self.clean_html()
        call(["ebook-convert", self.clean_html_file, self.txt_file])

    def parse(self):
        self.txt()
        if path.exists(self.parse_file):
            return
        txt_file = open(self.txt_file)
        parse_file = open(self.parse_file, "w")
        call("jumanpp", stdin=txt_file, stdout=parse_file)

    def load_parse(self):
        self.parse()
        with open(self.parse_file) as fd:
            lines = [[j for j in re_nl.split(i.strip()) if len(j) > 0] for i in fd]
        lines = [i for i in lines if len(i) > 0 and i[0] != "EOS"]
        self.words = [i[2] for i in lines]


def add_to_count(arr, d):
    for i in arr:
        d[i] = d[i] + 1


class dict_trie:
    def __init__(self, data):
        self.root = dict()
        self.add_data(data)

    def add_data(self, data):
        for ks, v in data:
            r = self.root
            for k in ks:
                if k not in r:
                    n = r[k] = dict()
                else:
                    n = r[k]
                r = n
            r["final"] = v

    def find(self, ks):
        r = self.root
        try:
            for k in ks:
                r = r[k]
            return r["final"]
        except KeyError as e:
            return None


if __name__ == "__main__":
    freq_counter = defaultdict(lambda: 0)
    dic_freq_counter = dict()
    word_occurences = defaultdict(lambda: [])
    books = []
    dicts = [yomi_dict(i).load_words() for i in os.listdir(dic_dir)]
    print("loaded dicts")
    for index, i in enumerate(os.listdir("books")):
        b = book(i, dir="./books")
        b.load_parse()
        add_to_count(b.words, freq_counter)
        for j_index, j in enumerate(b.words):
            word_occurences[j].append((index, j_index))
        books.append(b)
    print("loaded books")
    for d in dicts:
        for words, stems in tqdm(zip(d.originals, d.words), total=len(d.words)):
            word = "".join(words)
            if word in dic_freq_counter:
                continue
            c = 0
            if stems[0] not in word_occurences:
                continue
            for b_id, loc in word_occurences[stems[0]]:
                has = True
                for i in range(len(stems)):
                    if books[b_id].words[loc + i] != stems[i]:
                        has = False
                        break
                if has:
                    c += 1
            dic_freq_counter[word] = c
    for w, f in freq_counter.items():
        if w not in dic_freq_counter:
            dic_freq_counter[w] = f

    with open(
        path.join(freq_dic_dir, "term_meta_bank_1.json"), "w", encoding="utf8"
    ) as fd:
        res = [
            [key, "freq", value]
            for (key, value) in sorted(
                dic_freq_counter.items(), key=lambda x: x[1], reverse=True
            )
            if value > 0
        ]
        json.dump(res, fd, ensure_ascii=False)
    call(["rm", "freq.zip"])
    call(
        [
            "zip",
            "-j",
            "freq.zip",
            path.join(freq_dic_dir, "index.json"),
            path.join(freq_dic_dir, "term_meta_bank_1.json"),
        ]
    )
