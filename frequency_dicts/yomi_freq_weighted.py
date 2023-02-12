#!/usr/bin/python

import getopt
import io
import json
import math
import os
import sys
import zipfile
from collections import defaultdict

import regex as re
from epub2txt import epub2txt
from sudachipy import dictionary, tokenizer


def freq_from_files(files, weighted=True):
    CJK_PATTERN = re.compile(
        r"([\p{IsHan}\p{IsBopo}\p{IsHira}\p{IsKatakana}]+)", re.UNICODE
    )
    TOKENIZER = dictionary.Dictionary(dict_type="full").create()

    book_names_list = []
    per_book_freq = dict()

    freq = defaultdict(int)
    for i, file in enumerate(files):
        base_filename = os.path.basename(file)
        book_names_list.append(base_filename)
        print(f"{i+1}: processing {base_filename}")

        # {
        #   'book1': {'の': 2000, 'だ': 1000, 'は': 500.....},
        #   'book2': {'の': 1500, 'だ': 900, 'は': 500.....},
        # }
        per_book_freq[base_filename] = dict()

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
                per_book_freq[base_filename][token] = 0

            for token in tokens:
                if CJK_PATTERN.match(token):
                    freq[token] += 1
                    per_book_freq[base_filename][token] += 1  # my code

    # my code::
    if weighted:
        for morpheme in freq:
            weight_counter = 0
            for book in book_names_list:
                freq_in_book: dict = per_book_freq.get(book)
                freq_in_book = freq_in_book.get(
                    morpheme, 0
                )  # gets the freq of the morpheme inside the particular book, else 0
                if freq_in_book > 0:
                    weight_counter += 1

            # normalize to a range from (0 to 1)
            multiplier = weight_counter / len(book_names_list)
            old_multiplier = multiplier

            # remap to another range (0.8 to 1.2)
            min_range = 0.4
            max_range = 1.5
            distance = max_range - min_range
            multiplier = (multiplier * distance) + min_range

            new_freq = 0

            new_freq = freq[morpheme] * multiplier
            freq[morpheme] = new_freq
            # for book in book_names_list:
            #     freq_in_book: dict = per_book_freq.get(book)
            #     freq_in_book = freq_in_book.get(morpheme, 0)  # gets the freq of the morpheme inside the particular book, else 0
            #
            #     new_freq = (new_freq + freq_in_book)*multiplier
            #
            # max_size_to_original = 2  # max of how many times larger it can be than its original freq
            # min_size_to_original = 0.3
            #
            # # final value for new_freq (make sure it doesn't grow too far(high/low) from its original value)
            # if freq[morpheme] < 2000:
            #     if new_freq >= freq[morpheme]*max_size_to_original:
            #         new_freq = freq[morpheme]*max_size_to_original
            #     elif new_freq <= freq[morpheme]*min_size_to_original:
            #         new_freq = freq[morpheme]*min_size_to_original
            # else:
            #     new_freq = freq[morpheme]
            #
            # # store the new, normalized (based on frequency across diff books) frequency
            # freq[morpheme] = new_freq

    else:
        pass

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
                f"<{math.ceil(num_appearance)}>{index + 1}/{total_number_of_morphemes}",
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
        opts, folder = getopt.getopt(
            argv, "t:o:r:w", ["title=", "output=", "revision=", "weighted="]
        )
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

    weighted = True
    for opt, arg in opts:
        if opt == "-h":
            print_help_and_exit()
        elif opt in ("-t", "--title"):
            title = arg
        elif opt in ("-o", "--output"):
            output_file = arg
        elif opt in ("-r", "--revision"):
            revision = arg
        elif opt in ("-w", "--weighted"):
            weighted = False

    print(f"weighted mode?: {weighted}")

    freq = freq_from_files(files, weighted=weighted)
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
