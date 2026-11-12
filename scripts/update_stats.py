"""Generate public GitHub SVGs with Python's standard library.

No private repository data, API responses or credentials are saved. API failure
leaves the previously generated widgets intact. Run with GITHUB_TOKEN in env.
"""
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
USER = "G0d0v"
PROGRAMMING = {"Python", "TypeScript", "JavaScript", "PHP", "Java", "Go", "Rust", "C", "C++", "C#"}
COLORS = {"Python": "#69b7ff", "TypeScript": "#a78bfa", "JavaScript": "#e8d47a"}


def request_json(path, token, payload=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "G0d0v-profile",
               "Authorization": "Bearer " + token, "X-GitHub-Api-Version": "2022-11-28"}
    body = json.dumps(payload).encode() if payload is not None else None
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request("https://api.github.com" + path, data=body, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def streaks(days, today):
    """Accept yesterday while today's activity is pending; ignore future days."""
    counts = {date.fromisoformat(d["date"]): d["contributionCount"] for d in days}
    longest = run = 0
    previous = None
    for day in sorted(d for d in counts if d <= today):
        if counts[day] > 0:
            run = run + 1 if previous == day - timedelta(days=1) else 1
            longest = max(longest, run)
        else:
            run = 0
        previous = day
    cursor = today if counts.get(today, 0) else today - timedelta(days=1)
    current = 0
    while counts.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    return current, longest


def language_totals(repositories):
    total = Counter()
    for repo in repositories:
        if repo.get("private") or repo["name"].lower() == USER.lower():
            continue
        total.update({k: v for k, v in repo["languages"].items() if k in PROGRAMMING})
    return total


def text(x, y, content, size=18, color="#e6edf3", weight=400):
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'font-weight="{weight}">{escape(str(content))}</text>')


def card(width, height, title, parts):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>'
            '<style>text{font-family:Arial,Helvetica,sans-serif}</style>'
            f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="16" '
            'fill="#0d1117" stroke="#30363d"/>' + "".join(parts) + '</svg>\n')


def stats_svg(repository_count, contributions, current, longest, updated):
    parts = [text(28, 40, "GitHub / public activity", 22, "#a78bfa", 600)]
    for x, y, value, label in [(28, 100, repository_count, "Public repositories"),
                               (338, 100, contributions, "Contributions / last year"),
                               (28, 190, current, "Current streak / days"),
                               (338, 190, longest, "Longest streak / last year")]:
        parts += [text(x, y, value, 38, "#69b7ff", 700), text(x, y+27, label, 18, "#b1bac4")]
    parts.append(text(28, 258, "Updated " + updated + " UTC", 14, "#8b949e"))
    return card(640, 278, "GitHub public activity", parts)


def languages_svg(totals):
    parts = [text(28, 40, "Programming languages / public project code", 21, "#a78bfa", 600)]
    count = sum(totals.values())
    entries = totals.most_common()
    for index, (language, amount) in enumerate(entries):
        y = 82 + index*57
        share = amount/count if count else 0
        color = COLORS.get(language, "#69b7ff")
        parts += [text(28, y, language, 19), text(535, y, f"{share:.1%}", 18, "#b1bac4"),
                  f'<rect x="28" y="{y+12}" width="584" height="7" rx="3" fill="#21262d"/>',
                  f'<rect x="28" y="{y+12}" width="{584*share:.2f}" height="7" rx="3" fill="{color}"/>']
    height = max(175, 100 + len(entries)*57)
    if not entries:
        parts.append(text(28, 90, "No programming language data available", 18, "#b1bac4"))
    parts.append(text(28, height-22, "Code volume; forks included; profile repository excluded.", 15, "#8b949e"))
    return card(640, height, "Public programming language distribution", parts)


def calendar_svg(calendar):
    parts = [text(26, 38, "Contribution activity / last year", 22, "#a78bfa", 600)]
    weeks = calendar["weeks"]
    maximum = max((d["contributionCount"] for w in weeks for d in w["contributionDays"]), default=1)
    shades = ["#161b22", "#243950", "#32628b", "#588cce", "#a78bfa"]
    previous_month = None
    for column, week in enumerate(weeks):
        for day in week["contributionDays"]:
            when = date.fromisoformat(day["date"])
            row = (when.weekday()+1) % 7
            x, y = 28+column*15, 76+row*15
            count = day["contributionCount"]
            level = 0 if count == 0 else min(4, 1+int(3*count/max(1, maximum)))
            parts.append(f'<rect x="{x}" y="{y}" width="11" height="11" rx="2" fill="{shades[level]}">'
                         f'<title>{when.isoformat()}: {count} contributions</title></rect>')
        if week["contributionDays"]:
            first = date.fromisoformat(week["contributionDays"][0]["date"])
            if first.month != previous_month:
                parts.append(text(28+column*15, 65, first.strftime("%b"), 12, "#8b949e"))
                previous_month = first.month
    parts.append(text(28, 220, f'{calendar["totalContributions"]} contributions · GitHub contribution calendar', 17, "#b1bac4"))
    return card(860, 247, "GitHub contribution calendar", parts)


def collect(token):
    repositories = []
    page = 1
    while True:
        batch = request_json(f"/users/{USER}/repos?type=owner&per_page=100&page={page}", token)
        repositories += [repo for repo in batch if not repo["private"]]
        if len(batch) < 100:
            break
        page += 1
    for repo in repositories:
        repo["languages"] = request_json(f'/repos/{USER}/{repo["name"]}/languages', token)
    query = '''query { user(login: "G0d0v") { contributionsCollection {
      contributionCalendar { totalContributions weeks {
        contributionDays { date contributionCount } } } } } }'''
    result = request_json("/graphql", token, {"query": query})
    if result.get("errors") or not result.get("data", {}).get("user"):
        raise RuntimeError("GitHub contribution calendar is unavailable; previous SVGs preserved")
    return repositories, result["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def main(token=None):
    token = token or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required for GitHub's GraphQL API")
    repositories, calendar = collect(token)
    days = [d for w in calendar["weeks"] for d in w["contributionDays"]]
    today = datetime.now(timezone.utc).date()
    current, longest = streaks(days, today)
    outputs = {
        "github-stats.svg": stats_svg(len(repositories), calendar["totalContributions"], current, longest, today.isoformat()),
        "top-languages.svg": languages_svg(language_totals(repositories)),
        "contributions.svg": calendar_svg(calendar),
    }
    from xml.etree import ElementTree
    for content in outputs.values():
        ElementTree.fromstring(content)
    for filename, content in outputs.items():
        target = ROOT / "assets" / filename
        temporary = target.with_suffix(".svg.tmp")
        temporary.write_text(content, encoding="utf-8", newline="\n")
        temporary.replace(target)
    print("Updated 3 public SVG widgets; no credentials or API responses were saved.")


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        raise SystemExit(f"GitHub API HTTP {error.code}; existing widgets preserved") from None
    except URLError:
        raise SystemExit("GitHub API connection failed; existing widgets preserved") from None
