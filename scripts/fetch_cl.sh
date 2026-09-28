#!/usr/bin/env bash
# Fetch a Gerrit change for review: metadata, commit message, patch, comment
# threads, and the full base/new versions of every touched file.
#
# Usage: bash fetch_cl.sh <gerrit-url-or-change-number> <out-dir> [--since <old-patchset>] [--repo <dir>]
#   A bare number assumes fuchsia-review.googlesource.com.
#   --since writes interdiff.patch between <old-patchset> and the current one.
#   --repo defaults to the current directory and must be a clone of the change's
#   project so commits can be fetched incrementally.
set -euo pipefail

arg="${1:?usage: fetch_cl.sh <url-or-number> <out-dir> [--since N] [--repo DIR]}"
out="${2:?out-dir required}"
shift 2
since=""
repo="$PWD"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --since) since="$2"; shift 2 ;;
    --repo) repo="$2"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ "$arg" =~ ^[0-9]+$ ]]; then
  host="fuchsia-review.googlesource.com"
  num="$arg"
else
  host="$(sed -E 's#^https?://([^/]+)/.*#\1#' <<<"$arg")"
  num="$(grep -oE '/\+/[0-9]+' <<<"$arg" | tr -dc '0-9')"
  [[ -n "$num" ]] || num="$(grep -oE '[0-9]{5,}' <<<"$arg" | head -1)"
fi
[[ -n "${num:-}" ]] || { echo "cannot parse change number from: $arg" >&2; exit 1; }

rm -rf "$out/base" "$out/new"
mkdir -p "$out/base" "$out/new"
api="https://$host/changes/$num"

# Gerrit prefixes JSON responses with ")]}'" to block XSSI; strip that line.
curl -fsS "$api?o=ALL_REVISIONS&o=CURRENT_COMMIT&o=CURRENT_FILES&o=DETAILED_ACCOUNTS" \
  | tail -c +5 > "$out/change.json"
curl -fsS "$api/comments" | tail -c +5 > "$out/comments.json"
curl -fsS "$api/revisions/current/patch" | base64 -d > "$out/change.patch"

python3 - "$out" "$host" "$since" <<'PY'
import json, sys
out, host, since = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(f"{out}/change.json"))
cur = d["current_revision"]
rev = d["revisions"][cur]
commit = rev["commit"]
project = d["project"]
# X-review.googlesource.com serves git from X.googlesource.com.
git_host = host.replace("-review.googlesource.com", ".googlesource.com")
meta = {
    "number": d["_number"], "subject": d["subject"], "status": d["status"],
    "project": project, "branch": d["branch"],
    "owner": f'{d["owner"].get("name")} <{d["owner"].get("email")}>',
    "patchset": rev["_number"], "ref": rev["ref"],
    "new_commit": cur, "base_commit": commit["parents"][0]["commit"],
    "git_url": f"https://{git_host}/{project}",
    "url": f"https://{host}/c/{project}/+/{d['_number']}",
    "files": {f: {k: v.get(k, 0) for k in ("status", "lines_inserted", "lines_deleted")}
              for f, v in rev["files"].items() if f != "/COMMIT_MSG"},
}
if since:
    old = next((sha for sha, r in d["revisions"].items() if str(r["_number"]) == since), None)
    if old is None:
        sys.exit(f"patchset {since} not found")
    meta["since"] = {"patchset": int(since), "ref": d["revisions"][old]["ref"], "commit": old}
json.dump(meta, open(f"{out}/meta.json", "w"), indent=2)
open(f"{out}/commit_msg.txt", "w").write(commit["message"])

# Group comments into threads. A thread's status is the unresolved flag of its
# latest comment, which is how Gerrit decides it.
c = json.load(open(f"{out}/comments.json"))
by_id, roots = {}, []
for path, items in c.items():
    for it in items:
        it["_path"] = path
        by_id[it["id"]] = it
for it in by_id.values():
    it["_replies"] = []
for it in by_id.values():
    parent = by_id.get(it.get("in_reply_to"))
    (parent["_replies"] if parent else roots).append(it)

def flatten(t):
    yield t
    for r in sorted(t["_replies"], key=lambda x: x["updated"]):
        yield from flatten(r)

with open(f"{out}/existing_comments.txt", "w") as f:
    for root in sorted(roots, key=lambda x: (x["_path"], x.get("line", 0), x["updated"])):
        chain = list(flatten(root))
        status = "UNRESOLVED" if chain[-1].get("unresolved") else "resolved"
        side = " base-side" if root.get("side") == "PARENT" else ""
        f.write(f'=== [{status}] {root["_path"]}:{root.get("line", "-")}{side} (ps{root.get("patch_set")})\n')
        for it in chain:
            who = it.get("author", {}).get("name", "?")
            f.write(f'  [{who}, ps{it.get("patch_set")}] {it.get("message", "").strip()}\n')
        f.write("\n")

print(json.dumps({k: meta[k] for k in ("number", "subject", "owner", "patchset", "base_commit")}, indent=2))
PY

m() { python3 -c "import json,sys;d=json.load(open('$out/meta.json'));print(eval(sys.argv[1]))" "$1"; }
git_url="$(m "d['git_url']")"
base="$(m "d['base_commit']")"
new="$(m "d['new_commit']")"

git -C "$repo" fetch --no-tags -q "$git_url" "$(m "d['ref']")"

# Keep full files on both sides so claims about behavior can be checked against
# code outside the diff hunks, and so line numbers can be quoted exactly.
m "'\n'.join(d['files'])" | while read -r f; do
  mkdir -p "$out/base/$(dirname "$f")" "$out/new/$(dirname "$f")"
  git -C "$repo" show "${base}:${f}" > "$out/base/$f" 2>/dev/null || rm -f "$out/base/$f"
  git -C "$repo" show "${new}:${f}" > "$out/new/$f" 2>/dev/null || rm -f "$out/new/$f"
done

git -C "$repo" diff -U0 "$base" "$new" | grep -E '^(\+\+\+|@@)' > "$out/hunks.txt" || true

if [[ -n "$since" ]]; then
  old="$(m "d['since']['commit']")"
  git -C "$repo" fetch --no-tags -q "$git_url" "$(m "d['since']['ref']")"
  old_base="$(git -C "$repo" rev-parse "${old}^")"
  if [[ "$old_base" == "$base" ]]; then
    git -C "$repo" diff "$old" "$new" > "$out/interdiff.patch"
  else
    # Rebased: comparing commits would mix in unrelated upstream changes, so
    # compare the two patches instead.
    git -C "$repo" diff "$old_base" "$old" > "$out/old.patch"
    git -C "$repo" diff "$base" "$new" > "$out/new.patch"
    { echo "# rebased between patchsets: diff of the two patches"; diff -u "$out/old.patch" "$out/new.patch" || true; } > "$out/interdiff.patch"
  fi
  echo "interdiff: $out/interdiff.patch"
fi
echo "done: $out (base=$base new=$new)"
