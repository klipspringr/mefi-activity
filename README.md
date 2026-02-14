# MetaFilter activity stats

Available at [mefist.at](https://mefist.at/)

This is a personal side project. Issues and comments are welcome. I'm not looking for pull requests.

To remind myself how it works in future:

## GitHub scheduled action

- `infodump` workflow calls python module `infodump_tools.download`, on a cron schedule
- script checks "last updated" timestamp on [Infodump homepage](https://stuff.metafilter.com/infodump/)
- if a new Infodump is available, download files to `infodump/`, calculate stats, and output to `src/data/data.json`
- push json to repo
- a Personal Access Token must be stored in the `INFODUMP_ACCESS_TOKEN` repo secret, so pushes trigger a deployment
- `INFODUMP_USER_AGENT` repo secret should also be set

## Static frontend

- pushes trigger the `deploy` workflow to `pnpm build` the site and upload to GitHub pages

## Local development

- create a venv, activate it, install requirements

    ```shell
    python -m venv .env
    . .env/bin/activate
    pip install -r infodump_tools/requirements.txt
    ```

- install Node (perhaps using nvm)

- install pnpm

- run `pnpm install`

- optionally, set `INFODUMP_USER_AGENT` environment variable to a string that identifies you (User-Agent header is set when downloading large Infodump files)

- run `python -m infodump_tools.download --dev infodump src/data/data.json`
  - this downloads Infodump files to the `infodump` directory and outputs stats to `src/data/data.json`. with the `-d|--dev` flag, we always regenerate the json, even if there is no new Infodump
  - we format the json with Prettier, for more readable diffs. `infodump_tools.download` calls `pnpx prettier`.

## Notebooks

- Jupyter notebooks (in `notebooks/`) are an easy way of developing and testing Polars expressions. They are not used to generate the live site. Install Jupyter kernel requirements from `notebooks/requirements.txt`.
