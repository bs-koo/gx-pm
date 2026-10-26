# 로컬 실행 증적과 반영 입력

실제 수행 뒤 `execution.json`을 작성할 때 읽는다. Python 3.10 표준 라이브러리 도구
`utils/test-evidence.py`의 `plan`·`write`가 사용한다. `index`와 기존 테스트 결과 가져오기는 제공하지 않는다.

## execution.json

파일은 `증적/{시스템코드}/{run_id}/execution.json`에 둔다. 아래는 한 행의 구조 예시다.
해시·시각·관측값은 실제 실행에서 얻은 값으로 채운다. 예시를 실행 증적으로 복사하지 않는다.

```json
{
  "schema_version": 1,
  "run_id": "20261026T143000-local-01",
  "plan_hash": "plan.json의 plan_hash",
  "started_at": "2026-10-26T14:30:00+09:00",
  "finished_at": "2026-10-26T14:32:00+09:00",
  "operator": "홍길동",
  "sources": [
    {"path": "D:/projects/example-api", "revision": "a1b2c3d", "dirty": false}
  ],
  "targets": [
    {"base_url": "http://127.0.0.1:8080", "startup_evidence": "startup.txt", "startup_sha256": "가린 기동 로그의 전체 SHA-256 64자리"}
  ],
  "rows": {
    "UT-001": {
      "fingerprint": "plan.json의 해당 행 fingerprint",
      "execution": "completed",
      "channel": "api",
      "actual": "POST /items: HTTP 400, 메시지 '이름을 입력하세요', 저장 건수 0→0",
      "checks": [
        {"field": "사전조건", "expected": "관리자로 로그인, 등록 데이터 없음", "observed": "관리자 세션 확인, 조회 건수 0", "matched": true, "artifact": "UT-001-before.txt"},
        {"field": "입력", "expected": "이름=빈 문자열", "observed": "POST /items, name=빈 문자열 전송", "matched": true, "artifact": "UT-001-response.txt"},
        {"field": "기대결과", "expected": "\"이름을 입력하세요\" 안내 후 차단", "observed": "HTTP 400, 이름을 입력하세요", "matched": true, "artifact": "UT-001-response.txt"},
        {"field": "사후조건", "expected": "저장 없음", "observed": "후속 조회 건수 0, 이전 건수 0", "matched": true, "artifact": "UT-001-after.txt"}
      ],
      "artifacts": [
        {"path": "UT-001-before.txt", "sha256": "가린 증적 파일의 전체 SHA-256 64자리"},
        {"path": "UT-001-response.txt", "sha256": "가린 증적 파일의 전체 SHA-256 64자리"},
        {"path": "UT-001-after.txt", "sha256": "가린 증적 파일의 전체 SHA-256 64자리"}
      ]
    }
  }
}
```

- `rows`는 **계획서의 모든 테스트ID를 정확히 한 번씩** 포함한다. 미실행 행도 생략하지 않는다.
- `plan_hash`·`fingerprint`는 수행 전에 읽은 `plan.json` 값이다. 실행 뒤 바뀐 계획서에 맞춰 해시만 다시 찍지 않는다.
- 시각에는 UTC 오프셋을 넣고 시작≤완료를 만족해야 한다. `operator`는 시험 수행 책임자다.
- `sources`에는 실제 실행한 소스 경로·리비전·미커밋 여부를 적는다. VCS가 없으면 그 사실을 리비전에 명시하고 기동 로그에 파일 기준을 기록한다.
- `targets`는 loopback HTTP(S) URL과 기동/재사용 확인 로그 및 그 파일의 `startup_sha256`이다. 외부 URL은 이 로컬 시험 계약에서 받지 않는다. 주소 확정 전에 막혀 전 행이 `execution: blocked`, `channel: none`인 경우에만 빈 배열을 허용한다. 임의 URL을 만들지 말고 실패 로그는 각 행의 artifacts에 연결한다.
- `execution`은 `completed`, `blocked`, `not_implemented` 중 하나다. `channel`은 `api`, `browser`, `mixed`, `none` 중 하나다.
- `actual`은 실제 관측 또는 수행하지 못한 이유이며 모든 행에서 필수다. 부분 관측은 수행한 부분과 확인하지 못한 부분을 함께 쓴다.
- `checks.field`는 계획서의 사전조건·입력·기대결과·사후조건이다. 같은 field는 한 번만 적고 여러 조건의 관측을 하나의 `observed`에 정리한다. 일부만 관측한 조건을 통째로 true로 표시하지 않는다.
- `checks.expected`는 `〃`를 해소한 해당 계획서 칸 원문과 같아야 한다. `observed`는 도구로 확인한 실제 값이다. `matched`는 true/false/null이며 알 수 없는 것은 null이다.
- 사전조건·입력 칸이 비어도 실제로 사용한 환경·동작을 기록한다. 이때 `expected`는 빈 문자열이고, 빈칸이 '별도 조건 없음'으로 해석 가능한지 확인한 경우에만 `matched: true`다. 필요한 조건이 누락되어 해석할 수 없으면 null로 두고 미검증으로 남긴다.
- `checks.artifact`는 그 행의 `artifacts` 안에 등록된 파일이다. 브라우저 행은 DOM/조작 기록·스크린샷, 데이터 사후조건은 전후 조회 출력을 연결한다.
- 모든 증적 경로는 execution.json의 부모 폴더 내부 상대경로다. 절대경로·상위 폴더 탈출은 허용하지 않는다. 파일이 없거나 비었거나 SHA-256이 달라졌으면 반영하지 않는다.
- 응답 파일은 메서드·URL·실제 전송값·상태·본문, 브라우저 기록은 URL·조작·관측 요소를 포함한다. 민감한 인증값은 가리고 결과 판정에 필요한 업무 값은 남긴다.

## 판정과 미실행

유효한 시험은 사전조건·입력의 관측이 계획과 맞는 경우다. 유효한 실제 수행에서 기대결과/사후조건 중
하나라도 불일치가 확인되면 Fail, 필요한 네 칸이 모두 확인되어 일치하면 Pass다. 누락·미관측은 미검증이다.
빈 계획 칸을 채우려고 기준을 지어내지 않는다. 기대결과와 사후조건이 모두 비어 있으면 미검증이다.
`[미확정]`이 있으면 Pass·Fail로 쓰지 않는다.

환경/도구/선행조건 문제는 `execution: blocked`로 이유를 `actual`에 쓴다. 확보한 오류 로그가 있으면
artifacts에 연결한다. 기능이 제공되지 않는 것으로 확인된 경우에만 `not_implemented`를 쓰고 그 확인 파일을
반드시 연결한다. `none`은 요청이나 브라우저 수행을 하지 못한 행에서 사용한다. PM 확인 문장만으로 새 Pass를 만들지 않는다.

증적 JSON과 해시는 **기록의 연결·일관성**을 검증한다. 요청을 실제로 수행했는지, 여러 조건을 충분히 관측했는지는
에이전트가 실제 도구 출력으로 확인해야 한다. JSON이나 테스트용 fixture만 생성하고 시험 완료라고 보고하지 않는다.

## changes.json과 write

`execution.json`을 확정한 뒤 파일 전체의 SHA-256을 `evidence_hash`에 넣는다. 승인 중 JSON 내용까지
달라졌으면 다시 대조한다. `plan_hash`·`result_hash`는 승인 화면을 만든 시점의 `plan.json` 값이다.

```json
{
  "plan_hash": "...",
  "result_hash": "...",
  "evidence_hash": "execution.json 파일의 전체 SHA-256 64자리",
  "date": "2026.10.26",
  "project": "",
  "sources": "example-api D:/projects/example-api, main a1b2c3d",
  "basis": "20261026T143000-local-01, http://127.0.0.1:8080",
  "note": "",
  "mapping": {},
  "candidates": {"new": 0, "boost": 0},
  "revision": null,
  "rows": {
    "UT-001": {"상태": "Pass", "사유": "실행 확인 — 빈 이름 차단, 저장 없음", "수행일": "2026.10.26", "담당자": "홍길동", "비고": "", "keep": false}
  }
}
```

`rows`에는 계획서 전 행을 넣는다. 도구는 증적에서 판정·실제결과·수행일·담당자·근거를 도출하고
변경안의 상태와 대조한다. Pass·Fail의 수행일은 `finished_at`의 날짜, 담당자는 `operator`다.
미구현·미검증의 새 수행일·담당자는 공란이다. 실제결과·근거는 도구가 실행 증적에서 채운다.
`keep: true`는 계획 내용이 같은 행의 사람 값을 유지하는 선택이다. `case_changed` 행에서는 사용할 수 없다.
수행대장에는 이번 판정과 실제결과가 남으며, 바뀐 케이스의 옛 값은 결과서 백업에 보존한다.

먼저 `revision: null`로 dry-run한 뒤, 필요한 경우 승인된 개정이력 객체를 넣어 같은 입력으로 기록한다.
변화가 없으면 revision은 null이다. 기존 후보 건수·작성자 매핑 필드는 옛 대장 호환을 위해 남아 있다.
현재 시험의 책임자는 VCS 작성자 매핑에서 찾지 않는다.

```text
python {플러그인 루트}/utils/test-evidence.py write --de13 "{계획서}" --result "{결과서}" --ledger "{수행대장}" --changes "{changes.json}" --evidence "{execution.json}" --dry-run
```

승인 뒤 같은 명령에서 `--dry-run`을 뺀다. 중단한 실행도 전 행의 완료·미검증 상태를 담아 마감한다.
다시 수행할 때는 새 run_id로 계획서 전 행을 재수행하고 그 증적으로 판정한다. 선행 데이터도 복원한다.
이전 완료 결과를 새 실행에 합치거나 이전 관측에 새 실행 시각을 붙여 재활용하지 않는다.
