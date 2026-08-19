# Security

This is a personal automation project, not a widely-distributed package — this file exists mainly so a fix like the one described below never has to happen the hard way again.

## If you find something committed by mistake

If you notice real secrets, tokens, employee names/ID mappings, or other sensitive data committed to this repo (in the current tree **or** in git history), don't open a public issue describing it. Instead:

- If you have write access: fix it directly (extract to a local gitignored config, see `SECURITY.md` Category 1) and let the repo owner know what you found and where.
- If you don't: reach out to the repo owner directly rather than filing a public report — the point is to fix it before more people see it, not after.

## What this repo already does about it

- `scripts/check-repo-safe.sh` runs as a pre-commit hook (installed by `scripts/install.sh`) and blocks generic secret patterns, the specific "numeric-ID → real name" roster shape, and `.env` files staged despite `.gitignore`.
- `.gitignore` excludes all `.env` files, real sync configs (only `*.template.json` versions are committed), and scratch/experimental files.
- The public showcase mirror (this repo's public mirror) is never a direct push target — it's rebuilt on demand from a sanitized, squashed snapshot with company name, product names, and real identifiers replaced by generic placeholders. 

## Known limitation

If sensitive data was ever public (e.g. on a public GitHub remote) before being caught, rewriting git history stops *further* exposure but can't retroactively undo it — anyone who already cloned or forked before the fix may still have the old data, and GitHub can retain unreachable blobs in its cache for a period after a force-push. There's no way around this from git alone; ask affected people to re-clone, and involve GitHub support if a full cache purge is needed.
