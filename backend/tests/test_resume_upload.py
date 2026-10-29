import json
import sqlite3
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from docx import Document
from fastapi.testclient import TestClient

from app.core import database
from app.core.config import SEED_FILE, UPLOADS
from app.features.job_matching import routes as job_matching_routes
from app.features.job_matching.gemini import GeminiJobRequirements
from app.features.resume import gemini as resume_gemini
from app.features.resume import service as resume_service
from app.main import app
from app.schemas.profile import (
    Certification,
    Education,
    Experience,
    ExtractedProfile,
    Project,
)
from app.services import uploads as upload_service


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect_test_database() -> sqlite3.Connection:
    connection = sqlite3.connect(database.DATABASE, factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    return connection


def make_text_pdf(lines: list[str]) -> bytes:
    commands = []
    for index, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        y_position = 720 - index * 16
        commands.append(f"BT /F1 12 Tf 72 {y_position} Td ({escaped}) Tj ET")
    stream = "\n".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
        + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, content in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(content)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def make_docx(lines: list[str]) -> bytes:
    document = Document()
    for line in lines:
        document.add_paragraph(line)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


class ResumeUploadApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_database = database.DATABASE
        self.original_connect = database.connect
        database.DATABASE = Path(self.temp_dir.name) / "resume-upload-test.db"
        database.connect = connect_test_database
        self.upload_dir = Path(self.temp_dir.name) / "uploads"
        self.upload_dir.mkdir()
        self.private_resume_dir = Path(self.temp_dir.name) / "private-resumes"
        self.resume_uploads_patch = patch.object(resume_service, "UPLOADS", self.upload_dir)
        self.private_resumes_patch = patch.object(
            resume_service, "PRIVATE_RESUMES", self.private_resume_dir
        )
        self.generic_uploads_patch = patch.object(upload_service, "UPLOADS", self.upload_dir)
        self.resume_uploads_patch.start()
        self.private_resumes_patch.start()
        self.generic_uploads_patch.start()
        self.addCleanup(self.resume_uploads_patch.stop)
        self.addCleanup(self.private_resumes_patch.stop)
        self.addCleanup(self.generic_uploads_patch.stop)
        self.resume_extraction_patch = patch.object(
            resume_service,
            "extract_resume_profile",
            return_value=ExtractedProfile(),
        )
        self.resume_extraction_patch.start()
        self.addCleanup(self.resume_extraction_patch.stop)

        self.client = TestClient(app)
        self.client.__enter__()
        seed = json.loads(SEED_FILE.read_text(encoding="utf-8"))
        login = self.client.post(
            "/api/login",
            json={
                "email": seed["candidate"]["email"],
                "password": seed["candidate"]["password"],
            },
        )
        self.assertEqual(login.status_code, 200, login.text)

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        database.DATABASE = self.original_database
        database.connect = self.original_connect
        self.temp_dir.cleanup()

    def test_resume_upload_requires_authentication(self) -> None:
        with TestClient(app) as anonymous:
            response = anonymous.post(
                "/api/me/resume",
                files={"resume": ("resume.pdf", make_text_pdf(["Skills", "Go"]), "application/pdf")},
            )
        self.assertEqual(response.status_code, 401, response.text)

    def test_job_matching_learning_progress_is_persisted_in_candidate_profile(self) -> None:
        response = self.client.put(
            "/api/job-matching/learning-progress",
            json={"skill": "Docker", "status": "learning"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["learning_progress"]["Docker"], "learning")

        profile = self.client.get("/api/me")
        self.assertEqual(profile.status_code, 200, profile.text)
        self.assertEqual(profile.json()["learning_progress"]["Docker"], "learning")

    def test_job_matching_uses_fetched_linkedin_description_without_manual_text(self) -> None:
        listing = {
            "job_title": "Backend Developer",
            "company": "Example Co",
            "job_description": "Python is required. TypeScript is preferred.",
            "page_text": "Backend Developer at Example Co: Python is required. TypeScript is preferred.",
        }
        extracted = GeminiJobRequirements(
            job_title="Backend Developer",
            company="Example Co",
            job_summary="Build API services.",
            required_skills=["Python"],
            preferred_skills=["TypeScript"],
        )
        with (
            patch.object(job_matching_routes, "fetch_linkedin_job", return_value=listing),
            patch.object(job_matching_routes, "extract_job_requirements", return_value=extracted),
        ):
            response = self.client.post(
                "/api/job-matching/analyze",
                json={"linkedin_url": "https://www.linkedin.com/jobs/view/123456"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["source"], "linkedin_listing")
        self.assertEqual(body["job_title"], "Backend Developer")
        self.assertEqual(body["company"], "Example Co")
        self.assertEqual(body["job_summary"], "Build API services.")
        self.assertIn("Python", body["matched_skills"])
        self.assertIn("TypeScript", body["missing_preferred_skills"])

    def test_job_matching_sends_pasted_description_to_gemini(self) -> None:
        extracted = GeminiJobRequirements(
            job_title="Rust Developer",
            company="Example Co",
            job_summary="Build Rust services.",
            required_skills=["Rust"],
            preferred_skills=[],
        )
        with patch.object(
            job_matching_routes,
            "extract_job_requirements",
            return_value=extracted,
        ) as extract:
            response = self.client.post(
                "/api/job-matching/analyze",
                json={"job_description": "Rust experience is required."},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["source"], "pasted_description")
        self.assertEqual(response.json()["job_title"], "Rust Developer")
        self.assertEqual(extract.call_args.args[0], "")
        self.assertEqual(extract.call_args.args[2], "Rust experience is required.")

    def test_job_matching_combines_linkedin_and_pasted_description_in_gemini(self) -> None:
        listing = {
            "job_title": "Backend Developer",
            "company": "Example Co",
            "job_description": "Python is required.",
            "page_text": "Backend Developer at Example Co: Python is required.",
        }
        extracted = GeminiJobRequirements(
            job_title="Backend Developer",
            company="Example Co",
            job_summary="Build API services.",
            required_skills=["Python", "Docker"],
            preferred_skills=[],
        )
        with (
            patch.object(job_matching_routes, "fetch_linkedin_job", return_value=listing),
            patch.object(
                job_matching_routes,
                "extract_job_requirements",
                return_value=extracted,
            ) as extract,
        ):
            response = self.client.post(
                "/api/job-matching/analyze",
                json={
                    "linkedin_url": "https://www.linkedin.com/jobs/view/123456",
                    "job_description": "Python and Docker are required.",
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["source"], "linkedin_listing_and_description")
        self.assertEqual(extract.call_args.args[0], listing["page_text"])
        self.assertEqual(extract.call_args.args[2], "Python and Docker are required.")

    def test_job_matching_returns_clear_error_when_sources_do_not_match(self) -> None:
        listing = {
            "job_title": "Backend Developer",
            "company": "Example Co",
            "job_description": "Python is required.",
            "page_text": "Backend Developer at Example Co: Python is required.",
        }
        with (
            patch.object(job_matching_routes, "fetch_linkedin_job", return_value=listing),
            patch.object(
                job_matching_routes,
                "extract_job_requirements",
                side_effect=job_matching_routes.JobDescriptionMismatchError(
                    "The job description and LinkedIn job do not match. "
                    "Please check that they refer to the same job."
                ),
            ),
            patch.object(job_matching_routes, "analyze_job_requirements") as compare,
        ):
            response = self.client.post(
                "/api/job-matching/analyze",
                json={
                    "linkedin_url": "https://www.linkedin.com/jobs/view/123456",
                    "job_description": "Social media manager role at Another Co.",
                },
            )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("job description and LinkedIn job do not match", response.json()["detail"])
        compare.assert_not_called()

    def test_job_matching_does_not_call_gemini_without_any_source(self) -> None:
        with patch.object(job_matching_routes, "extract_job_requirements") as extract:
            response = self.client.post("/api/job-matching/analyze", json={})
        self.assertEqual(response.status_code, 422, response.text)
        extract.assert_not_called()

    def test_job_matching_uses_supplied_description_when_linkedin_is_unavailable(self) -> None:
        extracted = GeminiJobRequirements(
            job_title="Backend Developer",
            company="",
            job_summary="Build API services.",
            required_skills=["Python"],
            preferred_skills=[],
        )
        with (
            patch.object(
                job_matching_routes,
                "fetch_linkedin_job",
                side_effect=job_matching_routes.LinkedInFetchError("The listing is not public."),
            ),
            patch.object(
                job_matching_routes,
                "extract_job_requirements",
                return_value=extracted,
            ) as extract,
        ):
            response = self.client.post(
                "/api/job-matching/analyze",
                json={
                    "linkedin_url": "https://www.linkedin.com/jobs/view/123456",
                    "job_description": "Python is required.",
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["source"], "pasted_description")
        self.assertIn("not public", body["source_warning"])
        self.assertIn("Python", body["matched_skills"])
        self.assertEqual(extract.call_args.args[0], "")
        self.assertEqual(extract.call_args.args[2], "Python is required.")

    def test_pdf_is_saved_extracted_merged_and_used_by_job_matching(self) -> None:
        before = self.client.get("/api/me").json()
        content = make_text_pdf(
            [
                "Skills",
                "Rust, python",
                "Projects",
                "Project: community garden",
                "Project: Budget Planner",
                "Experience",
                "software engineer at northstar labs",
                "Data Analyst at Example Systems",
                "Education",
                "BSc Computer Science at State University 2022",
                "MSc Data Science at Northstar University 2024",
                "Certifications",
                "aws certified cloud practitioner",
                "AWS Certified Developer",
            ]
        )
        extracted = ExtractedProfile(
            skills=["Rust"],
            projects=[Project(title="Budget Planner")],
            experience=[Experience(job_title="Data Analyst", company="Example Systems")],
            education=[
                Education(
                    degree="MSc",
                    field_of_study="Data Science",
                    institution="Northstar University",
                    graduation_year="2024",
                )
            ],
            certifications=[Certification(name="AWS Certified Developer")],
        )
        with patch.object(resume_service, "extract_resume_profile", return_value=extracted):
            response = self.client.post(
                "/api/me/resume",
                files={"resume": ("resume.pdf", content, "application/pdf")},
            )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(set(body), {"profile", "extracted_added"})

        profile = body["profile"]
        added = body["extracted_added"]
        self.assertRegex(profile["resume"], r"^/api/me/resume/file/[0-9a-f]{32}\.pdf$")
        self.assertEqual(added["skills"], ["Rust"])
        self.assertEqual([item["title"] for item in added["projects"]], ["Budget Planner"])
        self.assertEqual([item["job_title"] for item in added["experience"]], ["Data Analyst"])
        self.assertEqual(added["experience"][0]["company"], "Example Systems")
        self.assertEqual(
            [item["institution"] for item in added["education"]],
            ["Northstar University"],
        )
        self.assertEqual(added["education"][0]["graduation_year"], "2024")
        self.assertEqual(
            [item["name"] for item in added["certifications"]],
            ["AWS Certified Developer"],
        )

        self.assertIn("Python", profile["skills"])
        self.assertIn("Rust", profile["skills"])
        self.assertEqual(profile["skills"].count("Python"), 1)
        self.assertIn("Community Garden", [item["title"] for item in profile["projects"]])
        self.assertIn("Budget Planner", [item["title"] for item in profile["projects"]])
        self.assertEqual(profile["bio"], before["bio"])
        self.assertEqual(profile["github_url"], before["github_url"])
        self.assertIn("Software Engineer", [item["job_title"] for item in profile["experience"]])
        self.assertIn("State University", [item["institution"] for item in profile["education"]])
        self.assertIn(
            "AWS Certified Cloud Practitioner",
            [item["name"] for item in profile["certifications"]],
        )
        self.assertEqual(
            [item["title"] for item in profile["projects"]].count("Community Garden"),
            1,
        )
        self.assertEqual(
            [item["job_title"] for item in profile["experience"]].count("Software Engineer"),
            1,
        )
        self.assertEqual(
            [item["institution"] for item in profile["education"]].count("State University"),
            1,
        )
        self.assertEqual(
            [item["name"] for item in profile["certifications"]].count(
                "AWS Certified Cloud Practitioner"
            ),
            1,
        )

        filename = Path(profile["resume"]).name
        stored_file = self.private_resume_dir / str(profile["id"]) / filename
        self.assertTrue(stored_file.is_file())
        self.assertEqual(stored_file.read_bytes(), content)
        self.assertEqual(self.client.get(profile["resume"]).content, content)
        UPLOADS.mkdir(parents=True, exist_ok=True)
        public_copy = UPLOADS / filename
        public_copy.write_bytes(content)
        try:
            self.assertEqual(self.client.get(f"/uploads/{filename}").status_code, 404)
        finally:
            public_copy.unlink(missing_ok=True)

        attempted_profile = dict(profile)
        attempted_profile["resume"] = "/api/me/resume/file/" + ("f" * 32) + ".pdf"
        edited = self.client.put("/api/me", data={"profile": json.dumps(attempted_profile)})
        self.assertEqual(edited.status_code, 200, edited.text)
        self.assertEqual(edited.json()["resume"], profile["resume"])

        rust_extraction = GeminiJobRequirements(
            job_title="",
            company="",
            job_summary="",
            required_skills=["Rust"],
            preferred_skills=[],
        )
        with patch.object(
            job_matching_routes,
            "extract_job_requirements",
            return_value=rust_extraction,
        ):
            match = self.client.post(
                "/api/job-matching/analyze",
                json={"job_description": "Rust experience is required."},
            )
        self.assertEqual(match.status_code, 200, match.text)
        self.assertIn("Rust", match.json()["matched_skills"])

        repeated = self.client.post(
            "/api/me/resume",
            files={"resume": ("same-resume.pdf", content, "application/pdf")},
        )
        self.assertEqual(repeated.status_code, 200, repeated.text)
        repeated_body = repeated.json()
        self.assertTrue(
            all(not values for values in repeated_body["extracted_added"].values())
        )
        self.assertEqual(repeated_body["profile"]["skills"].count("Rust"), 1)
        self.assertEqual(
            [item["title"] for item in repeated_body["profile"]["projects"]].count("Budget Planner"),
            1,
        )
        self.assertEqual(
            [item["job_title"] for item in repeated_body["profile"]["experience"]].count("Data Analyst"),
            1,
        )
        self.assertEqual(
            [item["institution"] for item in repeated_body["profile"]["education"]].count("Northstar University"),
            1,
        )
        self.assertEqual(
            [item["name"] for item in repeated_body["profile"]["certifications"]].count("AWS Certified Developer"),
            1,
        )
        self.assertFalse(stored_file.exists())

    def test_resume_download_is_authenticated_and_scoped_to_the_owner(self) -> None:
        content = make_text_pdf(["Skills", "Go"])
        uploaded = self.client.post(
            "/api/me/resume",
            files={"resume": ("resume.pdf", content, "application/pdf")},
        )
        self.assertEqual(uploaded.status_code, 200, uploaded.text)
        resume_url = uploaded.json()["profile"]["resume"]
        filename = Path(resume_url).name

        with TestClient(app) as anonymous:
            response = anonymous.get(resume_url)
        self.assertEqual(response.status_code, 401, response.text)

        second = TestClient(app)
        second.__enter__()
        try:
            profile = {
                "name": "Casey Example",
                "username": "caseyexample",
                "email": "casey@example.com",
            }
            signup = second.post(
                "/api/signup",
                data={"profile": json.dumps(profile), "password": "another-test-password"},
            )
            self.assertEqual(signup.status_code, 200, signup.text)
            self.assertNotEqual(signup.json()["profile"]["id"], uploaded.json()["profile"]["id"])
            denied = second.get(f"/api/me/resume/file/{filename}")
            self.assertEqual(denied.status_code, 404, denied.text)
        finally:
            second.__exit__(None, None, None)

    def test_signup_resume_is_moved_to_private_account_storage(self) -> None:
        content = make_docx(["Skills", "Elixir"])
        profile = {
            "name": "Morgan Example",
            "username": "morganexample",
            "email": "morgan@example.com",
        }
        with patch.object(
            resume_service,
            "extract_resume_profile",
            return_value=ExtractedProfile(skills=["Elixir"]),
        ):
            signup = self.client.post(
                "/api/signup",
                data={"profile": json.dumps(profile), "password": "signup-test-password"},
                files={
                    "resume": (
                        "resume.docx",
                        content,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )
        self.assertEqual(signup.status_code, 200, signup.text)
        result = signup.json()
        user_id = result["profile"]["id"]
        filename = Path(result["profile"]["resume"]).name
        self.assertTrue((self.private_resume_dir / str(user_id) / filename).is_file())
        self.assertFalse((self.private_resume_dir / "0" / filename).exists())
        self.assertIn("Elixir", result["profile"]["skills"])
        self.assertEqual(self.client.get(result["profile"]["resume"]).content, content)

    def test_legacy_resume_is_private_and_remains_available_to_its_owner(self) -> None:
        filename = f"{uuid4().hex}.pdf"
        docx_filename = f"{uuid4().hex}.docx"
        image_filename = f"{uuid4().hex}.png"
        UPLOADS.mkdir(parents=True, exist_ok=True)
        public_file = UPLOADS / filename
        public_docx = UPLOADS / docx_filename
        public_image = UPLOADS / image_filename
        legacy_file = self.upload_dir / filename
        public_file.write_bytes(b"legacy private resume")
        public_docx.write_bytes(b"legacy private resume")
        public_image.write_bytes(b"public profile image")
        legacy_file.write_bytes(b"legacy private resume")
        try:
            current_profile = self.client.get("/api/me").json()
            current_profile["resume"] = f"/uploads/{filename}"
            with database.database() as db:
                db.execute(
                    "UPDATE users SET profile_json = ? WHERE id = ?",
                    (json.dumps(current_profile), current_profile["id"]),
                )

            public_response = self.client.get(f"/uploads/{filename}")
            self.assertEqual(public_response.status_code, 200)
            self.assertEqual(public_response.content, b"legacy private resume")
            self.assertEqual(
                self.client.get(f"/uploads/{docx_filename}").status_code,
                404,
            )
            self.assertEqual(
                self.client.get(f"/uploads/{image_filename}").status_code,
                200,
            )
            protected_response = self.client.get(f"/api/me/resume/file/{filename}")
            self.assertEqual(protected_response.status_code, 200)
            self.assertEqual(protected_response.content, b"legacy private resume")

            with TestClient(app) as anonymous:
                self.assertEqual(
                    anonymous.get(f"/uploads/{filename}").status_code,
                    401,
                )

            second = TestClient(app)
            second.__enter__()
            try:
                signup = second.post(
                    "/api/signup",
                    data={
                        "profile": json.dumps(
                            {
                                "name": "Taylor Example",
                                "username": "taylorexample",
                                "email": "taylor@example.com",
                            }
                        ),
                        "password": "another-test-password",
                    },
                )
                self.assertEqual(signup.status_code, 200, signup.text)
                self.assertEqual(second.get(f"/uploads/{filename}").status_code, 404)
            finally:
                second.__exit__(None, None, None)

            with (
                patch.object(resume_service, "UPLOADS", UPLOADS),
                patch.object(
                    resume_service,
                    "extract_resume_profile",
                    return_value=ExtractedProfile(skills=["Rust"]),
                ),
            ):
                replacement = self.client.post(
                    "/api/me/resume",
                    files={
                        "resume": (
                            "replacement.pdf",
                            make_text_pdf(["Skills", "Rust"]),
                            "application/pdf",
                        )
                    },
                )
            self.assertEqual(replacement.status_code, 200, replacement.text)
            self.assertFalse(public_file.exists())
            self.assertEqual(self.client.get(f"/uploads/{filename}").status_code, 404)
        finally:
            public_file.unlink(missing_ok=True)
            public_docx.unlink(missing_ok=True)
            public_image.unlink(missing_ok=True)
            legacy_file.unlink(missing_ok=True)

    def test_docx_is_saved_extracted_and_merged(self) -> None:
        content = make_docx(
            [
                "Technical Skills",
                "Go, SQL",
                "Projects",
                "Project: Inventory Dashboard",
                "Experience",
                "Product Engineer at Example Studio",
                "Education",
                "BSc Software Engineering at City College 2023",
                "Certifications",
                "Cloud Security Certificate",
            ]
        )
        extracted = ExtractedProfile(
            skills=["Go", "SQL"],
            projects=[Project(title="Inventory Dashboard")],
            experience=[Experience(job_title="Product Engineer", company="Example Studio")],
            education=[
                Education(
                    degree="BSc",
                    field_of_study="Software Engineering",
                    institution="City College",
                    graduation_year="2023",
                )
            ],
            certifications=[Certification(name="Cloud Security Certificate")],
        )
        with patch.object(resume_service, "extract_resume_profile", return_value=extracted):
            response = self.client.post(
                "/api/me/resume",
                files={
                    "resume": (
                        "resume.docx",
                        content,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        profile = body["profile"]
        added = body["extracted_added"]
        self.assertIn("Go", added["skills"])
        self.assertIn("Inventory Dashboard", [item["title"] for item in added["projects"]])
        self.assertIn("Product Engineer", [item["job_title"] for item in added["experience"]])
        self.assertIn("City College", [item["institution"] for item in added["education"]])
        self.assertIn("Cloud Security Certificate", [item["name"] for item in added["certifications"]])
        self.assertIn("Go", profile["skills"])
        self.assertIn("Community Garden", [item["title"] for item in profile["projects"]])
        self.assertTrue(
            (self.private_resume_dir / str(profile["id"]) / Path(profile["resume"]).name).is_file()
        )

    def test_unsupported_resume_extension_is_rejected(self) -> None:
        response = self.client.post(
            "/api/me/resume",
            files={"resume": ("resume.txt", b"Skills\nPython", "text/plain")},
        )
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(
            [path for path in self.private_resume_dir.rglob("*") if path.is_file()],
            [],
        )

    def test_gemini_failure_does_not_save_or_replace_uploaded_resume(self) -> None:
        with patch.object(
            resume_service,
            "extract_resume_profile",
            side_effect=resume_gemini.ResumeGeminiServiceError(
                "Gemini did not return valid structured resume details."
            ),
        ):
            response = self.client.post(
                "/api/me/resume",
                files={
                    "resume": (
                        "resume.pdf",
                        make_text_pdf(["Skills", "Python"]),
                        "application/pdf",
                    )
                },
            )

        self.assertEqual(response.status_code, 502, response.text)
        self.assertIn("Gemini did not return valid structured resume details", response.json()["detail"])
        self.assertEqual(
            [path for path in self.private_resume_dir.rglob("*") if path.is_file()],
            [],
        )

    def test_corrupted_resume_and_oversized_resume_are_rejected_without_files(self) -> None:
        for filename, content in (
            ("broken.pdf", b"%PDF-not valid"),
            ("broken.docx", b"not a zip file"),
            ("empty.pdf", make_text_pdf([])),
            ("large.pdf", b"x" * (resume_service.MAX_RESUME_BYTES + 1)),
        ):
            with self.subTest(filename=filename):
                response = self.client.post(
                    "/api/me/resume",
                    files={"resume": (filename, content, "application/octet-stream")},
                )
                self.assertEqual(response.status_code, 400, response.text)
                self.assertEqual(
                    [path for path in self.private_resume_dir.rglob("*") if path.is_file()],
                    [],
                )


if __name__ == "__main__":
    unittest.main()
