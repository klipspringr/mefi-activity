import os
from datetime import date, datetime
import pathlib
from typing import Tuple

import polars as pl
from infodump_tools.config import (
    ACTIVITY_LEVELS,
    AGE_THRESHOLDS,
    KEY_TIMESTAMP,
    SITES,
    TOP_N,
)
from polars import DataFrame, Enum, UInt8, UInt32, col, lit


# we need to remove second fractions from timestamp as polars chokes on them
def date_parser(col_name):
    return pl.concat_str(
        col(col_name).str.head(20), col(col_name).str.slice(-2, 2)
    ).str.to_datetime("%b %_d %Y %I:%M:%S%p", time_unit="ms")


def extract_year(col_name):
    return col(col_name).dt.year()


def extract_month(col_name):
    return pl.date(col(col_name).dt.year(), col(col_name).dt.month(), 1)


# load infodump txt files into polars dataframes
def load_dfs(
    infodump_dir,
) -> Tuple[list, DataFrame, DataFrame, DataFrame, DataFrame]:
    # sometimes the infodump contains text files which were exported at different times
    # set infodump_date to the earliest timestamp
    file_timestamps = dict()

    for path in pathlib.Path(infodump_dir).glob("*.txt"):
        with open(path) as f:
            timestamp = datetime.strptime(f.readline().strip(), "%a %b %d %H:%M:%S %Y")
            file_timestamps[str(path)] = timestamp

    (oldest_file, infodump_date) = min(file_timestamps.items(), key=lambda x: x[1])

    print(f'Oldest file is "{oldest_file}": {infodump_date}')

    print("Load files into dataframes")

    df_users = pl.read_csv(
        source=os.path.join(infodump_dir, "usernames.txt"),
        separator="\t",
        skip_rows=1,
        schema_overrides={"userid": UInt32},
    ).with_columns(date_parser("joindate"))

    exclude_meta_askmes = (
        ~((col("site") == "meta") & (col("category") == 10)),
    )  # exclude early AskMes stored in MeTa table

    exclude_latest_month = col("month") < date(
        infodump_date.year, infodump_date.month, 1
    )  # exclude data from latest (incomplete) month

    df_posts_all = pl.concat(
        [
            pl.read_csv(
                source=os.path.join(infodump_dir, f"postdata_{site}.txt"),
                separator="\t",
                skip_rows=1,
                schema_overrides={
                    "userid": UInt32,
                    "category": UInt8,
                    "favorites": UInt32,
                    "deleted": UInt8,
                },
            )
            .rename({"favorites": "faves"})  # consistent columm names
            .with_columns(
                date_parser("datestamp"),
                site=lit(site, Enum(SITES)),
            )
            .with_columns(month=extract_month("datestamp"))
            .filter(exclude_meta_askmes, exclude_latest_month)
            for site in SITES
        ]
    ).sort("datestamp")

    df_comments_all = pl.concat(
        [
            pl.read_csv(
                source=os.path.join(infodump_dir, f"commentdata_{site}.txt"),
                separator="\t",
                skip_rows=1,
                schema_overrides={
                    "userid": UInt32,
                    "faves": UInt32,
                    "best answer?": UInt8,
                },
            )
            .rename({"best answer?": "best"})
            .with_columns(
                date_parser("datestamp"),
                site=lit(site, Enum(SITES)),
            )
            .with_columns(month=extract_month("datestamp"))
            .filter(exclude_latest_month)
            for site in SITES
        ]
    ).sort("datestamp")

    df_activity_all = pl.concat(
        [
            df.select(col("datestamp"), col("month"), col("site"), col("userid"))
            for df in [df_posts_all, df_comments_all]
        ]
    ).sort("datestamp")

    # if first post or comment is earlier than user joindate, overwrite joindate.
    # should only affect 70-ish 1999 users, plus a couple of stray later accounts.
    df_users = (
        df_users.join(
            df_activity_all.select("userid", "datestamp").unique(
                "userid", keep="first"
            ),
            on="userid",
            how="left",
            coalesce=True,
        )
        .with_columns(
            joindate=pl.when(col("joindate") > col("datestamp"))
            .then(col("datestamp"))
            .otherwise(col("joindate")),
        )
        .drop("datestamp")
    )

    # a small number of users made posts/comments but are not in df_users. create records for them, using date of first post/comment as joindate
    df_users.extend(
        df_activity_all.select("userid", "datestamp")
        .join(df_users, on="userid", how="anti")
        .sort("datestamp")
        .unique("userid", keep="first")
        .select(
            col("userid"),
            joindate=col("datestamp"),
            name=None,
        )
    )

    # extract join year and month
    df_users = df_users.with_columns(
        joinyear=extract_year("joindate"), joinmonth=extract_month("joindate")
    )

    joinyears = list(
        range(
            df_users.get_column("joinyear").min(),
            df_users.get_column("joinyear").max() + 1,
        )
    )

    return (
        joinyears,
        df_users,
        df_posts_all,
        df_comments_all,
        df_activity_all,
    )


def filter_df_by_site(site, df: DataFrame) -> DataFrame:
    return df if site == "all" else df.filter(col("site") == site)


def calculate_for_site(
    site: str,
    joinyears: list[int],
    df_users: DataFrame,
    df_posts_all: DataFrame,
    df_comments_all: DataFrame,
    df_activity_all: DataFrame,
) -> dict:
    print(f'Calculate stats for "{site}"')

    df_posts = filter_df_by_site(site, df_posts_all)
    df_comments = filter_df_by_site(site, df_comments_all)
    df_activity = filter_df_by_site(site, df_activity_all)

    # range of months from min to max
    # use this instead of group_by_dynamic(period="1mo"), because it includes months with no activity
    df_months = DataFrame(
        {
            "month": pl.date_range(
                df_activity.head(1).get_column("month")[0],
                df_activity.tail(1).get_column("month")[0],
                interval="1mo",
                eager=True,
            )
        }
    )

    start_date = df_months.head(1).get_column("month")[0]
    out = {
        "_start_year": start_date.year,
        "_start_month": start_date.month,
    }

    df_users_monthly = (
        df_months.join(
            df_activity.select("userid", "month"),
            on="month",
            how="left",
            coalesce=True,
        )
        .group_by(["month", "userid"], maintain_order=True)
        .agg(count=col("userid").count())
    )

    df_users_monthly_activity = df_users_monthly.group_by("month").agg(
        (
            col("count").filter(col("count") >= level).count().alias(str(level))
            for level in ACTIVITY_LEVELS
        )
    )

    out["users_monthly"] = [
        c.to_list() for c in df_users_monthly_activity.drop("month").get_columns()
    ]

    df_users_monthly_by_joined = (
        df_users_monthly.join(
            df_users.select("userid", "joinyear"),
            on="userid",
            how="left",
            coalesce=True,
        )
        .group_by("month")
        .agg(
            (
                col("joinyear").filter(joinyear=year).count().alias(str(year))
                for year in joinyears
            ),
        )
        .drop("month")
    )

    out["users_monthly_by_joined"] = [
        c.to_list() for c in df_users_monthly_by_joined.get_columns()
    ]

    df_activity_by_age = (
        df_months.join(
            df_activity.select("userid", "datestamp", "month"),
            on="month",
            how="left",
            coalesce=True,
        )
        .join(
            df_users.select("userid", "joindate"),
            on="userid",
            how="left",
            coalesce=True,
        )
        .with_columns(age=(col("datestamp") - col("joindate")).dt.total_days())
        .with_columns(
            col("age")
            .is_between(
                AGE_THRESHOLDS[i] * 365.25,
                AGE_THRESHOLDS[i + 1] * 365.25,
                closed="left",
            )
            .alias(str(i))
            for i in range(len(AGE_THRESHOLDS) - 1)
        )
        .group_by("month")
        .agg(col(str(i)).sum() for i in range(len(AGE_THRESHOLDS) - 1))
        .drop("month")
    )

    out["activity_by_age"] = [c.to_list() for c in df_activity_by_age.get_columns()]

    df_users_first = (
        df_months.join(
            df_activity.select("userid", "month").unique("userid", keep="first"),
            on="month",
            how="left",
        )
        .group_by("month")
        .agg(first=col("userid").len())
    )

    out["users_first"] = df_users_first.get_column("first").to_list()

    df_users_last = (
        df_months.join(
            df_activity.select("userid", "month").unique("userid", keep="last"),
            on="month",
            how="left",
        )
        .group_by("month")
        .agg(last=col("userid").len())
    )

    out["users_last"] = df_users_last.get_column("last").to_list()

    df_users_cum = df_users_first.select("month", cum=col("first").cum_sum())

    out["users_cum"] = df_users_cum.get_column("cum").to_list()

    # get registered users for whole site
    if site == "all":
        df_users_registered = (
            df_months.join(
                df_users.select("userid", "joinmonth"),
                left_on="month",
                right_on="joinmonth",
                how="left",
                coalesce=True,
            )
            .group_by("month")
            .agg(col("userid").count())
            .select(col("userid").cum_sum().alias("sum"))
        )

        out["users_registered"] = df_users_registered.get_column("sum").to_list()

    df_posts_deleted = (
        df_months.join(
            df_posts.select("month", "deleted"),
            on="month",
            how="left",
            coalesce=True,
        )
        .group_by("month")
        .agg(
            col("deleted").filter(col("deleted").is_in([1, 3])).len()
        )  # 1: deleted, 3: deleted and closed on Metatalk
    )

    out["posts_deleted"] = df_posts_deleted.get_column("deleted").to_list()

    for kind, df in [("posts", df_posts), ("comments", df_comments)]:
        df_totals = (
            df_months.join(df, on="month", how="left", coalesce=True)
            .group_by("month")
            .agg(pl.len(), pl.sum("faves"))
        )

        out[kind] = df_totals.get_column("len").to_list()

        for label, format in [("weekdays", "%u"), ("hours", "%H")]:
            out[f"{kind}_{label}_percent"] = (
                df.select("datestamp")
                .group_by(col("datestamp").dt.to_string(format).alias(label))
                .len()
                .sort(by=label)
                .select((col("len") / pl.sum("len")).round(4).alias("percent"))
                .get_column("percent")
                .to_list()
            )

        df_activity_by_top_users = (
            df_months.join(
                df.select("month", "userid"), on="month", how="left", coalesce=True
            )
            .group_by("month")
            .agg(
                pl.len(),
                col("userid").unique_counts().alias("counts").sort(descending=True),
            )
            .select(
                (
                    col("counts").list.head(col("counts").list.len() * n).list.sum()
                    / col("len")
                ).alias(str(n))
                for n in TOP_N
            )
            .select(pl.all().round(3))
        )

        out[f"{kind}_top_users"] = [
            c.to_list() for c in df_activity_by_top_users.get_columns()
        ]

    return out


# crunch infodump data into json
def calculate_stats(infodump_dir, publication_timestamp=None) -> dict:
    (
        joinyears,
        df_users,
        df_posts_all,
        df_comments_all,
        df_activity_all,
    ) = load_dfs(infodump_dir)

    out = {
        KEY_TIMESTAMP: publication_timestamp,
        "_start_joinyear": joinyears[0],
    }

    for site in ["all"] + SITES:
        out[site] = calculate_for_site(
            site,
            joinyears,
            df_users,
            df_posts_all,
            df_comments_all,
            df_activity_all,
        )

    return out
