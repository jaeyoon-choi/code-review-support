---
name: code-review-support
description: Use when the user asks to review, explain, or translate a Gerrit change (a fuchsia-review.googlesource.com URL, a CL number, or "이 CL 리뷰해줘"), or to re-review a CL after the author uploaded a new patchset, especially a change that bundles several fixes into one commit and is hard to follow. Also use it to review or explain the commits of a local git branch or commit range, such as the user's own branch before a pull request ("이 브랜치 커밋들 리뷰해줘", "커밋별로 설명해줘", "origin/main..HEAD 리뷰"), even when no Gerrit is involved.
---

# CL Review Support

## Overview

Produce one Korean markdown review file for a Gerrit change. It opens with a
verdict table, then the commit message, then one chapter per fix unit that
holds everything about that unit in reading order: what went wrong, how the
change fixes it, the diff, test coverage, problems, and ready-to-paste comments. Reference tables go to
the appendix. Every behavioral claim is checked against the full base code, and
every quote is checked by a script before the file is reported done.

For commits on a local branch instead of a Gerrit change, read
`references/branch-mode.md` first. It keeps this workflow but fetches each
commit into its own folder, because a line number only means something in the
commit that produced it.

Paths used below:

| Name | Path |
|---|---|
| `<dir>` | `${CODE_REVIEW_SUPPORT_DIR:-~/Documents/Claude/CodeReviewSupport}/<project>/` (`<project>` from `meta.json`) |
| `<file>` | `<dir>/<YYYY-MM-DD>-<number>-ps<patchset>.md` (review date first) |
| `<context>` | `<dir>/_context.md` |
| `<work>` | a fresh folder in the session scratchpad |

## Step 1: Fetch the change

For a local branch, use `scripts/fetch_range.py` as described in
`references/branch-mode.md` and continue at Step 2.

Run inside a local clone of the change's project (for a Fuchsia CL, your Fuchsia checkout).
First look for an earlier review of the same CL: `ls <dir>/*-<number>-ps*.md`.

```bash
# first review
bash ~/.claude/skills/code-review-support/scripts/fetch_cl.sh <url-or-number> <work>
# earlier review exists for patchset N
bash ~/.claude/skills/code-review-support/scripts/fetch_cl.sh <url-or-number> <work> --since N
```

It writes:

| File | Content |
|---|---|
| `meta.json` | number, subject, owner, patchset, base/new commit, url, file list |
| `commit_msg.txt` | full commit message |
| `change.patch`, `hunks.txt` | patch, and hunk ranges with new-side line numbers |
| `base/<path>`, `new/<path>` | full files before and after |
| `existing_comments.txt` | comment threads, each marked `[UNRESOLVED]` or `[resolved]`, with patchset. `scripts/comments_md.py <work>` turns it into quoted markdown |
| `interdiff.patch` | with `--since`: changes between the two patchsets (patch-vs-patch if rebased) |

The scripts use bash. In zsh never write `"$B:path"`, because `:s` is a
modifier. Write `"${B}:path"`.

## Step 2: Verify before writing

These rules exist because skipping them produced wrong reviews.

1. **Read `<context>` first** if it exists. It holds facts earlier reviews
   verified about this project's frameworks, hardware, and reviewers.
2. **Read `existing_comments.txt` before forming conclusions.** Other reviewers
   often own the framework involved. If a comment contradicts your reading,
   verify it and correct yourself. Only `[UNRESOLVED]` threads count as open.
   Never recommend a +1 on a `[resolved]` thread.
3. **Split the change into fix units.** Numbered items in the commit message
   are the starting point. Map every hunk in `hunks.txt` to exactly one unit.
4. **Explain each unit from the base code.** Read `base/<path>` and write the
   concrete failing sequence (call order, values, state) that the unit fixes.
5. **Follow the call path to the end before naming a failure class.** Before
   writing "deadlock", "race", "use-after-free" or "hang", trace which thread or
   dispatcher completes each wait. If the path does not close the loop, name
   the weaker real effect.
6. **Read the framework's own contract** (FIDL, header docs) before reasoning
   about how it interprets values, ordering, or threading.
7. **Check every commit message claim against the diff and base code.**
8. **For a regression, find the commit that introduced it** with
   `git log -S'<symbol>' -- <path>` and quote its hash and date.
9. **Hardware or spec claims need a source**: spec section, Linux driver
   behavior, or vendor devicetree. Mark confidence as 확인 or 추정.
10. **For each unit, find the tests that cover it** in the change and note what
    those tests cannot observe (for example a mock link that never breaks).

## Step 3: Write the review file

Write `<file>`. If `*-<number>-ps<patchset>.md` already exists, update it
instead of creating a new one. Put a `---` rule, with a blank line on each
side, before every `##` section. Inside a ```diff block every line must be
real code from `base/` or `new/`. Mark elided code with a line that is exactly
`...` and never write summaries such as `/* checks */` there.

**Place each existing thread where it is discussed.** Run
`python3 ~/.claude/skills/code-review-support/scripts/comments_md.py <work>`.
It prints one block per thread, separated by `<!-- thread -->` cut marks. Put
each block right under the finding it belongs to, before 추천 코멘트. Threads on
`/COMMIT_MSG` go in 커밋 메시지 부정확, patchset-level threads go in 전체 답글과
투표 before the reply draft, and a thread that matches no finding goes under the
unit whose code it is on. Replace every `<번역>` with a Korean translation in
polite speech (존댓말) that keeps identifiers, code, and list structure, and
keep the `> ` prefix so the translation stays inside the box. Never retype the
originals, and never drop the cut marks into the file.

**Boxes.** Comments use Obsidian callouts, which other markdown viewers show
as plain quotes: other reviewers' threads are `> [!quote]+` boxes (from
comments_md.py), and this review's own comments and reply draft are
`> [!tip]` boxes. Leave a blank line before and after every box.

**Attribute every point taken from a review comment, where it appears.** Any
fact, judgment, spec citation, failure scenario, or proposal that came from an
existing comment gets `(리뷰 코멘트: <author>, <path:line>, <미해결 | 해결됨>)`
in the same sentence or bullet. If you verified it yourself afterwards, add
`(직접 확인: <source>)`. Text without a tag must be this review's own analysis.
Never restate a reviewer's point in prose without the tag, even in 문제 상황.

Scale the shape to the change:

| Change | Shape |
|---|---|
| 2 or more fix units | Full template below |
| 1 fix unit | Drop 판정 요약 table (keep the verdict sentence), 목차, and 부록 흐름 표. Use `## 변경 내용` instead of `## 단위 1: ...` |
| No comment threads yet | Drop 기존 리뷰 코멘트 and the 출처 표시 line |
| Earlier review exists (`--since`) | Add `## 이전 리뷰 대비` right after 판정 요약 |

````markdown
# CL <number> 리뷰: <subject>

- 리뷰 날짜: <YYYY-MM-DD>
- 작성자: <owner>
- 패치셋: <ps>, 베이스: `<base short hash>`
- 링크: <url>

**목차:** [판정 요약](#판정-요약) · [커밋 메시지](#커밋-메시지-원문과-번역) · [기존 리뷰 코멘트](#기존-리뷰-코멘트) · [단위 1](#<anchor>) · ... · [전체 답글과 투표](#전체-답글과-투표) · [부록](#부록)

**출처 표시:** `(리뷰 코멘트: 작성자, 위치, 상태)`가 붙은 내용은 다른 리뷰어의 코멘트에서 온 것이다. "직접 확인"이 함께 붙으면 코멘트를 보고 코드나 문서로 따로 확인했다는 뜻이다. 표시가 없는 내용은 이 리뷰의 분석이다.

---

## 판정 요약

<One or two sentences with the overall verdict and suggested vote. Then:>

| 단위 | 내용 | 판정 | 핵심 이유 |
|---|---|---|---|

---

## 이전 리뷰 대비

<Only with --since. What changed between patchsets, from interdiff.patch, in
2-4 bullets. Then one row per finding of the earlier review:>

| 이전 문제점 | 상태 | 근거 |
|---|---|---|
<상태 is 해결 / 부분 해결 / 미해결 / 해당 없음(코드 삭제)>

---

## 커밋 메시지 원문과 번역

### 원문

```text
<commit_msg.txt verbatim>
```

### 번역

<Korean translation. Keep numbered items numbered and identifiers as-is.>

---

## 기존 리뷰 코멘트

<Omit when there are no comment threads. One sentence with thread and
unresolved counts, then one row per thread from existing_comments.txt:>

| 위치 | 작성자 | 상태 | 요지 | 이 문서에서 |
|---|---|---|---|---|
<상태 is 미해결 / 해결됨. 이 문서에서 names the unit or section that covers it,
or 참고만.>

<The table is only an index. The originals and translations go next to the
finding they belong to (see 문제점 below), not here.>

---

## 단위 N: <noun-phrase title>

### 문제 상황
<Numbered sequence of concrete events in the base code. Only the problem.
Paragraphs at most 3 sentences.>

### 해결 방법
<Prose, 1-3 short paragraphs, before any diff. Say what the change does to
the sequence above, why this approach and not the obvious alternative, and
how its pieces depend on each other (which part is useless without which).
Name the precedent when there is one (another driver, a framework rule).
No bullets and no code here: the reader should be able to predict the diff
from this section.>

### 변경 코드
<One ```diff block per important hunk. First line is a comment with
`path:new-side-line`, plus `(base N)` when the block only removes lines.
Bullets after each block explain what the changed lines do.>

### 테스트
- 덮는 테스트: <test names and what they check>
- 확인하지 못하는 것: <what the tests cannot observe>

### 문제점
<Omit when the unit has no findings. Each finding:>

**<one-line claim> (<수정 필요 | 확인 필요 | 사소함>, <신규 | 리뷰 코멘트: author, path:line, 미해결 | 해결됨>)**

- 위치: `path:line`
- 근거: <spec section, base code, Linux behavior, vendor DT>
- 실패 시나리오: <concrete sequence>

<If an existing thread raised or discusses this finding, paste its block here.>

> [!tip] 추천 코멘트 · `path:line`
> <English Gerrit comment, short, polite, ending with a question or concrete
> suggestion. For an open thread another reviewer started, a one-line +1 with
> only the new information. Otherwise "없음." with the reason.>

---

## 커밋 메시지 부정확
<Claims in the message that do not match the diff or base code, with 추천 코멘트.>

---

## 전체 답글과 투표
<Patchset-level threads from comments_md.py, then the reply draft as
`> [!tip] 우리 답글 초안` with the English reply inside, then 추천 투표 with reason.>

---

## 부록
### 파일별 변경 위치
<one table per unit: 파일 | 위치(new-side lines) | 변경>
### 겹치는 함수의 흐름
<only for functions touched by 2+ units: 행 | 동작 | 단위>
### 용어
<only abbreviations the file uses: 용어 | 뜻, one line each>
### 확인하지 못한 것
<anything that needs hardware, internal code, or the author's intent>
````

Heading anchors follow GitHub rules: lowercase, drop punctuation except `-`,
spaces become `-`. Example: `## 단위 1: init 리스` becomes `#단위-1-init-리스`.

## Step 4: Check and record

1. Run the quote checker and fix every problem it prints, then rerun until it
   reports `0 problem(s)`. Besides checking that quoted lines exist, it flags a
   `+` or `-` line that the change does not actually add or remove, which is
   how an unchanged line copied into a diff block gets caught.
   ```bash
   python3 ~/.claude/skills/code-review-support/scripts/check_refs.py <file> <work> <repo>
   # branch mode: checks each unit against its own commit
   python3 ~/.claude/skills/code-review-support/scripts/check_units.py <file> <work> <repo>
   ```
2. Add to `<context>` every fact verified in this review that a later review
   would need: framework semantics, spec rules, hardware facts, commit that
   introduced a behavior, reviewer ownership. One bullet each with its source
   and `확인: CL <number>`. If a fact turned out wrong, correct it in place and
   mark it 정정. Create `<context>` with a one-paragraph header if missing.
3. Reply in the terminal with the file path, the one-line verdict, and the top
   two findings. Do not paste the whole review.

## Quick Reference

| User asks for | Do |
|---|---|
| "번역만" | Step 1, then print the original and translated commit message |
| "리뷰해줘" / URL only | Steps 1-4 |
| "새 패치셋 올라왔어" / re-review | Steps 1-4 with `--since <old ps>`, new file for the new patchset |
| "왜 고친 거야?" | Expand each unit's 문제 상황 and 해결 방법 in the existing file, then summarize |
| "코멘트 올려줘" | Show the 추천 코멘트 blocks and ask before posting anything |
| "이 브랜치 커밋들 리뷰해줘" / "커밋별로 설명해줘" | Branch mode (`references/branch-mode.md`), Steps 2-4 |
| Branch changed since the last review | Branch mode with `git range-diff`, fill 이전 리뷰 대비 |

## Common Mistakes

| Mistake | Fix |
|---|---|
| Explaining the diff hunk by hunk | Group hunks by fix unit first |
| Jumping from 문제 상황 straight into diff blocks | Write 해결 방법 in prose first, so the diff only confirms it |
| Summary lines inside a diff block | Real code only, `...` for elision (checker enforces) |
| Calling a stall a deadlock | Trace who completes each wait (rule 5) |
| Assuming numeric values carry ordering | Read the framework contract (rule 6) |
| +1 on a thread that is already resolved | Check `[resolved]` in existing_comments.txt (rule 2) |
| Re-reviewing a new patchset from scratch | Use `--since` and fill 이전 리뷰 대비 |
| Line numbers from the old side | Use new-side numbers from `hunks.txt` |
| A reviewer's point retold as your own analysis | Tag it `(리뷰 코멘트: ...)` where it appears |
| Retyping reviewer comments, or putting them in a text block | Use `comments_md.py`; quotes wrap, code blocks scroll |
| Posting comments to Gerrit | Never post. 추천 코멘트 is for the user to paste |
| Marking an unchanged or moved line `+` | Copy the markers from the real diff (checker flags it) |
| Branch review line numbers from the range end | Use the unit's own commit; appendix tables under `#### 단위 N` |
