import os
from datetime import date, datetime
from typing import Tuple

import polars as pl
from infodump_tools.config import (
    ACTIVITY_LEVELS,
    AGE_THRESHOLDS,
    INFODUMP_FILENAMES,
    KEY_TIMESTAMP,
    SITES,
    TOP_N,
)
from polars import (
    DataFrame,
    Enum,
    Expr,
    String,
    UInt16,
    UInt8,
    UInt32,
    col,
    lit,
)


def read_timestamp(infodump_dir: str, filename: str) -> datetime:
    """
    Read the timestamp from an Infodump txt file.
    """
    with open(os.path.join(infodump_dir, f"{filename}.txt")) as f:
        return datetime.strptime(f.readline().strip(), "%a %b %d %H:%M:%S %Y")


def date_parser(col_name: str) -> Expr:
    """
    Parse Infodump datestamp column to a polars datetime.

    Remove fractional seconds, as polars chokes on them.

    The infodump datestamp column is in Mefi server time, America/Los_Angeles.
    """
    return pl.concat_str(
        col(col_name).str.head(20), col(col_name).str.slice(-2, 2)
    ).str.to_datetime("%b %_d %Y %I:%M:%S%p", time_unit="ms")


def extract_year(col_name: str) -> Expr:
    return col(col_name).dt.year().cast(UInt16)


def extract_month(col_name: str) -> Expr:
    return pl.date(col(col_name).dt.year(), col(col_name).dt.month(), 1)


def get_cutoff_date(infodump_dir: str, df_comments_all: DataFrame) -> date:
    """
    Get the date from which we want to exclude data. We only want months for which we have completed data for each subsite.

    The Infodump has often been published in an inconsistent state e.g. text files produced at different times, data stopping months before publication, etc.

    So we base the cutoff date calculation on the OLDEST of:
    - the timestamps on the first line of the text files
    - the latest comment left on each subsite, excluding Music (which sees too little activity to be useful for this purpose)
    """
    files: dict[str, datetime] = {
        filename: read_timestamp(infodump_dir, filename)
        for filename in INFODUMP_FILENAMES
    }

    oldest_file, oldest_file_timestamp = min(files.items(), key=lambda x: x[1])

    print(f"Oldest file timestamp ({oldest_file}): {oldest_file_timestamp}")

    latest_comments = dict(
        df_comments_all.filter(~col("site").is_in(["music"]))
        .group_by("site")
        .agg(col("datestamp").max())
        .iter_rows()
    )

    for site, timestamp in latest_comments.items():
        print(f'Latest comment on "{site}": {timestamp}')

    cutoff_timestamp = min(oldest_file_timestamp, min(latest_comments.values()))

    cutoff_date = date(cutoff_timestamp.year, cutoff_timestamp.month, 1)

    print(f"Exclude data from {cutoff_date} onward")

    return cutoff_date


def load_dfs(
    infodump_dir: str,
) -> Tuple[list[int], DataFrame, DataFrame, DataFrame, DataFrame]:
    """
    Load posts, comments, and users data from Infodump txt files into polars DataFrames.
    """

    print("Load posts")

    df_posts_all = pl.concat(
        [
            pl.read_csv(
                source=os.path.join(infodump_dir, f"postdata_{site}.txt"),
                separator="\t",
                skip_rows=1,
                schema_overrides={
                    "postid": UInt32,
                    "userid": UInt32,
                    "datestamp": String,
                    "category": UInt8,
                    "comments": UInt16,
                    "favorites": UInt16,
                    "deleted": UInt8,
                    "reason": String,
                },
                null_values=["[NULL]"],  # reason defaults to "[NULL]"
            )
            .rename({"favorites": "faves"})  # consistent columm names
            .with_columns(
                date_parser("datestamp"),
                site=lit(site, Enum(SITES)),
            )
            .with_columns(month=extract_month("datestamp"))
            .filter(
                ~((col("site") == "meta") & (col("category") == 10))
            )  # exclude early AskMes stored in MeTa table
            for site in SITES
        ]
    ).sort("datestamp")

    print("Load comments")

    df_comments_all = pl.concat(
        [
            pl.read_csv(
                source=os.path.join(infodump_dir, f"commentdata_{site}.txt"),
                separator="\t",
                skip_rows=1,
                schema_overrides={
                    "commentid": UInt32,
                    "postid": UInt32,
                    "userid": UInt32,
                    "datestamp": String,
                    "faves": UInt16,
                    "best answer?": UInt8,
                },
            )
            .rename({"best answer?": "best"})
            .with_columns(
                date_parser("datestamp"),
                site=lit(site, Enum(SITES)),
            )
            .with_columns(month=extract_month("datestamp"))
            for site in SITES
        ]
    ).sort("datestamp")

    df_activity_all = pl.concat(
        [
            df.select(col("datestamp"), col("month"), col("site"), col("userid"))
            for df in [df_posts_all, df_comments_all]
        ]
    ).sort("datestamp")

    print("Load users")

    df_users = pl.read_csv(
        source=os.path.join(infodump_dir, "usernames.txt"),
        separator="\t",
        skip_rows=1,
        schema_overrides={"userid": UInt32, "joindate": String, "name": String},
    ).with_columns(date_parser("joindate"))

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

    col_joinyear = df_users.get_column("joinyear")
    joinyears = list(
        range(
            col_joinyear.min(),
            col_joinyear.max() + 1,
        )
    )

    print("Filter out incomplete months...")

    cutoff_date = get_cutoff_date(infodump_dir, df_comments_all)

    df_posts_all = df_posts_all.filter(col("month") < cutoff_date)
    df_comments_all = df_comments_all.filter(col("month") < cutoff_date)
    df_activity_all = df_activity_all.filter(col("month") < cutoff_date)

    return (
        joinyears,
        df_users,
        df_posts_all,
        df_comments_all,
        df_activity_all,
    )


def filter_df_by_site(site, df: DataFrame) -> DataFrame:
    return df if site == "all" else df.filter(col("site") == site)


def get_months_df(df: DataFrame) -> DataFrame:
    """
    Range of months from min to max.

    Use this instead of group_by_dynamic(period="1mo"), because it includes months with no activity.

    Assumes df is sorted by datestamp, so first() is min and last() is max.
    """
    col = df.get_column("month")
    return DataFrame(
        {
            "month": pl.date_range(
                col.first(),
                col.last(),
                closed="both",
                interval="1mo",
                eager=True,
            )
        }
    )


def get_dfs_for_site(
    site: str,
    df_posts_all: DataFrame,
    df_comments_all: DataFrame,
    df_activity_all: DataFrame,
) -> Tuple[DataFrame, DataFrame, DataFrame, DataFrame]:
    """
    Get posts, comments, activity, and months DataFrames for a given site.
    """

    df_posts = filter_df_by_site(site, df_posts_all)
    df_comments = filter_df_by_site(site, df_comments_all)
    df_activity = filter_df_by_site(site, df_activity_all)

    df_months = get_months_df(df_activity)

    return df_posts, df_comments, df_activity, df_months


def calculate_for_site(
    site: str,
    joinyears: list[int],
    df_users: DataFrame,
    df_posts_all: DataFrame,
    df_comments_all: DataFrame,
    df_activity_all: DataFrame,
) -> dict:
    """
    Calculate stats for a given site.

    Returns a dictionary to be output as json.
    """

    print(f'Calculate stats for "{site}"')

    (
        df_posts,
        df_comments,
        df_activity,
        df_months,
    ) = get_dfs_for_site(site, df_posts_all, df_comments_all, df_activity_all)

    start_date = df_months.get_column("month").first()
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

    df_users_monthly_by_activity_level = (
        df_users_monthly.group_by("month")
        .agg(
            (
                col("count").filter(col("count") >= level).count().alias(str(level))
                for level in ACTIVITY_LEVELS
            )
        )
        .drop("month")
    )

    out["users_monthly"] = [
        c.to_list() for c in df_users_monthly_by_activity_level.get_columns()
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

        out[f"{kind}_faves"] = df_totals.get_column("faves").to_list()

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

    if site == "askme":
        df_best = (
            df_months.join(
                df_posts.select("month", "postid")
                .join(
                    df_comments.select("postid", "best"),
                    on="postid",
                    how="left",  # left join, so we keep posts with no comments
                    coalesce=True,
                )
                .group_by("postid")
                .agg(
                    month=col("month").first(),
                    best_sum=col("best").eq(1).sum(),
                    best_any=col("best").eq(1).any(),
                ),
                on="month",
                how="left",
            )
            .group_by("month")
            .agg(
                bests=col("best_sum").sum(),
                posts_with_best=col("best_any").sum(),
            )
        )

        out["bests"] = df_best.get_column("bests").to_list()
        out["posts_with_best"] = df_best.get_column("posts_with_best").to_list()

    return out


# crunch infodump data into json
def calculate_stats(infodump_dir: str, publication_timestamp: str) -> dict:
    """
    Calculate stats for all sites.

    Returns a dictionary to be output as json.
    """

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
