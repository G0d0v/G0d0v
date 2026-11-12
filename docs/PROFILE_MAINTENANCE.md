# Profile maintenance

## Data and attribution

Language data comes from GitHub's REST `languages` endpoint, which reports GitHub
Linguist results in bytes. The programming-language widget excludes markup,
configuration languages, private repositories, and this profile repository.
Forks remain included; their code volumes do not imply authorship or proficiency.

Statistics and streaks use GitHub's GraphQL contribution calendar. The longest
streak is bounded by the returned year, not lifetime. The current streak accepts
yesterday when today has no contributions yet. These widgets cannot represent
all work outside public GitHub.

Selected work outside GitHub is described at a product level. Do not publish
private source, deployment details, credentials, or unpublished repository links.
Remnawave SHOP retains attribution to CyberERROR/remnawave-shopbot and its MIT license.

## Update statistics

Run the **Refresh profile statistics** workflow manually, or let its daily schedule
run at 03:17 UTC. It uses the built-in repository-scoped `GITHUB_TOKEN`, not a stored
personal token. Only the three generated SVGs are committed by the bot. API failure
preserves the previous widgets and fails the workflow visibly.

Local use: supply `GITHUB_TOKEN` securely and run `python scripts/update_stats.py`.
Never commit tokens, environment files, API responses, or credential-manager helpers.
Tests: `python -m unittest discover -s tests -v`.

## Header

`python scripts/render_header.py` requires Pillow, NumPy, FFmpeg, and installed
Manrope. Use `--font PATH` for an existing font. No assets are downloaded.
The lunar animation is original procedural artwork. The README selects its PNG
when `prefers-reduced-motion: reduce` is active.

## License

This profile repository has no blanket software license. Another project's
code must not be relicensed through this profile. Technology icons are served
by Skill Icons and remain subject to their respective licenses.
