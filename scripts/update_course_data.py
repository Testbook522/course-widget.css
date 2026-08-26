#!/usr/bin/env python3
import csv, json, sys
from datetime import datetime, timezone
from pathlib import Path

CONFIGS = {
    "engineering": ("Engineering Recruitment Exams", ""),
    "ssc": ("SSC Exams", ""),
    "teaching": ("Teaching Exams", ""),
    "state": ("State Govt. Exams", ""),
    "banking": ("Banking Exams", ""),
    "defence": ("Defence Exams", ""),
    "upsc": ("Civil Services Exam", "UPSC"),
    "ugc-net": ("Teaching Exams", "NET"),
}

def norm(v): return str(v or "").strip().lower()
def false_value(v): return norm(v) in {"false", "0"}

def parse_date(v):
    s = str(v or "").strip()
    if not s: return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try: return datetime.strptime(s, fmt)
        except ValueError: pass
    try: return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError: return None

def normalize_url(v):
    url = str(v or "").strip()
    if url.startswith("//"): return "https:" + url
    if url.startswith("/"): return "https://testbook.com" + url
    if url.startswith("http://"): return "https:" + url[5:]
    return url if url.startswith("https://") else ""

def is_2026(course):
    fields = " ".join(str(course.get(k, "")) for k in ("title", "targetName", "url"))
    return "2026" in fields

def course_sort_key(course):
    release = parse_date(course.get("releaseDate"))
    return (
        0 if is_2026(course) else 1,
        -(release.toordinal() if release else 0),
        norm(course.get("title")),
    )

def main():
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    with src.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    required = {
        "_id", "title", "isDelisted", "classType", "courseLang",
        "SuperGroup", "Group", "releaseDate", "courseExpiry",
        "frontEndLink", "courseCreative", "targetName",
    }
    missing = required - set(rows[0].keys() if rows else [])
    if missing:
        raise SystemExit("Missing CSV columns: " + ", ".join(sorted(missing)))
    now = datetime.now()
    for cat, (sg, group) in CONFIGS.items():
        courses = []
        for r in rows:
            if norm(r.get("SuperGroup")) != norm(sg): continue
            if group and norm(r.get("Group")) != norm(group): continue
            if not false_value(r.get("isDelisted")): continue
            title = str(r.get("title", "")).strip()
            url = normalize_url(r.get("frontEndLink", ""))
            if not title or not url: continue
            release = parse_date(r.get("releaseDate"))
            expiry = parse_date(r.get("courseExpiry"))
            if release and release.date() > now.date(): continue
            if expiry and expiry.date() < now.date(): continue
            img = str(r.get("courseCreative", "")).strip()
            if img.startswith("//"): img = "https:" + img
            courses.append({
                "id": r.get("_id", ""),
                "title": title,
                "isDelisted": r.get("isDelisted", ""),
                "type": r.get("classType", ""),
                "language": r.get("courseLang", ""),
                "superGroup": r.get("SuperGroup", ""),
                "group": r.get("Group", ""),
                "releaseDate": r.get("releaseDate", ""),
                "expiryDate": r.get("courseExpiry", ""),
                "url": url,
                "image": img,
                "targetName": r.get("targetName", ""),
            })
        courses.sort(key=course_sort_key)
        (out / f"{cat}.json").write_text(
            json.dumps({"courses": courses}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        print(cat, len(courses))

if __name__ == "__main__":
    main()
