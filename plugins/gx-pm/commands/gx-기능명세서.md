---
description: "AN-03 기능명세서를 생성합니다. 요구사항정의서에서 기능을 도출하고 입력항목·처리내용·출력결과를 정의합니다. | 자연어: 기능명세서 만들어줘, 기능 정의, 기능 뽑아줘, 기능명세 작성"
argument-hint: "<요구사항정의서 또는 파일>"
---

# /gx-기능명세서 — AN-03 기능명세서 생성

> **공통 규칙**: `templates/approval-protocol.md`의 승인 루프 프로토콜을 적용한다.
> **선행조건**: `templates/prerequisites.md` 의 `/gx-기능명세서` 행을 따른다.
> **실행 규약**: `templates/pipeline-protocol.md` 를 따른다.

## Step 0: 프로젝트 컨텍스트 로드

**load-project-profile** 스킬로 활성 프로젝트를 확인한다. 프로파일이 없으면
`/gx-프로젝트설정` 을 먼저 실행하라고 안내 후 종료.

**review-confirmations**의 기존 응답 보호 절차로 확인요청서 md/xlsx를 먼저 확인한다.
응답 반영을 요청받았으면 **apply-confirmations**로 파일 전체를 반영하고 이어간다.
의도가 불분명할 때만 「확인요청서 반영하고 이어가기」를 묻는다.

**detect-existing-artifact** 스킬로 기존 `{시스템코드}-기능명세서.md` 를 확인한다.

## Step 1: 요구사항정의서 로드

승인된 AN-02 를 읽는다. 없으면 `/gx-요구사항정의서` 를 먼저 실행하라고 안내 후 종료.

## Step 2: 기능 도출

**generate-function-spec** 스킬을 수행한다.

## Step 2-1: ID 승계

직전 버전이 `backup/` 에 있으면 **reconcile-ids** 스킬로 기능ID 를 승계한다.
백업본이 없으면 첫 생성이므로 건너뛴다.
**승인(Step 3)보다 먼저 돈다** — 사용자가 검토하는 표에 최종 ID 가 실려 있어야 한다
(`skills/reconcile-ids/SKILL.md` §언제 도는가).

## Step 3: 승인 루프

`templates/approval-protocol.md` 를 따른다. `[가정]`·`[미확정]` 목록을 함께 보여준다.

## Step 4: 개정이력 기록

**manage-revision-history** 스킬로 개정이력 행을 만든다.

## Step 4-1: 저장 + 확인요청서

승인된 `{시스템코드}-기능명세서.md`를 저장한 뒤, **xlsx 를 묻기 전에**
**review-confirmations**로 이번 확인 항목의 합계를 판정한다.
`templates/confirmation-request.md` §낱개 커맨드에서도 같은 규칙으로 낸다를 따른다.
0건은 추가 발행 없음, 1~5건은 실제 응답을 기다리고 이력 기록, 6건 이상은 확인요청서 md·xlsx 발행 후 보류다.
미결이 남은 최종본은 보류하되 요청한 검토용 초안은 별도 출력한다. 이미 정한 xlsx 선택은 다시 묻지 않는다.

## Step 5: xlsx 추출

`utils/export-xlsx.py` 로 추출한다. 이 산출물에 미결이 남아 있으면 최종본을 보류하며,
요청받은 검토용 초안은 `--draft --separate`로 제공한다
(`templates/confirmation-request.md` §미확정이 0이어야 최종본을 낸다).

## 다음 제안

- `/gx-테이블정의서` — 입력항목을 컬럼으로 확정
- `/gx-단위테스트계획서` — 기능에서 테스트 케이스 도출
