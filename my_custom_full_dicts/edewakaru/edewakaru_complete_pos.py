import json

import jp_utils

DEBUG = False


def main():
    term_bank_with_incomplete_pos = "term_bank_4.json"
    with open(term_bank_with_incomplete_pos, "r", encoding="utf8") as f_in:
        data_in: list = json.load(f_in)

    for idx, line in enumerate(data_in):
        jp_utils.create_foosoft_pos_map()
        yomi_pos = jp_utils.get_foosoft_pos(line[0])
        data_in[idx][3] = yomi_pos

    with open("term_bank_4_new.json", "w", encoding="utf8") as f_out:
        json.dump(data_in, f_out, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
