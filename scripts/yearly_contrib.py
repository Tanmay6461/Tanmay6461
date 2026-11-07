"""Generate one simple GitHub-style contribution heatmap SVG per year (light + dark)."""
import datetime as dt
import json
import os
import urllib.request

USER = os.environ["USERNAME"]
TOKEN = os.environ["GITHUB_TOKEN"]
START_YEAR = 2024
OUT = "yearly-contrib"

THEMES = {
    "light": {"text": "#57606a", "levels": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]},
    "dark": {"text": "#8b949e", "levels": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]},
}
LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
QUERY = """query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){contributionsCollection(from:$f,to:$t){
contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""


def gql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", body,
                                 {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json",
                                  "User-Agent": "yearly-contrib-script"})
    return json.load(urllib.request.urlopen(req))["data"]["user"]


def fetch(year):
    data = gql(QUERY, {"u": USER, "f": f"{year}-01-01T00:00:00Z", "t": f"{year}-12-31T23:59:59Z"})
    return data["contributionsCollection"]["contributionCalendar"]


def render_total(total, since, theme):
    c = THEMES[theme]
    font = 'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif"'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="300" height="100" viewBox="0 0 300 100">'
            f'<text x="150" y="48" text-anchor="middle" {font} font-size="34" font-weight="700" '
            f'fill="{c["levels"][3]}">{total:,}</text>'
            f'<text x="150" y="72" text-anchor="middle" {font} font-size="14" font-weight="600" '
            f'fill="{c["text"]}">Total Contributions</text>'
            f'<text x="150" y="90" text-anchor="middle" {font} font-size="11" fill="{c["text"]}">'
            f'{since} – Present</text></svg>')


def render(year, cal, theme):
    c = THEMES[theme]
    cell, gap, left, top = 11, 3, 30, 36
    weeks = cal["weeks"]
    width = left + len(weeks) * (cell + gap) + 10
    height = top + 7 * (cell + gap) + 6
    font = 'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif"'
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           f'<text x="{left}" y="14" {font} font-size="13" font-weight="600" fill="{c["text"]}">'
           f'{year} · {cal["totalContributions"]:,} contributions</text>']
    last_month = None
    for wi, week in enumerate(weeks):
        x = left + wi * (cell + gap)
        for day in week["contributionDays"]:
            d = dt.date.fromisoformat(day["date"])
            if d.day <= 7 and d.month != last_month and day is week["contributionDays"][0] or (wi == 0 and last_month is None):
                last_month = d.month
                out.append(f'<text x="{x}" y="30" {font} font-size="9" fill="{c["text"]}">{d.strftime("%b")}</text>')
            y = top + ((d.weekday() + 1) % 7) * (cell + gap)
            color = c["levels"][LEVEL[day["contributionLevel"]]]
            out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{color}">'
                       f'<title>{day["date"]}: {day["contributionCount"]}</title></rect>')
    for i, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="0" y="{top + i * (cell + gap) + 9}" {font} font-size="9" fill="{c["text"]}">{label}</text>')
    out.append("</svg>")
    return "\n".join(out)


os.makedirs(OUT, exist_ok=True)
created = dt.date.fromisoformat(gql("query($u:String!){user(login:$u){createdAt}}", {"u": USER})["createdAt"][:10])
total = 0
for year in range(created.year, dt.date.today().year + 1):
    cal = fetch(year)
    total += cal["totalContributions"]
    if year < START_YEAR:
        continue
    for theme in THEMES:
        with open(f"{OUT}/{year}-{theme}.svg", "w") as f:
            f.write(render(year, cal, theme))
    print(year, cal["totalContributions"])

for theme in THEMES:
    with open(f"{OUT}/total-{theme}.svg", "w") as f:
        f.write(render_total(total, created.strftime("%b %Y"), theme))
print("total", total)
