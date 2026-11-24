#!/usr/bin/env python3
"""Build the 乾隆《泉州府志》原文 / 译文 / 注解 site from Markdown sources.

Reads ``NN-卷….md`` (and ``75上-`` / ``75下-``). ``进度.md`` and any other
non-volume file are ignored. Volume ids stay zero-padded (``00`` … ``76``);
卷七十五上、下 become ``75a`` / ``75b`` so the URLs stay in book order.

    python3 tools/build-fuzhi-yizhu.py
    python3 tools/build-fuzhi-yizhu.py --src /path/to/译文 --out fuzhi

Categories: ``tools/fuzhi-categories.json`` (explicit ids, then title keywords;
anything unmatched goes to「其他」). Names: ``tools/fuzhi-entities.json``.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fuzhi_entity_index as entidx  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent

FNAME = re.compile(r"^(\d+)(上|下)?-.+\.md$")
HR = {"---", "----", "***"}
JUAN_RE = re.compile(r"^(卷首|卷[一二三四五六七八九十百〇零]+[上下]?)")
LOC_RE = re.compile(r"整理本第\d+册第[\d０-９\-–—~～]+页(?:（[^）]*）|\([^)]*\))?")


def volume_id(num: str, suffix: str | None) -> str:
    n = int(num)
    if suffix == "上":
        return f"{n}a"
    if suffix == "下":
        return f"{n}b"
    return f"{n:02d}"


def sort_key_name(name: str):
    m = FNAME.match(name)
    suf = {None: 0, "上": 1, "下": 2}[m.group(2)]
    return (int(m.group(1)), suf, name)


def esc(text: str) -> str:
    return html.escape(text or "", quote=False)


# 与既有译注站一致：字数只计汉字（卷首原文据此为 12,474 字）。
_HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def count_chars(text: str) -> int:
    return len(_HAN.findall(text or ""))


def js_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def fmt_int(n: int) -> str:
    return f"{n:,}"


def fmt_wan(n: int) -> str:
    s = f"{n / 10000:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return s


def render_inlines(text: str) -> str:
    text = esc(text)
    text = re.sub(r"\[(\d{1,3})\]", r'<sup class="fn">[\1]</sup>', text)
    text = re.sub(r"［(\d{1,3})］", r'<sup class="fn">[\1]</sup>', text)
    text = text.replace("【简译】", '<span class="jianyi">【简译】</span>')
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


def _is_table_sep(line: str) -> bool:
    s = line.strip()
    return bool(s) and s.count("-") >= 2 and re.fullmatch(r"\|?[\s:|-]+\|?", s) is not None


def parse_table(lines: list[str], i: int) -> tuple[str, int]:
    rows = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        if not _is_table_sep(lines[i]):
            cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            rows.append(cells)
        i += 1
    if not rows:
        return "", i
    width = max(len(r) for r in rows)
    head, body = rows[0], rows[1:]

    def cell(tag, value):
        return f"<{tag}>{render_inlines(value)}</{tag}>"

    thead = "<thead><tr>" + "".join(cell("th", head[c] if c < len(head) else "") for c in range(width)) + "</tr></thead>"
    tbody = "<tbody>" + "".join(
        "<tr>" + "".join(cell("td", r[c] if c < len(r) else "") for c in range(width)) + "</tr>"
        for r in body
    ) + "</tbody>"
    return f'<div class="tw"><table>{thead}{tbody}</table></div>', i


def render_body(raw: str) -> str:
    lines = raw.splitlines()
    parts: list[str] = []
    para: list[str] = []

    def flush():
        if not para:
            return
        joined = "".join(x.strip() for x in para if x.strip())
        para.clear()
        if joined:
            parts.append(f"<p>{render_inlines(joined)}</p>")

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(">"):
            line = line.lstrip(">").strip()
        if not line.strip() or line.strip() in HR:
            flush()
            i += 1
            continue
        if line.strip().startswith("|") and i + 1 < len(lines) and _is_table_sep(lines[i + 1]):
            flush()
            table, i = parse_table(lines, i)
            if table:
                parts.append(table)
            continue
        if re.match(r"^\s*[-*]\s+", line) and not line.strip().startswith("**"):
            flush()
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i]).strip())
                i += 1
            parts.append("<ul>" + "".join(f"<li>{render_inlines(it)}</li>" for it in items) + "</ul>")
            continue
        if re.match(r"^\s*\d+\.\s+", line):
            flush()
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+\.\s+", "", lines[i]).strip())
                i += 1
            parts.append("<ol>" + "".join(f"<li>{render_inlines(it)}</li>" for it in items) + "</ol>")
            continue
        para.append(line)
        i += 1
    flush()
    return "".join(parts)


def block_plain(raw: str) -> str:
    bits = []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s in HR or _is_table_sep(s):
            continue
        if s.startswith(">"):
            s = s.lstrip(">").strip()
        s = re.sub(r"^\*\*(原文|译文|注解)\*\*\s*", "", s)
        s = re.sub(r"^\s*[-*]\s+", "", s)
        s = re.sub(r"^\s*\d+\.\s+", "", s)
        s = s.replace("**", "")
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            s = "".join(cells)
        if s:
            bits.append(s)
    return "".join(bits)


def split_chunks(lines: list[str]) -> list[str]:
    chunks: list[str] = []
    buf: list[str] = []

    def flush():
        text = "\n".join(buf).strip()
        buf.clear()
        if text:
            chunks.append(text)

    for line in lines:
        if line.strip() in HR:
            flush()
        else:
            buf.append(line)
    flush()
    return chunks


def strip_marker(text: str, label: str) -> str:
    return re.sub(rf"^\*\*{label}\*\*\s*", "", text).strip()


LABEL_RE = re.compile(r"(?m)^\*\*(原文|译文|注解)\*\*\s*$")
LABEL_KIND = {"原文": "yuan", "译文": "yi", "注解": "zhu"}


def explode_labels(chunk: str) -> list[tuple[str, str]]:
    """Split one dashed chunk on 原文 / 译文 / 注解 headings, which are often
    separated only by blank lines."""
    marks = list(LABEL_RE.finditer(chunk))
    if not marks:
        if chunk.startswith("【简译】"):
            return [("yi", chunk)]
        return [("auto", chunk)]
    out: list[tuple[str, str]] = []
    head = chunk[: marks[0].start()].strip()
    if head:
        out.append(("yi", head) if head.startswith("【简译】") else ("auto", head))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(chunk)
        body = chunk[m.end():end].strip()
        out.append((LABEL_KIND[m.group(1)], body))
    return out


def classify_blocks(title: str, lines: list[str], level: int, has_children: bool) -> tuple[bool, list[tuple[str, str]]]:
    chunks = split_chunks(lines)
    parsed: list[tuple[str, str]] = []
    for ch in chunks:
        parsed.extend(explode_labels(ch))
    structural = any(k in {"yuan", "yi", "zhu"} for k, _ in parsed)
    if level >= 3 and not structural:
        blocks = []
        for _, text in parsed:
            if text.strip():
                _add(blocks, "yiwen", text)
        return True, blocks

    blocks: list[tuple[str, str]] = []
    seen_yuan = False
    seen_yi = False
    title_key = re.sub(r"\s+", "", title)
    note_title = title_key.startswith("注解") or title_key.startswith("注释")
    for kind, text in parsed:
        if not text.strip():
            continue
        if kind == "yuan":
            _add(blocks, "yuanwen", text)
            seen_yuan = True
        elif kind == "yi":
            _add(blocks, "yiwen", text)
            seen_yi = True
        elif kind == "zhu":
            _add(blocks, "zhujie", text)
        elif note_title or text.lstrip().startswith("- ") or text.lstrip().startswith("1."):
            _add(blocks, "zhujie", text)
        elif seen_yuan and not seen_yi:
            _add(blocks, "yiwen", text)
            seen_yi = True
        elif not has_children and not seen_yuan and len(text) > 40 and not note_title:
            _add(blocks, "yiwen", text)
            seen_yi = True
        else:
            _add(blocks, "zhujie", text)
    return False, blocks


def _add(blocks: list[tuple[str, str]], kind: str, text: str) -> None:
    text = text.strip()
    if not text:
        return
    if blocks and blocks[-1][0] == kind:
        blocks[-1] = (kind, blocks[-1][1] + "\n\n" + text)
    else:
        blocks.append((kind, text))


def take_quotes(lines: list[str]) -> tuple[list[str], list[str]]:
    quotes: list[str] = []
    rest: list[str] = []
    lead = True
    for line in lines:
        if lead:
            if not line.strip() or line.strip() in HR:
                continue
            if line.startswith(">"):
                quotes.append(line.lstrip(">").strip())
                continue
            lead = False
        rest.append(line)
    return quotes, rest


def node_plain(title: str, blocks: list[tuple[str, str]]) -> str:
    body = "".join(block_plain(raw) for _, raw in blocks)
    title = (title or "").strip()
    return (title + body) if title else body


def parse_markdown(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    root = {"level": 0, "title": "", "lines": [], "children": []}
    stack = [root]
    for line in lines:
        m = re.match(r"^(#{1,3})\s+(.+?)\s*$", line)
        if m:
            level = len(m.group(1))
            node = {"level": level, "title": m.group(2).strip(), "lines": [], "children": []}
            while stack and stack[-1]["level"] >= level:
                stack.pop()
            stack[-1]["children"].append(node)
            stack.append(node)
        else:
            stack[-1]["lines"].append(line)
    if not root["children"] or root["children"][0]["level"] != 1:
        raise SystemExit(f"{path.name}: 缺少卷题（# 乾隆《泉州府志》…）")
    h1 = root["children"][0]
    quotes, rest = take_quotes(h1["lines"])
    full = h1["title"]
    m = re.match(r"^乾隆《泉州府志》\s*(.*)$", full)
    display = (m.group(1) if m else full).strip() or full
    jm = JUAN_RE.match(display)
    juan = jm.group(1) if jm else display
    title = display[len(juan):].strip(" 　") or juan
    vt = "" if title == juan else title
    location = ""
    if quotes:
        lm = LOC_RE.search(quotes[0])
        location = lm.group(0) if lm else re.split(r"[，。]", quotes[0])[0]
    tree: list[dict] = []
    if h1["children"]:
        pre_chunks = split_chunks(rest)
        preamble = []
        for ch in pre_chunks:
            if ch.strip():
                _add(preamble, "zhujie", ch)
        tree = [_finish(child) for child in h1["children"]]
    else:
        preamble = []
        yi, blocks = classify_blocks(title, rest, 1, False)
        if blocks:
            tree = [{
                "level": 0,
                "title": display,
                "yi": False,
                "blocks": blocks,
                "children": [],
                "id": None,
                "mentions": [],
                "plain": node_plain(display, blocks),
                "toc": False,
            }]
        else:
            tree = []
    _number(tree)
    for n in _flat(tree):
        n["plain"] = node_plain(n.get("title") if n.get("toc", True) else "", n["blocks"])
        if not n.get("toc", True):
            # implicit whole-volume body: still searchable, titled as the volume
            n["plain"] = node_plain(display, n["blocks"])
    chars = {"yuanwen": 0, "yiwen": 0, "zhujie": 0}
    for n in _flat(tree):
        for kind, raw in n["blocks"]:
            chars[kind] = chars.get(kind, 0) + count_chars(block_plain(raw))
    for kind, raw in preamble:
        chars[kind] = chars.get(kind, 0) + count_chars(block_plain(raw))
    mname = FNAME.match(path.name)
    vid = volume_id(mname.group(1), mname.group(2))
    return {
        "id": vid,
        "file": path.name,
        "full": full,
        "display": display,
        "juan": juan,
        "title": title,
        "vt": vt,
        "headnotes": quotes,
        "location": location,
        "preamble": preamble,
        "tree": tree,
        "charsYuan": chars.get("yuanwen", 0),
        "charsYi": chars.get("yiwen", 0),
        "charsZhu": chars.get("zhujie", 0),
    }


def _finish(raw: dict) -> dict:
    yi, blocks = classify_blocks(raw["title"], raw["lines"], raw["level"], bool(raw["children"]))
    return {
        "level": raw["level"],
        "title": raw["title"],
        "yi": yi,
        "blocks": blocks,
        "children": [_finish(ch) for ch in raw["children"]],
        "id": None,
        "mentions": [],
        "plain": "",
        "toc": True,
    }


def _number(nodes: list[dict], counter=None) -> None:
    if counter is None:
        counter = [0]
    for n in nodes:
        if n.get("toc", True) and n.get("level", 0) >= 2:
            counter[0] += 1
            n["id"] = f"s-{counter[0]}"
        elif n.get("yi"):
            counter[0] += 1
            n["id"] = f"s-{counter[0]}"
        _number(n["children"], counter)


def _flat(nodes: list[dict]):
    for n in nodes:
        yield n
        yield from _flat(n["children"])


def toc_sections(vol: dict) -> list[dict]:
    out = []
    for n in _flat(vol["tree"]):
        if n.get("id") and n.get("toc", True) and (n.get("level", 0) >= 2 or n.get("yi")):
            level = 3 if n.get("yi") else n["level"]
            out.append({"id": n["id"], "title": n["title"], "level": level})
    return out


def mentions_html(items: list[dict], prefix: str) -> str:
    if not items:
        return ""
    parts = []
    for m in items:
        label = "本条，" if m.get("bio") else ""
        href = f"{prefix}e.html?n={html.escape(quote_url(m['name']), quote=True)}"
        parts.append(f'<a href="{href}">{esc(m["name"])}<small>（{label}{m["n"]}处）</small></a>')
    return '<p class="mentions">本节涉及：' + "".join(parts) + "</p>"


def quote_url(name: str) -> str:
    from urllib.parse import quote
    return quote(name, safe="")


def render_unit(blocks: list[tuple[str, str]], inner_head: str = "") -> str:
    body = []
    labels = {"yuanwen": "原文", "yiwen": "译文", "zhujie": "注解"}
    for kind, raw in blocks:
        html_body = render_body(raw)
        if not html_body:
            continue
        body.append(
            f'<div class="blk {kind}"><div class="lab">{labels[kind]}</div><div class="body">{html_body}</div></div>'
        )
    if not body and not inner_head:
        return ""
    return f'<div class="unit">{inner_head}{"".join(body)}</div>'


def render_tree(nodes: list[dict], prefix: str) -> str:
    out = []
    for n in nodes:
        if n.get("yi"):
            head = f'<h3 class="h3" id="{n["id"]}">{esc(n["title"])}</h3>'
            ment = mentions_html(n.get("mentions") or [], prefix)
            unit = render_unit(n["blocks"], inner_head=head + ment)
            if unit:
                # yi-entry class sits on the unit
                unit = unit.replace('<div class="unit">', '<div class="unit yi-entry">', 1)
                out.append(unit)
            else:
                out.append(f'<div class="unit yi-entry">{head}{ment}</div>')
            continue
        if n.get("id"):
            level = n["level"] if n["level"] in (2, 3) else 2
            out.append(f'<h{level} class="h{level}" id="{n["id"]}">{esc(n["title"])}</h{level}>')
            ment = mentions_html(n.get("mentions") or [], prefix)
            if ment:
                out.append(ment)
        elif n.get("mentions"):
            out.append(mentions_html(n["mentions"], prefix))
        unit = render_unit(n["blocks"])
        if unit:
            out.append(unit)
        if n["children"]:
            out.append(render_tree(n["children"], prefix))
    return "\n".join(out)


def toc_html(sections: list[dict]) -> str:
    if not sections:
        return '<h2>本卷篇目</h2><p style="padding:0 16px;color:var(--ink-3);font-size:13px">本卷无分节目录</p>'
    items = []
    for s in sections:
        cls = "l3" if s["level"] >= 3 else "l2"
        items.append(f'<li><a class="{cls}" href="#{s["id"]}">{esc(s["title"])}</a></li>')
    return "<h2>本卷篇目</h2><ol>" + "".join(items) + "</ol>"


def page_volume(vol: dict, prev: dict | None, nxt: dict | None) -> str:
    sections = toc_sections(vol)
    meta_bits = []
    if vol["location"]:
        meta_bits.append(esc(vol["location"]))
    meta_bits.append(f"原文 {fmt_int(vol['charsYuan'])} 字")
    meta_bits.append(f"译文 {fmt_int(vol['charsYi'])} 字")
    notes = "".join(f"<p>{esc(p)}</p>" for p in vol["headnotes"])
    headnote = f'<div class="headnote">{notes}</div>' if notes else ""
    pre = render_unit(vol["preamble"]) if vol["preamble"] else ""
    body = render_tree(vol["tree"], "../")
    pager = ['<nav class="pager">']
    if prev:
        pager.append(f'<a href="{prev["id"]}.html"><span class="dir">上一卷</span>{esc(prev["display"])}</a>')
    else:
        pager.append("<span></span>")
    if nxt:
        pager.append(f'<a class="r" href="{nxt["id"]}.html"><span class="dir">下一卷</span>{esc(nxt["display"])}</a>')
    pager.append("</nav>")
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>{esc(vol["display"])} · 乾隆《泉州府志》译文注</title><link rel="stylesheet" href="../css/style.css"></head>
<body class="vol">
<header class="top"><a class="back" href="../index.html">总目</a>
  <div class="vt"><div class="kicker">乾隆《泉州府志》</div><h1>{esc(vol["display"])}</h1></div>
  <nav class="mini"><a href="../names.html">人物</a><a href="../places.html">地名</a></nav>
</header>
<div class="toolbar">
  <button type="button" class="note-btn" id="noteBtn" aria-pressed="false">收起注解</button>
  <button type="button" class="toc-btn" id="tocBtn">篇目</button>
</div>
<div class="layout">
  <aside class="toc" id="toc">{toc_html(sections)}</aside>
  <div class="toc-mask" id="tocMask"></div>
  <main class="vmain" id="top">
    <p class="vmeta">{' · '.join(meta_bits)}</p>
    {headnote}
    {pre}
{body}
    {''.join(pager)}
  </main>
</div>
<script src="../js/volume.js"></script></body></html>
"""


def peek_text(sections: list[dict]) -> str:
    titles = [s["title"] for s in sections]
    n = len(titles)
    if not n:
        return "本卷无分节"
    shown = titles[:8]
    text = " · ".join(shown)
    if n > 8:
        text += f" 等 {n} 条"
    return text


def tree_block(volumes: list[dict], href_prefix: str) -> str:
    items = []
    for vol in volumes:
        sections = toc_sections(vol)
        vn = "" if vol["title"] == vol["juan"] else vol["title"]
        href = f"{href_prefix}v/{vol['id']}.html"
        sects = []
        for s in sections:
            cls = "lv3" if s["level"] >= 3 else "lv2"
            sects.append(f'<li class="{cls}"><a href="{href}#{s["id"]}">{esc(s["title"])}</a></li>')
        if not sects:
            sects.append('<li class="empty">本卷无分节目录</li>')
        items.append(
            "<li><details class=\"vol\"><summary>"
            f'<a class="vj" href="{href}" onclick="event.stopPropagation()">{esc(vol["juan"])}</a>'
            f'<a class="vn" href="{href}" onclick="event.stopPropagation()">{esc(vn)}</a>'
            f'<span class="n">{len(sections)} 篇</span>'
            f'<span class="peek">{esc(peek_text(sections))}</span>'
            f"</summary><ul class=\"sects\">{''.join(sects)}</ul></details></li>"
        )
    return '<ul class="tree">' + "".join(items) + "</ul>"


def load_categories(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cats = data["categories"]
    keywords = data.get("keywords") or []
    return cats, keywords


def assign_categories(volumes: list[dict], cats: list[dict], keywords: list[dict]) -> list[dict]:
    by_id = {}
    for cat in cats:
        for vid in cat.get("volumes") or []:
            by_id[str(vid)] = cat["id"]
    used = {c["id"]: [] for c in cats}
    other = {"id": "qita", "name": "其他", "brief": "尚未写入门类配置的卷次", "volumes": []}
    for vol in volumes:
        cid = by_id.get(vol["id"])
        if not cid:
            hay = vol["title"] + vol["display"]
            for rule in keywords:
                if any(w and w in hay for w in rule.get("words") or []):
                    cid = rule["cat"]
                    break
        if not cid or cid not in used:
            cid = "qita"
            used.setdefault("qita", [])
        vol["cat"] = cid
        used.setdefault(cid, []).append(vol)
    ordered = []
    for cat in cats:
        vols = used.get(cat["id"]) or []
        if vols:
            ordered.append({**cat, "vols": vols})
    if used.get("qita"):
        ordered.append({**other, "vols": used["qita"]})
    return ordered


def write_index(out: Path, groups: list[dict], volumes: list[dict], people_n: int, places_n: int, generated: str) -> None:
    yuan = sum(v["charsYuan"] for v in volumes)
    yi = sum(v["charsYi"] for v in volumes)
    cats_html = []
    index_cats = []
    index_vols = []
    for g in groups:
        secs = sum(len(toc_sections(v)) for v in g["vols"])
        cy = sum(v["charsYuan"] for v in g["vols"])
        cats_html.append(
            f'<section class="cat" id="cat-{g["id"]}"><div class="cat-h"><h2><a href="c/{g["id"]}.html">{esc(g["name"])}</a></h2>'
            f'<div class="n">{len(g["vols"])} 卷 · {secs} 篇 · 原文约 {fmt_wan(cy)} 万字</div></div>'
            f'<p class="brief">{esc(g["brief"])}</p>'
            f'{tree_block(g["vols"], "")}</section>'
        )
        index_cats.append({
            "id": g["id"], "name": g["name"], "brief": g["brief"],
            "count": len(g["vols"]), "charsYuan": cy,
        })
        for v in g["vols"]:
            index_vols.append({
                "id": v["id"], "juan": v["juan"], "title": v["title"],
                "fullTitle": v["full"], "display": v["display"],
                "href": f"v/{v['id']}.html", "cat": v["cat"],
                "location": v["location"],
                "charsYuan": v["charsYuan"], "charsYi": v["charsYi"], "charsZhu": v["charsZhu"],
                "sections": toc_sections(v),
            })
    payload = {
        "title": "乾隆《泉州府志》原文 · 译文 · 注解",
        "generated": generated,
        "categories": index_cats,
        "volumes": index_vols,
    }
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "data" / "index.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "data" / "index.js").write_text("window.FUZHI_INDEX=" + js_json(payload) + ";\n", encoding="utf-8")
    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>乾隆《泉州府志》原文 · 译文 · 注解</title><link rel="stylesheet" href="css/style.css"></head>
<body>
<header class="wrap site-top"><a class="home" href="../index.html">拆书房</a><nav class="snav"><a href="index.html" class="on">总目</a><a href="names.html">人物</a><a href="places.html">地名</a></nav></header>
<section class="wrap hero">
  <div class="seal">乾隆二十八年</div>
  <h1><small>乾隆</small>《泉州府志》</h1>
  <p class="sub">原文 · 译文 · 注解，按门类、篇目与人名地名检索</p>
  <div class="stat">
    <span>已整理 <b>{len(volumes)}</b> 卷</span>
    <span>原文约 <b>{fmt_wan(yuan)} 万字</b></span>
    <span>译文约 <b>{fmt_wan(yi)} 万字</b></span>
    <span>人名 <b>{fmt_int(people_n)}</b></span>
    <span>地名 <b>{fmt_int(places_n)}</b></span>
  </div>
  <div class="search">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
    <input id="q" type="search" placeholder="检索篇目、人名或地名，如 蔡襄、星纪、洛阳桥…" autocomplete="off">
  </div>
  <div class="search-out" id="searchOut"></div>
</section>
<main class="wrap" id="cats">
{''.join(cats_html)}
</main>
<footer class="wrap site-foot">
  原文照录 2025 年福建人民出版社点校本，不改字。译文与注解为整理稿。卷首至卷七十六（含卷七十五上、下，共 {len(volumes)} 卷）均已收入。<br>
  <a href="names.html">人物索引</a> · <a href="places.html">地名索引</a> · <a href="../book.html?b=quanzhou-fuzhi">返回《泉州府志》书页</a>
</footer>
<script src="data/index.js"></script>
<script src="data/entities.js"></script>
<script src="js/index.js"></script></body></html>
"""
    (out / "index.html").write_text(page, encoding="utf-8")
    cdir = out / "c"
    cdir.mkdir(parents=True, exist_ok=True)
    for g in groups:
        secs = sum(len(toc_sections(v)) for v in g["vols"])
        cy = sum(v["charsYuan"] for v in g["vols"])
        page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>{esc(g["name"])} · 乾隆《泉州府志》</title><link rel="stylesheet" href="../css/style.css"></head>
<body>
<header class="wrap site-top"><a class="home" href="../../index.html">拆书房</a><nav class="snav"><a href="../index.html">总目</a><a href="../names.html">人物</a><a href="../places.html">地名</a></nav></header>
<section class="wrap hero slim">
  <div class="seal">门类</div>
  <h1>{esc(g["name"])}</h1>
  <p class="sub">{esc(g["brief"])}</p>
  <div class="stat"><span>{len(g["vols"])} 卷</span><span>{secs} 篇</span><span>原文约 {fmt_wan(cy)} 万字</span></div>
</section>
<main class="wrap">
{tree_block(g["vols"], "../")}
</main>
<footer class="wrap site-foot"><a href="../index.html">返回总目</a></footer>
</body></html>
"""
        (cdir / f"{g['id']}.html").write_text(page, encoding="utf-8")


def write_entities(out: Path, entities: list[dict]) -> tuple[int, int]:
    people = [e for e in entities if e["kind"] == "person" and e.get("sec_total")]
    places = [e for e in entities if e["kind"] == "place" and e.get("sec_total")]
    people.sort(key=lambda e: (e["initial"], entidx.sort_key(e["surname"]), entidx.sort_key(e["name"])))
    places.sort(key=lambda e: entidx.sort_key(e["name"]))
    redirects = entidx.alias_redirects(people + places)

    def meta(e: dict) -> dict:
        bios = []
        seen = set()
        for src in e["sources"]:
            if src["href"] in seen:
                continue
            seen.add(src["href"])
            bios.append({
                "juan": src["juan"],
                "volTitle": src["vt"] or src["juan"],
                "sec": src["sec"],
                "href": src["href"],
            })
        return {
            "name": e["name"],
            "kind": e["kind"],
            "aliases": e["aliases"],
            "hits": e["hit_total"],
            "secs": e["sec_total"],
            "shard": entidx.shard_of(e["name"], e["kind"]),
            "bio": bios,
            "surname": e.get("surname") or "",
            "initial": e.get("initial") or "#",
        }

    people_meta = [meta(e) for e in people]
    places_meta = [meta(e) for e in places]
    payload = {"people": people_meta, "places": places_meta, "alias": redirects}
    (out / "data" / "entities.js").write_text("window.FUZHI_ENTITIES=" + js_json(payload) + ";\n", encoding="utf-8")
    (out / "data" / "entities.json").write_text(
        json.dumps({"people": len(people_meta), "places": len(places_meta)}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    shards: dict[str, dict] = defaultdict(dict)
    for e, m in list(zip(people, people_meta)) + list(zip(places, places_meta)):
        shards[m["shard"]][e["name"]] = {
            "name": e["name"],
            "kind": e["kind"],
            "aliases": e["aliases"],
            "hits": e["hits"],
        }
    edir = out / "data" / "e"
    if edir.exists():
        shutil.rmtree(edir)
    edir.mkdir(parents=True)
    for shard, pack in shards.items():
        (edir / f"{shard}.js").write_text("window.FUZHI_HITS=" + js_json(pack) + ";\n", encoding="utf-8")

    # names.html
    letters: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for e in people:
        letters[e["initial"] or "#"][e["surname"] or e["name"][:1]].append(e)
    letter_ids = []
    sections = []
    for letter in list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ["#"]:
        groups = letters.get(letter)
        if not groups:
            continue
        lid = "L" + ("#" if letter == "#" else letter)
        letter_ids.append((lid, "#" if letter == "#" else letter))
        sur_html = []
        for sur in sorted(groups, key=entidx.sort_key):
            names = sorted(groups[sur], key=lambda e: entidx.sort_key(e["name"]))
            links = "".join(
                f'<a class="nm" href="e.html?n={html.escape(quote_url(e["name"]), quote=True)}">{esc(e["name"])}<small>{e["sec_total"]}</small></a>'
                for e in names
            )
            sur_html.append(f'<div class="sg"><h3>{esc(sur)}</h3><div class="nlist">{links}</div></div>')
        sections.append(f'<section class="letter" id="{lid}"><h2>{esc(letter)}</h2>{"".join(sur_html)}</section>')
    nav = "".join(f'<a href="#{lid}">{esc(label)}</a>' for lid, label in letter_ids)
    (out / "names.html").write_text(_index_page("人物索引", "人物", "names", nav, "".join(sections), "person"), encoding="utf-8")

    order = ["山岭", "桥梁津渡", "水利", "祠庙寺观", "城池公署", "学校", "其他"]
    grouped = {k: [] for k in order}
    for e in places:
        grouped[entidx.place_group(e["name"])].append(e)
    pnav = []
    psecs = []
    for i, name in enumerate(order):
        rows = grouped[name]
        if not rows:
            continue
        rows.sort(key=lambda e: entidx.sort_key(e["name"]))
        links = "".join(
            f'<a class="nm" href="e.html?n={html.escape(quote_url(e["name"]), quote=True)}">{esc(e["name"])}<small>{e["sec_total"]}</small></a>'
            for e in rows
        )
        pnav.append(f'<a href="#K{i}">{esc(name)}</a>')
        psecs.append(f'<section class="letter" id="K{i}"><h2>{esc(name)}</h2><div class="nlist">{links}</div></section>')
    (out / "places.html").write_text(
        _index_page("地名 · 建筑索引", "地名", "places", "".join(pnav), "".join(psecs), "place"),
        encoding="utf-8",
    )
    return len(people_meta), len(places_meta)


def _index_page(title: str, seal_nav: str, on: str, nav: str, body: str, kind: str) -> str:
    names_on = ' class="on"' if on == "names" else ""
    places_on = ' class="on"' if on == "places" else ""
    h1 = "人物索引" if on == "names" else "地名 · 建筑索引"
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>{esc(title)} · 乾隆《泉州府志》</title><link rel="stylesheet" href="css/style.css"></head>
<body>
<header class="wrap site-top"><a class="home" href="../index.html">拆书房</a><nav class="snav"><a href="index.html">总目</a><a href="names.html"{names_on}>人物</a><a href="places.html"{places_on}>地名</a></nav></header>
<section class="wrap hero slim">
  <div class="seal">索引</div>
  <h1>{h1}</h1>
  <p class="sub">据篇目标题自动抽名，再通检全书原文、译文与注解。数字为出现的篇数。</p>
  <div class="search">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
    <input id="q" type="search" placeholder="在本页检索姓名或别称…" autocomplete="off">
  </div>
  <div class="search-out" id="searchOut"></div>
</section>
<main class="wrap idx-main" id="idxMain" data-kind="{kind}">
<nav class="az">{nav}</nav>{body}
</main>
<footer class="wrap site-foot"><a href="index.html">返回总目</a></footer>
<script src="data/entities.js"></script>
<script src="js/names.js"></script></body></html>
"""


def clean_generated(out: Path) -> None:
    vdir = out / "v"
    if vdir.exists():
        for p in vdir.glob("*.html"):
            p.unlink()
    cdir = out / "c"
    if cdir.exists():
        for p in cdir.glob("*.html"):
            p.unlink()


def build(src: Path, out: Path, config: Path, entities_path: Path) -> dict:
    files = sorted([p for p in src.glob("*.md") if FNAME.match(p.name)], key=lambda p: sort_key_name(p.name))
    if not files:
        raise SystemExit(f"没有在 {src} 找到卷次 Markdown（形如 00-卷首.md、75上-….md）")
    print(f"解析 {len(files)} 卷…", flush=True)
    volumes = [parse_markdown(p) for p in files]
    cats, keywords = load_categories(config)
    groups = assign_categories(volumes, cats, keywords)
    ent_cfg = json.loads(entities_path.read_text(encoding="utf-8"))
    print("抽取篇目人名、地名…", flush=True)
    entities = entidx.collect_entities(volumes, ent_cfg)
    print(f"通检全书（词条 {len(entities)}）…", flush=True)
    entidx.attach_hits(volumes, entities)
    clean_generated(out)
    (out / "v").mkdir(parents=True, exist_ok=True)
    for i, vol in enumerate(volumes):
        prev = volumes[i - 1] if i else None
        nxt = volumes[i + 1] if i + 1 < len(volumes) else None
        (out / "v" / f"{vol['id']}.html").write_text(page_volume(vol, prev, nxt), encoding="utf-8")
    print("写索引…", flush=True)
    people_n, places_n = write_entities(out, entities)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    write_index(out, groups, volumes, people_n, places_n, generated)
    other = [v["id"] for v in volumes if v["cat"] == "qita"]
    stats = {
        "volumes": len(volumes),
        "ids": [v["id"] for v in volumes],
        "charsYuan": sum(v["charsYuan"] for v in volumes),
        "charsYi": sum(v["charsYi"] for v in volumes),
        "charsZhu": sum(v["charsZhu"] for v in volumes),
        "people": people_n,
        "places": places_n,
        "sections": sum(len(toc_sections(v)) for v in volumes),
        "categories": [(g["name"], len(g["vols"])) for g in groups],
        "other": other,
        "generated": generated,
    }
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description="生成乾隆《泉州府志》译注站")
    ap.add_argument("--src", default="/workspace/fuzhi-translation", help="译文 Markdown 目录")
    ap.add_argument("--out", default=str(ROOT / "fuzhi"), help="输出目录，默认 fuzhi/")
    ap.add_argument("--config", default=str(TOOLS / "fuzhi-categories.json"), help="门类配置")
    ap.add_argument("--entities", default=str(TOOLS / "fuzhi-entities.json"), help="人名地名停用词与手工别称")
    args = ap.parse_args()
    src = Path(args.src)
    if not src.is_dir():
        raise SystemExit(f"找不到译文目录：{src}")
    stats = build(src, Path(args.out), Path(args.config), Path(args.entities))
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    if stats["other"]:
        print("警告：下列卷次未归类，已进入「其他」：", " ".join(stats["other"]), file=sys.stderr)


if __name__ == "__main__":
    main()
