#!/usr/bin/env python3
"""Build all course JSON feeds and widget pages from Redash Query 9085."""

import csv
import html
import json
import re
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path


LEGACY_CONFIGS = OrderedDict([
    ("engineering", {
        "title": "Active Engineering Courses",
        "subtitle": "Explore AE/JE coaching courses or select an exam.",
        "filters": [("Engineering Recruitment Exams", "")],
    }),
    ("railway", {
        "title": "Active Railway Courses",
        "subtitle": "Explore RRB and Railway coaching courses or select an exam.",
        "filters": [
            ("Railways Exams", ""),
            ("Engineering Recruitment Exams", "Railways"),
        ],
    }),
    ("ssc", {
        "title": "Active SSC Courses",
        "subtitle": "Explore SSC coaching courses or select an exam.",
        "filters": [("SSC Exams", "")],
    }),
    ("banking", {
        "title": "Active Banking Courses",
        "subtitle": "Explore banking coaching courses or select an exam.",
        "filters": [("Banking Exams", "")],
    }),
    ("defence", {
        "title": "Active Defence Courses",
        "subtitle": "Explore defence coaching courses or select an exam.",
        "filters": [("Defence Exams", "")],
    }),
    ("teaching", {
        "title": "Active Teaching Courses",
        "subtitle": "Explore teaching coaching courses or select an exam.",
        "filters": [("Teaching Exams", "")],
    }),
    ("state", {
        "title": "Active State Government Courses",
        "subtitle": "Explore state government coaching courses or select an exam.",
        "filters": [("State Govt. Exams", "")],
    }),
    ("upsc", {
        "title": "Active UPSC Courses",
        "subtitle": "Explore UPSC coaching courses or select an exam.",
        "filters": [("Civil Services Exam", "UPSC")],
    }),
    ("ugc-net", {
        "title": "Active UGC NET Courses",
        "subtitle": "Explore UGC NET coaching courses or select an exam.",
        "filters": [("Teaching Exams", "NET")],
    }),
])

REQUIRED_COLUMNS = {
    "_id", "title", "isDelisted", "classType", "courseLang",
    "SuperGroup", "Group", "releaseDate", "courseExpiry",
    "frontEndLink", "courseCreative", "targetName",
}

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{title}</title>
  <link rel="stylesheet" href="./widget.css">
</head>
<body>
  <div id="tbCourseWidget"
       class="tb-course-widget"
       data-category="{category}"
       data-data-url="./data/{category}.json"
       data-title="{title}"
       data-subtitle="{subtitle}">
    <div class="tb-course-message">Loading active courses...</div>
  </div>
  <script src="./widget.js"></script>
</body>
</html>
"""


def norm(value):
    return str(value or "").strip().lower()


def false_value(value):
    return norm(value) in {"false", "0"}


def parse_date(value):
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None)
    except ValueError:
        return None


def normalize_url(value):
    url = str(value or "").strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://testbook.com" + url
    if url.startswith("http://"):
        return "https:" + url[5:]
    return url if url.startswith("https://") else ""


def normalize_image(value):
    image = str(value or "").strip()
    if image.startswith("//"):
        return "https:" + image
    if image.startswith("http://"):
        return "https:" + image[5:]
    return image


def title_years(title):
    text = str(title or "")
    years = [int(value) for value in re.findall(r"\b20\d{2}\b", text)]
    for start, end in re.findall(r"\b(20\d{2})\s*[-/]\s*(\d{2})\b", text):
        years.append((int(start) // 100) * 100 + int(end))
    return set(years)


def course_year_score(course, current_year):
    years = title_years(course.get("title"))
    if current_year in years:
        return 3
    if any(year > current_year for year in years):
        return 2
    if not years:
        return 1
    return 0


def course_sort_key(course, current_year):
    release = parse_date(course.get("releaseDate"))
    stamp = release.timestamp() if release else 0
    return (-course_year_score(course, current_year), -stamp, norm(course.get("title")))


def slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "-", norm(value)).strip("-")
    return slug[:80] or "category"


def matches_filter(row, filters):
    for supergroup, group in filters:
        if norm(row.get("SuperGroup")) != norm(supergroup):
            continue
        if group and norm(row.get("Group")) != norm(group):
            continue
        return True
    return False


def to_course(row):
    return {
        "id": str(row.get("_id", "")).strip(),
        "title": str(row.get("title", "")).strip(),
        "isDelisted": row.get("isDelisted", ""),
        "type": row.get("classType", ""),
        "language": row.get("courseLang", ""),
        "superGroup": str(row.get("SuperGroup", "")).strip(),
        "group": str(row.get("Group", "")).strip(),
        "releaseDate": row.get("releaseDate", ""),
        "expiryDate": row.get("courseExpiry", ""),
        "url": normalize_url(row.get("frontEndLink", "")),
        "image": normalize_image(row.get("courseCreative", "")),
        "targetName": row.get("targetName", ""),
    }


def is_valid_active(row, today):
    if not false_value(row.get("isDelisted")):
        return False
    if not str(row.get("title", "")).strip() or not normalize_url(row.get("frontEndLink", "")):
        return False
    release = parse_date(row.get("releaseDate"))
    expiry = parse_date(row.get("courseExpiry"))
    if release and release.date() > today:
        return False
    if expiry and expiry.date() < today:
        return False
    return True


def dedupe_and_sort(courses, current_year):
    unique = []
    seen = set()
    for course in courses:
        course_id = course.get("id")
        if course_id and course_id in seen:
            continue
        if course_id:
            seen.add(course_id)
        unique.append(course)
    unique.sort(key=lambda course: course_sort_key(course, current_year))
    return unique


def write_feed(out_dir, slug, courses, current_year, supergroup=None):
    payload = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "currentYear": current_year,
        "superGroup": supergroup or "",
        "courses": courses,
    }
    (out_dir / f"{slug}.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def write_page(root_dir, slug, title, subtitle):
    content = PAGE_TEMPLATE.format(
        category=html.escape(slug, quote=True),
        title=html.escape(title, quote=True),
        subtitle=html.escape(subtitle, quote=True),
    )
    (root_dir / f"{slug}.html").write_text(content, encoding="utf-8")


def main():
    if len(sys.argv) < 3:
        raise SystemExit("Usage: update_course_data.py <input.csv> <output-dir>")
    source = Path(sys.argv[1])
    data_dir = Path(sys.argv[2])
    root_dir = data_dir.parent
    data_dir.mkdir(parents=True, exist_ok=True)

    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    missing = REQUIRED_COLUMNS - set(rows[0].keys() if rows else [])
    if missing:
        raise SystemExit("Missing CSV columns: " + ", ".join(sorted(missing)))

    now = datetime.now()
    today = now.date()
    current_year = now.year
    active_rows = [row for row in rows if is_valid_active(row, today)]

    # Every unique Redash SuperGroup receives its own stable slug/feed/page.
    supergroups = OrderedDict()
    for row in rows:
        name = str(row.get("SuperGroup", "")).strip()
        if name and norm(name) not in supergroups:
            supergroups[norm(name)] = name

    used_slugs = set(LEGACY_CONFIGS)
    dynamic_categories = []
    for key, name in supergroups.items():
        base = slugify(name)
        slug = base
        suffix = 2
        while slug in used_slugs:
            slug = f"{base}-{suffix}"
            suffix += 1
        used_slugs.add(slug)
        courses = dedupe_and_sort(
            [to_course(row) for row in active_rows if norm(row.get("SuperGroup")) == key],
            current_year,
        )
        write_feed(data_dir, slug, courses, current_year, name)
        write_page(root_dir, slug, f"Active {name} Courses", f"Explore {name} coaching courses or select an exam.")
        dynamic_categories.append({
            "name": name,
            "slug": slug,
            "dataUrl": f"./data/{slug}.json",
            "htmlUrl": f"./{slug}.html",
            "courseCount": len(courses),
        })
        print(f"supergroup {name}: {len(courses)}")

    legacy_categories = []
    for slug, config in LEGACY_CONFIGS.items():
        courses = dedupe_and_sort(
            [to_course(row) for row in active_rows if matches_filter(row, config["filters"])],
            current_year,
        )
        write_feed(data_dir, slug, courses, current_year, slug)
        write_page(root_dir, slug, config["title"], config["subtitle"])
        legacy_categories.append({
            "name": config["title"].replace("Active ", "").replace(" Courses", ""),
            "slug": slug,
            "dataUrl": f"./data/{slug}.json",
            "htmlUrl": f"./{slug}.html",
            "courseCount": len(courses),
        })
        print(f"{slug}: {len(courses)}")

    # index.html has always mirrored Engineering and remains a stable alias.
    write_page(root_dir, "index", LEGACY_CONFIGS["engineering"]["title"], LEGACY_CONFIGS["engineering"]["subtitle"])

    categories_payload = {
        "generatedAt": now.isoformat(timespec="seconds"),
        "currentYear": current_year,
        "categories": dynamic_categories + legacy_categories,
        "legacyAliases": {
            "index": "engineering",
            **{slug: slug for slug in LEGACY_CONFIGS},
        },
    }
    (data_dir / "categories.json").write_text(
        json.dumps(categories_payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
