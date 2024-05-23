#!/usr/bin/env python3
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from urllib.request import urlopen, Request
from zipfile import ZipFile
import argparse
import io
import json
import os
import re
import sys

INFODUMP_HOMEPAGE = "https://stuff.metafilter.com/infodump/"
INFODUMP_BASE = "https://mefi.us/infodump/"
HEADERS = { "User-Agent": "github.com/klipspringr/mefi-activity" }

CACHE_DIR = "cached_infodump"

SITES = ["mefi", "askme", "meta", "fanfare", "music"]

# mefi users table runs from Jan 27 2000 08:16:57:367PM to date
JOIN_YEARS = [str(year) for year in range(2000, datetime.now().year + 1)]

def get_infodump_timestamp():
    with urlopen(Request(INFODUMP_HOMEPAGE, headers=HEADERS)) as f:
        contents = f.read().decode("utf-8")
        raw_date = re.search("Last updated: <b>(.+)</b>", contents).group(1)
        parsed_date = datetime.strptime(raw_date, "%a %b %d %H:%M:%S %Y")
        return parsed_date.strftime("%d %B %Y %H:%M"), parsed_date.strftime("%Y-%b")
    
def read_file(reader, skip = 2):
    for _ in range(skip):
        reader.readline() # ignore initial lines
    while line := reader.readline():
        parts = line.replace("\n", "").split("\t")
        if len(parts) < 2 or not parts[0].isnumeric():
            continue # skip lines that can't be split by tab, or where first field is not numeric
        yield parts

def get_infodump_file(filename):
    if args.no_cache:
        url = INFODUMP_BASE + filename + ".txt.zip"
        print(f"get {url}")
        with urlopen(Request(url, headers=HEADERS)) as f:
            with ZipFile(BytesIO(f.read())) as zip:
                with zip.open(filename + ".txt") as txt:
                    yield from read_file(io.TextIOWrapper(txt, "utf-8"))
    else:
        path = os.path.join(CACHE_DIR, filename + ".txt")
        print(f"read {path}")
        with open(path, "r") as f:
            yield from read_file(f)

def main():             
    try:
        with open(args.json_path, "r") as f:
            json_timestamp = json.load(f)["infodump_timestamp"]
    except:
        json_timestamp = None

    infodump_timestamp, month_to_skip = get_infodump_timestamp()
    if infodump_timestamp == json_timestamp:
        print("infodump unchanged")
        sys.exit(0)

    user_joined = {}
    for user_id, date, _ in get_infodump_file("usernames"):
        user_joined[user_id] = date[7:11]

    posts = {site: defaultdict(int) for site in SITES}
    comments = {site: defaultdict(int) for site in SITES}
    unique_users = {site: defaultdict(set) for site in SITES}

    posts["all"] = defaultdict(int)
    comments["all"] = defaultdict(int)
    unique_users["all"] = defaultdict(set)

    for site in SITES:
        for _, user_id, date, category, *_ in get_infodump_file(f"postdata_{site}"):
            if site == "meta" and category == "10":
                continue # skip early askmes stored in meta db table
            month = f'{date[7:11]}-{date[:3]}'
            if month == month_to_skip:
                break
            posts[site][month] += 1
            posts["all"][month] += 1
            unique_users[site][month].add(user_id)
            unique_users["all"][month].add(user_id)

        for _, _, user_id, date, *_ in get_infodump_file(f"commentdata_{site}"):
            month = f'{date[7:11]}-{date[:3]}'
            if month == month_to_skip:
                break
            comments[site][month] += 1
            comments["all"][month] += 1
            unique_users[site][month].add(user_id)
            unique_users["all"][month].add(user_id)

    active = {}
    for site, months_users in unique_users.items():
        active[site] = {
            "labels": [k for k in months_users.keys()],
            "by_year": {join_year: [0 for _ in months_users.keys()] for join_year in JOIN_YEARS},
            "totals": [len(u) for u in months_users.values()]
        }
        for index, (month, users) in enumerate(months_users.items()):
            for user_id in users:
                # a few user_ids are not in user_joined: see https://mefiwiki.com/wiki/Infodump#Userid_munging
                if user_id in user_joined:
                    join_year = user_joined[user_id]
                    active[site]["by_year"][join_year][index] += 1

    with open(args.json_path, "w") as f:
        json.dump({
            "infodump_timestamp": infodump_timestamp,
            "posts": posts,
            "comments": comments,
            "active": active
        }, f)

    print(f"wrote to {args.json_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()
    main()
