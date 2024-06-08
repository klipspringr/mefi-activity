# MetaFilter activity stats

Available at [mefist.at](https://mefist.at/)

This is a personal side project. Issues and comments are welcome. I'm not looking for pull requests.

To remind myself how it works in future:

## GitHub scheduled action

- `infodump` workflow calls `parser/download.py` regularly
- script checks "last updated" timestamp on [Infodump homepage](https://stuff.metafilter.com/infodump/). We expect updates every few months
- if a new Infodump is available, download postdata, commentdata, and usernames to `infodump/`, and parse into `src/data/data.json`
- push json to repo
- for pushes to trigger a deployment, a Personal Access Token must be stored in a `INFODUMP_ACCESS_TOKEN` repo secret

## Static frontend

- pushes trigger the `deploy` workflow to `pnpm build` the site and upload to GitHub pages

## Local development

- create a venv and `pip install -r parser/requirements.txt`
- run `python parser/download.py -d infodump src/data/data.json`
- with the `-d|--dev` flag, we (a) download Infodump data on first run (but not subsequently, unless a new Infodump is published), and (b) always regenerate the json
- `notebook.ipynb` makes testing polars expressions easier. It is not used in "production". Install Jupyter kernel requirements from `parser/requirements_notebook.txt`
