import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core import database


class DemoCandidateSeedTests(unittest.TestCase):
    def test_initialization_creates_demo_accounts_and_distinct_oracle_skills(self) -> None:
        seed = json.loads(database.SEED_FILE.read_text())
        demo_candidates = seed["demo_candidates"]
        priya = next(candidate for candidate in demo_candidates if candidate["username"] == "priyamenon")
        rohan = next(candidate for candidate in demo_candidates if candidate["username"] == "rohanverma")
        primary_candidate = seed["candidate"]

        self.assertEqual(len(demo_candidates), 3)
        self.assertEqual(primary_candidate["name"], "Ananya Rao")
        self.assertIn("Distributed Systems", primary_candidate["profile"]["skills"])
        self.assertTrue(set(priya["profile"]["skills"]).issubset(seed["skills"]))
        self.assertTrue(set(rohan["profile"]["skills"]).issubset(seed["skills"]))
        self.assertFalse(set(priya["profile"]["skills"]) & set(rohan["profile"]["skills"]))

        with tempfile.TemporaryDirectory() as temp_dir:
            test_database = Path(temp_dir) / "seed-test.db"
            with patch.object(database, "DATABASE", test_database):
                database.initialize_database()
                with database.database() as db:
                    users = {
                        row["username"]: row["name"]
                        for row in db.execute("SELECT username, name FROM users")
                    }

        self.assertEqual(len(users), 4)
        self.assertEqual(users["ananyarao"], "Ananya Rao")
        self.assertEqual(users["karthiksubramaniam"], "Karthik Subramaniam")
        self.assertEqual(users["priyamenon"], "Priya Menon")
        self.assertEqual(users["rohanverma"], "Rohan Verma")


if __name__ == "__main__":
    unittest.main()
