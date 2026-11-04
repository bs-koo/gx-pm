"""관측된 값 손상과 응답 덮어쓰기를 실제 파일로 재검증한다."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import openpyxl

from helpers import load_export_module, load_util


class ExportIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_export_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.headers = self.mod.DOCUMENT_PROFILES['요구사항정의서']['columns'][0]

    def table(self, headers, rows):
        return ['| ' + ' | '.join(headers) + ' |',
                '| ' + ' | '.join(['---'] * len(headers)) + ' |',
                *['| ' + ' | '.join(row) + ' |' for row in rows]]

    def row(self, value='회원 등록', rid='REQ-001'):
        return ['1', rid, '회원', '등록', '회원 등록', value, '', '유지', 'RFP SFR-001', '']

    def export(self, rows, **kwargs):
        target = self.root / 'result.xlsx'
        self.mod.create_xlsx([('B-요구사항정의서.md', [('본문', self.table(self.headers, rows))])],
                             str(target), **kwargs)
        return target

    def test_escaped_pipe_preserves_column_positions(self):
        wb = openpyxl.load_workbook(self.export([self.row(r'권한=A\|B')]))
        self.addCleanup(wb.close)
        self.assertEqual(wb.active['F2'].value, '권한=A|B')
        self.assertEqual(wb.active['H2'].value, '유지')
        self.assertEqual(wb.active['I2'].value, 'RFP SFR-001')

    def test_fenced_example_is_excluded(self):
        example = self.table(self.headers, [self.row(rid='REQ-999')])
        actual = self.table(self.headers, [self.row()])
        text = '\n'.join(['## 예시', '```markdown', *example, '```', '## 본문', *actual])
        tables = self.mod.parse_markdown_tables(text)
        out = self.root / 'fenced.xlsx'
        self.mod.create_xlsx([('B-요구사항정의서.md', tables)], str(out))
        wb = openpyxl.load_workbook(out)
        self.addCleanup(wb.close)
        self.assertEqual(wb.active.max_row, 2)
        self.assertEqual(wb.active['B2'].value, 'REQ-001')

    def test_equals_is_literal_text(self):
        wb = openpyxl.load_workbook(self.export([self.row('=1+1')]))
        self.addCleanup(wb.close)
        self.assertEqual(wb.active['F2'].value, '=1+1')
        self.assertEqual(wb.active['F2'].data_type, 's')

    def test_oversize_cell_rejected_without_overwriting(self):
        target = self.root / 'result.xlsx'
        target.write_bytes(b'keep previous final')
        with self.assertRaisesRegex(ValueError, '32767|32,767'):
            self.export([self.row('가' * 33000)])
        self.assertEqual(target.read_bytes(), b'keep previous final')

    def test_strict_rejects_duplicate_ids_and_draft_allows_unresolved(self):
        with self.assertRaisesRegex(ValueError, 'REQ-001'):
            self.export([self.row(), self.row('탈퇴')], strict=True)
        for value in ('[미확정] 대상', '권한명 101자 [가정:100]', '[미확정:담당자 확인]'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, '미확정'):
                self.export([self.row(value)], strict=True)
        self.export([self.row('[미확정] 대상')], strict=True, draft=True)

    def test_strict_rejects_missing_duplicate_headers_and_malformed_rows(self):
        for headers, row in [(self.headers[:-1], self.row()[:-1]),
                             (self.headers + ['요구사항ID'], self.row() + ['REQ-999']),
                             (self.headers, self.row()[:-2])]:
            with self.subTest(headers=headers), self.assertRaises(ValueError):
                self.mod.create_xlsx([('B-요구사항정의서.md', [('본문', self.table(headers, [row]))])],
                                     str(self.root / 'bad.xlsx'), strict=True)

    def test_strict_allows_repeated_requirement_ids_in_matrix(self):
        h = self.mod.DOCUMENT_PROFILES['추적매트릭스']['columns'][0]
        rows = [['REQ-001', '등록', '유지', 'FN-001', '등록', '', '1', '0/0', '미수행'],
                ['REQ-001', '등록', '유지', 'FN-002', '조회', '', '1', '0/0', '미수행']]
        self.mod.create_xlsx([('B-추적매트릭스.md', [('본문', self.table(h, rows))])],
                             str(self.root / 'matrix.xlsx'), strict=True)

    def test_missing_test_result_column_is_rejected(self):
        h = self.mod.DOCUMENT_PROFILES['단위테스트계획서']['columns'][0][:-1]
        row = ['UT-001', 'FN-001', 'REQ-001', '등록', '', '이름=홍길동', '등록된다', '', '', '', '']
        with self.assertRaisesRegex(ValueError, '결과'):
            self.mod.create_xlsx([('B-단위테스트계획서.md', [('본문', self.table(h, [row]))])],
                                 str(self.root / 'plan.xlsx'), strict=True)

    def test_strict_cli_rejects_draft_and_stale_review_state_without_tags(self):
        source = self.root / 'B-요구사항정의서.md'
        body = '\n'.join(self.table(self.headers, [self.row()]))
        args = ['export-xlsx.py', '--strict', '--separate', str(source)]
        source.write_text('> 검토상태: 초안 · 미결 1건\n' + body, encoding='utf-8')
        with patch('sys.argv', args), self.assertRaisesRegex(ValueError, '검토'):
            self.mod.main()
        source.write_text(body, encoding='utf-8')
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        state_path = self.root / 'requirements-state.json'
        for record in [{'status': '확정', 'openCQ': ['CQ-001']},
                       {'status': '확정', 'upstreamChanges': ['REQ-001']},
                       {'status': '확정', 'contentHash': 'stale'}]:
            state_path.write_text(json.dumps({'schemaVersion': 1, 'documents': {'AN-02': record}}), encoding='utf-8')
            with self.subTest(record=record), patch('sys.argv', args), self.assertRaises(ValueError):
                self.mod.main()
            self.assertFalse(source.with_suffix('.xlsx').exists())
        state_path.write_text(json.dumps({'schemaVersion': 1, 'documents': {
            'AN-02': {'status': '확정', 'contentHash': digest, 'openCQ': [], 'upstreamChanges': []}
        }}), encoding='utf-8')
        with patch('sys.argv', args):
            self.mod.main()
        self.assertTrue(source.with_suffix('.xlsx').exists())

    def test_failed_workbook_write_preserves_previous_file(self):
        target = self.export([self.row()])
        before = target.read_bytes()
        with patch.object(openpyxl.Workbook, 'save', side_effect=OSError('disk write failed')):
            with self.assertRaises(OSError):
                self.export([self.row('수정 내용')])
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['result.xlsx'])

    def test_answered_confirmation_requires_matching_baseline(self):
        profile = self.mod.DOCUMENT_PROFILES['확인요청서']
        h = profile['columns'][1]
        row = ['CQ-001', 'AN-02', '1', 'REQ-001 대상', '일반회원', '원문 미정', '', '', '']
        tables = [('가정 확인', self.table(h, [row]))]
        target = self.root / 'B-확인요청서.xlsx'
        self.mod.create_xlsx([('B-확인요청서.md', tables)], str(target))
        wb = openpyxl.load_workbook(target)
        wb['가정 확인']['G2'] = '수정'
        wb['가정 확인']['H2'] = '관리자'
        wb.save(target)
        wb.close()
        original = target.read_bytes()
        with self.assertRaisesRegex(ValueError, 'CQ-001|응답'):
            self.mod.create_xlsx([('B-확인요청서.md', tables)], str(target))
        self.assertEqual(target.read_bytes(), original)
        with self.assertRaisesRegex(ValueError, '기준|지문|hash|해시'):
            self.mod.create_xlsx([('B-확인요청서.md', tables)], str(target),
                                 confirmation_base_hash='wrong')
        digest = hashlib.sha256(original).hexdigest()
        self.mod.create_xlsx([('B-확인요청서.md', tables)], str(target), confirmation_base_hash=digest)


class InputFingerprintTests(unittest.TestCase):
    def test_preserves_literal_input_spaces(self):
        mod = load_util('test-evidence.py')
        before = {'입력': '이름="홍 길동"', '기대결과': '원문 저장'}
        after = {**before, '입력': '이름="홍  길동"'}
        self.assertNotEqual(mod.fingerprint(before), mod.fingerprint(after))
        self.assertEqual(mod.fingerprint(before), mod.fingerprint({**before, '입력': '  이름="홍 길동"  '}))


if __name__ == '__main__':
    unittest.main()
