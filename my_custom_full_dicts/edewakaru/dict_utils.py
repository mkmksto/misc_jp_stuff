import json
import os
import pathlib
import shutil


def create_dictionary(
    final_list: list,
    terms_per_file: int,
    debug: bool,
    build_version: str,
    dict_name: str,
    dict_revision: str,
    dict_description: str,
    dict_attribution: str,
    test_name: str = "",
) -> None:
    """
    Create yomichan json files and zip them to an archive

    Args:
        final_list      :   final list of words and definitions in yomichan format
        terms_per_file  :   num of max terms per term_bank.json
        debug           :   True if currently testing, False for final builds
        build_version   :   version control
        dict_attribution:   URL to main page of the dictionary
        test_name       :   test name to be appended (e.g. TEST0)
    """
    print("creating dictionary")
    build_version = build_version

    if debug:
        test_name = test_name

    build_directory = f"yomichan_dictionary_json_files_{build_version}{test_name}"
    try:
        os.mkdir(build_directory)
    except FileExistsError:
        print("directory already exists")

    terms_per_file = terms_per_file
    max_i = int(len(final_list) / terms_per_file) + 1
    for i in range(max_i):
        if pathlib.Path(f"{build_directory}/term_bank{i+1}.json").is_file():
            os.remove(f"{build_directory}/term_bank{i+1}.json")

        with open(
            f"{build_directory}/term_bank_{i+1}.json", "w", encoding="utf8"
        ) as f_out:
            start = terms_per_file * i
            end = terms_per_file * (i + 1)
            print(f"creating term_bank_{i+1}.json")
            json.dump(final_list[start:end], f_out, indent=4, ensure_ascii=False)

        with open(f"{build_directory}/index.json", "w", encoding="utf8") as f:
            index = {
                "title": f"{dict_name}{test_name}",
                "revision": f"{dict_revision}.{build_version}",
                "url": "https://github.com/aiko-tanaka/Grammar-Dictionaries/",
                "sequenced": True,
                "format": 3,
                "description": f"{dict_description}",
                "attribution": f"{dict_attribution}",
                "author": "nihongobongo",
            }
            json.dump(index, f, indent=4, ensure_ascii=False)

        zip_filename = f"[Grammar] {dict_name}{build_version}{test_name}"
        if pathlib.Path(f"{zip_filename}.zip").is_file():
            os.remove(f"{zip_filename}.zip")
        shutil.make_archive(f"{zip_filename}", "zip", build_directory)
