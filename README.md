# MetaFilter activity stats

Available at <https://klipspringr.github.io/mefi-activity/>

To remind myself how this works in future:

- GitHub Action runs `download.py` daily
- check "last updated" timestamp on [infodump page](https://stuff.metafilter.com/infodump/). We expect updates roughly every month
- if changed, download post comment and user data and parse into `public/data.json`
- deploy `public` to GitHub Pages
