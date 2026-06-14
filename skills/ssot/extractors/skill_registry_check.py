"""내장 추출기: 스킬 레지스트리 정합성 검사.

두 가지 검사를 수행한다:
  1. scan_refs    — SSOT 파일 안에 /hams:<name> 슬래시 참조가 있는데
                    marketplace.json 에 등록되지 않은 경우 WARN (stale 참조)
  2. find_orphans — skills/<name>/ 디렉터리가 있는데 SKILL.md 도 없고
                    git-추적 파일도 0개인 경우 WARN (orphan 스킬 디렉터리)

계약: argv[1]=project_root, argv[2:]=SSOT 파일 경로들.
출력 포맷 (stdout, TSV): WARN\t<location>\t<message>  (location 은 path 또는 path:line)
종료 코드: 항상 0 (gate 판단은 상위 runner 가 함).
"""

import json
import os
import re
import subprocess
import sys

REF = re.compile(r"/hams:([a-z][a-z0-9-]*)")


def registered_skills(project_root):
    """marketplace.json 에서 등록된 스킬 이름 집합을 반환.
    파일이 없거나 JSON 파싱 실패 시 WARN 출력 후 None 반환 (참조 검사 건너뜀).
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
    """SSOT 파일들에서 /hams:<name> 참조를 줄 단위로 추출해
    등록되지 않은 스킬 참조를 'WARN\tpath:line\t...' 로 출력한다.
    """
    for rel in files:
        path = os.path.join(project_root, rel)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                for name in REF.findall(line):
                    if name not in registered:
                        print(f"WARN\t{rel}:{i}\t등록되지 않은 스킬 참조 '/hams:{name}' (stale)")


def find_orphans(project_root):
    """skills/ 하위 디렉터리 중 SKILL.md 없고 git-추적 파일도 0개인
    디렉터리를 orphan 으로 WARN 출력한다.
    git 미설치 또는 git 오류 시 오탐을 방지하기 위해 검사를 생략한다.
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
