"""Person and place index for the 泉州府志 translation site.

Names are taken from section titles (biography headings, and place-like
headings), then located across the whole book. Courtesy names in a biography
(字 / 号 / 谥) and the manual pairs in ``fuzhi-entities.json`` become aliases.
"""

from __future__ import annotations

import re
from collections import defaultdict

from pypinyin import lazy_pinyin

COMPOUND = (
    "欧阳", "司马", "上官", "诸葛", "夏侯", "皇甫", "司徒", "司空", "令狐",
    "宇文", "长孙", "慕容", "申屠", "公孙", "端木", "南宫", "闻人", "赫连",
    "万俟", "尉迟", "澹台", "宗政", "濮阳", "淳于", "单于", "太叔", "申屠",
    "仲孙", "钟离", "鲜于", "闾丘", "子车", "司寇",
)

PLACE_RE = re.compile(
    r"^[\u4e00-\u9fff]{1,14}(?:山|岭|峰|岩|屿|岛|洞|泉|溪|江|河|桥|渡|陂|塘|堤|埭|寨|城|台|亭|祠|庙|宫|寺|庵|观|院|学|署|厅|门|驿道|卫)$"
)
PLACE_CUT = re.compile(r"[及与至、，,]")
PLACE_NOISE = re.compile(r"及|与|至|诸|其余|修|兴|记|说|考|附")
PERSON_CHARS = re.compile(r"^[\u4e00-\u9fff⿰-⿻□〇]{2,6}$")
BAD_PERSON = re.compile(r"(说|志|表|图|序|例|录|考|记|卷|县|门|类|附|及|与|街|巷|都|坊|铺|图)$")

SHARDS = 32


def surname_of(name: str) -> str:
    for c in COMPOUND:
        if name.startswith(c) and len(name) > len(c):
            return c
    return name[:1]


def initial_of(text: str) -> str:
    if not text:
        return "#"
    py = lazy_pinyin(text[0])
    if py and py[0] and py[0][0].isalpha():
        return py[0][0].upper()
    return "#"


def sort_key(text: str):
    return tuple(lazy_pinyin(text))


def _generic(title: str, stop: set[str]) -> bool:
    t = title.strip()
    if t in stop:
        return True
    bare = re.sub(r"[一二三四五六七八九十0-9上下]+$", "", t)
    bare = re.sub(r"^(国朝|本朝|明朝|宋朝|唐朝|五代|唐|宋|元|明)", "", bare)
    return bare in stop or t in stop


def is_clean_person(name: str, stop: set[str], allow_topo: bool = False) -> bool:
    if name in stop or _generic(name, stop):
        return False
    if not PERSON_CHARS.fullmatch(name):
        return False
    if BAD_PERSON.search(name):
        return False
    # 陈龙岩、曾素庵这类人名以山、岩、庵结尾。列传标题仍收人名；
    # 山川卷里的同名条目另走地名。
    if PLACE_RE.match(name) and not name.endswith("氏"):
        if not (allow_topo and len(name) <= 4):
            return False
    if re.match(r"^(国朝|本朝|明朝|宋朝|唐朝|晋江|南安|惠安|安溪|同安|府县|各县)", name):
        return False
    if re.search(r"(贡生|进士|举人|荐辟|武举|贞节|贞烈|古迹|要冲|县治|县川|丁口|四至|之属|名宦|武绩|勋绩|释衲|出使|阁帖|之谶|谶)$", name):
        return False
    if len(name) >= 5 and not name.startswith(COMPOUND) and not name.endswith(("氏", "禅师", "大师", "道人")):
        return False
    if len(name) == 6 and not name.endswith(("氏", "禅师", "大师", "道人")):
        return False
    return True


def place_names_from_title(title: str, stop: set[str]) -> list[str]:
    raw = re.sub(r"^[\d]+\.\s*", "", title).strip()
    raw = re.sub(r"^(第[一二三四五六七八九十百]+则)\s*", "", raw)
    found: list[str] = []

    def add(piece: str) -> None:
        piece = piece.strip(" 「」\"'()（）")
        piece = re.sub(r"(诸说|附考|考略|附)$", "", piece)
        if not piece or piece in stop or piece in found:
            return
        if PLACE_NOISE.search(piece):
            return
        if PLACE_RE.match(piece):
            found.append(piece)

    base = re.sub(r"（[^）]*）", "", raw)
    base = re.sub(r"\([^)]*\)", "", base).strip()
    if _generic(base, stop):
        return []
    add(base)
    for part in PLACE_CUT.split(base):
        add(part)
    for group in re.findall(r"（([^）]+)）", raw):
        for piece in re.split(r"[、，,]", group):
            add(piece)
    return found


def person_names_from_title(title: str, is_yi: bool, stop: set[str]) -> list[str]:
    raw = title.strip()
    if _generic(raw, stop):
        return []
    names: list[str] = []

    def add(piece: str, allow_topo: bool = False) -> None:
        piece = piece.strip()
        if piece and piece not in names and is_clean_person(piece, stop, allow_topo=allow_topo):
            names.append(piece)

    if is_yi:
        base = re.sub(r"（[^）]*）", "", raw)
        base = re.sub(r"\([^)]*\)", "", base).strip()
        base = re.sub(r"^[\d]+\.\s*", "", base)
        for part in re.split(r"[　、]", base):
            part = part.strip()
            if not part:
                continue
            if is_clean_person(part, stop, allow_topo=True):
                add(part, allow_topo=True)
            elif ("妻" in part or part.endswith("氏") or "未婚妻" in part) and 2 <= len(part) <= 32:
                if part not in names:
                    names.append(part)
        return names

    t = re.sub(r"^[\d]+\.\s*", "", raw).strip()
    t = re.sub(r"^[一二三四五六七八九十]+、\s*", "", t)
    m = re.match(r"^([\u4e00-\u9fff⿰-⿻]{2,4})(?:《|（)", t)
    if m:
        add(m.group(1))
    # 「又序（邵锐）」一类篇题里的作者。地名、官名括号不抽成人名。
    m = re.search(r"（([\u4e00-\u9fff]{2,4})）\s*$", t)
    if m and "则" not in t and re.search(r"序|跋|记|传|《", t):
        add(m.group(1))
    if is_clean_person(t, stop):
        add(t)
    return names


def courtesy_aliases(text: str, name: str) -> list[str]:
    """Only 字 / 号 / 谥 that sit next to this name, not any later 字."""
    if not text or not name:
        return []
    sur = surname_of(name)
    head = text[:240]
    snippet = head[head.find(name):head.find(name) + 48] if name in head else ""
    if not snippet:
        return []
    found: list[str] = []
    patterns = (
        rf"{re.escape(name)}，字([^，。；、]{{1,4}})",
        rf"{re.escape(name)}，号([^，。；、]{{1,6}})",
        rf"{re.escape(name)}，谥(?:曰|为)?([^，。；、]{{1,6}})",
    )
    for pat in patterns:
        m = re.search(pat, snippet)
        if not m:
            continue
        word = m.group(1).strip("「」\"'")
        if not word or word == name or not re.fullmatch(r"[\u4e00-\u9fff]{1,6}", word):
            continue
        cands = []
        if 2 <= len(word) <= 4 and word.startswith(sur):
            cands.append(word)
        elif not word.startswith(sur) and 1 <= len(word) <= 3:
            cands.append(sur + word)
        for c in cands:
            if c != name and c not in found and 2 <= len(c) <= 8:
                found.append(c)
    return found


def _walk(nodes):
    for n in nodes:
        yield n
        yield from _walk(n.get("children") or [])


def collect_entities(volumes: list[dict], config: dict) -> list[dict]:
    stop_people = set(config.get("stopPeople") or [])
    stop_places = set(config.get("stopPlaces") or [])
    manual = config.get("aliases") or {}
    bag: dict[tuple[str, str], dict] = {}

    def ensure(kind: str, name: str) -> dict:
        key = (kind, name)
        ent = bag.get(key)
        if ent is None:
            ent = {
                "name": name,
                "kind": kind,
                "aliases": [],
                "sources": [],
                "surname": surname_of(name) if kind == "person" else "",
                "initial": initial_of(surname_of(name) if kind == "person" else name),
            }
            bag[key] = ent
        return ent

    for vol in volumes:
        for node in _walk(vol["tree"]):
            if node.get("level", 0) < 2 and not node.get("yi"):
                continue
            title = node.get("title") or ""
            places = place_names_from_title(title, stop_places)
            people = person_names_from_title(title, bool(node.get("yi")), stop_people)
            plain = node.get("plain") or ""
            if node.get("yi"):
                kept = []
                for person in people:
                    head = plain[: len(person) + 48]
                    bio = re.search(
                        rf"{re.escape(person)}(?:，字|，号|是|，[^《在]{{0,12}}人)",
                        head,
                    )
                    if PLACE_RE.match(person):
                        gazetteer = re.search(rf"{re.escape(person)}(?:，《|在|，一名|，即)", plain[:180])
                        if not bio or gazetteer:
                            continue
                    elif (
                        len(person) >= 4
                        and "妻" not in person
                        and not person.endswith(("氏", "禅师", "大师", "道人"))
                        and not person.startswith(COMPOUND)
                        and not bio
                    ):
                        continue
                    kept.append(person)
                people = kept
                if people:
                    places = [p for p in places if p not in people]
            else:
                people = [p for p in people if p not in places]
            targets: list[tuple[str, str]] = [("place", p) for p in places]
            if not places or people:
                targets.extend(("person", p) for p in people)
            if node.get("yi") and not people and not places:
                # keep long biography headings (列女) that the cleaner rejected
                base = re.sub(r"（[^）]*）", "", title).strip()
                if ("妻" in base or base.endswith("氏")) and 2 <= len(base) <= 32:
                    targets.append(("person", base))
            for kind, name in targets:
                if len(name) < 2:
                    continue
                ent = ensure(kind, name)
                ent["sources"].append({
                    "vol": vol["id"],
                    "sid": node.get("id"),
                    "juan": vol["juan"],
                    "vt": vol["vt"],
                    "sec": title,
                    "href": f"v/{vol['id']}.html#{node['id']}" if node.get("id") else f"v/{vol['id']}.html",
                    "plain": node.get("plain") or "",
                })
    for name, aliases in manual.items():
        ent = bag.get(("person", name))
        if not ent:
            continue
        for a in aliases:
            if a and a != name and a not in ent["aliases"]:
                ent["aliases"].append(a)
    for ent in bag.values():
        if ent["kind"] != "person" or not ent["sources"]:
            continue
        text = ent["sources"][0].get("plain") or ""
        for a in courtesy_aliases(text, ent["name"]):
            if a not in ent["aliases"]:
                ent["aliases"].append(a)
    people = {e["name"] for e in bag.values() if e["kind"] == "person"}
    geo = {f"{n:02d}" for n in range(5, 18)} | {"75a", "75b"}
    for key, ent in list(bag.items()):
        if ent["kind"] != "place" or ent["name"] not in people:
            continue
        if not any(s["vol"] in geo for s in ent["sources"]):
            del bag[key]
    return list(bag.values())


class _AC:
    def __init__(self, words: list[str]):
        self.trie = [{}]
        self.out = [[]]
        self.fail = [0]
        for w in words:
            node = 0
            for ch in w:
                nxt = self.trie[node].get(ch)
                if nxt is None:
                    nxt = len(self.trie)
                    self.trie[node][ch] = nxt
                    self.trie.append({})
                    self.out.append([])
                    self.fail.append(0)
                node = nxt
            self.out[node].append(w)
        from collections import deque
        q = deque()
        for nxt in self.trie[0].values():
            q.append(nxt)
        while q:
            r = q.popleft()
            for ch, nxt in self.trie[r].items():
                q.append(nxt)
                f = self.fail[r]
                while f and ch not in self.trie[f]:
                    f = self.fail[f]
                self.fail[nxt] = self.trie[f].get(ch, 0)
                if self.fail[nxt] == nxt:
                    self.fail[nxt] = 0
                self.out[nxt] = self.out[nxt] + self.out[self.fail[nxt]]

    def find(self, text: str) -> list[tuple[int, int, str]]:
        node = 0
        spans = []
        for i, ch in enumerate(text):
            while node and ch not in self.trie[node]:
                node = self.fail[node]
            node = self.trie[node].get(ch, 0)
            for w in self.out[node]:
                spans.append((i - len(w) + 1, i + 1, w))
        return _keep_longest(spans)


def _keep_longest(spans: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    kept: list[tuple[int, int, str]] = []
    for s, e, w in spans:
        if any(s >= ks and e <= ke and (e - s) < (ke - ks) for ks, ke, _ in kept):
            continue
        kept.append((s, e, w))
    return kept


def _snip(text: str, start: int, length: int) -> str:
    a = max(0, start - 18)
    b = min(len(text), start + length + 42)
    s = text[a:b]
    if a:
        s = "…" + s
    if b < len(text):
        s = s + "…"
    return s


def attach_hits(volumes: list[dict], entities: list[dict]) -> None:
    """Fill hits, counts, and per-section mention lists. Mutates both."""
    word_to_ents: dict[str, list[dict]] = defaultdict(list)
    words = []
    words_seen: set[str] = set()
    for ent in entities:
        ent["hits"] = []
        ent["hit_total"] = 0
        ent["sec_total"] = 0
        seen = set()
        terms = [ent["name"]]
        terms.extend(a for a in ent["aliases"] if len(a) >= 3)
        for term in terms:
            if len(term) < 2 or term in seen:
                continue
            seen.add(term)
            if ent not in word_to_ents[term]:
                word_to_ents[term].append(ent)
            if term not in words_seen:
                words_seen.add(term)
                words.append(term)
    if not words:
        return
    ac = _AC(words)
    for vol in volumes:
        for node in _walk(vol["tree"]):
            text = node.get("plain") or ""
            if len(text) < 2:
                continue
            spans = ac.find(text)
            if not spans:
                continue
            by_ent: dict[int, dict] = {}
            for start, end, word in spans:
                for ent in word_to_ents.get(word, ()):
                    slot = by_ent.get(id(ent))
                    if slot is None:
                        slot = {"ent": ent, "n": 0, "at": start, "word": word}
                        by_ent[id(ent)] = slot
                    slot["n"] += 1
                    if start < slot["at"]:
                        slot["at"] = start
                        slot["word"] = word
            href = f"v/{vol['id']}.html#{node['id']}" if node.get("id") else f"v/{vol['id']}.html"
            mentions = []
            for slot in by_ent.values():
                ent = slot["ent"]
                bio = any(s["vol"] == vol["id"] and s["sid"] == node.get("id") for s in ent["sources"])
                hit = {
                    "vol": vol["id"],
                    "juan": vol["juan"],
                    "vt": vol["vt"],
                    "sec": node.get("title") or vol["display"],
                    "href": href,
                    "n": slot["n"],
                    "bio": bio,
                    "snip": _snip(text, slot["at"], len(slot["word"])),
                }
                ent["hits"].append(hit)
                ent["hit_total"] += slot["n"]
                ent["sec_total"] += 1
                mentions.append({
                    "name": ent["name"],
                    "n": slot["n"],
                    "bio": bio,
                    "kind": ent["kind"],
                })
            mentions.sort(key=lambda m: (not m["bio"], -m["n"], m["name"]))
            node["mentions"] = mentions[:30]
    for ent in entities:
        ent["hits"].sort(key=lambda h: (h["vol"], h["href"]))


def shard_of(name: str, kind: str) -> str:
    import zlib
    n = zlib.crc32(name.encode("utf-8")) % SHARDS
    prefix = "p" if kind == "person" else "g"
    return f"{prefix}-{n:02d}"


def place_group(name: str) -> str:
    if re.search(r"(山|岭|峰|岩|屿|岛)$", name):
        return "山岭"
    if re.search(r"(桥|渡)$", name):
        return "桥梁津渡"
    if re.search(r"(泉|溪|江|河|陂|塘|堤|埭)$", name):
        return "水利"
    if re.search(r"(祠|庙|宫|寺|庵|观)$", name):
        return "祠庙寺观"
    if re.search(r"(城|寨|台|亭|署|厅|门|卫)$", name):
        return "城池公署"
    if name.endswith("学") or name.endswith("院"):
        return "学校"
    return "其他"


def alias_redirects(entities: list[dict]) -> dict[str, str]:
    primary = {e["name"] for e in entities}
    mapping: dict[str, str] = {}
    conflict = set()
    for ent in entities:
        for alias in ent["aliases"]:
            if not alias or alias == ent["name"] or alias in primary:
                continue
            prev = mapping.get(alias)
            if prev and prev != ent["name"]:
                conflict.add(alias)
            else:
                mapping[alias] = ent["name"]
    for alias in conflict:
        mapping.pop(alias, None)
    return mapping
