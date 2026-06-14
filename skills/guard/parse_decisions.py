"""decisions.md 파서 + active 프로젝트 resolve.

parse_decisions(text) → [{n, category, text, reason, session}] (번호 1..N).
main: active 프로젝트 decisions.md를 읽어 번호매긴 JSON 출력 (SKILL.md가 소비).
"""
import json
import os
import re
import sys

SESSION_RE = re.compile(r"<!--\s*session:\s*(\S+?)\s*-->\s*$")
REASON_RE = re.compile(r"\s*\(이유:\s*(.*)\)\s*$")


def parse_decisions(text):
    decisions = []
    category = None
    n = 0
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## "):
            category = s[3:].strip()
            continue
        if not s.startswith("- "):
            continue
        body = s[2:].strip()
        session = None
        m = SESSION_RE.search(body)
        if m:
            session = m.group(1)
            body = SESSION_RE.sub("", body).rstrip()
        reason = None
        rm = REASON_RE.search(body)
        if rm:
            reason = rm.group(1).strip()
            body = REASON_RE.sub("", body).rstrip()
        n += 1
        decisions.append({"n": n, "category": category,
                          "text": body, "reason": reason, "session": session})
    return decisions


def _decisions_path():
    home = (os.environ.get("HOME") or os.environ.get("USERPROFILE")
            or os.path.expanduser("~"))
    cfg = os.path.join(home, ".config", "hamstern", "active-project.json")
    if not os.path.isfile(cfg):
        sys.exit('❌ active project 없음. /hams:link 또는 /hams:init 먼저.')
    with open(cfg, encoding="utf-8") as f:
        c = json.load(f)
    return os.path.join(c["hamstern_data_path"], "projects", c["uuid"], "decisions.md")


def main():
    path = _decisions_path()
    text = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            text = f.read()
    print(json.dumps(parse_decisions(text), ensure_ascii=False))


if __name__ == "__main__":
    main()
