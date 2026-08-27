#!/usr/bin/env python3
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Each category can match one or more (SuperGroup, Group) pairs.
CONFIGS = {
    "engineering": [("Engineering Recruitment Exams", "")],
    "railway": [
        ("Railways Exams", ""),
        # RRB JE courses are also maintained under Engineering Recruitment Exams.
        ("Engineering Recruitment Exams", "Railways"),
    ],
    "ssc": [("SSC Exams", "")],
    "teaching": [("Teaching Exams", "")],
    "state": [("State Govt. Exams", "")],
    "banking": [("Banking Exams", "")],
    "defence": [("Defence Exams", "")],
    "upsc": [("Civil Services Exam", "UPSC")],
    "ugc-net": [("Teaching Exams", "NET")],
}

CURRENT_YEAR = datetime.now().year

def norm(v):
    return str(v or "").strip().lower()

def false_value(v):
    return norm(v) in {"false", "0"}

def parse_date(v):
    s = str(v or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None

def title_years(title):
    text = str(title or "")
    years = [int(x) for x in re.findall(r"\b20\d{2}\b", text)]
    for a, b in re.findall(r"\b(20\d{2})\s*[-/]\s*(\d{2})\b", text):
        years.append((int(a) // 100) * 100 + int(b))
    return sorted(set(years))

def current_cycle(row):
    years = title_years(row.get("title"))
    return not years or max(years) >= CURRENT_YEAR

def matches_category(row, filters):
    for sg, group in filters:
        if norm(row.get("SuperGroup")) != norm(sg):
            continue
        if group and norm(row.get("Group")) != norm(group):
            continue
        return True
    return False

def sort_key(course):
    years = title_years(course.get("title"))
    if CURRENT_YEAR in years:
        score = 4
    elif any(y > CURRENT_YEAR for y in years):
        score = 3
    elif not years:
        score = 2
    else:
        score = 1
    rd = parse_date(course.get("releaseDate"))
    stamp = rd.timestamp() if rd else 0
    return (score, stamp)

def main():
    if len(sys.argv) < 3:
        raise SystemExit("Usage: update_course_data.py <input.csv> <output-dir>")
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)

    with src.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    required = {
        "_id", "title", "isDelisted", "classType", "courseLang",
        "SuperGroup", "Group", "releaseDate", "courseExpiry",
        "frontEndLink", "courseCreative", "targetName"
    }
    missing = required - set(rows[0].keys() if rows else [])
    if missing:
        raise SystemExit("Missing CSV columns: " + ", ".join(sorted(missing)))

    today = datetime.now().date()

    for cat, filters in CONFIGS.items():
        courses = []
        seen = set()
        for r in rows:
            if not matches_category(r, filters):
                continue
            if not false_value(r.get("isDelisted")):
                continue
            if not str(r.get("title", "")).strip() or not str(r.get("frontEndLink", "")).strip():
                continue
            release = parse_date(r.get("releaseDate"))
            expiry = parse_date(r.get("courseExpiry"))
            if release and release.date() > today:
                continue
            if expiry and expiry.date() < today:
                continue
            if not current_cycle(r):
                continue
            cid = str(r.get("_id", "")).strip()
            if cid and cid in seen:
                continue
            if cid:
                seen.add(cid)
            img = str(r.get("courseCreative", "")).strip()
            if img.startswith("//"):
                img = "https:" + img
            courses.append({
                "id": cid,
                "title": r.get("title", ""),
                "isDelisted": r.get("isDelisted", ""),
                "type": r.get("classType", ""),
                "language": r.get("courseLang", ""),
                "superGroup": r.get("SuperGroup", ""),
                "group": r.get("Group", ""),
                "releaseDate": r.get("releaseDate", ""),
                "expiryDate": r.get("courseExpiry", ""),
                "url": r.get("frontEndLink", ""),
                "image": img,
                "targetName": r.get("targetName", ""),
            })

        courses.sort(key=sort_key, reverse=True)
        payload = {
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "currentYear": CURRENT_YEAR,
            "courses": courses,
        }
        (out / f"{cat}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        print(cat, len(courses))

if __name__ == "__main__":
    main()
