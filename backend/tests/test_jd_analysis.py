import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.features.job_matching.gemini import (
    GeminiJobRequirements,
    JobDescriptionMismatchError,
)
from app.features.job_matching.listing import LinkedInFetchError
from app.main import app
from app.models.user import User


class JDAnalysisApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.user = User(
            id=1,
            name="Alex Candidate",
            username="alexcandidate",
            email="alex@example.com",
            password_hash="not-used",
            profile={"skills": ["Python"]},
        )

    def _extracted(self) -> GeminiJobRequirements:
        return GeminiJobRequirements(
            job_title="Backend Developer",
            company="Example Co",
            job_summary="Build and maintain API services.",
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Docker"],
            suggestions=["Build an API portfolio project.", "Prepare a service-debugging example."],
        )

    def test_analyzes_pasted_description_without_profile_matching(self) -> None:
        with (
            patch("app.features.jd_analysis.routes.get_session_user", return_value=self.user),
            patch("app.features.jd_analysis.routes.list_skills", return_value=["Python", "FastAPI"]),
            patch(
                "app.features.jd_analysis.routes.extract_job_requirements",
                return_value=self._extracted(),
            ) as extract,
        ):
            response = self.client.post(
                "/api/jd-analysis/analyze",
                json={"job_description": "Backend role using Python and FastAPI."},
            )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["source"], "pasted_description")
        self.assertEqual(body["required_skills"], ["Python", "FastAPI"])
        self.assertEqual(body["preferred_skills"], ["Docker"])
        self.assertEqual(len(body["suggestions"]), 2)
        self.assertNotIn("matched_skills", body)
        self.assertNotIn("readiness_feedback", body)
        self.assertEqual(extract.call_args.args[0], "")
        self.assertEqual(extract.call_args.args[2], "Backend role using Python and FastAPI.")

    def test_analyzes_linkedin_post_using_shared_scraper(self) -> None:
        listing = {
            "job_title": "Backend Developer",
            "company": "Example Co",
            "page_text": "Backend Developer at Example Co: Python and FastAPI.",
        }
        with (
            patch("app.features.jd_analysis.routes.get_session_user", return_value=self.user),
            patch("app.features.jd_analysis.routes.list_skills", return_value=["Python", "FastAPI"]),
            patch("app.features.jd_analysis.routes.fetch_linkedin_job", return_value=listing) as fetch,
            patch(
                "app.features.jd_analysis.routes.extract_job_requirements",
                return_value=self._extracted(),
            ) as extract,
        ):
            response = self.client.post(
                "/api/jd-analysis/analyze",
                json={"linkedin_url": "https://www.linkedin.com/posts/example_job-123"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["source"], "linkedin_listing")
        fetch.assert_called_once_with("https://www.linkedin.com/posts/example_job-123")
        self.assertEqual(extract.call_args.args[0], listing["page_text"])

    def test_combines_description_and_listing_and_surfaces_mismatch(self) -> None:
        listing = {
            "job_title": "Backend Developer",
            "company": "Example Co",
            "page_text": "Backend Developer at Example Co: Python and FastAPI.",
        }
        payload = {
            "linkedin_url": "https://www.linkedin.com/jobs/view/123",
            "job_description": "Python and FastAPI backend opening.",
        }
        with (
            patch("app.features.jd_analysis.routes.get_session_user", return_value=self.user),
            patch("app.features.jd_analysis.routes.list_skills", return_value=["Python", "FastAPI"]),
            patch("app.features.jd_analysis.routes.fetch_linkedin_job", return_value=listing),
            patch(
                "app.features.jd_analysis.routes.extract_job_requirements",
                return_value=self._extracted(),
            ) as extract,
        ):
            response = self.client.post("/api/jd-analysis/analyze", json=payload)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["source"], "linkedin_listing_and_description")
        self.assertEqual(extract.call_args.args[0], listing["page_text"])
        self.assertEqual(extract.call_args.args[2], payload["job_description"])

        with (
            patch("app.features.jd_analysis.routes.get_session_user", return_value=self.user),
            patch("app.features.jd_analysis.routes.list_skills", return_value=["Python"]),
            patch("app.features.jd_analysis.routes.fetch_linkedin_job", return_value=listing),
            patch(
                "app.features.jd_analysis.routes.extract_job_requirements",
                side_effect=JobDescriptionMismatchError(
                    "The job description and LinkedIn job do not match."
                ),
            ),
        ):
            mismatch = self.client.post("/api/jd-analysis/analyze", json=payload)
        self.assertEqual(mismatch.status_code, 422, mismatch.text)
        self.assertIn("do not match", mismatch.json()["detail"])

    def test_uses_description_if_linkedin_page_is_unavailable(self) -> None:
        with (
            patch("app.features.jd_analysis.routes.get_session_user", return_value=self.user),
            patch("app.features.jd_analysis.routes.list_skills", return_value=["Python"]),
            patch(
                "app.features.jd_analysis.routes.fetch_linkedin_job",
                side_effect=LinkedInFetchError("The listing is not public."),
            ),
            patch(
                "app.features.jd_analysis.routes.extract_job_requirements",
                return_value=self._extracted(),
            ) as extract,
        ):
            response = self.client.post(
                "/api/jd-analysis/analyze",
                json={
                    "linkedin_url": "https://www.linkedin.com/jobs/view/123",
                    "job_description": "Python backend role.",
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["source"], "pasted_description")
        self.assertIn("not public", response.json()["source_warning"])
        self.assertEqual(extract.call_args.args[0], "")

    def test_requires_at_least_one_input_and_authentication(self) -> None:
        unauthenticated = self.client.post(
            "/api/jd-analysis/analyze",
            json={"job_description": "Backend role using Python."},
        )
        self.assertEqual(unauthenticated.status_code, 401)

        with patch("app.features.jd_analysis.routes.get_session_user", return_value=self.user):
            missing_input = self.client.post("/api/jd-analysis/analyze", json={})
        self.assertEqual(missing_input.status_code, 422)


if __name__ == "__main__":
    unittest.main()
