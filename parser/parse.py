import json
import os
from datetime import date, datetime
from typing import Tuple

import polars as pl
from config import ACTIVITY_LEVELS, AGE_THRESHOLDS, KEY_TIMESTAMP, SITES, TOP_N
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


def load_dfs(
    infodump_dir,
) -> Tuple[list, DataFrame, DataFrame, DataFrame, DataFrame, DataFrame]:
    with open(os.path.join(infodump_dir, "usernames.txt")) as f:
        infodump_date = datetime.strptime(f.readline().strip(), "%a %b %d %H:%M:%S %Y")

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
                    "deleted": UInt8,
                },
            )
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
                },
            )
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

    df_months_all = DataFrame(
        {
            "month": pl.date_range(
                df_activity_all.head(1).get_column("month")[0],
                df_activity_all.tail(1).get_column("month")[0],
                interval="1mo",
                eager=True,
            )
        }
    )

    # get registered users for whole site
    df_users_registered = (
        df_months_all.join(
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

    joinyears = list(
        range(
            df_users.get_column("joinyear").min(),
            df_users.get_column("joinyear").max() + 1,
        )
    )

    return (
        joinyears,
        df_users,
        df_users_registered,
        df_posts_all,
        df_comments_all,
        df_activity_all,
    )


def filter_by_site(site, df: DataFrame) -> DataFrame:
    return df.filter(col("site") == site) if site != "all" else df


def get_site_dfs(
    site,
    df_posts_all: DataFrame,
    df_comments_all: DataFrame,
    df_activity_all: DataFrame,
) -> Tuple[DataFrame, DataFrame, DataFrame, DataFrame]:
    df_posts = filter_by_site(site, df_posts_all)
    df_comments = filter_by_site(site, df_comments_all)
    df_activity = filter_by_site(site, df_activity_all)

    # range of months from min to max. this is better than group_by_dynamic(period="1mo") because it includes all months even if no data
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

    return df_months, df_posts, df_comments, df_activity


def parse(infodump_dir, output_path, publication_timestamp=None):
    (
        joinyears,
        df_users,
        df_users_registered,
        df_posts_all,
        df_comments_all,
        df_activity_all,
    ) = load_dfs(infodump_dir)

    out = {
        KEY_TIMESTAMP: publication_timestamp,
        "_start_joinyear": joinyears[0],
    }

    for site in SITES + ["all"]:
        print("Parsing " + site)

        df_months, df_posts, df_comments, df_activity = get_site_dfs(
            site, df_posts_all, df_comments_all, df_activity_all
        )

        start_date = df_months.head(1).get_column("month")[0]
        out[site] = {
            "_start_year": start_date.year,
            "_start_month": start_date.month,
        }

        if site == "all":
            out[site]["users_registered"] = df_users_registered.get_column(
                "sum"
            ).to_list()

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

        out[site]["users_monthly"] = [
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

        out[site]["users_monthly_by_joined"] = [
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
                .is_between(AGE_THRESHOLDS[i], AGE_THRESHOLDS[i + 1], closed="left")
                .alias(str(i))
                for i in range(len(AGE_THRESHOLDS) - 1)
            )
            .group_by("month")
            .agg(col(str(i)).sum() for i in range(len(AGE_THRESHOLDS) - 1))
            .drop("month")
        )

        out[site]["activity_by_age"] = [
            c.to_list() for c in df_activity_by_age.get_columns()
        ]

        df_users_new = (
            df_months.join(
                df_activity.select("userid", "month").unique("userid", keep="first"),
                on="month",
                how="left",
                coalesce=True,
            )
            .group_by("month")
            .agg(new=col("userid").count())
        )

        out[site]["users_new"] = df_users_new.get_column("new").to_list()

        df_users_cum = df_users_new.select("month", cum=col("new").cum_sum())

        out[site]["users_cum"] = df_users_cum.get_column("cum").to_list()

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

        out[site]["posts_deleted"] = df_posts_deleted.get_column("deleted").to_list()

        for label, df in {"posts": df_posts, "comments": df_comments}.items():
            out[site][label] = (
                df_months.join(
                    df.select("month"), on="month", how="left", coalesce=True
                )
                .group_by("month")
                .agg(pl.len())
                .get_column("len")
                .to_list()
            )

            out[site][f"{label}_weekdays_percent"] = (
                df.select("datestamp")
                .group_by(col("datestamp").dt.weekday().alias("weekday"))
                .len()
                .sort(by="weekday")
                .select((col("len") / pl.sum("len")).round(4).alias("percent"))
                .get_column("percent")
                .to_list()
            )

            out[site][f"{label}_hours_percent"] = (
                df.select("datestamp")
                .group_by(col("datestamp").dt.hour().alias("hour"))
                .len()
                .sort(by="hour")
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

            out[site][f"{label}_top_users"] = [
                c.to_list() for c in df_activity_by_top_users.get_columns()
            ]

    with open(output_path, "w") as w:
        json.dump(out, w, sort_keys=True, indent=4)

    print(f'Wrote JSON to "{output_path}"')
