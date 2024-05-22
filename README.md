# MetaFilter activity stats

Available at <https://klipspringr.github.io/mefi-activity/>

To remind myself how this works in future:

- GitHub Action `infodump` runs `download.py` daily
- `download.py` checks "last updated" timestamp on [infodump page](https://stuff.metafilter.com/infodump/). We expect updates roughly every month or two
- if new infodump, download post comment and user data and parse into `public/data.json`
- push new json to repo (requires Personal Access Token, stored in `INFODUMP_ACCESS_TOKEN` repo secret)
- pushes trigger GitHub Action `deploy` to upload `public/` to GitHub Pages
