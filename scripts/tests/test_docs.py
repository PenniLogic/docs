import importlib.util
from pathlib import Path
import unittest


path = Path(__file__).resolve().parents[1] / "check_docs.py"
spec = importlib.util.spec_from_file_location("check_docs", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BacklogTests(unittest.TestCase):
    def item(self):
        return {
            "legacy_id": "source-1", "title": "Example task",
            "source_url": "https://github.com/PenniLogic-old/docs/issues/1",
            "legacy_status": "Backlog",
        }

    def test_valid_preserved_task(self):
        module.validate_backlog({"schema_version": 1, "item_count": 1, "items": [self.item()]})

    def test_duplicate_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            module.validate_backlog({"schema_version": 1, "item_count": 2, "items": [self.item(), self.item()]})

    def test_wrong_count_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "count"):
            module.validate_backlog({"schema_version": 1, "item_count": 0, "items": [self.item()]})

    def test_missing_provenance_is_rejected(self):
        item = self.item()
        item["source_url"] = "https://example.com"
        with self.assertRaisesRegex(ValueError, "provenance"):
            module.validate_backlog({"schema_version": 1, "item_count": 1, "items": [item]})

    def test_unknown_status_is_rejected(self):
        item = self.item()
        item["legacy_status"] = "Released without evidence"
        with self.assertRaisesRegex(ValueError, "status"):
            module.validate_backlog({"schema_version": 1, "item_count": 1, "items": [item]})


if __name__ == "__main__":
    unittest.main()
