#!/usr/bin/env python3
"""Count the prose of a review against the budgets in SKILL.md (Step 3).

Usage: python3 check_len.py <review.md>

Prose is every word outside fenced code blocks, boxes and quotes (lines that
start with ">"), table rows, headings, and the "### 커밋 메시지" part of a
branch-mode unit. A unit's budget follows its findings, read from the bold
finding titles: "(사소함", "(확인 필요", "(수정 필요".

A unit without a 확인 필요 or 수정 필요 finding is a compact chapter, so a diff
block or a full-chapter heading in it is also reported. Exit status is 1 when
anything is over.
"""
import re
import sys
from pathlib import Path

COMPACT, MINOR, FULL, MAJOR = 120, 100, 350, 200
FIXED = {"판정 요약": 100, "전체 그림": 150, "확인하지 못한 것": 120}
UNIT = re.compile(r"(단위 \d+|변경 내용)")
FINDING = re.compile(r"^\*\*.*\((사소함|확인 필요|수정 필요)[,)]")
FULL_ONLY = ("### 문제 상황", "### 해결 방법", "### 변경 코드", "### 테스트")


def sections(text):
    out, fence = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fence = not fence
        if not fence and line.startswith("## "):
            out.append([line[3:].strip(), []])
        elif out:
            out[-1][1].append(line)
    return out


def measure(lines):
    words, minor, major, fence, skip, shape = 0, 0, 0, False, False, []
    for line in lines:
        if line.startswith("```"):
            if not fence and line.startswith("```diff"):
                shape.append("diff block")
            fence = not fence
            continue
        if fence:
            continue
        if line.startswith("#"):
            skip = line.startswith("### 커밋 메시지")
            shape += [h[4:] for h in FULL_ONLY if line.startswith(h)]
            continue
        if skip or line.startswith((">", "|")) or line.strip() == "---":
            continue
        m = FINDING.match(line)
        if m:
            minor += m.group(1) == "사소함"
            major += m.group(1) != "사소함"
        words += len(line.split())
    return words, minor, major, shape


def main():
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    problems, total = 0, 0
    for title, lines in sections(text):
        words, minor, major, shape = measure(lines)
        total += words
        note = ""
        if UNIT.match(title):
            if major:
                budget, kind = FULL + MAJOR * major + MINOR * minor, "full"
            else:
                budget, kind = COMPACT + MINOR * minor, "compact"
                if shape:
                    note = "  <- compact chapter has: " + ", ".join(dict.fromkeys(shape))
        else:
            budget = next((v for k, v in FIXED.items() if title.startswith(k)), None)
            kind = ""
        over = budget is not None and words > budget
        if over:
            note = f"  <- over by {words - budget}" + note
        problems += over + bool(note and not over)
        limit = f"/{budget}" if budget is not None else ""
        print(f"{words:5d}{limit:<6} {kind:8} {title[:50]}{note}")
    print(f"{total} prose words, {len(text.splitlines())} lines")
    print(f"{problems} problem(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
