import http.server
import socketserver
import requests
import re
import json
import base64
import threading
import os
import sqlite3

from pathlib import Path
from urllib.parse import quote
from urllib.parse import unquote
from http import HTTPStatus
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from urllib.parse import parse_qs

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

HOSTNAME = "localhost"
PORT = 8775
MEDIA_DIR = "user_files"
DB_FILE = "forvo.db"


def get_program_root_path():
    script_path = os.path.realpath(__file__)
    return Path(script_path).parent


def get_db_file():
    root = get_program_root_path()
    db_file = root.joinpath(MEDIA_DIR).joinpath(DB_FILE)
    return db_file


def table_exists_and_has_data(db_file, table_name):
    if not db_file.is_file():
        return False
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        sql = "SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name = :name"
        cursor.execute(sql, {"name": table_name})
        result = cursor.fetchone()
        if int(result[0]) == 0:
            return False
        cursor.execute(f"SELECT count(*) FROM {table_name}")
        result = cursor.fetchone()
        has_data = int(result[0]) > 0
        cursor.close()
        return has_data


def init_forvo_table():
    db_file = get_db_file()
    if table_exists_and_has_data(db_file, "forvo"):
        return
    parent = Path(db_file).parent
    if not parent.is_dir():
        parent.mkdir(parents=True, exist_ok=True)
    drop_table_sql = "DROP TABLE IF EXISTS forvo"
    create_table_sql = """
       CREATE TABLE forvo (
           id integer PRIMARY KEY,
           lang text NOT NULL,
           expression text NOT NULL,
           result_type text NOT NULL,
           username text,
           filepath text NOT NULL
       );
    """
    with sqlite3.connect(db_file) as conn:
        cur = conn.cursor()
        cur.execute(drop_table_sql)
        cur.execute(create_table_sql)
        conn.commit()


def insert_record(record):
    db_file = get_db_file()
    with sqlite3.connect(db_file) as conn:
        cur = conn.cursor()
        sql = "INSERT INTO forvo (lang, expression, result_type, username, filepath) VALUES (?,?,?,?,?)"
        cur.execute(sql, record)
        conn.commit()


def find_records(lang, expression):
    records = []
    db_file = get_db_file()
    with sqlite3.connect(db_file) as conn:
        cur = conn.cursor()
        sql = "SELECT result_type, username, filepath FROM forvo WHERE lang = :lang AND expression = :expression"
        cur.execute(sql, {"lang": lang, "expression": expression})
        for row in cur.fetchall():
            if row[0] == "match":
                name = f"Forvo ({row[1]})"
            else:
                name = "Forvo Search"
            url = f"http://{HOSTNAME}:{PORT}/forvo/{quote(row[2])}"
            records.append({"name": name, "url": url})
    return records


class Forvo:
    """
    Forvo web-scraper utility class that matches YomiChan's expected output for a custom audio source
    """

    _SERVER_HOST = "https://forvo.com"
    _AUDIO_HTTP_HOST = "https://audio00.forvo.com"

    def __init__(self):
        self._set_session()

    def _set_session(self):
        """
        Sets the session with basic backoff retries.
        Put in a separate function so we can try resetting the session if something goes wrong
        """
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        # Use my personal user agent to try to avoid scraping detection
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

    def _get(self, path):
        """
        Makes a GET request assuming base url. Creates a new session if something goes wrong
        """
        url = self._SERVER_HOST + path
        try:
            return self.session.get(url, timeout=10).text

        except Exception:
            self._set_session()
            return self.session.get(url, timeout=10).text

    def set_language(self, language):
        self.language = language

    def _get_relative_path(self, url):
        return urlparse(url).path.removeprefix("/")

    def _download_audio(self, url):
        relpath = self._get_relative_path(url)
        root = get_program_root_path()
        media_dir = root.joinpath(MEDIA_DIR)
        filepath = media_dir.joinpath(relpath)
        if filepath.is_file():
            # File has already been downloaded
            return True
        print(f"Downloading {relpath}")
        parent = filepath.parent
        if not parent.is_dir():
            parent.mkdir(parents=True, exist_ok=True)
        download = self.session.get(url, timeout=10, stream=True)
        if download.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(download.content)
            return True
        else:
            print(f"Download failed for file {relpath}")
            return False

    def word(self, w):
        """
        Scrape forvo's word page for audio sources
        """
        w = w.strip()
        if len(w) == 0:
            return []

        cache = find_records(self.language, w)
        if len(cache) > 0:
            print(f"Found cached results for {w}")
            return cache

        path = f"/word/{w}/"
        html = self._get(path)
        soup = BeautifulSoup(html, features="html.parser")

        # Forvo's word page returns multiple result sets grouped by langauge like:
        # <div id="language-container-ja">
        #   <article>
        #       <ul class="show-all-pronunciations">
        #           <li>
        #              <span class="play" onclick"(some javascript to play the word audio)"></span>
        #                "Pronunciation by <span><a href="/username/link">skent</a></span>"
        #              <div class="more">...</div>
        #           </li>
        #       </ul>
        #       ...
        #   </article>
        #   <article id="extra-word-info-76">...</article>
        # </ul>
        # We also filter out ads
        results = soup.select(
            f"#language-container-{self.language}>article>ul.pronunciations-list>li:not(.li-ad)"
        )
        audio_sources = []
        for i in results:
            url = self._extract_url(i.div)
            if not self._download_audio(url):
                continue
            relpath = self._get_relative_path(url)
            username = (
                re.search(r"Pronunciation by([^(]+)\(", i.get_text(strip=True))
                .group(1)
                .strip()
            )
            insert_record((self.language, w, "match", username, relpath))
            local_url = f"http://{HOSTNAME}:{PORT}/forvo/{quote(relpath)}"
            audio_sources.append({"name": f"Forvo ({username})", "url": local_url})
        return audio_sources

    @classmethod
    def _extract_url(cls, element):
        play = element["onclick"]
        # We are interested in Forvo's javascript Play function which takes in some parameters to play the audio
        # Example: Play(786514,'OTA3Mjk2Ny83Ni85MDcyOTY3Xzc2XzExNDk0NzNfMS5tcDM=',...);return false;
        # Match anything that isn't commas, parentheses or quotes to capture the function arguments
        # Regex will match something like ["Play","786514","OTA3Mjk2Ny83Ni85MDcyOTY3Xzc2XzExNDk0NzNfMS5tcDM=", ...]
        play_args = re.findall(r"([^',\(\)]+)", play)

        # It seems that forvo has two locations for mp3, /audios/mp3 and just /mp3. I don't know what the difference
        # is so I'm just going to use the /mp3 version, which is the second argument in Play() base64 encoded
        file = base64.b64decode(play_args[2]).decode("utf-8")
        url = f"{cls._AUDIO_HTTP_HOST}/mp3/{file}"
        return url

    def search(self, s):
        """
        Scrape Forvo's search page for audio sources. Note that the search page omits the username
        """
        s = s.strip()
        if len(s) == 0:
            return []

        cache = find_records(self.language, s)
        if len(cache) > 0:
            print(f"Found cached results for {s}")
            return cache

        path = f"/search/{s}/{self.language}/"
        html = self._get(path)
        soup = BeautifulSoup(html, features="html.parser")

        # Forvo's search page returns two result sets like:
        # <ul class="word-play-list-icon-size-l">
        #   <li><span class="play" onclick"(some javascript to play the word audio)"></li>
        # </ul>
        results = soup.select("ul.word-play-list-icon-size-l>li>div.play")
        audio_sources = []

        for i in results:
            url = self._extract_url(i)
            if not self._download_audio(url):
                continue
            relpath = urlparse(url).path.removeprefix("/")
            insert_record((self.language, s, "search", None, relpath))
            local_url = f"http://{HOSTNAME}:{PORT}/forvo/{quote(relpath)}"
            audio_sources.append({"name": "Forvo Search", "url": local_url})
        return audio_sources


class ForvoHandler(http.server.SimpleHTTPRequestHandler):
    forvo = Forvo()

    # By default, SimpleHTTPRequestHandler logs to stderr
    # This would cause Anki to show an error, even on successful requests
    # log_error is still a useful function though, so replace it with the inherited log_message
    # Make log_message do nothing
    def log_error(self, *args, **kwargs):
        super().log_message(*args, **kwargs)

    def log_message(self, *args):
        pass

    def get_audio(self):
        root = get_program_root_path()
        media_dir = root.joinpath(MEDIA_DIR)
        audio_file = media_dir.joinpath(unquote(self.path).removeprefix("/forvo/"))
        if not audio_file.is_file():
            self.send_response(400)
        elif audio_file.suffix == ".mp3":
            self.send_response(200)
            self.send_header("Content-type", "text/mpeg")
            self.end_headers()
            with open(audio_file, "rb") as fh:
                self.wfile.write(fh.read())
        else:
            self.send_response(400)

    def do_GET(self):
        if self.path.startswith("/forvo/"):
            self.get_audio()
            return
        # Extract 'term' and 'reading' query parameters
        query_components = parse_qs(urlparse(self.path).query)

        language = (
            query_components["language"][0] if "language" in query_components else "ja"
        )
        term = query_components["term"][0] if "term" in query_components else ""
        # Yomichan used to use "expression" but renamed to term. Still support "expression" for older versions
        if term == "":
            term = (
                query_components["expression"][0]
                if "expression" in query_components
                else ""
            )
        reading = (
            query_components["reading"][0] if "reading" in query_components else ""
        )
        debug = query_components["debug"][0] if "debug" in query_components else False

        self.forvo.set_language(language)

        if debug:
            debug_resp = {"debug": True}
            debug_resp["reading"] = reading
            debug_resp["term"] = term
            debug_resp["word.term"] = self.forvo.word(term)
            debug_resp["word.reading"] = self.forvo.word(reading)
            debug_resp["search.term"] = self.forvo.search(term)
            debug_resp["search.reading"] = self.forvo.search(reading)
            self.wfile.write(bytes(json.dumps(debug_resp), "utf8"))
            return

        audio_sources = []

        # Try looking for word sources for 'term' first
        audio_sources = self.forvo.word(term)

        # Try looking for word sources for 'reading'
        if len(audio_sources) == 0:
            audio_sources += self.forvo.word(reading)

        # Finally use forvo search to look for similar words
        if len(audio_sources) == 0:
            audio_sources += self.forvo.search(term)

        if len(audio_sources) == 0:
            audio_sources += self.forvo.search(reading)

        # Build JSON that yomichan requires
        # Ref: https://github.com/FooSoft/yomichan/blob/master/ext/data/schemas/custom-audio-list-schema.json
        resp = {"type": "audioSourceList", "audioSources": audio_sources}

        # Writing the JSON contents with UTF-8
        payload = bytes(json.dumps(resp), "utf8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-length", str(len(payload)))
        self.end_headers()
        try:
            self.wfile.write(payload)
        except BrokenPipeError:
            self.log_error("BrokenPipe when sending reply")

        return


if __name__ == "__main__":
    # If we're not in Anki, run the server directly and blocking for easier debugging
    print("Running in debug mode...")
    init_forvo_table()
    httpd = socketserver.TCPServer((HOSTNAME, PORT), ForvoHandler)
    httpd.serve_forever()
else:
    # Else, run it in a separate thread so it doesn't block
    init_forvo_table()
    httpd = http.server.ThreadingHTTPServer((HOSTNAME, PORT), ForvoHandler)
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
