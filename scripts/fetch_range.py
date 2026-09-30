#!/usr/bin/env python3
"""Fetch a local git commit range for review, one work folder per commit.

Usage: python3 fetch_range.py <base> <head> <work> [--repo <dir>]

  <base>  where the range starts, usually the upstream branch (origin/main).
          Its own commits are not reviewed.
  <head>  the last commit to review, a branch name or sha.

For each commit in base..head, oldest first, <work>/cN/ gets the same files
fetch_cl.sh writes for a Gerrit change, with the commit's parent as the base:

  meta.json       number (cN), subject, owner, project, base/new commit, files
  commit_msg.txt  the full commit message
  change.patch    the commit's diff
  hunks.txt       hunk ranges with new-side line numbers
  base/, new/     full files before and after

<work>/all/ holds the whole range (base..head) the same way, and
<work>/units.json lists the units in order. A renamed file's old content is also
written to base/ under its new name, so `-` lines in it can be checked.

A commit whose author email appears in none of its Signed-off-by trailers is
reported, since history rewritten under a different git config changes the
author without touching the message.

Check a review against every folder with check_units.py.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r


def name_status(repo, base, new):
    """(status, old_path, new_path) for every file the diff touches."""
    out = git(repo, "diff", "--name-status", "-M", base, new).stdout
    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        status = parts[0][0]
        if status == "R":
            rows.append((status, parts[1], parts[2]))
        else:
            rows.append((status, parts[1], parts[1]))
    return rows


def write_side(repo, rev, path, dest):
    r = git(repo, "show", f"{rev}:{path}", check=False)
    if r.returncode == 0:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(r.stdout)


def build(repo, out, base, new, meta):
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for status, old_path, new_path in name_status(repo, base, new):
        write_side(repo, base, old_path, out / "base" / old_path)
        if old_path != new_path:
            write_side(repo, base, old_path, out / "base" / new_path)
        write_side(repo, new, new_path, out / "new" / new_path)
        entry = {"status": status}
        if old_path != new_path:
            entry["old_path"] = old_path
        files[new_path] = entry
    patch = git(repo, "diff", "-M", base, new).stdout
    (out / "change.patch").write_text(patch)
    hunks = [l for l in git(repo, "diff", "-U0", "-M", base, new).stdout.splitlines()
             if l.startswith(("+++", "@@"))]
    (out / "hunks.txt").write_text("\n".join(hunks) + "\n")
    meta.update({"base_commit": base, "new_commit": new, "files": files})
    (out / "meta.json").write_text(json.dumps(meta, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("base")
    ap.add_argument("head")
    ap.add_argument("work")
    ap.add_argument("--repo", default=".")
    a = ap.parse_args()

    repo = git(a.repo, "rev-parse", "--show-toplevel").stdout.strip()
    project = Path(repo).name
    base = git(repo, "rev-parse", a.base).stdout.strip()
    head = git(repo, "rev-parse", a.head).stdout.strip()
    commits = git(repo, "rev-list", "--reverse", f"{base}..{head}").stdout.split()
    if not commits:
        sys.exit(f"no commits in {a.base}..{a.head}")
    merges = git(repo, "rev-list", "--merges", f"{base}..{head}").stdout.split()
    if merges:
        print(f"warning: {len(merges)} merge commit(s); each is diffed against its first parent")

    work = Path(a.work)
    units = []
    for i, sha in enumerate(commits, 1):
        name = f"c{i}"
        parent = git(repo, "rev-parse", f"{sha}^").stdout.strip()
        fmt = git(repo, "log", "-1", "--format=%s%x00%an <%ae>%x00%h", sha).stdout.strip()
        subject, owner, short = fmt.split("\x00")
        meta = {"number": name, "unit": i, "subject": subject, "owner": owner,
                "project": project, "short": short}
        build(repo, work / name, parent, sha, meta)
        body = git(repo, "log", "-1", "--format=%B", sha).stdout
        (work / name / "commit_msg.txt").write_text(body)
        email = owner.rsplit("<", 1)[-1].rstrip(">")
        signoffs = [l for l in body.splitlines() if l.startswith("Signed-off-by:")]
        if signoffs and not any(email in l for l in signoffs):
            print(f"warning: {name} {short} author <{email}> is not in its Signed-off-by")
        units.append({"unit": name, "commit": sha, "short": short, "subject": subject,
                      "files": len(meta["files"])})

    branch = git(repo, "rev-parse", "--abbrev-ref", a.head, check=False).stdout.strip() or a.head
    build(repo, work / "all", base, head,
          {"number": "all", "subject": f"{a.base}..{a.head}", "project": project,
           "branch": branch, "short": head[:7]})
    msgs = "\n".join(f"--- {u['unit']} {u['short']}\n" +
                     git(repo, "log", "-1", "--format=%B", u["commit"]).stdout for u in units)
    (work / "all" / "commit_msg.txt").write_text(msgs)
    (work / "units.json").write_text(json.dumps(
        {"project": project, "branch": branch, "base": base, "head": head, "units": units}, indent=2))

    for u in units:
        print(f"{u['unit']:>4} {u['short']} {u['files']:>3} files  {u['subject']}")
    print(f"{'all':>4} {head[:7]} {len(json.loads((work / 'all' / 'meta.json').read_text())['files']):>3} files  "
          f"{a.base}..{a.head}")


if __name__ == "__main__":
    main()
