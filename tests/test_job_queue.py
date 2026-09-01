import json
import tempfile
import unittest
from pathlib import Path

from genesis.job_queue import JobStore


class JobQueueTests(unittest.TestCase):
    def test_generation_job_lifecycle_uses_isolated_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "genesis-test.db"
            store = JobStore(database)
            job_id = store.create(
                "Image generation",
                detail="Preparing workflow",
                workflow="neutral-workflow.json",
            )
            store.update(job_id, status="running", progress=44.5, detail="Working")
            store.update(
                job_id,
                status="completed",
                progress=100,
                outputs=[Path(directory) / "neutral-output.png"],
            )

            job = store.recent(1)[0]
            self.assertEqual(job["status"], "completed")
            self.assertEqual(job["progress"], 100)
            self.assertEqual(job["workflow"], "neutral-workflow.json")
            self.assertEqual(len(json.loads(job["outputs"])), 1)

    def test_job_updates_validate_status_and_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            store = JobStore(Path(directory) / "genesis-test.db")
            job_id = store.create("Neutral operation")
            store.update(job_id, progress=150)
            self.assertEqual(store.recent(1)[0]["progress"], 100)
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                store.update(job_id, status="interrupting")


if __name__ == "__main__":
    unittest.main()
