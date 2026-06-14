"""
내장 추출기: 스킬 레지스트리 정합성 검사

두 가지 검사를 수행한다:
  1. scan_refs  — changed files 안에 skills/<name> 참조가 있는데
                  marketplace.json 에 등록되지 않은 경우 WARN
  2. find_orphans — skills/<name>/ 디렉터리가 있는데 SKILL.md 도 없고
                   git-추적 파일도 0개인 경우 WARN (orphan 스킬 디렉터리)

출력 포맷 (stdout, TSV):
  WARN\t<location>\t<message>

종료 코드: 항상 0 (gate 판단은 상위 runner 가 함)
"""

import json
import os
import re
import subprocess
import sys

_SKILL_REF_RE = re.compile(r"skills/([a-zA-Z0-9_-]+)")


def registered_skills(project_root):
    """marketplace.json 에서 등록된 스킬 이름 집합을 반환.
    파일이 없거나 JSON 파싱 실패 시 WARN 출력 후 None 반환 (Fix 1).
    """
    mp = os.path.join(project_root, ".claude-plugin", "marketplace.json")
    try:
        with open(mp, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("WARN\t.claude-plugin/marketplace.json\t레지스트리 파일 없음/손상 — 참조 검사 건너뜀")
        return None
    names = set()
    for p in data.get("plugins", []):
        for s in p.get("skills", []):
            if isinstance(s, str):
                names.add(os.path.basename(s.rstrip("/")))
    return names


def scan_refs(project_root, files, registered):
    """변경된 파일 목록에서 skills/<name> 참조를 추출해
    등록되지 않은 스킬을 WARN 으로 출력한다.
    """
    for path in files:
        abs_path = os.path.join(project_root, path) if not os.path.isabs(path) else path
        if not os.path.isfile(abs_path):
            continue
        try:
            with open(abs_path, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            continue
        for m in _SKILL_REF_RE.finditer(content):
            skill_name = m.group(1)
            if skill_name not in registered:
                print(f"WARN\t{path}\t스킬 참조 '{skill_name}' 가 marketplace.json 에 미등록")


def find_orphans(project_root):
    """skills/ 하위 디렉터리 중 SKILL.md 없고 git-추적 파일도 0개인
    디렉터리를 orphan 으로 WARN 출력한다.
    git 미설치 또는 git 오류 시 오탐을 방지하기 위해 검사를 생략한다 (Fix 2).
    """
    skills_dir = os.path.join(project_root, "skills")
    if not os.path.isdir(skills_dir):
        return
    for name in sorted(os.listdir(skills_dir)):
        d = os.path.join(skills_dir, name)
        if not os.path.isdir(d):
            continue
        if os.path.isfile(os.path.join(d, "SKILL.md")):
            continue
        try:
            res = subprocess.run(
                ["git", "-C", project_root, "ls-files", f"skills/{name}/"],
                capture_output=True, text=True, stdin=subprocess.DEVNULL)
        except FileNotFoundError:
            return  # git 미설치 — orphan 판정 불가, 검사 생략
        if res.returncode != 0:
            continue
        if not res.stdout.strip():
            print(f"WARN\tskills/{name}\tSKILL.md 없고 추적 파일 0 — orphan 스킬 디렉터리")


def main():
    project_root = sys.argv[1]
    files = sys.argv[2:]
    registered = registered_skills(project_root)
    if registered is not None:
        scan_refs(project_root, files, registered)
    find_orphans(project_root)


if __name__ == "__main__":
    main()
