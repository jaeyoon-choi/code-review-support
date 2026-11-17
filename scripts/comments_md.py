#!/usr/bin/env python3
"""Print one markdown block per existing review thread, originals quoted verbatim.

Usage: python3 comments_md.py <work-dir>

Reads existing_comments.txt written by fetch_cl.sh. Each block is an Obsidian
callout box (`> [!quote]+`) titled with the location, authors, and status. Inside
it, every message is a nested quote followed by a `> <번역>` placeholder to
replace. Blocks are separated by a line `<!-- thread -->`, which is only a cut
mark and must not be pasted. Copying
originals by script keeps them exact, including the reviewers' typos.
"""
import re
import sys
from pathlib import Path

TITLE = {"/COMMIT_MSG": "커밋 메시지", "/PATCHSET_LEVEL": "패치셋 전체"}


def parse(text):
    threads = []
    for block in text.split("\n=== "):
        block = block.lstrip("= ").rstrip()
        if not block:
            continue
        head, *rest = block.split("\n")
        m = re.match(r"\[(\w+)\] (\S+):(\S+)", head)
        msgs = []
        for line in rest:
            mm = re.match(r"  \[([^,]+), ps\d+\] (.*)", line)
            if mm:
                msgs.append([mm.group(1), mm.group(2)])
            elif msgs:
                msgs[-1][1] += "\n" + line
        threads.append({
            "status": "미해결" if m.group(1) == "UNRESOLVED" else "해결됨",
            "path": m.group(2), "line": m.group(3), "msgs": msgs,
        })
    return threads


def main():
    work = Path(sys.argv[1])
    threads = parse((work / "existing_comments.txt").read_text(encoding="utf-8"))
    # Open threads first, then by location.
    threads.sort(key=lambda t: (t["status"] != "미해결", t["path"], t["line"]))
    for t in threads:
        name = t["path"].rsplit("/", 1)[-1] if t["path"] not in TITLE else None
        if t["path"] in TITLE:
            loc = TITLE[t["path"]] + (f":{t['line']}" if t["line"] != "-" else "")
        else:
            loc = f"`{name}:{t['line']}`"
        authors = ", ".join(dict.fromkeys(m[0] for m in t["msgs"]))
        print("<!-- thread -->")
        box = [f"> [!quote]+ 리뷰어 코멘트 · {loc} · {authors} · {t['status']}"]
        for k, (who, msg) in enumerate(t["msgs"]):
            if k:
                box.append(">")
            box += [f"> **{who}**", ">"]
            box += [("> > " + l).rstrip() for l in msg.strip().split("\n")]
            box += [">", "> <번역>"]
        print("\n".join(box) + "\n")


if __name__ == "__main__":
    main()
