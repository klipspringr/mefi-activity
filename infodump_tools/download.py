import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from urllib.request import Request, urlopen
from zipfile import ZipFile

from infodump_tools.calculate import calculate_stats
from infodump_tools.config import (
    INFODUMP_BASE_URL,
    INFODUMP_FILENAMES,
    INFODUMP_HOMEPAGE,
    KEY_TIMESTAMP,
)


def get_publication_timestamp():
    with urlopen(INFODUMP_HOMEPAGE) as f:
        contents = f.read().decode("utf-8")
        raw_date = re.search("Last updated: <b>(.+)</b>", contents).group(1).strip()
        published = datetime.strptime(raw_date, "%a %b %d %H:%M:%S %Y")
        return published.strftime("%-d %B %Y %H:%M")


def download_zip(filename, infodump_dir, user_agent):
    url = INFODUMP_BASE_URL + filename + ".txt.zip"

    req = Request(url)
    if user_agent is not None:
        req.add_header("User-Agent", user_agent)

    try:
        with urlopen(req) as resp, tempfile.NamedTemporaryFile(delete=False) as tmp:
            shutil.copyfileobj(resp, tmp)
            tmp_path = tmp.name

        with ZipFile(tmp_path) as zip:
            member = filename + ".txt"
            with (
                zip.open(member) as src,
                open(os.path.join(infodump_dir, member), "wb") as dst,
            ):
                shutil.copyfileobj(src, dst)
    finally:
        os.remove(tmp_path)


def format_json(output_path):
    # should keep the version consistent with package.json
    args = ["pnpx", "prettier@3.8.1", "--write", output_path]
    print(*args)
    subprocess.run(args, check=True)


def download_infodump(dev, infodump_dir, output_path, user_agent):
    download_needed = True

    publication_timestamp = get_publication_timestamp()
    print(f'Infodump last published "{publication_timestamp}"')

    if os.path.isfile(output_path):
        with open(output_path, "r") as f:
            last_json = json.load(f)
            if (
                KEY_TIMESTAMP in last_json
                and last_json[KEY_TIMESTAMP] == publication_timestamp
            ):
                print("Infodump already processed")
                download_needed = False

    if not (download_needed or dev):
        print("Nothing to do")
        return

    os.makedirs(infodump_dir, exist_ok=True)

    for filename in INFODUMP_FILENAMES:
        if download_needed or not os.path.isfile(f"{infodump_dir}/{filename}.txt"):
            print(f'Download and extract "{filename}"...')
            download_zip(filename, infodump_dir, user_agent)

    print(f'Read files from "{infodump_dir}" and calculate stats...')
    out = calculate_stats(infodump_dir, publication_timestamp)

    print(f'Write JSON to "{output_path}"')
    with open(output_path, "w") as w:
        json.dump(out, w, sort_keys=True)

    print("Format with Prettier")
    format_json(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dev", action="store_true")
    parser.add_argument("infodump_dir")
    parser.add_argument("output_path")
    args = parser.parse_args()

    user_agent = os.environ.get("INFODUMP_USER_AGENT")

    download_infodump(args.dev, args.infodump_dir, args.output_path, user_agent)
