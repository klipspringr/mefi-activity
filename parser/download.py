import argparse
from datetime import datetime
import json
import os
import re
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile

from config import HEADERS, INFODUMP_BASE_URL, INFODUMP_HOMEPAGE, SITES, KEY_TIMESTAMP
from parse import parse


def get_publication_timestamp():
    with urlopen(Request(INFODUMP_HOMEPAGE, headers=HEADERS)) as f:
        contents = f.read().decode("utf-8")
        raw_date = re.search("Last updated: <b>(.+)</b>", contents).group(1).strip()
        return datetime.strptime(raw_date, "%a %b %d %H:%M:%S %Y").strftime(
            "%-d %B %Y %H:%M"
        )


def download_file(filename, infodump_dir):
    url = INFODUMP_BASE_URL + filename + ".txt.zip"
    print(f"Download and extract {url}")
    with urlopen(Request(url, headers=HEADERS)) as f:
        with ZipFile(BytesIO(f.read())) as zip:
            zip.extract(filename + ".txt", infodump_dir)


def download_infodump(force_parse, infodump_dir, output_path):
    publication_timestamp = get_publication_timestamp()

    download_required = True

    if os.path.exists(output_path):
        with open(output_path, "r") as f:
            last_json = json.load(f)
            if (
                KEY_TIMESTAMP in last_json
                and last_json[KEY_TIMESTAMP] == publication_timestamp
            ):
                print("No new infodump")
                download_required = False

    if download_required:
        print("Download infodump")
        if not os.path.exists(infodump_dir):
            print(f"Create dir {infodump_dir}")
            os.mkdir(infodump_dir)
        else:
            print(f'Delete "{infodump_dir}/*.txt"')
            for txt in Path(infodump_dir).glob("*.txt"):
                txt.unlink()

        download_file("usernames", infodump_dir)
        for site in SITES:
            download_file(f"postdata_{site}", infodump_dir)
            download_file(f"commentdata_{site}", infodump_dir)

    if download_required or force_parse:
        print(f'Parsing data from "{infodump_dir}" to "{output_path}"')
        parse(infodump_dir, output_path, publication_timestamp)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--force-parse", action="store_true")
    parser.add_argument("infodump_dir")
    parser.add_argument("output_path")
    args = parser.parse_args()
    download_infodump(args.force_parse, args.infodump_dir, args.output_path)
