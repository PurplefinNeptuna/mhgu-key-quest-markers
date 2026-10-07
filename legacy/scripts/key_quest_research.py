from paths import MOD, SCRIPTS, FORGE, DEPS, PYTHON, CONTAINER_STORAGE, input_path
#!/usr/bin/env python3
"""Inspect copied MHGU quest resources and cross-check saved Kiranico HTML.

Read-only against all inputs. Writes research JSON, never a mod or save.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct

from mhgu_assets import read_arc, require

from paths import ROOT, MOD, SCRIPTS, FORGE, DEPS, PYTHON, CONTAINER_STORAGE, input_path
WORK = ROOT / "work/key-quest-markers"
KEY_GROUPS = frozenset(range(1, 18)) | frozenset(range(19, 23))


def quest_groups(data):
    require(len(data) >= 8, "Truncated quest-group header")
    version, count = struct.unpack_from("<fI", data)
    require(version == 4.0 and len(data) == 8 + count * 7,
            "Unexpected quest-group version/count/length")
    groups = {}
    duplicates = []
    for index in range(count):
        quest_id, attr1, attr2, title_ver = struct.unpack_from("<IBBB", data, 8 + index * 7)
        value = [attr1, attr2, title_ver]
        if quest_id in groups:
            require(groups[quest_id] == value, f"Conflicting group entries: {quest_id}")
            duplicates.append({"id": quest_id, "index": index})
        groups.setdefault(quest_id, value)
    return groups, count, duplicates


def quest_title(data):
    require(len(data) >= 40 and data[:4] == b"GMD\0", "Invalid GMD header")
    index_count, string_count, name_bytes, text_bytes, package_bytes = struct.unpack_from(
        "<5I", data, 20)
    require(index_count == name_bytes == 0 and string_count == 7,
            "Expected non-keyed seven-string quest GMD")
    text_start = 40 + package_bytes + 1
    require(text_start <= len(data) and data[text_start - 1] == 0,
            "Invalid GMD package-name bounds")
    require(text_start + text_bytes == len(data), "Invalid GMD text length")
    text = data[text_start:].split(b"\0")
    require(len(text) == string_count + 1 and text[-1] == b"", "Invalid GMD string count")
    return text[0].decode("utf-8")


def local_inventory(inputs):
    provenance = json.loads((inputs / "provenance.json").read_text())
    for item in provenance:
        path = Path(item["copy"])
        require(path.resolve().is_relative_to(inputs.resolve()), "Copy outside input directory")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"],
                f"Copied input changed: {path}")
    _, common = read_arc(inputs / "loc/arc/village/common.arc")
    group_data = common[("quest\\quest_group", 0x61CF79AF)]["data"]
    groups, count, duplicates = quest_groups(group_data)
    quests = []
    for arc in ("vq", "gq", "gq2"):
        _, entries = read_arc(inputs / f"loc/arc/quest/{arc}.arc")
        for (name, kind), entry in entries.items():
            match = re.fullmatch(r"eng\\quest\\questData\\questData_(\d{7})_eng", name)
            if not match:
                continue
            require(kind == 0x242BB29A, "Unexpected quest GMD type")
            quest_id = int(match[1])
            loc_name = f"loc\\quest\\questData\\questData_{quest_id:07}"
            records = [e["data"] for (n, _), e in entries.items() if n == loc_name]
            require(len(records) == 1, f"Missing/ambiguous quest data: {quest_id}")
            data = records[0]
            require(len(data) == 369 and struct.unpack_from("<2I", data) == (0x434B0000, 1),
                    "Unexpected compact quest-data layout")
            require(struct.unpack_from("<I", data, 12)[0] == quest_id, "Quest ID mismatch")
            require(quest_id in groups, f"Quest missing from group resource: {quest_id}")
            quests.append(dict(id=quest_id, arc=arc, title=quest_title(entry["data"]),
                               level=data[18], group=groups[quest_id],
                               key=groups[quest_id][0] in KEY_GROUPS))
    require(len({q["id"] for q in quests}) == len(quests), "Duplicate inventory quest IDs")
    return quests, dict(count=count, unique_ids=len(groups), duplicates=duplicates,
                       resource_sha256=hashlib.sha256(group_data).hexdigest())


def compare(quests, html_path):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_path.read_text(), "html.parser")
    web = []
    outside_keys = Counter()
    for row in soup.select("tr"):
        link = row.select_one('a[href^="https://mhgu.kiranico.com/quest/"]')
        pane = row.find_parent(class_="tab-pane")
        if link is None or pane is None:
            continue
        badges = [b.get_text(strip=True) for b in row.select(".badge")]
        pane_id = pane.get("id", "")
        if not re.fullmatch(r"s[01]-\d+", pane_id):
            if "Key" in badges:
                outside_keys[pane_id] += 1
            continue
        web.append(dict(pane=pane_id, title=link.get_text(" ", strip=True),
                        url=link["href"], badges=badges))
    local = defaultdict(list)
    for quest in quests:
        if quest["id"] >= 1000000 or quest["id"] // 10000 % 10 not in (0, 1):
            continue
        pane = f"s{0 if quest['arc'] == 'vq' else 1}-{quest['level']}"
        local[(pane, quest["title"])].append(quest)
    web_counts = Counter((q["pane"], q["title"]) for q in web)
    require(web_counts == Counter({k: len(v) for k, v in local.items()}),
            "Area/tier/title inventories disagree with Kiranico")
    matched, ambiguous, mismatches = [], [], []
    for row in web:
        candidates = local[(row["pane"], row["title"])]
        item = dict(web=row, candidates=candidates)
        if len(candidates) == 1:
            matched.append(item)
        else:
            ambiguous.append(item)
        if any(q["key"] != ("Key" in row["badges"]) for q in candidates):
            mismatches.append(item)
    require(not mismatches, "Key classification disagrees with Kiranico")
    web_key_ids = {m["candidates"][0]["id"] for m in matched if "Key" in m["web"]["badges"]}
    require(web_key_ids == {q["id"] for q in quests if q["key"]},
            "Missing or ambiguous key-quest identity")
    return dict(source="https://mhgu.kiranico.com/quest", html_sha256=hashlib.sha256(
                    html_path.read_bytes()).hexdigest(), web_rows=len(web),
                uniquely_matched_rows=len(matched), ambiguous_rows=ambiguous,
                key_count=len(web_key_ids), key_counts_by_pane=dict(sorted(Counter(
                    row["pane"] for row in web if "Key" in row["badges"]).items())),
                mismatches=mismatches, matched=matched,
                outside_scope_key_badges=dict(outside_keys))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=WORK / "inputs")
    parser.add_argument("--html", type=Path, default=WORK / "research/kiranico-quest.html")
    parser.add_argument("--output", type=Path, default=WORK / "research/verified-crosscheck.json")
    args = parser.parse_args()
    input_paths = [p.resolve() for p in args.inputs.rglob("*") if p.is_file()] + [args.html.resolve()]
    require(args.output.resolve() not in input_paths, "Output must not overwrite an input")
    quests, groups = local_inventory(args.inputs)
    report = dict(quest_group=groups, local_resource_quests=len(quests),
                  comparison=compare(quests, args.html))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    result = report["comparison"]
    print(f"{result['web_rows']} quest rows; {result['key_count']} keys; "
          f"{result['uniquely_matched_rows']} unique matches; "
          f"{len(result['ambiguous_rows'])} duplicate-title rows; no key mismatches.")
    print(args.output)


if __name__ == "__main__":
    main()
