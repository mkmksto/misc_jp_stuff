# -*- coding: utf-8 -*-
# Copyright: Tanaka Aiko (https://github.com/aiko-tanaka)
# License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.en.html

# parts of this code are copied from tatsumoto-ren/Ajatt-tools
# https://github.com/Ajatt-Tools/PasteImagesAsWebP/blob/main/config.py

from aqt import mw

from .consts import ADDON_PATH


def get_config() -> dict:
    cfg: dict = mw.addonManager.getConfig(__name__) or dict()

    # https://stackoverflow.com/questions/11152559/best-idiom-to-get-and-set-a-value-in-a-python-dict
    cfg["kanji_etym_field"]: str = cfg.get("kanji_etym_field", "Okjiten_Kanji_Etym")
    cfg["dong_kanji_etym_field"]: str = cfg.get(
        "dong_kanji_etym_field", "Dong_Kanji_Etym"
    )
    cfg["expression_field"]: str = cfg.get("expression_field", "Reading")
    cfg["vocab_field"]: str = cfg.get("vocab_field", "Vocab")
    cfg["force_update"]: bool = cfg.get("force_update", False)
    cfg["keybinding"]: str = cfg.get("keybinding", "")
    cfg["update_separator"]: str = cfg.get("update_separator", "<br>")
    cfg["error_tag"]: str = cfg.get("error_tag", "KanjiEtymError")
    cfg["cross_profile_name"]: str = cfg.get("cross_profile_name", "subs2srsss")

    cfg["media_debug_folder"]: str = cfg.get(
        "media_debug_folder", r"D:\TeMP\1_!_!_!_TEMP\Z_trash_Anki_media"
    )
    cfg["kanji_cache_path"]: str = cfg.get(
        "kanji_cache_path", r"D:\Libraries\Documents\MEGA\MEGAsync\000_JAP"
    )
    cfg["okjiten_cache_filename"]: str = cfg.get(
        "okjiten_cache_filename", "okjiten_cache.json"
    )

    cfg["kanjidic_folder"]: str = ADDON_PATH or cfg.get("kanjidic_folder")
    cfg["kanjidic_filename"]: str = cfg.get(
        "kanjidic_filename", "kanji_bank_complete-dict-format.json"
    )

    return cfg


config = get_config()

if __name__ == "__main__":
    import os

    print(os.path.dirname(__file__))
