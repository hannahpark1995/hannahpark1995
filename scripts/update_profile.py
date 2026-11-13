"""Render a GitHub-safe SVG using only the account's public data."""
import collections
import datetime as dt
import html
import json
import os
from pathlib import Path
import urllib.request

USER = 'hannahpark1995'
ROOT = Path(__file__).resolve().parents[1]

def get(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'profile-dashboard'}
    if os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urllib.request.urlopen(urllib.request.Request('https://api.github.com/' + path, headers=headers)) as response:
        return json.load(response)

def pages(path, limit=None):
    result = []
    page = 1
    while True:
        batch = get(f'{path}{"&" if "?" in path else "?"}per_page=100&page={page}')
        result.extend(batch)
        if len(batch) < 100 or (limit and page >= limit):
            return result
        page += 1

# Calendar comes from the same public contribution grid shown on GitHub.
import base64
import re
from html.parser import HTMLParser

class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.counts = {}
        self.target = None
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'td' and a.get('data-date'):
            self.cells[a['id']] = (a['data-date'], int(a['data-level']))
        if tag == 'tool-tip':
            self.target = a.get('for')
    def handle_data(self, data):
        if self.target in self.cells:
            match = re.match(r'(No|[\d,]+) contributions?', data.strip())
            if match:
                self.counts[self.target] = 0 if match[1] == 'No' else int(match[1].replace(',', ''))
    def handle_endtag(self, tag):
        if tag == 'tool-tip':
            self.target = None

profile = get(f'users/{USER}')
repos = [r for r in pages(f'users/{USER}/repos?type=owner') if not r['private']]
now = dt.datetime.now(dt.timezone.utc)
with urllib.request.urlopen(f'https://github.com/users/{USER}/contributions') as response:
    calendar = Calendar()
    calendar.feed(response.read().decode())
if len(calendar.cells) < 350 or len(calendar.counts) != len(calendar.cells):
    raise RuntimeError('Public contribution calendar is incomplete; keeping previous dashboard')
daily = {date: calendar.counts[key] for key, (date, level) in calendar.cells.items()}
levels = {date: level for date, level in calendar.cells.values()}
languages = collections.Counter()
commits = {}
for repo in repos:
    if repo['fork']:
        continue
    languages.update(get(f'repos/{USER}/{repo["name"]}/languages'))
    if repo['size']:
        for commit in pages(f'repos/{USER}/{repo["name"]}/commits?author={USER}&since={(now-dt.timedelta(days=90)).isoformat()}', limit=3):
            if (commit.get('author') or {}).get('type') != 'Bot':
                commits[commit['sha']] = dt.datetime.fromisoformat(commit['commit']['author']['date'].replace('Z', '+00:00'))
hours = collections.Counter(d.hour for d in commits.values())
weekdays = collections.Counter((d.weekday()+1)%7 for d in commits.values())
parts = ['''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="720" viewBox="0 0 1200 720" role="img" aria-labelledby="title desc">
<title id="title">luckyzinzin — GitHub metrics</title>
<desc id="desc">Penguin portrait, GitHub statistics, hourly and weekly commit charts, a 3D contribution calendar, and language distribution.</desc>
<style>text{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif;fill:#c9d1d9}.muted{fill:#8b949e}.blue{fill:#58a6ff}.green{fill:#3fb950}.small{font-size:11px}.label{font-size:13px}.body{font-size:15px}.heading{font-size:17px;font-weight:600}</style>
<defs><clipPath id="avatar"><circle cx="134" cy="145" r="94"/></clipPath></defs>
<rect width="1200" height="720" rx="16" fill="#0d1117"/>
''']
def text(x,y,value,cls='body',extra=''):
    parts.append(f'<text x="{x}" y="{y}" class="{cls}" {extra}>{html.escape(str(value))}</text>')
def section(x,y,value): text(x,y,value,'heading blue')
def rect(x,y,w,h,fill,rx=0):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"/>')
def poly(points,fill):
    parts.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in points)}" fill="{fill}"/>')
image = base64.b64encode((ROOT/'assets/avatar.png').read_bytes()).decode()
parts.append(f'<image x="40" y="51" width="188" height="188" clip-path="url(#avatar)" xlink:href="data:image/png;base64,{image}"/>')
parts.append('<circle cx="134" cy="145" r="95" fill="none" stroke="#30363d"/>')
text(38,285,'luckyzinzin','heading','style="font-size:28px"')
text(38,314,'Onchain × AI builder','body muted')
text(38,360,'gm. keep building.','body green')
for y,line in [(398,'Agents with their own wallets.'),(422,'Stories hidden in onchain data.'),(446,'Tools that make crypto simpler.')]: text(38,y,line,'label muted')
text(38,505,'CURRENTLY EXPLORING','small muted')
for i,line in enumerate(['AI agents & automation','Onchain data & smart contracts','Small tools, open experiments']): text(38,535+i*26,line,'label')
text(38,649,'Build. Learn. Repeat.','body green')
section(305,57,'◉ GitHub overview')
text(305,89,'Joined GitHub '+profile['created_at'][:10],'label muted')
for x,y,n,label in [(305,125,len(repos),'Public repos'),(495,125,sum(r['stargazers_count'] for r in repos),'Stars'),(305,158,profile['followers'],'Followers'),(495,158,sum(r['forks_count'] for r in repos),'Forks')]:
    text(x,y,f'{n}  {label}','body')
text(305,193,f'{sum(daily.values())} contributions in the last year','label green')
section(305,241,'◷ Coding habits')
text(305,267,'Commits by hour · UTC','label blue')
def bars(x,y,width,height,values,labels):
    maximum=max(max(values),1)
    step=width/len(values)
    for i,n in enumerate(values):
        h=height*n/maximum
        rect(x+i*step+2,y-h,max(4,step*.48),max(h,3),'#238636' if n else '#21262d',3)
        if n: text(x+i*step+2,y-h-6,n,'small muted')
        text(x+i*step+1,y+18,labels[i],'small muted')
bars(305,365,390,65,[hours[i] for i in range(24)],[str(i).zfill(2) if i%2==0 else '' for i in range(24)])
text(305,424,'Commits by weekday','label blue')
bars(305,527,185,70,[weekdays[i] for i in range(7)],['S','M','T','W','T','F','S'])
text(515,424,'Language activity','label blue')
colors={'Python':'#3572A5','TypeScript':'#3178c6','JavaScript':'#f1e05a','HTML':'#e34c26','CSS':'#563d7c','Solidity':'#AA6746','Shell':'#89e051'}
total=sum(languages.values())
for i,(name,value) in enumerate(languages.most_common(4)):
    y=455+i*27
    text(515,y,name,'small muted')
    rect(590,y-9,83,7,'#21262d',3)
    rect(590,y-9,83*value/total,7,colors.get(name,'#3fb950'),3)
    text(682,y,f'{value/total:.0%}','small muted')
if not languages: text(515,459,'No language data yet','small muted')
text(305,577,f'{len(commits)} authored commits sampled · last 90 days','small muted')
section(305,616,'⌘ Technologies I’m exploring')
for i,(name,color) in enumerate([('TS','#3178c6'),('PY','#3572a5'),('SOL','#AA6746'),('Next','#30363d'),('ETH','#627eea'),('Base','#0052ff'),('AI','#238636')]):
    rect(305+i*55,635,44,30,color,6)
    text(327+i*55,655,name,'label','text-anchor="middle"')
section(750,57,'▦ Contributions calendar')
text(750,84,'Real GitHub contributions · last 52 weeks','label muted')
# Isometric columns: one cell per day, height proportional to real contributions.
dates=sorted(daily)[-364:]
start=dt.date.fromisoformat(dates[0])
for date in dates:
    index=(dt.date.fromisoformat(date)-start).days
    week,day=divmod(index,7)
    x=800+week*5.7-day*8.2
    y=122+week*2.45+day*4.7
    n=daily[date]
    h=min(44,4+n*4) if n else 0
    level=levels[date]
    top=['#212b2a','#0e4429','#006d32','#26a641','#39d353'][level]
    if n:
        poly([(x,y-h),(x+5.4,y+2.3-h),(x+5.4,y+2.3),(x,y)],'#17622f')
        poly([(x+5.4,y+2.3-h),(x-2.5,y+6.8-h),(x-2.5,y+6.8),(x+5.4,y+2.3)],'#238636')
    parts.append(f'<g><title>{date}: {n} contributions</title>')
    poly([(x,y-h),(x+5.4,y+2.3-h),(x-2.5,y+6.8-h),(x-7.9,y+4.5-h)],top)
    parts.append('</g>')
text(750,321,f'{sum(daily[d] for d in dates)} contributions','body green')
text(1000,321,'Less','small muted')
for i,c in enumerate(['#212b2a','#0e4429','#006d32','#26a641','#39d353']): rect(1031+i*14,311,10,10,c,2)
text(1106,321,'More','small muted')
section(750,375,'◉ Most used languages')
if total:
    x=750
    for name,value in languages.most_common():
        width=410*value/total
        rect(x,401,width,10,colors.get(name,'#3fb950'),2); x+=width
    for i,(name,value) in enumerate(languages.most_common(6)):
        x=750+(i%2)*205; y=438+(i//2)*24
        parts.append(f'<circle cx="{x+4}" cy="{y-4}" r="4" fill="{colors.get(name,"#3fb950")}"/>')
        text(x+15,y,f'{name} {value/total:.1%}','label muted')
else: text(750,413,'No language data yet.','label muted')
section(750,545,'⌁ Recent public projects')
projects=sorted([r for r in repos if r['name']!=USER],key=lambda r:r['pushed_at'] or '',reverse=True)[:3]
for i,r in enumerate(projects):
    y=578+i*32
    text(750,y,r['name'][:42],'label blue')
    text(1148,y,r.get('language') or '—','small muted','text-anchor="end"')
rect(38,685,1124,1,'#21262d')
text(38,705,'Public GitHub data · Contribution calendar + authored commit sample','small muted')
text(1162,705,'Updated '+now.strftime('%Y-%m-%d %H:%M UTC'),'small muted','text-anchor="end"')
parts.append('</svg>')
(ROOT/'dashboard.svg').write_text('\n'.join(parts))
