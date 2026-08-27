# Testbook Course Widgets – Responsive + Railway + Current-Cycle Fix

This package fixes three issues:

1. Mobile cards are readable (one card at a time on phones; no tiny/stretch layout).
2. Old explicit-year courses are hidden. In 2026, titles explicitly marked 2025 or older are excluded; 2026+, future-year and evergreen/no-year active courses remain.
3. Iframe height can auto-resize using `wordpress-auto-resize-iframe-snippet.html`, removing the large blank area below the widget.

## Widget URLs

- engineering.html
- railway.html
- ssc.html
- teaching.html
- state.html
- banking.html
- defence.html
- upsc.html
- ugc-net.html

`index.html` mirrors Engineering.

## Railway mapping

Railway combines:
- `SuperGroup = Railways Exams`
- `SuperGroup = Engineering Recruitment Exams` AND `Group = Railways`

This keeps RRB JE courses together with other Railway/RRB courses.

## Dropdown cleanup

Common discipline variants are grouped:
- RRB JE CE / EE / EC / ME -> RRB JE
- SSC JE CE / EE / ME -> SSC JE
- GATE CE / EE / EC / ME / CS -> GATE
- Year text is removed from dropdown labels.

## Auto update

The workflow uses existing repository secret `REDASH_API_KEY` and Redash Query 9085. It refreshes generated JSON on the schedule.

## WordPress iframe blank-space fix

Use `wordpress-auto-resize-iframe-snippet.html` once in the WordPress snippet/plugin layer. The GitHub widget pages send their actual height with `postMessage`, and the parent page updates the iframe height.

## Current repository workflow retained

The existing `.github/workflows/update-course-data.yml` from the uploaded GitHub repository is retained, including the working `Authorization: Key ...` Redash authentication. The updated Python generator automatically adds `data/railway.json` on the next workflow run.
