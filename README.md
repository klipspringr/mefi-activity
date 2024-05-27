# MetaFilter activity stats

Available at [mefist.at](https://mefist.at/)

To remind myself how this works in future:

- `infodump` GitHub workflow calls `download.py` daily
- `download.py` checks "last updated" timestamp on [infodump page](https://stuff.metafilter.com/infodump/). We expect updates every month or two
- if new infodump, download post data, comment data, and usernames
- parse into `public/data.js` and push to repo
- pushes trigger the `deploy` workflow to upload `public/` to GitHub pages
- in order for automated pushes from `infodump` to trigger `deploy`, a Personal Access Token must be stored in a `INFODUMP_ACCESS_TOKEN` repo secret

For local development, manually download `postdata_*.txt.zip`, `commentdata_*.txt.zip` and `usernames.txt.zip`. Unzip and store in `cached_infodump/`. `download.py` reads these files, to avoid downloading infodump content every time.

In live usage, the `infodump` workflow calls `download.py` with the `--live` arg.

We only download infodump data if the page timestamp indicates the data is new.
