"""Tests for the Linear roadmap synchronization tool."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from tools import linear_sync


SAMPLE_ROADMAP = """\
# Roadmap

## 1. Audit

- Objectives: Inspect the repository.
- Success criteria: Risks are recorded.
- Estimated effort: S
- Status: ✅ done

## Notes

Not a stage.

## 2. Port Logic

- Objectives: Port useful logic.
- Success criteria: Logic runs locally.
- Estimated effort: M
"""


class LinearSyncTests(unittest.TestCase):
    """Exercise roadmap parsing, mapping, idempotency, and HTTP handling."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.tmp_path = Path(self.temporary_directory.name)

    def test_parse_roadmap_with_sample_markdown(self) -> None:
        stages = linear_sync.parse_roadmap(SAMPLE_ROADMAP)

        self.assertEqual(len(stages), 2)
        self.assertEqual(
            stages[0],
            linear_sync.Stage(
                number=1,
                name="Audit",
                objective="Inspect the repository.",
                success_criteria="Risks are recorded.",
                estimated_effort="S",
                status="✅ done",
            ),
        )
        self.assertEqual(stages[1].status, "Not started")

    def test_build_issue_payload_returns_correct_structure(self) -> None:
        stage = linear_sync.parse_roadmap(SAMPLE_ROADMAP)[0]

        payload = linear_sync.build_issue_payload(stage)

        self.assertEqual(payload["externalId"], "pulse-of-earth-stage-1")
        self.assertEqual(payload["title"], "Stage 1: Audit")
        self.assertEqual(payload["state"], "Done")
        self.assertEqual(payload["priority"], 4)
        self.assertEqual(payload["labels"], ["discovery"])
        self.assertEqual(payload["initiative"], "Discovery")
        self.assertIn(
            "## Objective\n\nInspect the repository.", payload["description"]
        )
        self.assertIn(
            "pulse-of-earth-external-id: pulse-of-earth-stage-1",
            payload["description"],
        )

    def test_search_find_existing_updates_instead_of_creating(self) -> None:
        roadmap = self.tmp_path / "ROADMAP.md"
        roadmap.write_text(SAMPLE_ROADMAP.split("## Notes")[0], encoding="utf-8")
        existing = {"id": "issue-id", "identifier": "ENG-1", "title": "old"}
        updated = {"id": "issue-id", "identifier": "ENG-1", "title": "new"}

        with (
            mock.patch.object(
                linear_sync, "search_existing_issue", return_value=existing
            ) as search,
            mock.patch.object(linear_sync, "create_issue") as create,
            mock.patch.object(
                linear_sync, "update_issue", return_value=updated
            ) as update,
        ):
            result = linear_sync.sync(
                roadmap,
                api_key="test-key",
                project_id="project-id",
                state_file=self.tmp_path / "state.json",
            )

        search.assert_called_once_with("pulse-of-earth-stage-1")
        create.assert_not_called()
        update.assert_called_once()
        self.assertEqual(result["actions"][0]["action"], "updated")

    def test_dry_run_makes_no_http_calls(self) -> None:
        roadmap = self.tmp_path / "ROADMAP.md"
        roadmap.write_text(SAMPLE_ROADMAP, encoding="utf-8")

        with mock.patch.object(
            linear_sync.urllib.request, "urlopen"
        ) as urlopen:
            result = linear_sync.sync(roadmap, dry_run=True)

        urlopen.assert_not_called()
        self.assertTrue(result["dry_run"])
        self.assertEqual(len(result["actions"]), 2)
        self.assertFalse((self.tmp_path / ".linear-sync-state.json").exists())

    def test_state_file_read_write(self) -> None:
        path = self.tmp_path / "nested" / "state.json"
        state = {
            "4": {
                "issue_id": "uuid",
                "issue_identifier": "ENG-4",
                "last_sync_hash": "abc",
            }
        }

        linear_sync.save_state(path, state)

        self.assertEqual(linear_sync.load_state(path), state)
        self.assertEqual(
            json.loads(path.read_text(encoding="utf-8")), state
        )

    def test_missing_api_key_is_an_error_before_http(self) -> None:
        roadmap = self.tmp_path / "ROADMAP.md"
        roadmap.write_text(SAMPLE_ROADMAP, encoding="utf-8")

        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(
                linear_sync.urllib.request, "urlopen"
            ) as urlopen,
        ):
            with self.assertRaisesRegex(
                linear_sync.LinearSyncError, "LINEAR_API_KEY"
            ):
                linear_sync.sync(roadmap, project_id="project-id")

        urlopen.assert_not_called()

    def test_http_401_is_reported_without_retry(self) -> None:
        linear_sync._runtime.api_key = "secret"
        linear_sync._runtime.last_request_at = None
        error = urllib.error.HTTPError(
            linear_sync.LINEAR_API_URL,
            401,
            "Unauthorized",
            {},
            io.BytesIO(b""),
        )

        with mock.patch.object(
            linear_sync.urllib.request, "urlopen", side_effect=error
        ) as urlopen:
            with self.assertRaisesRegex(
                linear_sync.LinearSyncError, "authorization"
            ):
                linear_sync._request("query Test { viewer { id } }", {})

        urlopen.assert_called_once()

    def test_search_existing_issue_with_mocked_http_response(self) -> None:
        response = {
            "data": {
                "issueSearch": {
                    "nodes": [
                        {
                            "id": "issue-id",
                            "identifier": "ENG-4",
                            "title": "Stage 4: Hermes-Linear",
                            "description": (
                                "<!-- pulse-of-earth-external-id: "
                                "pulse-of-earth-stage-4 -->"
                            ),
                            "project": {"id": "project-id"},
                        }
                    ]
                },
                "project": {
                    "id": "project-id",
                    "teams": {
                        "nodes": [
                            {
                                "id": "team-id",
                                "states": {
                                    "nodes": [
                                        {"id": "todo-id", "name": "Todo"},
                                        {"id": "done-id", "name": "Done"},
                                    ]
                                },
                                "labels": {
                                    "nodes": [
                                        {
                                            "id": "architecture-id",
                                            "name": "architecture",
                                        }
                                    ]
                                },
                            }
                        ]
                    },
                    "initiatives": {"nodes": []},
                },
            }
        }
        encoded = json.dumps(response).encode("utf-8")
        http_response = mock.MagicMock()
        http_response.read.return_value = encoded
        http_response.__enter__.return_value = http_response
        linear_sync._runtime.api_key = "test-key"
        linear_sync._runtime.project_id = "project-id"
        linear_sync._runtime.last_request_at = None

        with mock.patch.object(
            linear_sync.urllib.request,
            "urlopen",
            return_value=http_response,
        ):
            issue = linear_sync.search_existing_issue(
                "pulse-of-earth-stage-4"
            )

        self.assertEqual(
            issue,
            {
                "id": "issue-id",
                "identifier": "ENG-4",
                "title": "Stage 4: Hermes-Linear",
            },
        )
        self.assertEqual(linear_sync._runtime.team_id, "team-id")


if __name__ == "__main__":
    unittest.main()
