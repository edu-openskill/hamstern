# hamstern 플러그인 개발 규칙

이 저장소는 Claude Code 플러그인(`hams`) 마켓플레이스다.
스킬을 추가/삭제/이름변경할 때 아래 규칙을 **반드시** 지킨다. 어기면 사용자 로컬에 동기화가 안 된다.

---

## 규칙 1 — 스킬 변경 시 매니페스트 2곳을 같이 고친다 (절대)

`skills/` 폴더에 디렉터리를 추가/삭제/이름변경하면, 같은 커밋에서 다음을 함께 수정한다:

1. **`.claude-plugin/marketplace.json`의 `plugins[].skills` 배열** — `skills/` 폴더 실제 목록과 **정확히 일치**시킨다 (추가분 등록, 삭제분 제거).
2. **버전 bump** — `.claude-plugin/plugin.json`과 `.claude-plugin/marketplace.json`의 `version`을 **둘 다** 올린다.

> SKILL.md만 추가하고 매니페스트를 안 고치면, Claude Code가 스킬을 등록하지 못하거나 디렉터리 스캔에만 의존하게 되어 불안정하다.

## 규칙 2 — 버전은 내용이 바뀌면 무조건 올린다 (절대)

Claude Code 플러그인 업데이터는 **버전 문자열로만** 갱신 여부를 판단한다.
설치된 버전과 GitHub 버전이 같으면(`1.1.0 == 1.1.0`), 내용이 아무리 바뀌어도
`/plugin` 업데이트 확인은 **"이미 최신"으로 오판하고 재다운로드하지 않는다.**

- 스킬/기능 추가 → minor bump (`1.1.0 → 1.2.0`)
- 버그·문구 수정 → patch bump (`1.2.0 → 1.2.1`)
- `plugin.json`과 `marketplace.json`의 `version`은 **항상 동일**하게 유지한다.

> 과거 사고: 커밋 `89486ea`에서 context-save/resume/decisions를 추가했으나
> 매니페스트·버전을 안 건드려, 버전이 `1.1.0` 그대로라 로컬에 동기화가 안 됐다.
> (`9bc0964`에서 `1.2.0`으로 수정)

## 규칙 3 — 폐기(deprecate)는 파일을 지우지 않는다

스킬을 폐기할 때는 SKILL.md를 삭제하지 말고, `[DEPRECATED YYYY-MM-DD]` 표시 +
대체 스킬 안내 스텁으로 남긴다. 파일이 디스크에 남아 있으면 `skills` 배열에도 등록을 유지한다.
(예: `record`/`remind` → `context-save`/`context-resume`로 대체, 스텁 유지)

---

## 변경 후 체크리스트

- [ ] `ls skills/` 폴더 목록 == `marketplace.json`의 `skills` 배열 (개수·이름 일치)
- [ ] `plugin.json` version 올림
- [ ] `marketplace.json` metadata.version 올림 (= plugin.json과 동일)
- [ ] `marketplace.json` / `plugin.json` JSON 유효성 확인
- [ ] commit + push
- [ ] 검증: 로컬에서 `/plugin` → hamstern → 업데이트가 새 버전을 인식하는지 확인

## 빠른 검증 명령

```bash
# skills/ 디스크 목록과 매니페스트 skills 배열이 일치하는지 비교
# (ls가 트레일링 슬래시를 붙일 수 있어 sed로 제거 — 안 하면 항상 MISMATCH 오탐)
diff <(ls skills/ | sed 's|/$||' | sort) \
     <(grep -oE '"\./skills/[^"]+"' .claude-plugin/marketplace.json | sed 's|"\./skills/||;s|"||' | sort) \
  && echo "OK: 매니페스트와 디스크 일치" || echo "MISMATCH: 위 차이를 marketplace.json에 반영하라"

# 두 매니페스트 버전이 같은지 확인
grep '"version"' .claude-plugin/plugin.json .claude-plugin/marketplace.json
```
