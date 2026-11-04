#!/usr/bin/env python3
"""Gera todos os SVGs do README de perfil a partir de dados reais do GitHub.

Só usa a biblioteca padrão. Roda diariamente em .github/workflows/snake.yml.

Uso local:
    GITHUB_TOKEN=$(gh auth token) python3 scripts/generate.py --out dist
"""
import argparse
import base64
import json
import math
import os
import random
import re
import urllib.request
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

LOGIN = "GustaReis-bit"
ASSETS = Path(__file__).resolve().parent / "assets"
MONO = "'JetBrains Mono','Fira Code',ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"
SANS = "Inter,'Segoe UI',-apple-system,BlinkMacSystemFont,'Helvetica Neue',Roboto,'Noto Sans',sans-serif"

BG, BG2, LINE = "#0a0f1e", "#111a2e", "#22304d"
TEAL, BLUE, VIOLET = "#00C9A7", "#2f9fe0", "#8b7cf6"
TEXT, MUTED = "#e8eefb", "#8fa0bf"

# Scaffolding do Flutter infla C++/CMake; aqui conta só o que foi escrito no projeto.
LANG_ONLY = {"quiz_mobile": {"Dart"}}
IGNORED_REPOS = {LOGIN}

PROJECTS = [
    dict(repo="Portal-do-Aluno", title="Portal do Aluno", route="/projetos/portal-do-aluno", lang="TypeScript",
         desc=["API REST de rematrícula acadêmica com controle", "de acesso por papéis e documentação interativa."],
         chips=["NestJS", "Supabase", "JWT", "OAuth2"]),
    dict(repo="Rematricula-API", title="Rematrícula API", route="/projetos/rematricula-api", lang="TypeScript",
         desc=["Alunos, cursos, disciplinas, turmas e pré-requisitos", "com fluxo de matrícula e autenticação."],
         chips=["NestJS", "TypeORM", "Postgres", "Swagger"]),
    dict(repo="catalogo-de-produtos", title="Catálogo de Produtos", route="/projetos/catalogo", lang="TypeScript",
         desc=["Busca, filtro por categoria, página de detalhes", "e cadastro validado de novos produtos."],
         chips=["React", "Vite", "Axios", "Tailwind"]),
    dict(repo="PortifolioGustavo", title="Portfólio", route="/projetos/portfolio", lang="TypeScript",
         desc=["Meu portfólio responsivo, com habilidades,", "projetos e contato."],
         chips=["React 19", "TypeScript", "Vite", "Tailwind"]),
    dict(repo="quiz_mobile", title="Quiz Mobile", route="/projetos/quiz-mobile", lang="Dart",
         desc=["Quiz com 10 perguntas sorteadas por partida,", "alternativas embaralhadas e pontuação final."],
         chips=["Flutter", "Dart", "Android", "iOS"]),
    dict(repo="ping-tool", title="Docker Git Lab", route="/projetos/ping-tool", lang="Dockerfile",
         desc=["Laboratório de containers: imagem com ping,", "build multi-stage e Nginx via Compose."],
         chips=["Docker", "Compose", "Nginx"]),
]

STACK = [
    ("Linguagens", ["java", "ts", "js", "dart", "c"]),
    ("Back-end", ["nodejs", "nestjs", "spring"]),
    ("Front & mobile", ["react", "vite", "tailwind", "bootstrap", "html", "css", "flutter"]),
    ("Dados", ["postgres", "mongodb", "firebase", "supabase"]),
    ("Infra & deploy", ["docker", "nginx", "vercel", "linux", "git", "github"]),
]
STACK_EXTRAS = ["Swagger", "TypeORM", "JWT", "OAuth2", "Render", "WSL"]

QUERY = """query($login:String!){user(login:$login){createdAt
 repositories(ownerAffiliations:OWNER,privacy:PUBLIC,isFork:false,first:100){nodes{name stargazerCount homepageUrl
  languages(first:12,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}
 contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{contributionCount date}}}}}}"""


def fetch(token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-readme-generator"},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        body = json.load(res)
    if body.get("errors"):
        raise SystemExit(f"GraphQL: {body['errors']}")
    return body["data"]["user"]


def summarize(user):
    repos = [r for r in user["repositories"]["nodes"] if r["name"] not in IGNORED_REPOS]
    sizes, colors = Counter(), {"Dockerfile": "#384d54"}
    for r in repos:
        allowed = LANG_ONLY.get(r["name"])
        for e in r["languages"]["edges"]:
            name = e["node"]["name"]
            colors[name] = e["node"]["color"] or "#8fa0bf"
            if allowed is None or name in allowed:
                sizes[name] += e["size"]
    total = sum(sizes.values()) or 1
    langs = [(n, s / total, colors[n]) for n, s in sizes.most_common(5)]

    created = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    months = (now.year - created.year) * 12 + now.month - created.month - (now.day < created.day)
    years, rest = divmod(months, 12)
    parts = []
    if years:
        parts.append(f"{years} ano" + ("s" if years > 1 else ""))
    if rest:
        parts.append(f"{rest} " + ("mês" if rest == 1 else "meses"))

    cal = user["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    peak = max(days, key=lambda d: d["contributionCount"])
    return dict(
        repos={r["name"]: r for r in repos},
        count=len(repos),
        live=sum(1 for r in repos if r["homepageUrl"]),
        langs=langs,
        colors=colors,
        age=" e ".join(parts) or "menos de 1 mês",
        total=cal["totalContributions"],
        weeks=cal["weeks"],
        peak=peak,
        active_days=sum(1 for d in days if d["contributionCount"]),
    )


BASE_CSS = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"


def svg(w, h, title, css, body, defs=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{escape(title)}"><title>{escape(title)}</title>'
        f"<style>{BASE_CSS}{css}</style><defs>{defs}</defs>{body}</svg>"
    )


def panel(w, h, r=18, fill="url(#panel)"):
    return (
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="{r}" fill="{fill}" stroke="{LINE}"/>'
    )


PANEL_DEF = (
    f'<linearGradient id="panel" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{BG2}"/>'
    f'<stop offset="1" stop-color="{BG}"/></linearGradient>'
)
BRAND_DEF = (
    f'<linearGradient id="brand" x1="0" x2="1" y1="0" y2="0"><stop stop-color="{TEAL}"/>'
    f'<stop offset=".55" stop-color="{BLUE}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>'
)


def typed_line(text, y, x, idx, count, cycle, size=15):
    """Texto digitado com cursor, em janela própria dentro de um ciclo compartilhado."""
    cw = size * 0.6
    n = len(text)
    start, span = idx / count, 1 / count
    frames = [(0.0, 0)]
    for c in range(n + 1):
        frames.append((start + span * 0.42 * c / n, c))
    frames.append((start + span * 0.93, 0))
    frames.append((1.0, 0))
    frames = sorted({round(t, 5): c for t, c in frames}.items())
    if frames[0][0] != 0:
        frames.insert(0, (0.0, 0))
    times = ";".join(str(t) for t, _ in frames)
    widths = ";".join(f"{c*cw:.1f}" for _, c in frames)
    xs = ";".join(f"{x+c*cw:.1f}" for _, c in frames)
    # O cursor só aparece enquanto a própria linha está ativa.
    vis_t = sorted({0.0, round(start, 5), round(start + span * 0.93, 5), 1.0})
    vis_v = ";".join("1" if round(start, 5) <= t < round(start + span * 0.93, 5) else "0" for t in vis_t)
    return (
        f'<clipPath id="tc{idx}"><rect x="{x}" y="{y-size-2}" height="{size+10}" width="0">'
        f'<animate attributeName="width" dur="{cycle}s" repeatCount="indefinite" calcMode="discrete" '
        f'keyTimes="{times}" values="{widths}"/></rect></clipPath>'
        f'<text clip-path="url(#tc{idx})" x="{x}" y="{y}" font-family="{MONO}" font-size="{size}" '
        f'fill="{TEAL}" textLength="{n*cw:.1f}" lengthAdjust="spacingAndGlyphs" xml:space="preserve">{escape(text)}</text>'
        f'<rect y="{y-size+2}" width="{cw:.1f}" height="{size+1}" fill="{TEAL}" opacity="0">'
        f'<animate attributeName="x" dur="{cycle}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{times}" values="{xs}"/>'
        f'<animate attributeName="opacity" dur="{cycle}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{";".join(map(str, vis_t))}" values="{vis_v}"/>'
        f"</rect>"
    )


def hero():
    w, h = 900, 360
    rnd = random.Random(5905)
    stars = "".join(
        f'<circle class="tw" cx="{rnd.randint(8,w-8)}" cy="{rnd.randint(8,h-8)}" r="{rnd.choice([.7,.9,1.2,1.5])}" '
        f'style="animation-delay:-{rnd.uniform(0,6):.1f}s"/>'
        for _ in range(60)
    )
    css = (
        ".tw{fill:#cfe6ff;animation:tw 6s ease-in-out infinite}@keyframes tw{0%,100%{opacity:.12}50%{opacity:.85}}"
        ".a1{animation:d1 16s ease-in-out infinite alternate}.a2{animation:d2 20s ease-in-out infinite alternate}"
        ".a3{animation:d3 24s ease-in-out infinite alternate}"
        "@keyframes d1{to{transform:translate(170px,60px)}}@keyframes d2{to{transform:translate(-190px,-40px)}}"
        "@keyframes d3{to{transform:translate(90px,-90px)}}"
        ".pulse{animation:p 2s ease-in-out infinite}@keyframes p{0%,100%{opacity:1}50%{opacity:.25}}"
        ".edge{stroke-dasharray:3 6;animation:e 1.2s linear infinite}@keyframes e{to{stroke-dashoffset:-9}}"
        ".rise{animation:r .9s cubic-bezier(.2,.8,.2,1) both}@keyframes r{from{opacity:0;transform:translateY(14px)}}"
    )
    defs = (
        f'<clipPath id="c"><rect width="{w}" height="{h}" rx="22"/></clipPath>'
        f'<radialGradient id="g1"><stop stop-color="{TEAL}" stop-opacity=".5"/><stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="g2"><stop stop-color="{BLUE}" stop-opacity=".5"/><stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="g3"><stop stop-color="{VIOLET}" stop-opacity=".42"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="name" x1="0" x2="1" y1="0" y2="0" gradientUnits="objectBoundingBox">'
        f'<stop stop-color="#ffffff"/><stop offset=".5" stop-color="#8ff5e0"/><stop offset="1" stop-color="#ffffff"/>'
        f'<animateTransform attributeName="gradientTransform" type="translate" values="-1 0;1 0" dur="7s" repeatCount="indefinite"/></linearGradient>'
        '<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1" fill="#fff" opacity=".07"/></pattern>'
        '<filter id="glow" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="3.5"/></filter>'
    )

    # Diagrama: uma requisição atravessa a API de verdade, com auth e banco.
    A, C, U, D, S = (720, 180), (610, 84), (830, 84), (830, 276), (610, 276)
    route = [(C, (C[0], A[1]), A), (A, (U[0], A[1]), U), (U, (U[0], A[1]), A),
             (A, (D[0], A[1]), D), (D, (D[0], A[1]), A), (A, (C[0], A[1]), C)]
    pts = [C]
    for seg in route:
        pts.extend(seg[1:])
    lengths = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total = sum(lengths)
    path_d = "M" + " L".join(f"{x} {y}" for x, y in pts)
    arrivals, run = {}, 0.0
    for p, l in zip(pts[1:], lengths):
        run += l
        arrivals.setdefault(p, []).append(run / total)
    dur = 7

    def node(center, label, sub, nw=96, nh=50, accent=TEAL):
        x, y = center
        hits = arrivals.get(center, [])
        anim = ""
        if hits:
            # Pisca quando o pacote chega no nó.
            stamps = [(0.0, .0)]
            for t in hits:
                t = min(t, .985)
                stamps += [(max(t - .005, .001), 0.0), (t, 1.0), (min(t + .07, .999), 0.0)]
            stamps.append((1.0, .0))
            stamps = sorted(dict(stamps).items())
            anim = (
                f'<rect x="{x-nw/2-3}" y="{y-nh/2-3}" width="{nw+6}" height="{nh+6}" rx="13" fill="none" stroke="{accent}" stroke-width="2" opacity="0">'
                f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" keyTimes="{";".join(str(round(t,4)) for t,_ in stamps)}" values="{";".join(str(v) for _,v in stamps)}"/></rect>'
            )
        return (
            f'<rect x="{x-nw/2}" y="{y-nh/2}" width="{nw}" height="{nh}" rx="11" fill="#0d1527" fill-opacity=".88" stroke="{LINE}"/>{anim}'
            f'<text x="{x}" y="{y-3}" text-anchor="middle" font-family="{MONO}" font-size="13" font-weight="700" fill="{TEXT}">{label}</text>'
            f'<text x="{x}" y="{y+14}" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="{MUTED}">{sub}</text>'
        )

    edges = "".join(
        f'<path class="edge" d="M{a[0]} {a[1]} L{a[0]} {A[1]} L{A[0]} {A[1]}" fill="none" stroke="#4a6187" stroke-width="1.4"/>'
        for a in (C, U, D, S)
    )
    motion = lambda begin: (
        f'<animateMotion dur="{dur}s" begin="{begin}s" repeatCount="indefinite" path="{path_d}"/>'
    )
    comet = (
        f'<circle r="9" fill="{TEAL}" opacity=".55" filter="url(#glow)">{motion(0)}</circle>'
        + "".join(
            f'<circle r="{r}" fill="{TEAL if i==0 else "#7fe9d6"}" opacity="{o}">{motion(-i*.05)}</circle>'
            for i, (r, o) in enumerate([(4, 1), (3, .7), (2.3, .45), (1.6, .25)])
        )
    )
    diagram = (
        edges
        + node(C, "cliente", "HTTP request")
        + node(U, "auth", "JWT · OAuth2", accent=VIOLET)
        + node(D, "postgres", "via TypeORM", accent=BLUE)
        + node(S, "swagger", "/api/docs")
        + node(A, "API", "Nest · Spring", nw=112, nh=58)
        + comet
    )

    lines = [
        "$ construindo APIs com NestJS e Spring Boot",
        "$ migrando de carreira para TI, sem volta",
        "$ graduando em Análise e Desenv. de Sistemas",
    ]
    typed = "".join(typed_line(l, 248, 40, i, len(lines), 18) for i, l in enumerate(lines))

    body = (
        f'<g clip-path="url(#c)"><rect width="{w}" height="{h}" fill="{BG}"/>'
        f'<ellipse class="a1" cx="170" cy="60" rx="340" ry="230" fill="url(#g1)"/>'
        f'<ellipse class="a2" cx="760" cy="300" rx="360" ry="240" fill="url(#g2)"/>'
        f'<ellipse class="a3" cx="480" cy="340" rx="300" ry="190" fill="url(#g3)"/>'
        f'<rect width="{w}" height="{h}" fill="url(#dots)"/>{stars}{diagram}'
        f'<g class="rise">'
        f'<rect x="40" y="52" width="264" height="28" rx="14" fill="{TEAL}" fill-opacity=".12" stroke="{TEAL}" stroke-opacity=".5"/>'
        f'<circle class="pulse" cx="58" cy="66" r="4.5" fill="{TEAL}"/>'
        f'<text x="72" y="71" font-family="{MONO}" font-size="12" font-weight="600" fill="#a6f4e4" letter-spacing=".6">ABERTO A OPORTUNIDADES</text>'
        f'<text x="38" y="148" font-family="{SANS}" font-size="62" font-weight="800" letter-spacing="-1.5" fill="url(#name)">Gustavo Reis</text>'
        f'<text x="40" y="190" font-family="{SANS}" font-size="25" font-weight="500" fill="{TEXT}">Desenvolvedor Back-end</text>'
        f"</g>{typed}"
        f'<text x="40" y="312" font-family="{MONO}" font-size="12.5" fill="{MUTED}">github.com/{LOGIN}</text>'
        f"</g>"
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="22" fill="none" stroke="#fff" stroke-opacity=".1"/>'
    )
    return svg(w, h, "Gustavo Reis, desenvolvedor back-end, aberto a oportunidades", css, body, defs)


def section(method, path, status):
    w, h = 900, 62
    color = TEAL if method == "GET" else "#f5b14c"
    css = (
        ".sw{animation:sw 5s ease-in-out infinite}@keyframes sw{0%{transform:translateX(-260px)}60%,100%{transform:translateX(900px)}}"
        ".pulse{animation:p 2s ease-in-out infinite}@keyframes p{0%,100%{opacity:1}50%{opacity:.3}}"
    )
    defs = (
        PANEL_DEF
        + f'<clipPath id="c"><rect width="{w}" height="{h}" rx="14"/></clipPath>'
        + f'<linearGradient id="s"><stop stop-color="{color}" stop-opacity="0"/><stop offset=".5" stop-color="{color}" stop-opacity=".19"/><stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient>'
    )
    mw = 20 + len(method) * 10
    body = (
        panel(w, h, 14)
        + f'<g clip-path="url(#c)"><rect class="sw" width="260" height="{h}" fill="url(#s)"/></g>'
        + f'<rect x="18" y="16" width="{mw}" height="30" rx="8" fill="{color}" fill-opacity=".15" stroke="{color}" stroke-opacity=".6"/>'
        + f'<text x="{18+mw/2}" y="36" text-anchor="middle" font-family="{MONO}" font-size="14" font-weight="800" fill="{color}">{method}</text>'
        + f'<text x="{18+mw+14}" y="38" font-family="{MONO}" font-size="20" font-weight="700" fill="{TEXT}">{escape(path)}</text>'
        + f'<circle class="pulse" cx="{w-22-len(status)*8.1-14}" cy="31" r="4.5" fill="{color}"/>'
        + f'<text x="{w-22}" y="36" text-anchor="end" font-family="{MONO}" font-size="13.5" fill="{MUTED}">{escape(status)}</text>'
    )
    return svg(w, h, f"{method} {path}", css, body, defs)


def profile(d):
    frames = sorted(ASSETS.glob("dog-*.webp"))
    n = len(frames)
    frame_t = 0.3
    w, h = 900, 432
    css = (
        f".f{{opacity:0;animation:f {n*frame_t}s step-end infinite}}"
        f"@keyframes f{{0%{{opacity:1}}{100/n:.3f}%,100%{{opacity:0}}}}"
        ".pulse{animation:p 2s ease-in-out infinite}@keyframes p{0%,100%{opacity:1}50%{opacity:.3}}"
        ".bl{animation:b 1.1s step-end infinite}@keyframes b{50%{opacity:0}}"
        ".g{transform-box:fill-box;animation:g 1.4s cubic-bezier(.2,.8,.2,1) both}@keyframes g{from{transform:scaleX(0)}}"
    )
    imgs = "".join(
        f'<image class="f" style="animation-delay:{i*frame_t:.1f}s" x="30" y="84" width="220" height="220" '
        f'clip-path="url(#dog)" href="data:image/webp;base64,{base64.b64encode(p.read_bytes()).decode()}"/>'
        for i, p in enumerate(frames)
    )
    defs = (
        PANEL_DEF + BRAND_DEF + '<clipPath id="dog"><rect x="30" y="84" width="220" height="220" rx="16"/></clipPath>'
        f'<clipPath id="bar"><rect x="30" y="378" width="840" height="10" rx="5"/></clipPath>'
    )
    keys = [
        ("Nome", "Gustavo Reis"),
        ("Função", "Desenvolvedor Back-end"),
        ("Formação", "Análise e Desenvolvimento de Sistemas"),
        ("Momento", "Migrando de carreira para TI"),
        ("Foco", "APIs REST · Autenticação · PostgreSQL"),
        ("Stack", "NestJS · Spring Boot · React · Docker"),
        ("No GitHub", f"há {d['age']}"),
        ("Projetos", f"{d['count']} públicos · {d['live']} no ar"),
    ]
    rows = ""
    for i, (k, v) in enumerate(keys):
        y = 120 + i * 24.5
        rows += (
            f'<text x="282" y="{y}" font-family="{MONO}" font-size="14" font-weight="700" fill="{TEAL}">{escape(k)}</text>'
            f'<line x1="374" x2="412" y1="{y-4}" y2="{y-4}" stroke="#3a4b6b" stroke-dasharray="1.5 4" stroke-linecap="round"/>'
            f'<text x="420" y="{y}" font-family="{MONO}" font-size="14" fill="{TEXT}">{escape(v)}</text>'
        )
    # Barra de linguagens com dados reais de bytes por repositório.
    bar, legend, x = "", "", 30.0
    lx = 30
    for name, share, color in d["langs"]:
        seg = 840 * share
        bar += f'<rect class="g" x="{x:.1f}" y="378" width="{seg:.1f}" height="10" fill="{color}"/>'
        x += seg
        label = f"{name} {share*100:.1f}%"
        legend += (
            f'<circle cx="{lx+5}" cy="407" r="5" fill="{color}"/>'
            f'<text x="{lx+16}" y="412" font-family="{MONO}" font-size="12.5" fill="{MUTED}">{escape(label)}</text>'
        )
        lx += 16 + len(label) * 7.6 + 24
    body = (
        panel(w, h)
        + f'<path d="M1 44 H{w-1}" stroke="{LINE}"/>'
        + "".join(f'<circle cx="{26+i*20}" cy="22" r="6" fill="{c}"/>' for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]))
        + f'<text x="{w/2}" y="27" text-anchor="middle" font-family="{MONO}" font-size="13" fill="{MUTED}">gustavo@github: ~</text>'
        + f'<rect x="26" y="80" width="228" height="228" rx="19" fill="none" stroke="url(#brand)" stroke-width="2"/>'
        + imgs
        + f'<text x="140" y="332" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{MUTED}">eu em produção</text>'
        + f'<text x="282" y="84" font-family="{MONO}" font-size="14" fill="{MUTED}"><tspan fill="{TEAL}">$</tspan> whoami --verbose<tspan class="bl" fill="{TEAL}"> ▌</tspan></text>'
        + rows
        + f'<text x="30" y="366" font-family="{MONO}" font-size="12.5" font-weight="700" fill="{TEAL}">Linguagens nos repositórios</text>'
        + f'<g clip-path="url(#bar)"><rect x="30" y="378" width="840" height="10" fill="{LINE}"/>{bar}</g>'
        + legend
    )
    return svg(w, h, "Sobre Gustavo: desenvolvedor back-end, graduando em ADS, migrando de carreira para TI", css, body, defs)


def icon(name, x, y, size, css_class=""):
    raw = (ASSETS / "icons" / f"{name}.svg").read_text()
    m = re.search(r"<svg[^>]*>(.*)</svg>\s*$", raw, re.S)
    inner = m.group(1).strip()
    # Prefixa ids para os ícones não colidirem dentro do mesmo SVG.
    inner = re.sub(r'\bid="([^"]+)"', rf'id="{name}-\1"', inner)
    inner = re.sub(r"url\(#([^)]+)\)", rf"url(#{name}-\1)", inner)
    inner = re.sub(r'href="#([^"]+)"', rf'href="#{name}-\1"', inner)
    cls = f' class="{css_class}"' if css_class else ""
    return f'<svg{cls} x="{x}" y="{y}" width="{size}" height="{size}" viewBox="0 0 256 256">{inner}</svg>'


def stack():
    row_h, top, size = 66, 22, 48
    w, h = 900, top + row_h * len(STACK) + 62
    css = ".b{animation:b 4.5s ease-in-out infinite}@keyframes b{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}"
    body = panel(w, h)
    n = 0
    for r, (label, icons) in enumerate(STACK):
        y = top + r * row_h
        body += f'<text x="30" y="{y+size/2+5}" font-family="{MONO}" font-size="14" font-weight="700" fill="{TEAL}">{escape(label)}</text>'
        for i, name in enumerate(icons):
            body += f'<g class="b" style="animation-delay:-{n*.17:.2f}s">{icon(name, 200+i*64, y, size)}</g>'
            n += 1
        if r < len(STACK) - 1:
            body += f'<path d="M30 {y+row_h-9} H870" stroke="{LINE}" stroke-opacity=".55"/>'
    x = 30
    cy = h - 50
    for chip in STACK_EXTRAS:
        cw = len(chip) * 8.2 + 24
        body += (
            f'<rect x="{x}" y="{cy}" width="{cw}" height="30" rx="15" fill="{TEAL}" fill-opacity=".08" stroke="{TEAL}" stroke-opacity=".35"/>'
            f'<text x="{x+cw/2}" y="{cy+20}" text-anchor="middle" font-family="{MONO}" font-size="13" fill="#a6f4e4">{escape(chip)}</text>'
        )
        x += cw + 10
    names = ", ".join(n for _, g in STACK for n in g) + ", " + ", ".join(STACK_EXTRAS)
    return svg(w, h, f"Tecnologias: {names}", css, body, PANEL_DEF)


def project(p, d):
    w, h = 440, 214
    info = d["repos"].get(p["repo"], {})
    live = bool(info.get("homepageUrl"))
    stars = info.get("stargazerCount", 0)
    color = d["colors"].get(p["lang"], TEAL)
    css = ".pulse{animation:p 1.8s ease-in-out infinite}@keyframes p{0%,100%{opacity:1}50%{opacity:.3}}"
    defs = (
        PANEL_DEF
        + f'<linearGradient id="top"><stop stop-color="{color}"/><stop offset="1" stop-color="{TEAL}" stop-opacity=".1"/></linearGradient>'
        + f'<clipPath id="c"><rect width="{w}" height="{h}" rx="16"/></clipPath>'
    )
    body = panel(w, h, 16) + f'<g clip-path="url(#c)"><rect width="{w}" height="3" fill="url(#top)"/></g>'
    body += (
        f'<text x="22" y="34" font-family="{MONO}" font-size="12" fill="{MUTED}"><tspan fill="{TEAL}" font-weight="700">GET</tspan> {escape(p["route"])}</text>'
        f'<text x="22" y="70" font-family="{SANS}" font-size="24" font-weight="700" fill="{TEXT}">{escape(p["title"])}</text>'
    )
    for i, line in enumerate(p["desc"]):
        body += f'<text x="22" y="{98+i*20}" font-family="{SANS}" font-size="14" fill="{MUTED}">{escape(line)}</text>'
    x = 22
    for chip in p["chips"]:
        cw = len(chip) * 7 + 18
        body += (
            f'<rect x="{x}" y="142" width="{cw}" height="24" rx="7" fill="#ffffff" fill-opacity=".05" stroke="{LINE}"/>'
            f'<text x="{x+cw/2}" y="158" text-anchor="middle" font-family="{MONO}" font-size="11.5" fill="#c4d2ec">{escape(chip)}</text>'
        )
        x += cw + 7
    body += (
        f'<circle cx="28" cy="189" r="6" fill="{color}"/>'
        f'<text x="41" y="194" font-family="{MONO}" font-size="12.5" fill="{MUTED}">{escape(p["lang"])}'
        + (f"  ★ {stars}" if stars else "")
        + "</text>"
    )
    if live:
        body += (
            f'<circle class="pulse" cx="{w-78}" cy="189" r="4.5" fill="{TEAL}"/>'
            f'<text x="{w-22}" y="194" text-anchor="end" font-family="{MONO}" font-size="12.5" font-weight="700" fill="{TEAL}">no ar</text>'
        )
    return svg(w, h, f"{p['title']}: {' '.join(p['desc'])}", css, body, defs)


def shade(hex_color, factor):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(min(255, int(c * factor)) for c in (r, g, b))


def skyline(d):
    w, h = 900, 430
    a, b = 13.4, 4.9
    weeks = d["weeks"]
    ox, oy = 141, 74
    top_max = max(1, d["peak"]["contributionCount"])
    base, towers = [], []

    def tile(x, y):
        return f"M{x:.1f} {y-b:.1f}L{x+a:.1f} {y:.1f}L{x:.1f} {y+b:.1f}L{x-a:.1f} {y:.1f}Z"

    last = None
    for wi, week in enumerate(weeks):
        for day in week["contributionDays"]:
            di = date.fromisoformat(day["date"]).isoweekday() % 7
            x = ox + (wi - di) * a
            y = oy + (wi + di) * b + 40
            count = day["contributionCount"]
            last = (x, y)
            if not count:
                base.append(tile(x, y))
                continue
            frac = count / top_max
            th = 12 + 96 * math.sqrt(frac)
            top = TEAL if frac > .5 else "#26b6c9" if frac > .2 else BLUE
            tx, ty = x, y - th
            towers.append(
                f'<g class="t" style="transform-origin:{x:.1f}px {y+b:.1f}px;animation-delay:{wi*.022:.2f}s">'
                f'<path d="M{x-a:.1f} {y:.1f}L{x:.1f} {y+b:.1f}L{x:.1f} {ty+b:.1f}L{x-a:.1f} {ty:.1f}Z" fill="{shade(top,.58)}"/>'
                f'<path d="M{x+a:.1f} {y:.1f}L{x:.1f} {y+b:.1f}L{x:.1f} {ty+b:.1f}L{x+a:.1f} {ty:.1f}Z" fill="{shade(top,.36)}"/>'
                f'<path d="{tile(tx,ty)}" fill="{top}"/></g>'
            )
    css = (
        ".t{animation:t 1.1s cubic-bezier(.2,.9,.25,1.15) both}@keyframes t{from{transform:scaleY(.02);opacity:0}}"
        ".ring{animation:r 2.4s ease-out infinite;transform-box:fill-box;transform-origin:center}@keyframes r{from{transform:scale(.4);opacity:1}to{transform:scale(1.9);opacity:0}}"
    )
    defs = (
        PANEL_DEF
        + f'<clipPath id="c"><rect width="{w}" height="{h}" rx="18"/></clipPath>'
        + f'<radialGradient id="glow"><stop stop-color="{TEAL}" stop-opacity=".17"/><stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient>'
    )
    peak_day = date.fromisoformat(d["peak"]["date"]).strftime("%d/%m/%Y")
    today = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    lx, ly = last

    def stat(x, y, value, label, anchor="start"):
        return (
            f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{SANS}" font-size="38" font-weight="800" fill="{TEXT}">{value}</text>'
            f'<text x="{x}" y="{y+22}" text-anchor="{anchor}" font-family="{MONO}" font-size="12.5" fill="{MUTED}">{escape(label)}</text>'
        )

    body = (
        panel(w, h)
        + f'<g clip-path="url(#c)"><ellipse cx="{w/2}" cy="{h/2+20}" rx="440" ry="190" fill="url(#glow)"/>'
        + f'<path d="{"".join(base)}" fill="#172540" stroke="#22304d" stroke-width=".6"/>'
        + "".join(towers)
        + f'<ellipse class="ring" cx="{lx:.1f}" cy="{ly:.1f}" rx="{a:.1f}" ry="{b:.1f}" fill="none" stroke="{TEAL}" stroke-width="1.6"/></g>'
        + stat(30, h - 92, d["total"], "contribuições em 12 meses")
        + stat(262, h - 92, d["active_days"], "dias ativos")
        + f'<text x="{w-30}" y="34" text-anchor="end" font-family="{MONO}" font-size="12" fill="{MUTED}">dia mais ativo: {peak_day} ({d["peak"]["contributionCount"]})</text>'
        + f'<text x="30" y="{h-22}" font-family="{MONO}" font-size="12" fill="{MUTED}">dados reais · atualizado em {today}</text>'
    )
    return svg(w, h, f"Calendário de contribuições em 3D: {d['total']} contribuições nos últimos 12 meses", css, body, defs)


def button(icon_svg, label, sub):
    w, h = 290, 76
    css = ".ar{animation:a 1.8s ease-in-out infinite}@keyframes a{0%,100%{transform:translateX(0)}50%{transform:translateX(4px)}}"
    body = (
        panel(w, h, 16)
        + icon_svg
        + f'<text x="72" y="33" font-family="{SANS}" font-size="17" font-weight="700" fill="{TEXT}">{escape(label)}</text>'
        + f'<text x="72" y="54" font-family="{MONO}" font-size="11.5" fill="{MUTED}">{escape(sub)}</text>'
        + f'<text class="ar" x="{w-34}" y="44" font-family="{MONO}" font-size="20" fill="{TEAL}">→</text>'
    )
    return svg(w, h, f"{label}: {sub}", css, body, PANEL_DEF)


def globe():
    return (
        f'<rect x="16" y="18" width="40" height="40" rx="10" fill="#242938"/>'
        f'<g fill="none" stroke="{TEAL}" stroke-width="1.8"><circle cx="36" cy="38" r="11"/><ellipse cx="36" cy="38" rx="4.8" ry="11"/><path d="M25 38h22"/></g>'
    )


def footer():
    w, h = 900, 150
    css = (
        ".w1{animation:w 11s linear infinite}.w2{animation:w 17s linear infinite reverse}"
        "@keyframes w{to{transform:translateX(-900px)}}"
    )
    wave = lambda y, amp: (
        f"M0 {y}" + "".join(f" q112.5 {-amp if i%2==0 else amp} 225 0" for i in range(8)) + f" V{h} H0 Z"
    )
    defs = (
        BRAND_DEF
        + f'<clipPath id="c"><rect width="{w}" height="{h}" rx="20"/></clipPath>'
    )
    body = (
        f'<g clip-path="url(#c)"><rect width="{w}" height="{h}" fill="{BG}"/>'
        f'<path class="w2" d="{wave(92,22)}" fill="{BLUE}" fill-opacity=".28"/>'
        f'<path class="w1" d="{wave(106,18)}" fill="url(#brand)" fill-opacity=".62"/></g>'
        f'<text x="{w/2}" y="46" text-anchor="middle" font-family="{MONO}" font-size="16" font-weight="700" fill="{TEXT}">'
        f'<tspan fill="{TEAL}">HTTP/1.1 200 OK</tspan> · obrigado pela visita</text>'
        f'<text x="{w/2}" y="70" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{MUTED}">Connection: keep-alive</text>'
    )
    return svg(w, h, "HTTP 200 OK, obrigado pela visita", css, body, defs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("Defina GITHUB_TOKEN")
    data = summarize(fetch(token))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    files = {
        "hero.svg": hero(),
        "section-whoami.svg": section("GET", "/whoami", "200 OK"),
        "section-projetos.svg": section("GET", "/projetos", "200 OK"),
        "section-stack.svg": section("GET", "/stack", "200 OK"),
        "section-atividade.svg": section("GET", "/atividade", "200 OK"),
        "section-contato.svg": section("POST", "/contato", "202 aguardando você"),
        "profile.svg": profile(data),
        "stack.svg": stack(),
        "skyline.svg": skyline(data),
        "btn-linkedin.svg": button(icon("linkedin", 16, 18, 40), "LinkedIn", "/in/gustavoreis05"),
        "btn-email.svg": button(icon("gmail", 16, 18, 40), "E-mail", "manda uma mensagem"),
        "btn-portfolio.svg": button(globe(), "Portfólio", "projetos e contato"),
        "footer.svg": footer(),
    }
    for p in PROJECTS:
        files[f"project-{p['repo']}.svg"] = project(p, data)
    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8")
    print(f"{len(files)} SVGs em {out}/ · {data['total']} contribuições · {data['count']} repos")


if __name__ == "__main__":
    main()
