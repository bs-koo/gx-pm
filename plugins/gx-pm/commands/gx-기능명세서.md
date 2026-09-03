---
description: "AN-03 기능명세서를 생성합니다. 요구사항정의서에서 기능을 도출하고 입력항목·처리내용·출력결과를 정의합니다. | 자연어: 기능명세서 만들어줘, 기능 정의, 기능 뽑아줘, 기능명세 작성"
---

# /gx-기능명세서 — AN-03 기능명세서 생성

> **선행조건**: `templates/prerequisites.md` 의 `/gx-기능명세서` 행을 따른다.
> **실행 규약**: `templates/pipeline-protocol.md` 를 따른다.

## Step 0: 프로젝트 컨텍스트 로드

**load-project-profile** 스킬로 활성 프로젝트를 확인한다. 프로파일이 없으면
`/gx-프로젝트설정` 을 먼저 실행하라고 안내 후 종료.

**detect-existing-artifact** 스킬로 기존 `{시스템코드}-기능명세서.md` 를 확인한다.

## Step 1: 요구사항정의서 로드

승인된 AN-02 를 읽는다. 없으면 `/gx-요구사항정의서` 를 먼저 실행하라고 안내 후 종료.

## Step 2: 기능 도출

**generate-function-spec** 스킬을 수행한다.

## Step 3: 승인 루프

`templates/approval-protocol.md` 를 따른다. `[확인필요]` 목록을 함께 보여준다.

## Step 4: 개정이력 기록

**manage-revision-history** 스킬로 개정이력 행을 만든다.

## Step 5: xlsx 추출

`utils/export-xlsx.py` 로 추출한다.

## 다음 제안

- `/gx-테이블정의서` — 입력항목을 컬럼으로 확정
- `/gx-단위테스트계획서` — 기능에서 테스트 케이스 도출
