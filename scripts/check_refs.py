#!/usr/bin/env python3
"""Check that a review file quotes the change accurately.

Usage: python3 check_refs.py <review.md> <work-dir> [git-repo-dir]

Checks, against the base/ and new/ files written by fetch_cl.sh:
  * every `path:line` reference names a line that exists. Files outside the
    change are looked up in the base commit when git-repo-dir is given.
  * in every ```diff block, `+` lines exist in the new file, `-` lines exist in
    the base file, and context lines exist in either, near the cited line
A diff line that is exactly "..." (optionally indented) marks elided code and is
skipped. Anything else that is not real code is reported.
Exit status is 1 when a problem is found.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

NEAR = 80  # lines of slack around the line cited in a diff header


def load(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return None


def norm(s):
    return " ".join(s.split())


def main():
    review, work = Path(sys.argv[1]), Path(sys.argv[2])
    repo = sys.argv[3] if len(sys.argv) > 3 else None
    meta = json.loads((work / "meta.json").read_text())
    files = list(meta["files"])
    tree = None

    def base_tree():
        nonlocal tree
        if tree is None:
            out = subprocess.run(["git", "-C", repo, "ls-tree", "-r", "--name-only", meta["base_commit"]],
                                 capture_output=True, text=True)
            tree = out.stdout.splitlines()
        return tree

    def outside_change(name, lo, hi):
        if repo is None:
            return f"ref `{name}:{lo}`: not a changed file; pass git-repo-dir to check it"
        hits = [f for f in base_tree() if f == name or f.endswith("/" + name)]
        if len(hits) != 1:
            return f"ref `{name}:{lo}`: {len(hits)} files match in base tree; use a longer path"
        out = subprocess.run(["git", "-C", repo, "show", f"{meta['base_commit']}:{hits[0]}"],
                             capture_output=True, text=True)
        n = len(out.stdout.splitlines())
        return None if 1 <= lo and hi <= n else f"ref `{name}:{lo}-{hi}`: beyond end of {hits[0]} ({n} lines)"
    text = review.read_text(encoding="utf-8")
    problems = []

    def resolve(name):
        if name in files:
            return name
        hits = [f for f in files if f == name or f.endswith("/" + name)]
        return hits[0] if len(hits) == 1 else None

    # Inline references outside code fences.
    prose = re.sub(r"```.*?```", "", text, flags=re.S)
    for m in re.finditer(r"`([\w./-]+\.[a-z]+):(\d+)(?:-(\d+))?`", prose):
        name, lo, hi = m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))
        path = resolve(name)
        if path is None:
            if any(name.endswith(e) for e in (".cc", ".h", ".rs", ".fidl", ".bind", ".gn", ".py", ".go")):
                why = outside_change(name, lo, hi)
                if why:
                    problems.append(why)
            continue
        new = load(work / "new" / path)
        if new is None:
            problems.append(f"ref `{name}:{lo}`: file deleted in this change")
        elif hi > len(new) or lo < 1:
            problems.append(f"ref `{name}:{lo}-{hi}`: beyond end of file ({len(new)} lines)")

    # Diff blocks.
    for block in re.finditer(r"```diff\n(.*?)```", text, flags=re.S):
        lines = block.group(1).splitlines()
        if not lines:
            continue
        head = re.search(r"([\w./-]+\.[a-z]+)(?::(\d+))?", lines[0])
        base_hint = re.search(r"base (\d+)", lines[0])
        path = resolve(head.group(1)) if head else None
        if path is None:
            problems.append(f"diff block: header `{lines[0].strip()}` does not name a changed file")
            continue
        new = load(work / "new" / path) or []
        base = load(work / "base" / path) or []
        new_at = int(head.group(2)) if head.group(2) else None
        base_at = int(base_hint.group(1)) if base_hint else None

        def found(src, s, at):
            idx = [i + 1 for i, l in enumerate(src) if norm(l) == s]
            if not idx:
                return "missing"
            if at is not None and not any(abs(i - at) <= NEAR for i in idx):
                return f"far from line {at} (found at {idx[:3]})"
            return None

        for raw in lines[1:]:
            if not raw.strip():
                continue
            sign, body = raw[0], norm(raw[1:])
            if body == "..." or not body:
                continue
            if sign == "+":
                why = found(new, body, new_at)
            elif sign == "-":
                why = found(base, body, base_at)
            elif sign == " ":
                a, b = found(new, body, new_at), found(base, body, base_at)
                why = None if a is None or b is None else a
            else:
                why = "line has no diff prefix"
            if why:
                problems.append(f"diff {path}: `{raw.strip()[:70]}`: {why}")

    for p in problems:
        print(p)
    print(f"{len(problems)} problem(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
