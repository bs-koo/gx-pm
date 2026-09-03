# 표준용어 MCP 연계 — DDL·컬럼 표준화 가이드

> gx-pm이 생성하는 테이블정의서(DE-08)의 **DB 컬럼명을 사업부 표준용어사전(`sqi-comn-term` MCP)** 에 맞춰 표준화한다.
> **gx-pm 스킬·커맨드·템플릿은 수정하지 않는다.** 이 규칙(및 `CLAUDE.md`의 요약 섹션)만 따르면, gx-pm 스킬 실행 중 Claude가 MCP를 호출해 표준 컬럼을 만든다.

## 왜 필요한가

공공/SI 감리의 단골 지적이 **비표준 컬럼명**이다. gx-pm이 기능명세(AN-03)의 입력항목에서 도출한 신규 컬럼(예: `STN_NM`, `AVG_TA`, `OBS_DATE`, `LATITUDE`)은 표준단어 사전에 맞지 않는 경우가 많다. MCP로 검증·변환하면 표준 약어·표준 데이터타입까지 자동으로 맞춘다. 기존 스키마의 컬럼은 `현행유지`가 기본이고, MCP 판정은 신규 컬럼에만 적용한다.

## 전제

- **MCP는 세션 레벨 도구** — gx-pm 스킬 실행 중에도 호출 가능.
- **gx-pm 스킬은 `allowed-tools` 제한이 없음**(확인됨) — 호출을 막는 장치가 없다.
- 따라서 남은 건 "언제 부를지"를 알려주는 규칙뿐. → 이 문서 + `CLAUDE.md` 섹션.

## 출처(카테고리) 우선순위

`translate_column`/`validate_column`은 **출처 우선순위(`sourcePriority`)를 지정해야** 동작한다(없으면 `setupRequired`만 반환). 기본값:

```
sourcePriority = ["BLDG_ENGY", "MOIS_STD"]   # 건물에너지 우선 → 행안부 공통표준 보강
```

사업부 표준 사전의 카테고리(`list_categories` 결과):

| ctgryId | 이름 | 설명 | 규모 |
|---|---|---|---|
| `MOIS_STD` | 행안부표준 | 행정안전부 공공데이터 공통표준 | 16,565 |
| `BLDG_ENGY` | 건물에너지 | 한국부동산원 국가건물에너지 데이터 표준 | 1,588 |
| `ECAP` | 총량제 | 건물에너지 따르되 신규는 총량제 | 204 |
| `LH` | LH | 서비스파트 LH 표준 | 4,470 |
| `DP_STD` | DP표준 | GX사업본부 데이터플랫폼 파트 표준 | 34 |

> 프로젝트 도메인에 맞춰 우선순위를 조정한다(예: LH 사업이면 `["LH","MOIS_STD"]`).

## 프로토콜 (테이블/DDL 생성 시)

DE-08은 역생성 문서다 — **기존 컬럼과 신규 컬럼을 다르게 처리한다.** 기존 컬럼은 운영 중인
스키마이므로 이름을 바꾸지 않는다. 표준형으로 교체하는 것은 신규 컬럼뿐이다.

1. **한글 → 표준 컬럼 변환** (신규 컬럼 대상)
   ```
   translate_column(inputs=["관측소명","관측일자","위도", …], sourcePriority=["BLDG_ENGY","MOIS_STD"])
   ```
   → `columnName`(표준 영문), `dataType`(표준 도메인 타입), `status`(FULL/PARTIAL/AI_SUGGESTED), `ctgryNms`(출처).
2. **기존 영문 컬럼 검증** (기존 컬럼 대상)
   ```
   validate_column(columnNames=["STN_NM","AVG_TA", …], sourcePriority=["BLDG_ENGY","MOIS_STD"])
   ```
   → 컬럼별 `status`(PASS/PARTIAL/FAIL), 미등록 토큰의 `suggestions`, `suggestedColumnName`.
3. **결과 상태별 처리**

   **기존 컬럼 (`validate_column`) — 이름은 절대 바꾸지 않는다**

   | 상태 | 표준 판정 | 조치 |
   |---|---|---|
   | `PASS` | `표준준수` | 그대로 사용 |
   | `PARTIAL` / `FAIL` | `현행유지` | **컬럼명은 그대로 두고**, `표준 권고명`에 `suggestedColumnName`만 병기 |

   **신규 컬럼 (`translate_column`) — 표준형을 채택 대상으로 제시**

   | 상태 | 표준 판정 | 조치 |
   |---|---|---|
   | `FULL` | `신규적용` | 표준형(`columnName`)을 그대로 채택 |
   | `PARTIAL` / `AI_SUGGESTED` | `신규적용`(근거 명시) | 표준형을 근거와 함께 제시. 사용자가 반려하면 대안을 묻는다 |
   | `FAIL` / `decisionRequired=true` | 미확정 | **임의 추정 금지** — `humanHint`를 승인 게이트에 그대로 노출하고 그 자리에서 사용자 확인 |
   | `dataTypeCandidates` 다건 | 미확정 | 타입 후보를 나열하고 사용자에게 선택 요청 |
   | 미등록 도메인어 | 미확정 | 우선순위 밖 출처에만 존재 — 힌트 노출 후 출처 조정 또는 신규 등록 |

4. **DE-08 반영** — 기존 컬럼은 `구분=기존`으로 두고 `표준 판정`·`표준 권고명`만 채운다(컬럼명은
   불변). 신규 컬럼은 `구분=신규`, `표준 판정=신규적용`으로 표준 컬럼명을 `컬럼명`에 직접 쓴다.
   두 경우 모두 `근거` 열에 `{ctgryNms} · {단어 매칭}`을 남긴다. 열 모델의 정본은
   `templates/DE-08-table-definition.md`의 「본문 컬럼 (정본)」 절이다 — `표준 출처(ctgryNm)`라는
   별도 열은 없다.
5. **최초 1회** — 출력 포맷·출처 우선순위를 사용자에게 확인한 뒤 진행(MCP 지침).

## ACT 워크드 예시 (실측)

아래는 신규 컬럼 도출 사례다 — 이 프로젝트에는 대응하는 기존 DDL 이 없어 전건이 신규 컬럼으로
취급됐고, 그래서 표준형으로 "교체"됐다. 기존 컬럼이 있었다면 위 프로토콜대로 `현행유지` + 표준
권고명 병기가 됐을 것이다.

`ACT-테이블정의서.md`의 한글 속성을 `translate_column`(출처 `BLDG_ENGY→MOIS_STD`)으로 변환한 실제 결과:

| 한글 속성 | gx-pm 기존 컬럼 | **표준 컬럼** | 표준 데이터타입 | 출처 | 상태 |
|---|---|---|---|---|---|
| 관측소명 | `STN_NM` | **`OBSVTR_NM`** | VARCHAR(200) | 행안부표준 | 교체 |
| 관측일자 | `OBS_DATE` | **`OBSRVN_YMD`** | CHAR(8) | 행안부표준 | 교체 |
| 위도 | `LATITUDE` | **`LAT`** | NUMERIC(12,10) | 행안부표준 | 교체 |
| 경도 | `LONGITUDE` | **`LOT`** | NUMERIC(13,10) | 행안부표준 | 교체 |
| 수정일시 | `MOD_DT` | **`MDFCN_DT`** | DATETIME | 행안부표준 | 교체 |
| 지역코드 | `REGION_CD` | **`RGN_CD`** | (코드) | 행안부표준 | 교체 |
| 사용여부 | `USE_YN` | `USE_YN` | CHAR(1) | 행안부표준 | 유지 |
| 등록일시 | `REG_DT` | `REG_DT` | DATETIME | 행안부표준 | 유지 |
| 일평균 기온 | `AVG_TA` | `???_ARTMP`(기온=ARTMP) | dataTypeCandidates 선택 | 행안부표준 | 결정필요 |

## 검증 (오라클: `validate_column`)

표준 컬럼을 역검증한 실제 결과:
```
validate_column(["OBSVTR_NM","OBSRVN_YMD","LAT","LOT","USE_YN","REG_DT","MDFCN_DT","REGION_CD"],
                sourcePriority=["BLDG_ENGY","MOIS_STD"])
→ OBSVTR_NM PASS · OBSRVN_YMD PASS · LAT PASS · LOT PASS
  · USE_YN PASS · REG_DT PASS · MDFCN_DT PASS      (7건 PASS)
  · REGION_CD PARTIAL → 표준은 RGN_CD (지역=RGN)     (교정)
```
→ 표준형은 전부 PASS. `REGION_CD`처럼 "표준처럼 보이는" 컬럼도 검증에서 걸러 `RGN_CD`로 교정된다. **항상 validate로 확정한다.**

## 미등록 도메인어

- **"쾌적성"**: 우선순위(`BLDG_ENGY`/`MOIS_STD`) 밖 `LH` 출처에만 존재. 처리 옵션:
  - (a) `sourcePriority`에 `LH` 추가
  - (b) 표준단어 신규 등록 요청
  - (c) 승인된 대체어 사용
  - → 임의 약어 금지, 사용자 확인 필수.

## 사용 예 (자연어)

```
/gx-테이블정의서
  → (생성 중) "표준용어사전(BLDG_ENGY→MOIS_STD)으로 컬럼명 검증·변환해줘"
  → 기존 컬럼은 `현행유지`+표준 권고명, 신규 컬럼은 `신규적용`+근거가 채워진 DE-08 산출
```
또는 `CLAUDE.md`의 규칙이 로드돼 있으면 별도 지시 없이도 적용된다.


## 설치 (MCP가 없을 때)

`sqi-comn-term` 도구가 세션에 없으면 설치 후 사용한다. (사업부 "공통표준용어사전 MCP 가이드" 기준, **무인증 MVP** — 헤더/토큰 불필요)

**유저 스코프 (모든 프로젝트, 권장)** — 터미널:
```
claude mcp add -s user --transport http sqi-comn-term http://52.78.238.167:8687/api/v1/mcp
claude mcp list        # 등록 확인
```

**프로젝트 스코프** — 프로젝트 루트에 `.mcp.json`:
```json
{
  "mcpServers": {
    "sqi-comn-term": { "type": "http", "url": "http://52.78.238.167:8687/api/v1/mcp" }
  }
}
```
(사내망/로컬 구동 시 `http://localhost:8080/api/v1/mcp`)

**연결 확인**: `/mcp` 명령으로 상태 확인. 연결이 안 되면 상세에서 `Reconnect`.

> **미설치 시 처리 흐름**: 테이블/DDL 생성 시 `sqi-comn-term` 도구 존재를 먼저 확인한다.
> - **있으면** → `translate_column`/`validate_column` 수행.
> - **없으면** → ① 위 설치 명령 실행 → ② `claude mcp list` 확인 → ③ **사용자에게 안내**: "MCP를 설치했습니다. `/mcp`에서 `Reconnect` 또는 Claude Code 재시작 후 명령을 다시 실행해 주세요." 새로 추가한 MCP는 현재 세션에 바로 로드되지 않으므로, **재실행 세션부터** 표준화가 적용된다.
