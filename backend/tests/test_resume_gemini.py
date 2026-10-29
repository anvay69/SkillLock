import json
import unittest
from io import BytesIO
from unittest.mock import patch

from app.features.resume import gemini, service
from app.schemas.profile import (
    Certification,
    Education,
    Experience,
    ExtractedProfile,
    ProfileData,
    Project,
)


class FakeResponse(BytesIO):
    pass


class ResumeGeminiExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.response_json = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "skills": ["Python", "FastAPI"],
                                        "projects": [
                                            {
                                                "title": "Inventory Tool",
                                                "description": "A warehouse inventory app.",
                                                "tech_stack": "Python, FastAPI",
                                                "repository_url": "",
                                                "live_url": "",
                                            }
                                        ],
                                        "experience": [
                                            {
                                                "job_title": "Backend Developer",
                                                "company": "Example Studio",
                                                "description": "Built API services.",
                                                "start_date": "2022-01",
                                                "end_date": "",
                                            }
                                        ],
                                        "education": [
                                            {
                                                "institution": "City College",
                                                "degree": "BSc",
                                                "field_of_study": "Computer Science",
                                                "graduation_year": "2022",
                                                "grade": "",
                                            }
                                        ],
                                        "certifications": [
                                            {
                                                "name": "Cloud Developer Certificate",
                                                "issuing_organization": "Example Org",
                                                "credential_url": "",
                                            }
                                        ],
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        }

    def _profile(self) -> ProfileData:
        return ProfileData(
            name="Alex Candidate",
            username="alexcandidate",
            email="alex.candidate@example.com",
            bio="Personal biography must not leave the app.",
            github_url="https://github.com/alexcandidate",
            linkedin_url="https://linkedin.com/in/alexcandidate",
            skills=["Python"],
            projects=[
                Project(
                    title="Existing Project",
                    description="Contact Alex Candidate at 555-123-4567.",
                    tech_stack="Python",
                    repository_url="https://github.com/private/repository",
                )
            ],
            experience=[
                Experience(
                    job_title="Software Engineer",
                    company="Current Employer",
                    description="Email alex.candidate@example.com for details.",
                )
            ],
            education=[Education(institution="State University", degree="BSc")],
            certifications=[
                Certification(name="Existing Certificate", credential_url="https://example.com/credential")
            ],
        )

    def test_sends_professional_sections_only_and_returns_combined_profile(self) -> None:
        response = FakeResponse(json.dumps(self.response_json).encode())
        profile = self._profile()
        sections = {
            "skills": [
                "Python, React",
                "Email alex.candidate@example.com",
                "Work location: 15 Main Street",
            ],
            "personal_info": ["Private address must not be sent."],
            "projects": ["Inventory Tool: A warehouse inventory app."],
            "experience": ["Backend Developer at Example Studio"],
            "education": ["BSc Computer Science at City College"],
            "certifications": ["Cloud Developer Certificate"],
        }
        with (
            patch.object(gemini, "GEMINI_API_KEY", "test-secret"),
            patch.object(gemini, "GEMINI_MODEL", "gemini-2.5-flash"),
            patch.object(gemini, "urlopen", return_value=response) as urlopen,
        ):
            result = gemini.extract_resume_profile(sections, profile)

        payload = json.loads(urlopen.call_args.args[0].data)
        prompt = payload["contents"][0]["parts"][0]["text"]
        self.assertIn("Python, React", prompt)
        self.assertIn("Existing Project", prompt)
        self.assertIn("Backend Developer", prompt)
        self.assertIn("State University", prompt)
        self.assertIn("Existing Certificate", prompt)
        self.assertNotIn("Alex Candidate", prompt)
        self.assertNotIn("alexcandidate", prompt)
        self.assertNotIn("alex.candidate@example.com", prompt)
        self.assertNotIn("15 Main Street", prompt)
        self.assertNotIn("Private address must not be sent.", prompt)
        self.assertNotIn("Personal biography must not leave the app.", prompt)
        self.assertNotIn("github.com/alexcandidate", prompt)
        self.assertNotIn("private/repository", prompt)
        self.assertNotIn("555-123-4567", prompt)
        self.assertNotIn("Contact Alex Candidate", prompt)
        self.assertNotIn("profile_picture", prompt)
        self.assertEqual(payload["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(result.skills, ["Python", "FastAPI"])
        self.assertEqual(result.projects[0].title, "Inventory Tool")
        self.assertEqual(result.experience[0].company, "Example Studio")
        self.assertEqual(result.education[0].institution, "City College")
        self.assertEqual(result.certifications[0].name, "Cloud Developer Certificate")
        self.assertEqual(result.projects[0].repository_url, "")

    def test_personal_information_section_is_not_collected_for_gemini(self) -> None:
        sections = service._sections(
            "Skills\nPython\nPersonal Info\n"
            "Private address and contact information\nProjects\nInventory Tool"
        )
        self.assertEqual(sections["skills"], ["Python"])
        self.assertEqual(sections["projects"], ["Inventory Tool"])
        self.assertNotIn("Private address and contact information", str(sections))

    def test_does_not_call_gemini_when_only_personal_information_is_present(self) -> None:
        profile = ProfileData(
            name="Alex Candidate",
            username="alexcandidate",
            email="alex.candidate@example.com",
        )
        with (
            patch.object(gemini, "GEMINI_API_KEY", "test-secret"),
            patch.object(gemini, "GEMINI_MODEL", "gemini-2.5-flash"),
            patch.object(gemini, "urlopen") as urlopen,
        ):
            result =             gemini.extract_resume_profile(
                {"personal_info": ["Private address must not be sent."]},
                profile,
            )
        urlopen.assert_not_called()
        self.assertEqual(result, ExtractedProfile())

    def test_requires_api_key_without_sending_resume_data(self) -> None:
        with (
            patch.object(gemini, "GEMINI_API_KEY", ""),
            patch.object(gemini, "urlopen") as urlopen,
            self.assertRaisesRegex(gemini.ResumeGeminiConfigurationError, "GEMINI_API_KEY"),
        ):
            gemini.extract_resume_profile({"skills": ["Private test skill"]}, self._profile())
        urlopen.assert_not_called()

    def test_preserves_existing_user_values_and_fills_missing_combined_details(self) -> None:
        profile = self._profile()
        extracted = ExtractedProfile(
            skills=["Python", "Go"],
            projects=[
                Project(
                    title="Existing Project",
                    description="A model-generated description.",
                    tech_stack="Python, React",
                )
            ],
            experience=[
                Experience(
                    job_title="Software Engineer",
                    company="Current Employer",
                    description="Improved existing work history.",
                )
            ],
            education=[
                Education(
                    institution="State University",
                    degree="BSc",
                    field_of_study="Computer Science",
                )
            ],
            certifications=[Certification(name="Existing Certificate")],
        )

        merged, added = service.add_extracted_profile(profile, extracted)

        self.assertEqual(merged.skills.count("Python"), 1)
        self.assertIn("Go", added.skills)
        project = next(item for item in merged.projects if item.title == "Existing Project")
        self.assertIn("Contact Alex Candidate", project.description)
        self.assertEqual(project.tech_stack, "Python")
        experience = next(item for item in merged.experience if item.job_title == "Software Engineer")
        self.assertIn("alex.candidate@example.com", experience.description)
        self.assertEqual(experience.company, "Current Employer")
        education = next(item for item in merged.education if item.institution == "State University")
        self.assertEqual(education.field_of_study, "Computer Science")


if __name__ == "__main__":
    unittest.main()
