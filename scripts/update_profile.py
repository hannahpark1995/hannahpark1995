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

profile = get(f'users/{USER}')
repos = [r for r in pages(f'users/{USER}/repos?type=owner') if not r['private']]
events = pages(f'users/{USER}/events/public', limit=3)
now = dt.datetime.now(dt.timezone.utc)
days = collections.Counter(e['created_at'][:10] for e in events)
langs = collections.Counter(r['language'] for r in repos if r.get('language') and not r['fork'])
parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="710" viewBox="0 0 1200 710" role="img" aria-labelledby="title desc">
<title id="title">Hannah's GitHub dashboard</title>
<desc id="desc">Onchain and AI builder. Public repository statistics, recent public activity and technology interests.</desc>
<style>text{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif;fill:#e6edf3}.muted{fill:#8b949e}.blue{fill:#58a6ff}.green{fill:#3fb950}.label{font-size:13px}.body{font-size:16px}.heading{font-size:18px;font-weight:600}.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}</style>
<rect width="1200" height="710" rx="20" fill="#0d1117"/>
<path d="M320 38V654M750 38V654" stroke="#21262d"/>
''']
def text(x,y,value,cls='body',extra=''):
    parts.append(f'<text x="{x}" y="{y}" class="{cls}" {extra}>{html.escape(str(value))}</text>')
def section(x,y,value):
    text(x,y,value,'heading blue')
def badge(x,y,w,label):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="30" rx="6" fill="#161b22" stroke="#30363d"/>')
    text(x+12,y+20,label,'label')
text(36,65,'HANNAH / BUILDER','label muted mono')
parts.append('<circle cx="83" cy="132" r="39" fill="#12241b" stroke="#238636"/>')
text(60,145,'hp','heading green', 'style="font-size:34px"')
text(36,213,'hannahpark1995','heading')
text(36,243,'Onchain × AI','body green')
text(36,290,'Exploring the intersection of','body muted')
text(36,315,'wallets, data, and agents.','body muted')
section(36,374,'Currently exploring')
for y,s in [(410,'Agents with their own wallets'),(440,'Stories hidden in onchain data'),(470,'Tools that make crypto simpler')]: text(36,y,s,'label muted')
section(36,538,'Build. Learn. Repeat.')
text(36,573,'Small tools. Open experiments.','label muted')
text(36,597,'One commit at a time.','label muted')
section(350,65,'GitHub overview')
for x,y,n,label in [(350,118,len(repos),'public repositories'),(550,118,sum(r['stargazers_count'] for r in repos),'repository stars'),(350,200,profile['followers'],'followers'),(550,200,sum(r['forks_count'] for r in repos),'repository forks')]:
    text(x,y,n,'heading', 'style="font-size:32px"');text(x,y+25,label,'label muted')
section(350,295,'Recent public activity')
text(350,323,'Public events by day · last 28 days','label muted')
counts=[days[(now.date()-dt.timedelta(days=27-i)).isoformat()] for i in range(28)]
peak=max(max(counts),1)
for i,n in enumerate(counts):
    h=4+70*n/peak
    parts.append(f'<rect x="{350+i*13}" y="{424-h}" width="9" height="{h}" rx="3" fill="{"#3fb950" if n else "#21262d"}"/>')
text(350,448,(now.date()-dt.timedelta(days=27)).strftime('%b %d'),'label muted')
text(655,448,now.strftime('%b %d'),'label muted')
text(350,482,f'{sum(counts)} public events in this window','label green')
text(350,507,'Events include pushes, issues, and pull requests.','label muted')
text(350,530,'Not the GitHub contributions calendar.','label muted')
section(350,588,'Languages in public repositories')
if langs:
    text(350,621,'  ·  '.join(f'{k} ({v})' for k,v in langs.most_common())[:60],'label muted')
else:
    text(350,621,'No language data available yet.','label muted')
section(780,65,'Interests & toolbox')
text(780,99,'Technologies I’m exploring','label muted')
for x,y,w,s in [(780,122,97,'TypeScript'),(887,122,79,'Python'),(976,122,83,'Solidity'),(780,164,87,'Next.js'),(877,164,95,'Tailwind'),(982,164,98,'Ethereum'),(780,206,65,'Base'),(855,206,79,'Solana'),(944,206,104,'AI agents')]: badge(x,y,w,s)
section(780,295,'Public projects')
projects=sorted([r for r in repos if r['name']!=USER],key=lambda r:r['pushed_at'] or '',reverse=True)[:3]
for i,r in enumerate(projects):
    y=333+i*88
    parts.append(f'<a href="{html.escape(r["html_url"],quote=True)}">')
    text(780,y,r['name'][:36],'body blue');parts.append('</a>')
    description=r.get('description') or 'An open experiment on GitHub.'
    text(780,y+24,description[:48] + ('…' if len(description)>48 else ''),'label muted')
    text(780,y+44,r.get('language') or 'Repository','label green')
if not projects: text(780,333,'More experiments coming soon.','body muted')
text(780,621,'gm. keep building.','body green mono')
parts.append('<path d="M36 654H1164" stroke="#21262d"/>')
text(36,684,'PUBLIC DATA ONLY / GITHUB API','label muted mono')
text(780,684,'Updated '+now.strftime('%Y-%m-%d %H:%M UTC'),'label muted')
parts.append('</svg>')
(ROOT/'dashboard.svg').write_text('\n'.join(parts))
