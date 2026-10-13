# Branch mode: reviewing a local commit range

Use this when the change is a range of commits on a local git branch rather
than a Gerrit CL: the user's own branch before a pull request, a GitHub branch,
or `origin/main..HEAD`. Everything in SKILL.md still applies. This file lists
only what changes.

## Why the shape changes

A Gerrit CL is one commit with one base, so one pair of `base/` and `new/`
folders describes every line. A branch has several commits, each with its own
parent, and a line number is only meaningful in the commit that produced it.
The review therefore treats each commit as a unit with its own folders, and the
checker checks each part of the review against the right folder.

## Step 1: fetch the range

Fetch the upstream first (`git fetch`), then:

```bash
python3 ~/.claude/skills/code-review-support/scripts/fetch_range.py <base> <head> <work> [--repo <dir>]
```

- `<base>` is where the range starts, usually `origin/main`. `<head>` is the
  branch or sha to review.
- It prints one line per commit and writes `<work>/c1` … `<work>/cN` (each
  commit against its parent), `<work>/all` (the whole range), and
  `<work>/units.json`. Each folder has the same files fetch_cl.sh writes.
- A `warning:` line means a commit's author email is in none of its
  `Signed-off-by` trailers. Report it: history rewritten under a different git
  config changes the author without touching the message.

Paths: `<project>` comes from `units.json`. Name the file
`<dir>/<YYYY-MM-DD>-<branch>-<head short sha>.md`. For an earlier review of the
same branch, look for `<dir>/*-<branch>-*.md`, and describe what moved with
`git range-diff <old-base>..<old-head> <base>..<head>` in 이전 리뷰 대비.

## Units

- One commit is one unit, numbered in commit order: `## 단위 N` is `<work>/cN`.
  check_units.py relies on that numbering, so keep it even when a unit is small.
- If one commit bundles several fixes, keep one chapter for it and number the
  fixes inside 문제 상황 and 변경 코드. Whether it should be split is a finding.
- Inside a unit, every line number is that commit's new side, and `(base N)` in
  a diff header is its parent. Appendix tables for a unit go under a
  `#### 단위 N` heading so they are checked against the same folder. Anything
  else (verdict, cross-unit flow tables) uses the range end, `<work>/all`.

## Template changes

- Header: 리뷰 날짜, 작성자, `범위: <base>(<short>) 위 N개 커밋, 끝 <head short>`,
  and a branch or PR link when there is one. Right after it, one paragraph
  telling the reader that line numbers belong to each unit's commit.
- 판정 요약 gets a 커밋 column.
- Each unit chapter opens with one sentence naming its commit, then
  `### 커밋 메시지` with the original in a ```text block and a Korean
  translation, then 문제 상황, 해결 방법, 변경 코드, 테스트, 문제점. There is no separate
  커밋 메시지 원문과 번역 chapter.
- Drop 기존 리뷰 코멘트 and 전체 답글과 투표 unless a pull request already has
  comments. If it does, place each one under its finding with
  `(리뷰 코멘트: author, path:line, 미해결 | 해결됨)`.
- 커밋 메시지 부정확 also covers metadata: the author-email warnings, and
  trailers that differ from the target branch (compare with
  `git log <base> --format=%B`).
- 추천 코멘트 stay in English, ready for a pull request. On the user's own
  branch they double as a to-do list.

## Verifying a branch

- Check each message claim against that commit's diff and parent (rule 7), not
  against the range end. A later commit in the same range often changes what an
  earlier message describes.
- A branch review is often written for the author, who wants to know what was
  actually exercised. In 테스트, say separately what ran on real hardware, what
  ran only as a mock, and what was checked only by reading source.
- Look at the project's CI (for example `.github/workflows/`) and say what it
  runs and what it cannot see.

## Step 4: check

```bash
python3 ~/.claude/skills/code-review-support/scripts/check_units.py <file> <work> <repo>
```

It splits the file at the unit headings and runs check_refs.py on each part
with the matching folder. Fix every problem and rerun until `0 problem(s)`.
