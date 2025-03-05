# Typescript Build Env for JupyterHub server assets

# Adding new asset exports
Specify assets to export in the "inputs" option in `rollup.config.mjs`. See Rollup Docs.

# Referencing exported assets in a jupyterhub template
If a file is exported using entriesFromGlob, it will be available at the same subpath on `hub/static/ts/[file]` as it lives in `/ts/src/[file]`

E.G.

`src/templates/login.ts` exported with `entriesFromGlob("templates/**/*.ts")` can be referenced in a jinja template with: `{{ static_url('ts/templates/login.js') }}`