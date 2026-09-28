# code-review-support

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that turns a
Gerrit change into a Korean review document you can read top to bottom and act
on. It is built for changes that bundle several fixes into one commit.

For each change it writes one markdown file with:

- a verdict table, one row per fix unit
- the original commit message and a Korean translation
- an index of existing reviewer threads, with resolved state
- one chapter per fix unit: what went wrong in the base code, the diff, what the
  tests cover and miss, the problems found, the reviewer threads about each
  problem (original and translation), and a ready-to-paste English comment
- an appendix with file/line maps, per-function flow, and a glossary

On a new patchset it compares against the previous review and tracks which
earlier findings were fixed.

## Install

```bash
git clone https://github.com/jaeyoon-choi/code-review-support ~/.claude/skills/code-review-support
```

Requirements: `bash`, `python3`, `curl`, `git`, and a local clone of the
change's project (the scripts fetch the change's commits into it).

## Use

In Claude Code, from inside the project checkout:

```
/code-review-support https://fuchsia-review.googlesource.com/c/fuchsia/+/1234567
```

A bare change number assumes fuchsia-review.googlesource.com. Asking in plain
language ("이 CL 리뷰해줘") also triggers the skill.

Reviews are saved to
`${CODE_REVIEW_SUPPORT_DIR:-~/Documents/Claude/CodeReviewSupport}/<project>/<date>-<change>-ps<patchset>.md`.
The skill also keeps `<project>/_context.md` there, a list of facts verified in
earlier reviews (framework semantics, spec rules, hardware) that later reviews
read first.

Comments are rendered as [Obsidian callouts](https://help.obsidian.md/Editing+and+formatting/Callouts).
Other markdown viewers show them as plain quotes.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/fetch_cl.sh` | Download change metadata, patch, and comment threads through the Gerrit REST API, fetch the commits, and extract full base/new files. `--since N` also writes a diff against patchset N |
| `scripts/comments_md.py` | Render existing comment threads as callout boxes with originals quoted verbatim and translation placeholders |
| `scripts/check_refs.py` | Check that every `path:line` reference and every line in a diff block of the review matches the real code |

The skill never posts anything to Gerrit. Suggested comments are for you to
review and paste.
