---
name: code-review-support
description: Use when the user asks to review, explain, or translate a Gerrit change (a fuchsia-review.googlesource.com URL, a CL number, or "이 CL 리뷰해줘"), or to re-review a CL after the author uploaded a new patchset, especially a change that bundles several fixes into one commit and is hard to follow. Also use it to review or explain the commits of a local git branch or commit range, such as the user's own branch before a pull request ("이 브랜치 커밋들 리뷰해줘", "커밋별로 설명해줘", "origin/main..HEAD 리뷰"), even when no Gerrit is involved.
---

# CL Review Support

## Overview

Produce one short Korean markdown review file for a Gerrit change. It opens
with a verdict table, then the commit message, then one chapter per fix unit.
A unit with no finding gets one paragraph. A unit with a real finding gets the
full treatment in reading order: what went wrong, how the change fixes it, the
diff, test coverage, problems, and ready-to-paste comments. Every behavioral
claim is checked against the full base code whatever the chapter's length, and
every quote and every section's length is checked by a script before the file
is reported done.

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
7a. **Write for a reader who has not read the code.** The person reading the
   review knows the product but not this subsystem's internals. Before using a
   type, field, lock or state name in an argument, say in one sentence what it
   is and what it is for. A finding that only makes sense to someone who
   already read the diff has failed, however correct it is.
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

**Spend words where the findings are.** The reader wants the verdict, what
each unit does, and what to say to the author. Step 2 runs in full for every
unit, and what gets written down is set by the unit's worst finding:

| Worst finding in the unit | Chapter | Prose budget |
|---|---|---|
| none | Compact: 변경 요약 | 120 words |
| 사소함 | Compact: 변경 요약 and 문제점, one paragraph per finding | 120 + 100 per finding |
| 확인 필요 or 수정 필요 | Full: 문제 상황, 해결 방법, 변경 코드, 테스트, 문제점 | 350 + 200 per such finding |

Prose is the text outside code blocks, boxes, tables, headings and the commit
message. 판정 요약 has 100 words of prose, 변경 목적과 필요성 has 150, 전체
그림 has 150, Rust 문법 has 900, and 확인하지 못한 것 has 120.
`check_len.py` (Step 4) counts each section against these numbers. A compact
chapter has no diff block and no 문제 상황, 해결 방법 or 테스트 heading. What
Step 2 verified but the chapter does not show stays in `<context>` when a later
review needs it, and nowhere otherwise.

**Quote only open threads.** Run
`python3 ~/.claude/skills/code-review-support/scripts/comments_md.py <work> --open`.
It prints one block per unresolved thread, separated by `<!-- thread -->` cut
marks. Put each block right under the finding it belongs to, before 추천
코멘트. An open thread on `/COMMIT_MSG` goes in 커밋 메시지 부정확, an open
patchset-level thread goes in 전체 답글과 투표 before the reply draft, and an
open thread that matches no finding goes under the unit whose code it is on.
Replace every `<번역>` with a Korean translation in polite speech (존댓말) that
keeps identifiers, code, and list structure, and keep the `> ` prefix so the
translation stays inside the box. Never retype the originals, and never drop
the cut marks into the file.

A resolved thread is one row of the 기존 리뷰 코멘트 table. Check that the
final code carries the fix and write where in the 반영 column. When the code
does not carry it, that is a finding: write it in the unit and quote the thread
there (run `comments_md.py` without `--open` to get its block).

**Boxes.** Comments use Obsidian callouts, which other markdown viewers show
as plain quotes: other reviewers' threads are `> [!quote]+` boxes (from
comments_md.py), and this review's own comments and reply draft are
`> [!tip]` boxes. Leave a blank line before and after every box. Every
English comment or reply in a `[!tip]` box ends, inside the same box, with a
blank `>` line and `> **번역:** <Korean>`: a translation in polite speech
(존댓말) that keeps identifiers and code as-is, so the user can read what
they are about to paste. A "없음." box needs no translation.

**Attribute every point taken from a review comment, where it appears.** Any
fact, judgment, spec citation, failure scenario, or proposal that came from an
existing comment gets `(리뷰 코멘트: <author>, <path:line>, <미해결 | 해결됨>)`
in the same sentence or bullet. If you verified it yourself afterwards, add
`(직접 확인: <source>)`. Text without a tag must be this review's own analysis.
Never restate a reviewer's point in prose without the tag, even in 문제 상황.

**Write plainly.** Open 판정 요약 with what the change does in everyday words
(what the device or driver did before and does after), not with identifiers.
Explain each term in a short phrase where it first appears, since the file has
no glossary. Leave out how the change was fetched, alternatives nobody would
propose, and spec cross-references that do not change the verdict.

**Say why the commit exists.** Right after the commit message, `## 변경 목적과
필요성` says in two short paragraphs what the commit changes, what goes wrong
or stays awkward without it, and why it is needed now: the bug, the reviewer
request, or the later change that needs it. Look for the origin before
writing: the commit message, the bug, and the comment threads of related CLs
(`/changes/<n>/comments` on the parent and child CLs), where an author often
answers "Done in a separate change". Tag a point taken from another CL's
thread as `(리뷰 코멘트: <author>, CL <n> <path> N행, <미해결 | 해결됨>)`.

**Teach the Rust syntax.** The reader writes C and C++ drivers and does not
read Rust fluently. When the change touches Rust, add `## Rust 문법` before the
first unit and write it as a short lecture, not a table. Use numbered `###`
subsections ordered so that each one uses only what came before: types and
`impl` blocks with module privacy, references and borrow checking, generics
and traits, lifetimes, then whatever else the change uses (`Arc`, `async` and
`.await`, `?`, macros, `#[cfg]`, closures, `Drop`, `Send` and `Sync`). In each
subsection, state the rule in plain Korean, give the C or C++ counterpart,
show a few real lines from the change in a ```rust block, and say what those
lines do here and what the compiler would reject if they were written another
way. Cover only what the diff, the quoted code, reviewer comments or this
review's argument rely on, and skip what a C programmer reads correctly
unaided (`let`, `if`, plain function signatures). When a finding rests on a
language rule, point back to its subsection where the finding uses it.

Scale the shape to the change:

| Change | Shape |
|---|---|
| 2 or more fix units | Template below |
| 1 fix unit | Drop the 판정 요약 table (keep the sentences). Use `## 변경 내용` instead of `## 단위 1: ...`, with the same compact or full rule |
| No comment threads yet | Drop 기존 리뷰 코멘트 |
| Earlier review exists (`--since`) | Add `## 이전 리뷰 대비` right after 판정 요약 |
| Change touches Rust code | Add `## Rust 문법` right before the first unit |

````markdown
# CL <number> 리뷰: <subject>

- 리뷰 날짜: <YYYY-MM-DD>
- 작성자: <owner>
- 패치셋: <ps>, 베이스: `<base short hash>`
- 링크: <url>

---

## 판정 요약

<Two or three sentences: what the device or driver did before and does after,
the suggested vote, and how many findings of each severity. Branch mode adds
one or two sentences on what was exercised. Then:>

| 단위 | 내용 | 판정 | 핵심 이유 |
|---|---|---|---|
<내용 and 핵심 이유 are phrases of at most ten words each.>

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

## 변경 목적과 필요성

<Two short paragraphs (see Say why the commit exists). First: what was wrong
or awkward in the base code, as a reader who has not seen it would need to
hear it, and how bad it is today. Second: what this commit does about it and
where the request came from (bug, review thread on this or a related CL, or
the later CL that needs it), with the source.>

---

## 기존 리뷰 코멘트

<Omit when there are no comment threads. One sentence with thread and
unresolved counts, then one row per thread from existing_comments.txt:>

| 위치 | 작성자 | 상태 | 요지 | 반영 |
|---|---|---|---|---|
<상태 is 미해결 / 해결됨. 요지 is one phrase. 반영 for a resolved thread is
`반영됨 (path:line)` or `미반영 (단위 N)`. For an open thread it names the unit
that quotes it.>

---

## 전체 그림: <noun-phrase>

<Only when the change introduces or reshapes a subsystem the reader does not
already hold in their head (a new protocol layer, a new power sequence, a new
queueing scheme). Skip it for a change that only fixes existing code.

One paragraph: the scale in numbers, which component owns what, and one
end-to-end walk with real values (an actual LBA, an actual register write).
Then one table, either the pieces and their owners or what this change covers
and what is left for later changes.>

---

## Rust 문법

<Only when the change touches Rust (see Teach the Rust syntax). One or two
sentences on why the reader needs it, then a lecture:>

### 1. <noun phrase, e.g. 구조체와 `impl` 블록>

<The rule in plain Korean and its C or C++ counterpart, one paragraph.>

```rust
<a few real lines from the change, `...` for elided lines>
```

<What these lines do in this change, and what the compiler would reject if
they were written another way. Cite `path:line`.>

---

## 단위 N: <noun-phrase title>

<COMPACT chapter: the unit has no finding, or only 사소함 findings.>

### 변경 요약

<One paragraph, two to four sentences: what the base code did, what the change
does instead, and the one design choice worth knowing.>

- 확인: <one line: what was checked against the base code, which test or CI
  job covers it, and what that cannot observe>

### 문제점
<Omit when the unit has no findings. Each 사소함 finding:>

**<결과>: <원인> (사소함, <신규 | 리뷰 코멘트: author, path:line, 미해결 | 해결됨>)**

- 위치: `path:line` (`function()`)

<One paragraph, two to four sentences: what happens and when, why it is only
minor, and the fix.>

> [!tip] 추천 코멘트 · `path:line`
> <as in the full chapter below>

---

## 단위 N: <noun-phrase title>

<FULL chapter: the unit has a 확인 필요 or 수정 필요 finding.>

### 문제 상황
<Numbered sequence of three or four concrete events in the base code. Only the
problem.>

### 해결 방법
<Prose, one or two short paragraphs, before any diff. Say what the change does
to the sequence above, why this approach and not the obvious alternative, and
how its pieces depend on each other (which part is useless without which).
Name the precedent when there is one (another driver, a framework rule).
No bullets and no code here: the reader should be able to predict the diff
from this section.>

### 변경 코드
<One ```diff block for each hunk a finding refers to, and at most one more for
the hunk that carries the change. First line is a comment with
`path:new-side-line`, plus `(base N)` when the block only removes lines.
Bullets after each block explain what the changed lines do.>

### 테스트
- 덮는 테스트: <test names and what they check>
- 확인하지 못하는 것: <what the tests cannot observe>

### 문제점

**<결과>: <원인> (<수정 필요 | 확인 필요>, <신규 | 리뷰 코멘트: author, path:line, 미해결 | 해결됨>)**

- 위치: `path:line` (`function()`)

**배경 N: <one-sentence noun phrase>** <Only when the mechanism needs a
prerequisite the reader does not have. One short paragraph each, numbered, in
dependency order, each introducing exactly one thing (what a slot is, what the
field tracks, who clears it and when). Put the line reference in trailing
parentheses. Stop as soon as the next paragraph can stand on its own: usually
one, at most two, never a tutorial.>

**그래서 생기는 일.** <The defect itself, now that the reader has the pieces.
Plain sentences, no new names.>

**실패 시나리오.** <A table in time order, three or four rows, one row per
event, with a last column showing the state that matters (a mask, a flag, a
level). A numbered list is fine when there is no state to track.>

| 시각 | 사건 | <state> |
|---|---|---|

**수정과 그 자리가 안전한 이유.** <The fix, short enough to quote, then why
that spot is safe, with the evidence in trailing parentheses. When an obvious
alternative fix exists (move the check, reorder two calls, widen a lock), say
why it does not work: a reviewer will propose it otherwise, and the answer is
often that some other code already depends on the current shape.>

<Title: keep it to "결과: 원인", short enough to read at a glance, e.g.
`서스펜드 실패: 타임아웃 슬롯이 드레인 전에 정리되지 않음`. Never pack the
whole mechanism into the title.>

<If an open thread raised or discusses this finding, paste its block here.>

> [!tip] 추천 코멘트 · `path:line`
> <English Gerrit comment, polite, ending with a question or concrete
> suggestion. For an open thread another reviewer started, a one-line +1 with
> only the new information. Otherwise "없음." with the reason.
>
> Two sentences: the symptom and the ask. Three when the cause needs one of
> its own, four only when a rejected alternative has to be pre-empted. No code
> block unless the fix is one line, and no semicolons. The evidence, the
> mechanism and the rejected alternatives stay in the document above: the
> author reads them if they ask "why?".
>
> Lead with the symptom the author cares about, not with the internals. Anchor
> the comment on the line that is wrong rather than the top of the function,
> and when a comment in the code claims the behavior that does not happen,
> point at that comment: it is shorter than the call graph and the author
> cannot read it twice without seeing the gap.
>
> Spend one sentence pre-empting the fix a reader would propose instead, when
> there is one, since that is the reply you would otherwise have to write
> anyway. But leave out any detail that invites a counter-argument you would
> then have to answer, such as an exception that holds only sometimes or a
> caller that could in theory run. State the claim instead of the enumeration
> ("and nothing else runs it here" rather than listing the other callers) and
> keep the nuance in the document for when the author raises it.>
>
> **번역:** <Korean translation of the comment above, 존댓말, identifiers as-is.>

---

## 커밋 메시지 부정확
<Only when a claim in the message does not match the diff or base code. Each
one in a sentence or two, with 추천 코멘트.>

---

## 전체 답글과 투표
<Open patchset-level threads from comments_md.py, then the reply draft as
`> [!tip] 우리 답글 초안` with an English reply of two to four sentences and
its `**번역:**` line inside, then one line with 추천 투표.>

---

## 확인하지 못한 것
<At most five bullets: what needs hardware, internal code, or the author's
intent, and would change the verdict if it turned out otherwise. Omit when
there is none.>
````

## Step 4: Check and record

1. Run the quote checker and fix every problem it prints, then rerun until it
   reports `0 problem(s)`. Besides checking that quoted lines exist, it flags a
   `+` or `-` line that the change does not actually add or remove, which is
   how an unchanged line copied into a diff block gets caught. It also flags a
   `<name>` outside code, such as `Foo<M>` written without backticks in the
   commit message translation, because markdown reads it as an HTML tag and
   hides the rest of the line.
   ```bash
   python3 ~/.claude/skills/code-review-support/scripts/check_refs.py <file> <work> <repo>
   # branch mode: checks each unit against its own commit
   python3 ~/.claude/skills/code-review-support/scripts/check_units.py <file> <work> <repo>
   ```
2. Run the length checker and cut until it reports `0 problem(s)`. Cut by
   removing whole points that do not change the verdict. Do not shorten by
   dropping particles, stacking nouns, or moving prose into tables and boxes.
   ```bash
   python3 ~/.claude/skills/code-review-support/scripts/check_len.py <file>
   ```
3. Add to `<context>` every fact verified in this review that a later review
   would need: framework semantics, spec rules, hardware facts, commit that
   introduced a behavior, reviewer ownership. One bullet each with its source
   and `확인: CL <number>`. If a fact turned out wrong, correct it in place and
   mark it 정정. Create `<context>` with a one-paragraph header if missing.
4. Reply in the terminal with the file path, the verdict in plain words (what
   the CL does and the vote), and at most the top two findings with their
   comments. Keep it to a few short lines. Do not paste the whole review.

## Quick Reference

| User asks for | Do |
|---|---|
| "번역만" | Step 1, then print the original and translated commit message. For a pull request, the PR description first, then each commit message |
| "리뷰해줘" / URL only | Steps 1-4 |
| "새 패치셋 올라왔어" / re-review | Steps 1-4 with `--since <old ps>`, new file for the new patchset |
| "왜 고친 거야?" / "단위 N 자세히" | Rewrite the units asked about as full chapters in the existing file (all units when none is named), then summarize. Units expanded on request are exempt from `check_len.py` |
| "코멘트 올려줘" | Show the 추천 코멘트 blocks and ask before posting anything |
| "이 브랜치 커밋들 리뷰해줘" / "커밋별로 설명해줘" | Branch mode (`references/branch-mode.md`), Steps 2-4 |
| Branch changed since the last review | Branch mode with `git range-diff`, fill 이전 리뷰 대비 |

## Common Mistakes

| Mistake | Fix |
|---|---|
| Explaining the diff hunk by hunk | Group hunks by fix unit first |
| A full chapter for a unit with no finding, or a 배경 and 실패 시나리오 for a 사소함 finding | Compact chapter: one paragraph and one 확인 line, one paragraph per minor finding (`check_len.py` flags it) |
| Quoting resolved threads with translations | One row in 기존 리뷰 코멘트 with where the fix landed. Quote only open threads (`comments_md.py --open`) |
| Listing everything that was verified | Write what the reader needs for the verdict. Facts a later review needs go to `<context>` |
| An appendix of file/line maps and a glossary | Neither exists. Explain a term where it first appears. `## Rust 문법` explains language syntax only, never project terms |
| A Rust review that assumes the reader knows lifetimes, borrows and traits | Add `## Rust 문법` (Teach the Rust syntax) |
| Rust syntax as a table of features | Teach it as a lecture: numbered subsections, each with the rule, its C or C++ counterpart, and real lines from the change |
| A review that never says why the commit was written | Add `## 변경 목적과 필요성` after the commit message, with the bug or the review thread that asked for it |
| Meeting the budget by compressing sentences | Remove points instead. Keep full sentences |
| A summary full of identifiers and side detail | Lead with what the CL does in everyday words and cut detail that does not change the verdict (Write plainly) |
| Jumping from 문제 상황 straight into diff blocks (full chapter) | Write 해결 방법 in prose first, so the diff only confirms it |
| A finding only a reader of the diff can follow | Add 배경 paragraphs for the prerequisites, then state the defect (rule 7a) |
| 실패 시나리오 as prose when one value drives it | Use the timeline table with a state column |
| Leaving the obvious alternative fix unaddressed | Say why it fails; some other code often depends on the current order |
| Enumerating callers or cases in a comment | State the claim; an enumeration invites "but that one does run" |
| Anchoring a comment at the top of the function | Anchor on the wrong line, and on a stale code comment when there is one |
| Summary lines inside a diff block | Real code only, `...` for elision (checker enforces) |
| Calling a stall a deadlock | Trace who completes each wait (rule 5) |
| Assuming numeric values carry ordering | Read the framework contract (rule 6) |
| +1 on a thread that is already resolved | Check `[resolved]` in existing_comments.txt (rule 2) |
| Re-reviewing a new patchset from scratch | Use `--since` and fill 이전 리뷰 대비 |
| Line numbers from the old side | Use new-side numbers from `hunks.txt` |
| A reviewer's point retold as your own analysis | Tag it `(리뷰 코멘트: ...)` where it appears |
| Retyping reviewer comments, or putting them in a text block | Use `comments_md.py`; quotes wrap, code blocks scroll |
| Posting comments to Gerrit | Never post. 추천 코멘트 is for the user to paste |
| A pull request review with the commit messages translated but not the PR description | Add PR 설명 원문과 번역 (`references/branch-mode.md`) |
| An English 추천 코멘트 or 우리 답글 초안 without a Korean translation | Add `> **번역:** ...` inside the same box (see Boxes) |
| Marking an unchanged or moved line `+` | Copy the markers from the real diff (checker flags it) |
| A finding title that tells the whole story, or one 근거 bullet holding every reason and line number | Title is `결과: 원인`. In a full chapter split the body into 배경 / 그래서 생기는 일 / 실패 시나리오 / 수정, and push identifiers and line numbers to trailing parentheses |
| Branch review line numbers from the range end | Use the unit's own commit |
