#!/usr/bin/env python3
"""Check a branch review, unit by unit, against the folders fetch_range.py wrote.

Usage: python3 check_units.py <review.md> <work-dir> [git-repo-dir]

Line numbers in a branch review belong to the commit a unit describes, so each
part of the file is checked against its own folder:

  * from a "## 단위 N" heading until the next heading of level 2 or higher,
    and from a "#### 단위 N" heading (the appendix tables) until the next
    heading of level 4 or higher, against <work>/cN
  * everything else, against <work>/all (the whole range)

Each part goes through check_refs.py. Exit status is 1 when any part has a
problem.
"""
import re
import subprocess
import sys
from pathlib import Path

UNIT = re.compile(r"^(#{2}|#{4}) 단위 (\d+)\b")
HEADING = re.compile(r"^(#{1,6}) ")


def split(text):
    parts, cur, level = {}, "all", None
    fence = False
    for line in text.splitlines(keepends=True):
        if line.startswith("```"):
            fence = not fence
        if not fence:
            m = UNIT.match(line)
            h = HEADING.match(line)
            if m:
                cur, level = f"c{m.group(2)}", len(m.group(1))
            elif h and level is not None and len(h.group(1)) <= level:
                cur, level = "all", None
        parts.setdefault(cur, []).append(line)
    return parts


def main():
    review, work = Path(sys.argv[1]), Path(sys.argv[2])
    repo = sys.argv[3] if len(sys.argv) > 3 else None
    checker = Path(__file__).with_name("check_refs.py")
    total = 0
    for name, lines in sorted(split(review.read_text(encoding="utf-8")).items()):
        folder = work / name
        if not folder.is_dir():
            print(f"[{name}] no folder {folder}; is the unit number right?")
            total += 1
            continue
        part = work / f".part_{name}.md"
        part.write_text("".join(lines), encoding="utf-8")
        cmd = ["python3", str(checker), str(part), str(folder)] + ([repo] if repo else [])
        out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()
        part.unlink()
        count = int(out[-1].split()[0]) if out else 0
        total += count
        print(f"[{name}] {out[-1] if out else '0 problem(s)'}")
        for line in out[:-1]:
            print(f"    {line}")
    print(f"{total} problem(s)")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
