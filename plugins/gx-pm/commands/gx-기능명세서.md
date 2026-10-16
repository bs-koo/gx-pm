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

**확인요청서가 있으면 3분기보다 먼저 묻는다.** 「확인요청서 반영하고 이어가기」를 고르면
**apply-confirmations** 스킬로 반영한다. 화면과 분기는
`templates/confirmation-request.md` §낱개 커맨드에서도 같은 규칙으로 낸다 가 정본이다.

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

`{시스템코드}-기능명세서.md` 로 저장한 뒤, **xlsx 를 묻기 전에** `[가정]` + `[미확정]`
합계로 확인요청서를 판정한다 — `templates/confirmation-request.md` §낱개 커맨드에서도 같은 규칙으로 낸다.
0건이면 Step 5 로, 1~5건이면 그 자리에서 대화로 묻고 Step 5 로 간다.
**6건 이상이라 발행했으면 Step 5 로 가지 않고 끝낸다.**
Step 3 의 목록 표시로 갈음하지 않는다 — 보여준 것과 물은 것은 다르다.

## Step 5: xlsx 추출

`utils/export-xlsx.py` 로 추출한다. 이 산출물에 `[미확정]` 이 남아 있으면 뽑지 않는다
(`templates/confirmation-request.md` §미확정이 0이어야 최종본을 낸다).

## 다음 제안

- `/gx-테이블정의서` — 입력항목을 컬럼으로 확정
- `/gx-단위테스트계획서` — 기능에서 테스트 케이스 도출
