import json
import unittest
from io import BytesIO
from unittest.mock import patch

from app.features.job_matching import gemini


class FakeResponse(BytesIO):
    pass


class GeminiJobExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.response_json = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "job_title": "Backend Developer",
                                        "company": "Example Co",
                                        "job_summary": "Build and maintain API services.",
                                        "required_skills": ["Python", "FastAPI"],
                                        "preferred_skills": ["Docker"],
                                        "suggestions": [
                                            "Build a small API portfolio project.",
                                            "Prepare examples of debugging services.",
                                        ],
                                        "sources_match": True,
                                        "mismatch_reason": "",
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        }

    def test_sends_listing_text_for_structured_extraction(self) -> None:
        response = FakeResponse(json.dumps(self.response_json).encode())
        with (
            patch.object(gemini, "GEMINI_API_KEY", "test-secret"),
            patch.object(gemini, "GEMINI_MODEL", "gemini-2.5-flash"),
            patch.object(gemini, "urlopen", return_value=response) as urlopen,
        ):
            result = gemini.extract_job_requirements(
                "The scraped LinkedIn job page text.",
                ["Python", "FastAPI", "Docker"],
            )

        request = urlopen.call_args.args[0]
        payload = json.loads(request.data)
        prompt = payload["contents"][0]["parts"][0]["text"]
        self.assertIn("The scraped LinkedIn job page text.", prompt)
        self.assertIn('"Python"', prompt)
        self.assertEqual(payload["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(request.get_header("X-goog-api-key"), "test-secret")
        self.assertNotIn("test-secret", request.full_url)
        self.assertEqual(result.required_skills, ["Python", "FastAPI"])
        self.assertEqual(result.preferred_skills, ["Docker"])
        self.assertEqual(len(result.suggestions), 2)
        self.assertEqual(result.company, "Example Co")

    def test_sends_both_sources_and_combines_them_as_one_job(self) -> None:
        response = FakeResponse(json.dumps(self.response_json).encode())
        with (
            patch.object(gemini, "GEMINI_API_KEY", "test-secret"),
            patch.object(gemini, "GEMINI_MODEL", "gemini-2.5-flash"),
            patch.object(gemini, "urlopen", return_value=response) as urlopen,
        ):
            result = gemini.extract_job_requirements(
                "Scraped public listing text for Example Co.",
                ["Python", "FastAPI", "Docker"],
                "The pasted description adds Docker experience.",
            )

        payload = json.loads(urlopen.call_args.args[0].data)
        prompt = payload["contents"][0]["parts"][0]["text"]
        self.assertIn("Scraped public listing text for Example Co.", prompt)
        self.assertIn("The pasted description adds Docker experience.", prompt)
        self.assertIn("Merge complementary details", prompt)
        self.assertIn("even a few", prompt)
        self.assertIn("meaningful job-related overlap", prompt)
        self.assertTrue(result.sources_match)
        self.assertEqual(result.required_skills, ["Python", "FastAPI"])
        self.assertTrue(result.suggestions)

    def test_partial_job_term_overlap_is_considered_a_match(self) -> None:
        partial_overlap_response = json.loads(json.dumps(self.response_json))
        partial_overlap_response["candidates"][0]["content"]["parts"][0]["text"] = json.dumps(
            {
                **json.loads(
                    partial_overlap_response["candidates"][0]["content"]["parts"][0]["text"]
                ),
                "sources_match": True,
            }
        )
        response = FakeResponse(json.dumps(partial_overlap_response).encode())
        with (
            patch.object(gemini, "GEMINI_API_KEY", "test-secret"),
            patch.object(gemini, "GEMINI_MODEL", "gemini-2.5-flash"),
            patch.object(gemini, "urlopen", return_value=response),
        ):
            result = gemini.extract_job_requirements(
                "Frontend role requiring React, JavaScript, and building web interfaces.",
                ["React", "JavaScript"],
                "Frontend developer opportunity involving React and user-facing products.",
            )

        self.assertTrue(result.sources_match)

    def test_rejects_job_description_that_gemini_says_does_not_match(self) -> None:
        mismatch_response = json.loads(json.dumps(self.response_json))
        mismatch = json.loads(
            mismatch_response["candidates"][0]["content"]["parts"][0]["text"]
        )
        mismatch["sources_match"] = False
        mismatch["mismatch_reason"] = "The pasted text describes a different role."
        mismatch_response["candidates"][0]["content"]["parts"][0]["text"] = json.dumps(mismatch)
        response = FakeResponse(json.dumps(mismatch_response).encode())
        with (
            patch.object(gemini, "GEMINI_API_KEY", "test-secret"),
            patch.object(gemini, "GEMINI_MODEL", "gemini-2.5-flash"),
            patch.object(gemini, "urlopen", return_value=response),
            self.assertRaisesRegex(
                gemini.JobDescriptionMismatchError,
                "job description and LinkedIn job do not match",
            ),
        ):
            gemini.extract_job_requirements(
                "Listing for a Backend Developer at Example Co.",
                ["Python"],
                "Description for a Social Media Manager at Another Co.",
            )

    def test_requires_api_key_without_making_a_request(self) -> None:
        with (
            patch.object(gemini, "GEMINI_API_KEY", ""),
            patch.object(gemini, "urlopen") as urlopen,
            self.assertRaisesRegex(gemini.GeminiConfigurationError, "GEMINI_API_KEY"),
        ):
            gemini.extract_job_requirements("public job page text", ["Python"])
        urlopen.assert_not_called()

    def test_requires_a_source_without_making_a_request(self) -> None:
        with (
            patch.object(gemini, "GEMINI_API_KEY", "test-secret"),
            patch.object(gemini, "GEMINI_MODEL", "gemini-2.5-flash"),
            patch.object(gemini, "urlopen") as urlopen,
            self.assertRaisesRegex(ValueError, "Provide a job description"),
        ):
            gemini.extract_job_requirements("", ["Python"], "  ")
        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
