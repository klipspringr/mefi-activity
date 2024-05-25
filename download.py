#!/usr/bin/env python3
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from string import Template
from urllib.request import urlopen, Request
from zipfile import ZipFile
import argparse
import io
import json
import os
import re
import sys

SITES = ["mefi", "askme", "meta", "fanfare", "music"]
JOIN_YEARS = [str(year) for year in range(2000, datetime.now().year + 1)] # first users join date Jan 27 2000 in DB

INFODUMP_HOMEPAGE = "https://stuff.metafilter.com/infodump/"
INFODUMP_BASE = "https://mefi.us/infodump/"
HEADERS = { "User-Agent": "github.com/klipspringr/mefi-activity" }

CACHE_DIR = "cached_infodump"
TEMPLATE_PATH = "template.js"

def get_infodump_timestamp():
    with urlopen(Request(INFODUMP_HOMEPAGE, headers=HEADERS)) as f:
        contents = f.read().decode("utf-8")
        raw_date = re.search("Last updated: <b>(.+)</b>", contents).group(1)
        parsed_date = datetime.strptime(raw_date, "%a %b %d %H:%M:%S %Y")
        return parsed_date, parsed_date.strftime("%d %B %Y %H:%M")
    
def read_file(reader):
    reader.readline()
    reader.readline() # ignore headers
    while line := reader.readline():
        parts = line.replace("\n", "").split("\t")
        if len(parts) < 2 or not parts[0].isnumeric():
            continue # skip lines that can't be split by tab, or where first field is not numeric
        yield parts

def get_infodump_file(filename):
    if args.live:
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
    infodump_date, infodump_timestamp = get_infodump_timestamp()
    if args.live:
        try:
            with open(args.output_path, "r") as f:
                js_timestamp = re.search("TIMESTAMP = \"(.+)\"", f.readline()).group(1)
        except:
            js_timestamp = None
        if infodump_timestamp == js_timestamp:
            print("infodump unchanged")
            sys.exit(0)

    user_joined = {}
    for user_id, raw_date, _ in get_infodump_file("usernames"):
        user_joined[user_id] = raw_date[7:11]

    monthly = {site: defaultdict(lambda: { "posts": 0, "comments": 0, "users": set() }) for site in SITES + ["all"]}
    daily = {site: { "posts": [0] * 7, "comments": [0] * 7 } for site in SITES + ["all"]}
    hourly = {site: { "posts": [0] * 24, "comments": [0] * 24 } for site in SITES + ["all"]}

    def parse_line(site, type, raw_date, user_id):
        date = datetime.strptime(raw_date, "%b %d %Y %I:%M:%S:%f%p")
        if date.year == infodump_date.year and date.month == infodump_date.month:
            return False # stop parsing if date is same month as infodump timestamp
        month_key = date.strftime("%Y %b")
        for s in [site, "all"]:
            monthly[s][month_key][type] += 1
            monthly[s][month_key]["users"].add(user_id)
            hourly[s][type][date.hour] += 1
            daily[s][type][date.weekday()] += 1
        return True

    # parse infodump into monthly, daily, and hourly counters
    for site in SITES:
        for _, user_id, raw_date, category, *_ in get_infodump_file(f"postdata_{site}"):
            if site == "meta" and category == "10":
                continue # skip early askmes stored in meta db table
            if not parse_line(site, "posts", raw_date, user_id):
                break

        for _, _, user_id, raw_date, *_ in get_infodump_file(f"commentdata_{site}"):
            if not parse_line(site, "comments", raw_date, user_id):
                break
    
    # transform counter data into efficient json representation for charts
    monthly_summary = {s: {
        "labels": list(monthly[s].keys()),
        "posts": [],
        "comments": [],
        "users_total": [],
        "users_by_year": { year: [0] * len(monthly[s]) for year in JOIN_YEARS},
        } for s in SITES + ["all"] }
    
    for s in SITES + ["all"]:
        for i, c in enumerate(monthly[s].values()):
            monthly_summary[s]["posts"].append(c["posts"])
            monthly_summary[s]["comments"].append(c["comments"])
            monthly_summary[s]["users_total"].append(len(c["users"]))
            for user_id in c["users"]:
                # a few user_ids are not real: see https://mefiwiki.com/wiki/Infodump#Userid_munging
                if user_id in user_joined:
                    join_year = user_joined[user_id]
                    monthly_summary[s]["users_by_year"][join_year][i] += 1

        for type in ["posts", "comments"]:
            sum_daily = sum(daily[s][type])
            sum_hourly = sum(hourly[s][type])
            daily[s][type] = [round(x / sum_daily, 4) for x in daily[s][type]]
            hourly[s][type] = [round(x / sum_hourly, 4) for x in hourly[s][type]]

    with open(TEMPLATE_PATH, "r") as t:
        template = Template(t.read())
        result = template.substitute(
            infodump_timestamp=infodump_timestamp,
            monthly=json.dumps(monthly_summary),
            daily=json.dumps(daily),
            hourly=json.dumps(hourly))
        with open(args.output_path, "w") as o:
            o.write(result)

    print(f"wrote to {args.output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_path")
    parser.add_argument("--live", action="store_true", help="download live data from server")
    args = parser.parse_args()
    main()
