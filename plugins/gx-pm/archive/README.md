# archive — 커맨드에서 내린 산출물

2026-09-03 기능 축 전환(v3.0.0)으로 커맨드 표면에서 내린 파일들이다.
**삭제하지 않은 이유**: 감리가 있는 공공 사업은 화면목록표·감리대응·총괄테스트계획서를
여전히 요구한다. 그때 되살린다.

## 여기 있는 것

| 종류 | 개수 | 파일 |
|------|------|------|
| 커맨드 | 10 | 화면목록표 · 프로그램정의서 · 인터페이스정의서 · 결함관리대장 · 총괄테스트계획서 · 시스템테스트 · 통합테스트시나리오 · 테스트결과서 · 감리대응 · testplan |
| 스킬 | 13 | 위 커맨드가 쓰던 12개 + `generate-erd-guide`(테이블정의서 순방향 생성 경로) |
| 템플릿 | 7 | DE-03 · DE-05 · DE-14 · TE-01 · ST-01 · DF-01 · inspection-criteria |

`generate-erd-guide` 는 커맨드가 아니라 **경로**가 사라져서 내려왔다. DE-08 테이블정의서가
순방향(요구사항 → 테이블 추론)을 폐지하고 역생성만 남기면서 쓰이지 않게 됐다.

## 되살리는 방법

**파일만 되돌리면 테스트가 무더기로 빨개진다.** 아래 8~11번(개수 갱신·금지어 완화)을
빠뜨린 것이 그 원인이지 되살리기가 실패한 것이 아니다 — 무엇이 왜 실패하는지는
「되돌렸을 때 실제로 나는 실패」 절이 실측값으로 적어 뒀다.

1. 해당 파일을 `commands/` · `skills/` · `templates/` 로 되돌린다
2. `templates/prerequisites.md` 에 선행조건 행을 추가한다
3. 화면ID 파생 규칙(`PG_` · `U_` · `TC_`)이 필요하면 `templates/id-naming-rules.md` 에
   되살린다 — 현재 체인에는 파생 ID 가 없다
4. 옛 컬럼(`제안요청ID` · `수용여부` · `화면ID`)을 참조하는 곳을 현재 컬럼으로 고친다
5. `utils/export-xlsx.py` 의 `DOCUMENT_PROFILES` 에 해당 산출물 프로파일을 되살린다 —
   없으면 xlsx 추출이 컬럼 재배열 없이 원본 순서로 조용히 나간다
6. 되살린 커맨드를 진입점(`commands/gx-프로젝트설정.md` 또는 파이프라인)에서 안내한다 —
   안내하지 않으면 `test_모든_커맨드가_사용자에게_도달_가능하다` 가 잡는다
7. **되살린 커맨드가 참조하는 다른 커맨드도 함께 되살리거나, 그 참조를 지운다.**
   `gx-화면목록표.md` 는 `/gx-프로그램정의서`·`/gx-인터페이스정의서`·`/gx-testplan` 을
   백틱으로 참조하는데, 그것들이 아직 archive 에 있으면
   `test_백틱으로_참조된_커맨드가_모두_존재한다` 가 참조 하나당 1건씩 잡는다
8. **개수 표기 4곳을 갱신한다.** 커맨드·스킬 수가 늘어난 것을 아무도 자동으로 세지
   않는다 — `VersionConsistencyTest` 가 네 자리를 각각 본다

   | 자리 | 무엇 |
   |------|------|
   | 저장소 `README.md` 배지 | `skills-{N}-green` · `commands-{N}-orange` |
   | 저장소 `README.md` 디렉토리 트리 주석 | `commands/ # N개 커맨드` · `skills/ # N개 스킬` |
   | `.claude-plugin/plugin.json` 의 `description` | `{N}개 스킬` · `커맨드 {N}개` |
   | 루트 `.claude-plugin/marketplace.json` 의 `description` | 위와 같다 |

9. **금지어 목록을 완화한다.** `tests/test_plugin_consistency.py` 의
   `FiveDocumentContractTest.test_화면_축_잔재가_현역_문서에_없다` 는 `화면목록표` ·
   `PG_{화면ID}` · `제안요청ID` · `수용여부` 를 **현역 문서의 금지어**로 본다.
   화면 축 산출물을 되살리면 그 낱말이 정당하게 돌아오므로, 되살린 축에 해당하는 낱말을
   그 목록에서 뺀다. **목록을 통째로 비우지는 않는다** — 되살리지 않은 축의 잔재는
   계속 잡아야 한다
10. `commands/gx-spec.md` 의 파이프라인 구성이 바뀌면 `PIPELINE_ARTIFACTS` ·
    `PIPELINE_GATES` · `SurfaceTest.test_커맨드가_일곱_개다` 의 기대값도 함께 고친다
11. **그 산출물을 지키던 테스트도 함께 되살린다** (아래 참조)
12. 테스트를 돌린다: `python -m unittest discover -s tests -v`

## 되돌렸을 때 실제로 나는 실패

`gx-화면목록표` 세 벌(커맨드 1 + 스킬 1 + 템플릿 1)만 되돌리고
`python -m unittest discover -s tests` 를 돌리면 **`Ran 125 tests … FAILED (failures=14)`**
가 난다. 실측한 14건은 아래와 같고, **두 종류로 갈린다.**

**규칙 위반 — 되살리기 절차가 아직 안 끝났다는 신호 (7건)**

| 실패 | 건수 | 무엇이 빠졌나 |
|------|------|-------------|
| `CrossReferenceTest.test_모든_커맨드가_사용자에게_도달_가능하다` | 1 | 6번. 진입점이 되살린 커맨드를 안내하지 않는다 |
| `CrossReferenceTest.test_백틱으로_참조된_커맨드가_모두_존재한다` | 3 | 7번. 되살린 `gx-화면목록표.md` 가 아직 archive 에 있는 `gx-프로그램정의서`·`gx-인터페이스정의서`·`gx-testplan` 을 참조한다 |
| `PrerequisiteRegistryTest.test_모든_커맨드가_레지스트리에_있다` | 1 | 2번. 선행조건 행이 없다 |
| `SurfaceTest.test_커맨드가_일곱_개다` | 1 | 10번. 표면 커맨드 목록의 기대값 |
| `SurfaceTest.test_화면_축_커맨드가_남아있지_않다` | 1 | 10번. "화면 축은 내렸다" 를 고정한 검사라, 되살리기로 결정했으면 이 기대값을 뒤집어야 한다 |

**개수·목록 갱신 — 되살린 것 자체는 옳고 표기만 안 따라왔다 (7건)**

| 실패 | 건수 | 무엇이 빠졌나 |
|------|------|-------------|
| `FiveDocumentContractTest.test_화면_축_잔재가_현역_문서에_없다` | 3 | 9번. `화면목록표` 라는 낱말이 현역 금지어라 되살린 파일 3개가 **전부** 걸린다 |
| `VersionConsistencyTest.test_README_배지가_실제_스킬_커맨드_수와_같다` | 1 | 8번 |
| `VersionConsistencyTest.test_README_디렉토리_트리의_개수가_실제와_같다` | 1 | 8번 |
| `VersionConsistencyTest.test_설명문의_스킬_커맨드_수가_실제와_같다` | 2 | 8번. `plugin.json` 과 `marketplace.json` 각 1건 |

되살리는 파일이 늘면 건수는 달라진다. **종류는 그대로다.**

## 되살려야 할 테스트

위 14건은 시끄럽게 실패하니 놓칠 수 없다. **정작 위험한 것은 조용한 쪽이다** — 이
산출물들을 지키던 계약 검사가 `tests/test_plugin_consistency.py` 에서 함께 삭제돼,
**되살려도 아무것도 실패하지 않는다.** 규칙 문서(예:
`skills/generate-screen-list/SKILL.md` 의 판정 순서, A·C 는 묻고 D 는 묻지 않는 규정,
DE-03 컬럼 결속)는 여기 온전히 남아 있지만, **그것을 강제하던 장치는 없다.**
되살린 뒤 규칙을 고쳐도 아무도 모르게 되고, 그것이 `PG_`·`U_`·`TC_` 전건 재채번을
부르는 경로다.

삭제 직전 판본은 커밋 `7242319` 에 있다.

```bash
git show 7242319:plugins/gx-pm/tests/test_plugin_consistency.py > /tmp/옛계약.py
```

거기서 아래를 꺼내 현재 파일에 되돌린다.

| 되살릴 것 | 지키던 것 |
|----------|----------|
| `ScreenSplitRuleTest` (7건) | 화면 분리 미결정 판정이 추론표보다 앞설 것, A·C 는 묻고 D 는 묻지 않을 것, 기록 규칙이 DE-03 의 실제 컬럼을 지목할 것, 재질문 금지 |
| `test_화면목록표_커맨드가_유형별_동작을_복제하지_않는다` | 커맨드가 `generate-screen-list/SKILL.md` §3-2 를 복제하지 않을 것 |

같은 커밋의 `PIPELINE_ARTIFACTS` 도 함께 본다 — `/gx-testplan` 을 되살린다면 그 파이프라인의
구성 산출물이 거기 있다. 그 시점에는 `PIPELINE_GATES` 상수가 아직 없었다 — 게이트 수(2개)는
`PipelineCommandTest` 안에 하드코딩된 리터럴이었다. 찾다가 헷갈리지 않도록 여기 적어 둔다.

## 주의

`tests/helpers.py` 의 `read_docs()` 가 이 디렉터리를 건너뛴다.
여기 있는 파일은 계약 검사를 받지 않으므로, 되살릴 때 반드시 4번과 11번을 한다.
