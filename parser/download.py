import argparse
import json
import os
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile

from config import INFODUMP_BASE_URL, INFODUMP_HOMEPAGE, KEY_TIMESTAMP, SITES
from parse import parse


def get_publication_timestamp():
    with urlopen(INFODUMP_HOMEPAGE) as f:
        contents = f.read().decode("utf-8")
        raw_date = re.search("Last updated: <b>(.+)</b>", contents).group(1).strip()
        return datetime.strptime(raw_date, "%a %b %d %H:%M:%S %Y").strftime(
            "%-d %B %Y %H:%M"
        )


def download_file(filename, infodump_dir, user_agent):
    url = INFODUMP_BASE_URL + filename + ".txt.zip"
    print(f"Download and extract {url}")
    headers = {}
    if user_agent is not None:
        headers["User-Agent"] = user_agent
    with urlopen(Request(url, headers)) as f:
        with ZipFile(BytesIO(f.read())) as zip:
            zip.extract(filename + ".txt", infodump_dir)


def download_infodump(dev, infodump_dir, output_path, user_agent):
    download_required = True
    publication_timestamp = get_publication_timestamp()

    if os.path.exists(output_path):
        with open(output_path, "r") as f:
            last_json = json.load(f)
            if (
                KEY_TIMESTAMP in last_json
                and last_json[KEY_TIMESTAMP] == publication_timestamp
            ):
                print(
                    f"Latest Infodump ({publication_timestamp}) already parsed to {output_path}"
                )
                download_required = False

    # download infodump if it is fresh, or if we are in dev mode and have not downloaded it already
    infodump_path = Path(infodump_dir)
    if download_required or (dev and not (infodump_path / "commentdata_mefi.txt").exists()):
        print("Download Infodump")

        if infodump_path.exists():
            print(f'Delete "{infodump_dir}/*.txt"')
            for txt in infodump_path.glob("*.txt"):
                txt.unlink()
        else:
            infodump_path.mkdir()

        download_file("usernames", infodump_dir, user_agent)
        for site in SITES:
            download_file(f"postdata_{site}", infodump_dir, user_agent)
            download_file(f"commentdata_{site}", infodump_dir, user_agent)

    if download_required or dev:
        print(f'Parsing data from "{infodump_dir}" to "{output_path}"')
        parse(infodump_dir, output_path, publication_timestamp)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dev", action="store_true")
    parser.add_argument("infodump_dir")
    parser.add_argument("output_path")
    args = parser.parse_args()

    user_agent = os.environ.get("INFODUMP_USER_AGENT")

    download_infodump(args.dev, args.infodump_dir, args.output_path, user_agent)
