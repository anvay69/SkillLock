export const emptyProfile = {
  name: "",
  username: "",
  email: "",
  bio: "",
  github_url: "",
  linkedin_url: "",
  skills: [],
  projects: [],
  experience: [],
  education: [],
  certifications: [],
};

export const profileSections = [
  {
    key: "projects",
    title: "Projects",
    hint: "Show what you’ve made. Add as many as you like.",
    addLabel: "a project",
    fields: [
      { key: "title", label: "Title", placeholder: "Project name" },
      { key: "tech_stack", label: "Tech stack", placeholder: "React, Python..." },
      { key: "description", label: "Description", placeholder: "What did you build?", multiline: true },
      { key: "repository_url", label: "Repository URL", placeholder: "https://github.com/..." },
      { key: "live_url", label: "Live project URL", placeholder: "https://..." },
    ],
  },
  {
    key: "experience",
    title: "Experience",
    hint: "The roles that brought you here.",
    addLabel: "experience",
    fields: [
      { key: "job_title", label: "Job title", placeholder: "Software Engineer" },
      { key: "company", label: "Company", placeholder: "Company name" },
      { key: "start_date", label: "Start date", type: "month" },
      { key: "end_date", label: "End date", type: "month" },
      { key: "description", label: "Description", placeholder: "What did you work on?", multiline: true },
    ],
  },
  {
    key: "education",
    title: "Education",
    hint: "A little about how you learned.",
    addLabel: "education",
    fields: [
      { key: "institution", label: "Institution", placeholder: "School or university" },
      { key: "degree", label: "Degree", placeholder: "B.S." },
      { key: "field_of_study", label: "Field of study", placeholder: "Computer Science" },
      { key: "graduation_year", label: "Graduation year", placeholder: "2025" },
      { key: "grade", label: "Grade", placeholder: "Optional" },
    ],
  },
  {
    key: "certifications",
    title: "Certifications",
    hint: "Credentials that matter to you.",
    addLabel: "certification",
    fields: [
      { key: "name", label: "Name", placeholder: "Certification name" },
      { key: "issuing_organization", label: "Issuing organization", placeholder: "Organization" },
      { key: "credential_url", label: "Credential URL", placeholder: "https://..." },
    ],
  },
];
