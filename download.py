#!/usr/bin/env python3
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
JOIN_YEARS = [
    year for year in range(2000, datetime.now().year + 1)
]  # DB stores early users' join date as Jan 27 2000
AGE_CUTOFFS = [15, 10, 5, 1, 0]
MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}

INFODUMP_HOMEPAGE = "https://stuff.metafilter.com/infodump/"
INFODUMP_BASE = "https://mefi.us/infodump/"
HEADERS = {"User-Agent": "github.com/klipspringr/mefi-activity"}

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cached_infodump")
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "template.js")


def get_infodump_timestamp():
    with urlopen(Request(INFODUMP_HOMEPAGE, headers=HEADERS)) as f:
        contents = f.read().decode("utf-8")
        raw_date = re.search("Last updated: <b>(.+)</b>", contents).group(1)
        parsed_date = datetime.strptime(raw_date, "%a %b %d %H:%M:%S %Y")
        return parsed_date, parsed_date.strftime("%d %B %Y %H:%M")


def read_file(reader):
    reader.readline()
    reader.readline()  # ignore headers
    while line := reader.readline():
        parts = line.replace("\n", "").split("\t")
        if len(parts) < 2 or not parts[0].isnumeric():
            continue  # skip lines that can't be split by tab, or where first field is not numeric
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
        js_timestamp = None
        if os.path.exists(args.output_path):
            with open(args.output_path, "r") as f:
                js_timestamp = re.search('TIMESTAMP = "(.+)"', f.readline()).group(1)
        if infodump_timestamp == js_timestamp:
            print("infodump unchanged")
            sys.exit(0)

    user_joined = {}
    for user_id, raw_date, _ in get_infodump_file("usernames"):
        user_joined[user_id] = datetime(
            int(raw_date[7:11]), MONTHS[raw_date[0:3]], int(raw_date[4:6])
        )

    monthly = {
        site: {"epoch_year": None, "epoch_month": None} for site in SITES + ["all"]
    }
    daily = {site: {"posts": [0] * 7, "comments": [0] * 7} for site in SITES + ["all"]}
    hourly = {
        site: {"posts": [0] * 24, "comments": [0] * 24} for site in SITES + ["all"]
    }

    def hour24(hour, pm):
        if hour == 12:
            return 12 if pm else 0
        return hour + 12 if pm else hour

    def parse_line(site, type, raw_date, user_id):
        # let's manually parse date because strptime is so slow. Format: "Jun 29 2006 08:10:14:467PM"
        date = datetime(
            int(raw_date[7:11]),
            MONTHS[raw_date[0:3]],
            int(raw_date[4:6]),
            hour24(int(raw_date[12:14]), raw_date[24] == "P"),
        )

        if date.year == infodump_date.year and date.month == infodump_date.month:
            return False  # stop parsing when we hit month of infodump timestamp

        for s in [site, "all"]:
            if monthly[s]["epoch_year"] is None:
                monthly[s]["epoch_year"] = date.year
                monthly[s]["epoch_month"] = date.month
                # add 1 to count first month, but take off 1 as don't want last (incomplete) month
                num_months = (infodump_date.year - date.year) * 12 + (
                    infodump_date.month - date.month
                )
                monthly[s]["posts"] = [0] * num_months
                monthly[s]["comments"] = [0] * num_months
                monthly[s]["activity_by_age"] = {
                    cutoff: [0] * num_months for cutoff in AGE_CUTOFFS + [999]
                }
                monthly[s]["users_set"] = [set() for _ in range(num_months)]
                monthly[s]["users_total"] = [0] * num_months
                monthly[s]["users_by_year"] = {
                    year: [0] * num_months for year in JOIN_YEARS
                }
                monthly[s]["users_cumulative"] = [0] * num_months
                monthly[s]["users_new"] = [0] * num_months

            month_key = (date.year - monthly[s]["epoch_year"]) * 12 + (
                date.month - monthly[s]["epoch_month"]
            )
            monthly[s][type][month_key] += 1
            if user_id in user_joined:
                monthly[s]["users_set"][month_key].add(user_id)
                # calculate user age based on join date. can be negative for 1999 users, so set a min of 0.
                user_age = max((date - user_joined[user_id]).days / 365.25, 0)
                for cutoff in AGE_CUTOFFS:
                    if user_age >= cutoff:
                        monthly[s]["activity_by_age"][cutoff][month_key] += 1
                        break

            hourly[s][type][date.hour] += 1
            daily[s][type][date.weekday()] += 1

        return True

    # parse infodump into monthly, daily, and hourly counters
    for site in SITES:
        for _, user_id, raw_date, category, *_ in get_infodump_file(f"postdata_{site}"):
            if site == "meta" and category == "10":
                continue  # skip early askmes stored in meta db table
            if not parse_line(site, "posts", raw_date, user_id):
                break

        for _, _, user_id, raw_date, *_ in get_infodump_file(f"commentdata_{site}"):
            if not parse_line(site, "comments", raw_date, user_id):
                break

    for s in SITES + ["all"]:
        # calculate users totals, by join year, cumulative and new
        users_ever_active = set()
        for month_index, users in enumerate(monthly[s]["users_set"]):
            users_ever_active_previous = len(users_ever_active)

            for user_id in users:
                join_year = user_joined[user_id].year
                monthly[s]["users_by_year"][join_year][month_index] += 1
                monthly[s]["users_total"][month_index] += 1
                users_ever_active.add(user_id)

            monthly[s]["users_cumulative"][month_index] = len(users_ever_active)
            monthly[s]["users_new"][month_index] = (
                len(users_ever_active) - users_ever_active_previous
            )

        del monthly[s]["users_set"]

        for cutoff in monthly[s]["activity_by_age"]:
            monthly[s]["activity_by_age"][cutoff] = [
                round(x / (monthly[s]["posts"][i] + monthly[s]["comments"][i]), 4)
                for i, x in enumerate(monthly[s]["activity_by_age"][cutoff])
            ]

        # divide daily and hourly activity by weekly/daily total
        for type in ["posts", "comments"]:
            total = sum(daily[s][type])
            daily[s][type] = [round(x / total, 4) for x in daily[s][type]]
            hourly[s][type] = [round(x / total, 4) for x in hourly[s][type]]

    with open(TEMPLATE_PATH, "r") as t:
        template = Template(t.read())
        result = template.substitute(
            infodump_timestamp=infodump_timestamp,
            monthly=json.dumps(monthly),
            daily=json.dumps(daily),
            hourly=json.dumps(hourly),
        )
        with open(args.output_path, "w") as o:
            o.write(result)

    print(f"wrote to {args.output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_path")
    parser.add_argument(
        "--live", action="store_true", help="download live data from server"
    )
    args = parser.parse_args()
    main()
