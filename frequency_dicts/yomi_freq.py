#!/usr/bin/python

import getopt
import io
import json
import os
import sys
import zipfile
from collections import defaultdict

import regex as re
from epub2txt import epub2txt
from sudachipy import dictionary, tokenizer


def freq_from_files(files):
    CJK_PATTERN = re.compile(
        r"([\p{IsHan}\p{IsBopo}\p{IsHira}\p{IsKatakana}]+)", re.UNICODE
    )
    TOKENIZER = dictionary.Dictionary(dict_type="full").create()

    freq = defaultdict(int)
    for i, file in enumerate(files):
        print(f"{i+1}: processing {os.path.basename(file)}")
        if file.endswith(".epub"):
            lines = [
                line + "。"
                for content in epub2txt(file, outputlist=True)
                for line in content.split("。")
            ]
        else:
            lines = open(file, "r", encoding="UTF-8")

        for line in lines:
            tokens = [
                morpheme.dictionary_form()
                for morpheme in TOKENIZER.tokenize(
                    line, tokenizer.Tokenizer.SplitMode.B
                )
            ]

            for token in tokens:
                if CJK_PATTERN.match(token):
                    freq[token] += 1
    return freq


def freq_to_zip(freq, output_file, title, revision):
    total_number_of_morphemes = len(freq.keys())
    term_meta_bank = []
    for index, morpheme in enumerate(sorted(freq, key=freq.get, reverse=True)):
        num_appearance = freq[morpheme]
        term_meta_bank.append(
            [
                morpheme,
                "freq",
                f"<{num_appearance}>{index + 1}/{total_number_of_morphemes}",
            ]
        )

    index_dict = {"title": title, "format": 3, "revision": f"frequency{revision}"}

    with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("index.json", json.dumps(index_dict, ensure_ascii=False))
        zip_file.writestr(
            "term_meta_bank_1.json", json.dumps(term_meta_bank, ensure_ascii=False)
        )


def print_help_and_exit():
    print(
        f"{sys.argv[0]} -t <title in yomichan> -o <output file> -r <revision> input_files"
    )
    sys.exit()


def main2(argv):
    try:
        # folder = folder located on the same directory as this script containing all the files (txt and epubs)
        opts, folder = getopt.getopt(argv, "t:o:r:", ["title=", "output=", "revision="])
    except getopt.GetoptError:
        sys.exit(2)

    curdir = os.path.dirname(os.path.realpath(__file__))
    subs_dir = os.path.join(curdir, str(folder[0]))
    files = [os.path.join(subs_dir, filename) for filename in os.listdir(subs_dir)]

    if len(files) > 1000:
        print("too many files, reduce and try again")
        print_help_and_exit()

    if len(files) < 1:
        print_help_and_exit()

    print(f"processing {len(files)} files")

    revision = "1"
    first_file = files[0]

    pathname, extension = os.path.splitext(first_file)
    title = pathname.split("/")[-1]
    output_file = f"{title}.zip"

    for opt, arg in opts:
        if opt == "-h":
            print_help_and_exit()
        elif opt in ("-t", "--title"):
            title = arg
        elif opt in ("-o", "--output"):
            output_file = arg
        elif opt in ("-r", "--revision"):
            revision = arg

    freq = freq_from_files(files)
    print("creating zip file....")
    freq_to_zip(freq, output_file, title, revision)


def main(argv):
    try:
        opts, files = getopt.getopt(argv, "t:o:r:", ["title=", "output=", "revision="])
    except getopt.GetoptError:
        sys.exit(2)

    if len(files) < 1:
        print_help_and_exit()

    revision = "1"
    first_file = files[0]

    pathname, extension = os.path.splitext(first_file)
    title = pathname.split("/")[-1]
    output_file = f"{title}.zip"

    for opt, arg in opts:
        if opt == "-h":
            print_help_and_exit()
        elif opt in ("-t", "--title"):
            title = arg
        elif opt in ("-o", "--output"):
            output_file = arg
        elif opt in ("-r", "--revision"):
            revision = arg

    freq = freq_from_files(files)
    freq_to_zip(freq, output_file, title, revision)


if __name__ == "__main__":
    main2(sys.argv[1:])
    # curdir = os.path.dirname(os.path.realpath(__file__))
    # subs_dir = os.path.join(curdir, 'Darker_Than_Black')
    # files = [os.path.join(subs_dir, filename) for filename in os.listdir(subs_dir)]
    # print(curdir)
    # print(subs_dir)
    # print(files)

# Refactored Aa's yomichan frequency python script to take command line arguments and supports multiple raw txt and epub (may not work with all) files!
# The frequency format is still the same <rank>/<total words>.
# python3/pip required dependencies: pip install regex epub2txt sudachipy sudachidict_full
# To run python yomifreq.py -t <title in yomichan> -o <output file> -r <revision> <files...>

# Some examples:
# python yomifreq.py eustia.txt
# will create an eustia.zip and will appear as eustia in Yomichan.

# python yomifreq.py -t MyBooks -o mybooksfreq.zip mommyln1.epub mommyln2.epub raw.txt
# will create a mybooksfreq.zip and will appears as MyBooks in Yomichan.

# folder use:
# python yomifreq.py -t oregairu -o oregairu.zip Yahari
# python yomifreq.py -t DTB -o dtb.zip Darker_Than_Black


# my uses: (OLDER USE, deprecated!)
# python yomifreq.py -t BB連続 -o bbcases.zip bbcases.txt
# python yomifreq.py -t DNBBandMain -o deathnote.zip bbcases.txt dn-combined.txt
