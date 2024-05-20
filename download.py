#!/usr/bin/env python3
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from urllib.request import urlopen, Request
from zipfile import ZipFile
import json
import re
import sys

INFODUMP_HOMEPAGE = "https://stuff.metafilter.com/infodump/"
INFODUMP_BASE = "https://mefi.us/infodump/"
HEADERS = { "User-Agent": "github.com/klipspringr/mefi-activity" }

SITES = ["mefi", "askme", "meta", "fanfare", "music"]

# mefi users table runs from Jan 27 2000 08:16:57:367PM to date
JOIN_YEARS = [str(year) for year in range(2000, datetime.now().year + 1)]

def download(filename, skip = 2):
    url = INFODUMP_BASE + filename + ".txt.zip"
    print(f"get {url}")

    with urlopen(Request(url, headers=HEADERS)) as f:
        with ZipFile(BytesIO(f.read())) as zip:
            with zip.open(filename + ".txt") as txt:
                for _ in range(skip):
                    txt.readline() # ignore initial lines
                while line := txt.readline():
                    parts = line.decode('utf-8').replace("\n", "").split("\t")
                    if len(parts) < 2 or not parts[0].isnumeric():
                        continue # skip lines that can't be split by tab, or where first field is not numeric
                    yield parts

if len(sys.argv) != 2 or sys.argv[1] == "":
    raise Exception("Expected argument: path to output json")

json_path = sys.argv[1]

try:
    with open(json_path, "r") as f:
        json_version = json.load(f)["infodump_version"]
except:
    json_version = None

with urlopen(Request(INFODUMP_HOMEPAGE, headers=HEADERS)) as f:
    contents = f.read().decode("utf-8")
    raw_date = re.search("Last updated: <b>(.+)</b>", contents).group(1)
    infodump_version = datetime.strptime(raw_date, "%a %b %d %H:%M:%S %Y").strftime("%d %B %Y %H:%M")
    if not infodump_version:
        raise Exception("couldn't get infodump version")

if json_version == infodump_version:
    print("infodump unchanged")
    sys.exit(0)

user_joined = {}
for user_id, date, _ in download("usernames"):
    user_joined[user_id] = date[7:11]

posts = {site: defaultdict(int) for site in SITES}
comments = {site: defaultdict(int) for site in SITES}
unique_users = {site: defaultdict(set) for site in SITES}

posts["all"] = defaultdict(int)
comments["all"] = defaultdict(int)
unique_users["all"] = defaultdict(set)

for site in SITES:
    for _, user_id, date, *_ in download(f"postdata_{site}"):
        month = f'{date[7:11]}-{date[:3]}'
        posts[site][month] += 1
        posts["all"][month] += 1
        unique_users[site][month].add(user_id)
        unique_users["all"][month].add(user_id)

    for _, _, user_id, date, *_ in download(f"commentdata_{site}"):
        month = f'{date[7:11]}-{date[:3]}'
        comments[site][month] += 1
        comments["all"][month] += 1
        unique_users[site][month].add(user_id)
        unique_users["all"][month].add(user_id)

active = {}
for site, months_users in unique_users.items():
    active[site] = {
        "labels": [k for k in months_users.keys()],
        "data": {join_year: [0 for _ in months_users.keys()] for join_year in JOIN_YEARS}
    }
    for index, (month, users) in enumerate(months_users.items()):
        for user_id in users:
            if user_id in user_joined:
                join_year = user_joined[user_id]
                active[site]["data"][join_year][index] += 1

with open(json_path, "w") as f:
    json.dump({
        "infodump_version": infodump_version,
        "posts": posts,
        "comments": comments,
        "active": active
    }, f)

print(f"wrote to {json_path}")
