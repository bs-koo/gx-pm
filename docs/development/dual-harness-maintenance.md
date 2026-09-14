# gx-pm Claude·Codex 공동 유지보수 지침

이 문서는 **저장소 개발용**이다. 사용자가 설치된 gx-pm으로 산출물을 만들 때의 규칙은
`plugins/gx-pm/commands/`, `skills/`, `templates/`가 정한다. 저장소에서 Claude로 작업하든
Codex로 작업하든 아래 순서로 수정하면 두 환경의 실행 경로가 함께 유지된다.

## 어디에 무엇을 고치는가

| 책임 | 정본 | 각 환경의 진입점 |
|---|---|---|
| 산출물 절차·게이트 | `plugins/gx-pm/commands/gx-*.md` | Claude: `/gx-*`; Codex: `$gx-pm-workflow` |
| 도출·대조 규칙 | `plugins/gx-pm/skills/*/SKILL.md` | 두 환경이 같은 파일을 읽는다 |
| 양식·ID·선행조건·승인 정책 | `plugins/gx-pm/templates/*.md` | 두 환경이 같은 파일을 읽는다 |
| Codex 라우팅·도구 변환 | `plugins/gx-pm/skills/gx-pm-workflow/SKILL.md` | Codex 전용 |
| 설치·발견 | Claude: `.claude-plugin/marketplace.json`, `plugins/gx-pm/.claude-plugin/plugin.json`; Codex: `.agents/plugins/marketplace.json`, `plugins/gx-pm/.codex-plugin/plugin.json` | 각 플랫폼별 매니페스트 |

업무 판정이나 화면 문구를 고칠 때는 원래 정본 한 곳을 수정한다. Codex 진입 스킬에 같은
절차를 복사하지 않는다. 새 내부 스킬은 해당 Claude 커맨드에서 호출하고 Codex에서는 그
커맨드를 통해 읽히게 한다. 스킬 폴더명과 프론트매터 `name`을 일치시킨다.

## 도구·경로 호환 계약

- 공통 문서에는 **무엇을 사용자에게 확인해야 하는지**와 승인 전 중단해야 하는 지점을
  명시한다. 기존 문서의 `AskUserQuestion`은 Claude에서 그 의미를 구현하는 도구다.
  신규 공통 규칙에 Claude 도구의 JSON 인자 구조를 복제하지 않는다.
- Codex 진입 스킬은 `AskUserQuestion` 지점을 현재 제공되는 `request_user_input_async` 등
  실제 입력 도구에 맞게 변환한다. 도구가 없으면 대화로 묻고 **실제 응답을 기다린다**.
  응답 없음, 텍스트 출력, 시간 경과를 승인으로 취급하지 않는다. 기존 `templates/approval-protocol.md`
  및 파이프라인 게이트의 승인 순서를 유지한다.
- 플러그인 파일 참조는 설치된 **플러그인 루트 기준 상대 경로**로 쓴다. 사용자 프로젝트의
  동명 `templates/` 또는 고정된 개발 PC 경로를 참조하지 않는다. 새 자산은 Codex 설치
  캐시에 포함되는지 확인한다.
- `sqi-comn-term` MCP가 하드 선행조건인 테이블정의서·명세일괄은 세션에 도구가 없으면
  중단한다. 설치 안내를 바꿀 때 `plugins/gx-pm/docs/표준용어-mcp-연계.md`의 Claude·Codex
  명령과 README를 같이 갱신한다.
- `${CLAUDE_PLUGIN_ROOT}` 절대경로 조립, `Skill()` 호출, `Task()` 디스패치를 공통 실행
  문서에 새로 도입하지 않는다. 플랫폼 고유 기능이 꼭 필요하면 해당 진입점에만 두고
  다른 플랫폼의 대응 방법을 이 문서에 기록한다.

## 변경별 체크리스트

1. **기존 스킬/템플릿 수정:** 이를 쓰는 커맨드의 단계·승인·출력 열과 맞는지 확인한다.
   두 환경에서 같은 파일을 읽으므로 규칙 복사본을 만들지 않는다.
2. **커맨드 추가·이름 변경:** `templates/prerequisites.md`에 선행조건을 적고
   `skills/gx-pm-workflow/SKILL.md`의 Codex 연결표, README의 커맨드 목록과 디렉터리 표,
   개수 계약 테스트를 갱신한다. Claude의 슬래시 커맨드 이름이 Codex에서 자동으로
   생기는 것은 아니다.
3. **질문·승인 흐름 수정:** Claude의 `AskUserQuestion`과 Codex의 현재 입력 도구에서
   같은 사용자 선택과 중단점이 유지되는지 확인한다. 필수 승인 없이 저장·추출로
   진행하지 않는다.
4. **MCP·xlsx·파일 경로 수정:** 두 환경의 설치/실행 안내와 Codex 설치 캐시의
   `commands/`, `templates/`, `utils/`, `docs/` 포함 여부를 확인한다.
5. **릴리스:** Claude·Codex 매니페스트, Claude 마켓플레이스, README 배지,
   CHANGELOG의 버전과 스킬·커맨드 개수를 함께 맞춘다. `test_codex_compat.py`의
   릴리스 버전 기대값도 갱신한다. 같은 버전을 로컬에 다시
   설치하면 Codex가 이전 캐시를 유지할 수 있으므로, 설치된 캐시에서 새 파일을
   직접 확인하고 필요하면 로컬 플러그인을 재설치한다.

## 검증 명령

저장소 루트에서 실행한다. Windows PowerShell은 `codex.cmd`, macOS/Linux는 `codex`를 쓴다.

```powershell
python -m unittest discover -s plugins/gx-pm/tests -q
$validator = Join-Path $env:USERPROFILE ".codex/skills/.system/plugin-creator/scripts/validate_plugin.py"
if (Test-Path $validator) { python $validator plugins/gx-pm }
git diff --check
codex.cmd plugin list -m gx-pm --json
```

macOS/Linux에서는 `$HOME/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py`와
`codex` 명령을 사용한다. `plugin-creator` 스킬이 설치되지 않은 환경에서는 검사기 줄을
생략하고 나머지 테스트를 실행한다. 정적 테스트만으로 실제 문서 생성이 검증되지는
않는다. 프로젝트 자료와 외부 MCP가 있는 환경에서 프로파일 설정, 명세 생성 중단점,
최종 산출물을 두 환경에서 확인한다.
