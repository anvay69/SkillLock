import unittest

from app.features.job_matching.service import analyze_job_requirements


class JobMatchingScoreTests(unittest.TestCase):
    def test_required_skills_are_weighted_twice_as_much_as_preferred(self) -> None:
        result = analyze_job_requirements(
            ["Python", "FastAPI"],
            ["Docker"],
            ["Python", "Docker"],
            ["Python", "FastAPI", "Docker"],
        )

        self.assertEqual(result["match_score"], 60)

    def test_score_is_unavailable_without_recognized_job_skills(self) -> None:
        result = analyze_job_requirements([], [], ["Python"], ["Python"])

        self.assertIsNone(result["match_score"])


if __name__ == "__main__":
    unittest.main()
