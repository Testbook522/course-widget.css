# Testbook Course Widgets - Auto Update

This version avoids browser CORS issues. GitHub Actions fetches Redash query 9085 every 5 minutes using a repository secret named `REDASH_API_KEY`, generates sanitized category JSON in `/data`, and the GitHub Pages widgets fetch those same-origin JSON files.

Setup: upload everything in this ZIP preserving folders, add repository secret `REDASH_API_KEY`, enable Actions, then run `Update Course Widget Data` once manually.
