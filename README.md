# MetaFilter activity stats

Available at [mefist.at](https://mefist.at/)

This is a personal side project. Issues and comments are welcome. I'm not looking for pull requests.

To remind myself how it works in future:

## GitHub scheduled action

- `infodump` workflow calls `parser/download.py` regularly
- script checks "last updated" timestamp on [Infodump homepage](https://stuff.metafilter.com/infodump/)
- if a new Infodump is available, download postdata, commentdata, and usernames to `infodump/`, and parse into `src/data/data.json`
- push json to repo
- a Personal Access Token must be stored in the `INFODUMP_ACCESS_TOKEN` repo secret, so pushes trigger a deployment
- `INFODUMP_USER_AGENT` repo secret is also required

## Static frontend

- pushes trigger the `deploy` workflow to `pnpm build` the site and upload to GitHub pages

## Local development

- create a venv, run `pip install -r parser/requirements.txt`, activate venv
- set `INFODUMP_USER_AGENT` environment variable to a string that identifies you (this is sent when downloading large Infodump files)
- run `python parser/download.py --dev infodump src/data/data.json`
- with `-d|--dev`, we always regenerate the json, even if there is no new Infodump

## Notebook

- `parser/notebook.ipynb` makes testing Polars expressions easier. It is not used to generate the live site. Install Jupyter kernel requirements from `parser/requirements_notebook.txt`. Some packages are included to support the Data Wrangler VS Code extension
