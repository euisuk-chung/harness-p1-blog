"""승인 근거 시험. 임시 사본에서 규칙만 실행하고 git push·gh는 가짜로 바꾼다.

    uv run python tests/test_approval_evidence.py

실제 GitHub PR·모델·발행·사람의 승인 판단은 이 시험의 범위 밖이다.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import approval_evidence as evidence
import render
import request_approval

SRC = Path(__file__).resolve().parents[1]


class ApprovalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-approval-evidence-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "blog"
        shutil.copytree(SRC, self.root, ignore=shutil.ignore_patterns("requests", "drafts", "logs", "__pycache__", ".git"))
        self.rid = "evidence-test"
        self.d = self.root / "requests" / self.rid
        self.d.mkdir(parents=True)
        (self.d / "state.json").write_text(json.dumps({"case": "case-01-standard"}), encoding="utf-8")
        shutil.copy2(self.root / "samples/reference/case-01-standard.json", self.d / "draft.json")
        self.original_review = b'{"old_review": "must stay unchanged"}\n'
        (self.d / "review.json").write_bytes(self.original_review)
        with patch.object(render, "ROOT", self.root):
            self.out = render.render(self.rid)

    def test_fresh_checks_bound_to_files_and_original_review_unchanged(self):
        card = evidence.build(self.root, self.rid, self.out)
        self.assertEqual(card["exit"], 0)
        self.assertTrue(card["observed"].startswith("일치:"))
        self.assertEqual(set(card["checks"]), set(evidence.GUARDS))
        self.assertEqual(card["artifact_sha256"], hashlib.sha256(self.out.read_bytes()).hexdigest())
        self.assertEqual(card["input_sha256"], hashlib.sha256((self.d / "draft.json").read_bytes()).hexdigest())
        self.assertTrue(card["files_unchanged"])
        self.assertTrue(card["snapshot_matches_inputs"])
        self.assertTrue(card["render_matches_artifact"])
        self.assertEqual((self.d / "review.json").read_bytes(), self.original_review)
        self.assertTrue(any("실제 발행" in x for x in card["limits"]))

    def test_rejected_draft_does_not_inherit_old_pass(self):
        draft = json.loads((self.d / "draft.json").read_text())
        draft["claims"][0]["quote"] = "원문에 없는 인용"
        (self.d / "draft.json").write_text(json.dumps(draft), encoding="utf-8")
        with patch.object(render, "ROOT", self.root):
            render.render(self.rid)
        card = evidence.build(self.root, self.rid, self.out)
        self.assertEqual(card["exit"], 1)
        self.assertFalse(card["checks"]["G3"]["pass"])
        self.assertTrue(card["observed"].startswith("불일치:"))

    def test_missing_source_is_unverified(self):
        (self.root / "cases/sources/week-01/model-acme-lumen-3.card.md").unlink()
        card = evidence.build(self.root, self.rid, self.out)
        self.assertTrue(card["observed"].startswith("미확인"))
        self.assertEqual(card["checks"], {})

    def test_broken_draft_is_unverified_and_preserves_review(self):
        (self.d / "draft.json").write_text("{", encoding="utf-8")
        card = evidence.build(self.root, self.rid, self.out)
        self.assertEqual(card["exit"], 2)
        self.assertTrue(card["observed"].startswith("미확인"))
        self.assertEqual((self.d / "review.json").read_bytes(), self.original_review)

    def test_unrelated_article_is_not_bound_to_passing_checks(self):
        self.out.write_text("UNRELATED STALE OUTPUT", encoding="utf-8")
        card = evidence.build(self.root, self.rid, self.out)
        self.assertEqual(card["exit"], 0)
        self.assertFalse(card["render_matches_artifact"])
        self.assertTrue(card["observed"].startswith("미확인:"))

    def test_copied_bytes_must_match_hashed_input(self):
        real_copy = shutil.copy2

        def changed_copy(source, target):
            result = real_copy(source, target)
            if source == self.d / "draft.json":
                with Path(target).open("a") as f:
                    f.write(" ")
            return result

        with patch.object(evidence.shutil, "copy2", side_effect=changed_copy):
            card = evidence.build(self.root, self.rid, self.out)
        self.assertEqual(card["exit"], 0)
        self.assertFalse(card["snapshot_matches_inputs"])
        self.assertTrue(card["observed"].startswith("미확인:"))

    def test_malformed_case_is_unverified(self):
        (self.root / "cases/case-01-standard.yaml").write_text("sources: [", encoding="utf-8")
        card = evidence.build(self.root, self.rid, self.out)
        self.assertEqual(card["observed"], "미확인")
        self.assertTrue(any("완성하지 못했다" in x for x in card["limits"]))

    def test_code_revision_and_dirty_working_file_are_separate(self):
        def git(*args):
            return subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True, check=True)

        git("init", "-b", "main")
        git("add", "--", "review.py")
        git("-c", "user.name=hackers-kit", "-c", "user.email=offline-test",
            "commit", "-m", "isolated test fixture")
        revision = git("rev-parse", "HEAD").stdout.strip()
        with (self.root / "review.py").open("a") as f:
            f.write("\n# changed working copy\n")
        card = evidence.build(self.root, self.rid, self.out)
        self.assertEqual(card["code_revision"], revision)
        self.assertTrue(card["code_worktree_changed"])
        self.assertEqual(card["files"]["review.py"], evidence.digest(self.root / "review.py"))
        self.assertEqual(card["exit"], 0)

    def test_changed_input_during_check_is_unverified(self):
        real_run = subprocess.run

        def change(*args, **kwargs):
            result = real_run(*args, **kwargs)
            if args[0][1:2] == ["review.py"]:
                with (self.d / "draft.json").open("a") as f:
                    f.write(" ")
            return result

        with patch.object(evidence.subprocess, "run", side_effect=change):
            card = evidence.build(self.root, self.rid, self.out)
        self.assertFalse(card["files_unchanged"])
        self.assertTrue(card["observed"].startswith("미확인:"))

    def test_local_approval_keeps_wait_signal_and_writes_card(self):
        with patch.object(request_approval, "ROOT", self.root), patch.object(render, "ROOT", self.root), \
                patch.object(sys, "argv", ["request_approval.py", self.rid]), patch.dict(os.environ, {"HACKERS_PR": "0"}):
            self.assertEqual(request_approval.main(), 3)
        self.assertIn("G1", (self.d / "approval-evidence.md").read_text(encoding="utf-8"))
        self.assertEqual(json.loads((self.d / "approval-evidence.json").read_text())["exit"], 0)

    def test_mock_pr_body_contains_evidence_and_original_gate(self):
        calls = []
        real_run = subprocess.run

        def fake_git(*args):
            output = "main\n" if "--abbrev-ref" in args else str(self.root) if "--show-toplevel" in args else ""
            return subprocess.CompletedProcess(args, 0, output, "")

        def fake_gh(*args, **kwargs):
            if args[0][:3] == ["gh", "pr", "create"]:
                calls.append(args[0])
                return subprocess.CompletedProcess(args[0], 0, "https://example.invalid/mock-pr\n", "")
            return real_run(*args, **kwargs)

        with patch.object(request_approval, "ROOT", self.root), patch.object(render, "ROOT", self.root), \
                patch.object(request_approval, "git", side_effect=fake_git), \
                patch.object(request_approval.subprocess, "run", side_effect=fake_gh), \
                patch.object(request_approval.signal, "signal"), \
                patch.object(sys, "argv", ["request_approval.py", self.rid]), patch.dict(os.environ, {"HACKERS_PR": "1"}):
            self.assertEqual(request_approval.main(), 3)
        self.assertEqual(len(calls), 1)
        body = calls[0][calls[0].index("--body") + 1]
        for text in ("합치면 발행을 승인", "SHA-256", "G1", "기대:", "관찰:", "확인하지 못한 것"):
            self.assertIn(text, body)


if __name__ == "__main__":
    unittest.main()
