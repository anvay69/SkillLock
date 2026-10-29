import re
from collections.abc import Iterable
from typing import Literal


SKILL_ALIASES = {
    "JavaScript": ("JS",),
    "PostgreSQL": ("Postgres",),
    "REST APIs": ("REST API", "RESTful API", "RESTful APIs"),
}
SkillPriority = Literal["required", "preferred"]


def _normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


def canonical_skill(skill: str) -> str:
    normalized = _normalized(skill)
    for canonical, aliases in SKILL_ALIASES.items():
        if normalized == _normalized(canonical) or any(
            normalized == _normalized(alias) for alias in aliases
        ):
            return canonical
    return skill.strip()


def skill_pattern(skill: str) -> re.Pattern[str]:
    variants = [skill, *SKILL_ALIASES.get(skill, ())]
    alternatives = []
    for variant in sorted(variants, key=len, reverse=True):
        escaped_variant = re.escape(" ".join(variant.split()))
        if variant.casefold() == "js":
            alternatives.append(r"(?<![\w.])JS(?!\w)")
        else:
            alternatives.append(rf"(?<!\w){escaped_variant}(?!\w)")
    alternatives_pattern = "|".join(alternatives)
    if skill == "C":
        return re.compile(rf"(?<!\w)(?:{alternatives_pattern})(?![\w+#])", re.IGNORECASE)
    return re.compile(rf"(?:{alternatives_pattern})", re.IGNORECASE)


def _skill_mentions(
    job_description: str,
    skills: Iterable[str],
) -> list[tuple[str, int, int]]:
    canonical_skills = list(dict.fromkeys(canonical_skill(skill) for skill in skills if skill.strip()))
    mentions: list[tuple[str, int, int]] = []
    for skill in canonical_skills:
        for match in skill_pattern(skill).finditer(job_description):
            mentions.append((skill, match.start(), match.end()))
    return sorted(mentions, key=lambda mention: (mention[1], mention[2]))


def extract_recognized_skills(text: str, skills: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(skill for skill, _, _ in _skill_mentions(text, skills)))


_NEGATIVE_MENTION = re.compile(
    r"\b(?:not\s+(?:required|necessary|needed|used|utili[sz]ed)|"
    r"(?:is|are)\s+not\s+(?:required|necessary|needed|used|utili[sz]ed)|"
    r"(?:isn't|aren't)\s+(?:required|necessary|needed|used|utili[sz]ed)|"
    r"does\s+not\s+use|do\s+not\s+use|doesn't\s+use|don't\s+use|"
    r"not\s+a\s+requirement)\b",
    re.IGNORECASE,
)
_PREFERRED_MENTION = re.compile(
    r"\b(?:preferred|preferable|optional|bonus|desirable|nice\s+to\s+have)\b",
    re.IGNORECASE,
)
_REQUIRED_MENTION = re.compile(
    r"\b(?:required|requirement|mandatory|essential|must\s+have)\b",
    re.IGNORECASE,
)
_REQUIRED_HEADINGS = {
    "required",
    "required skills",
    "must have",
    "must haves",
    "essential",
    "essential skills",
    "mandatory",
    "mandatory skills",
}
_PREFERRED_HEADINGS = {
    "preferred",
    "preferred skills",
    "nice to have",
    "nice to have skills",
    "optional",
    "optional skills",
    "desirable",
    "bonus skills",
}
_OTHER_SECTION_HEADINGS = {
    "about",
    "about us",
    "about the role",
    "about you",
    "responsibilities",
    "what you will do",
    "qualifications",
    "experience",
    "education",
    "benefits",
    "location",
    "how to apply",
}
_INLINE_SECTION_LABELS = {
    *_REQUIRED_HEADINGS,
    *_PREFERRED_HEADINGS,
    "required skills",
    "must have",
    "must haves",
    "essential skills",
    "mandatory skills",
    "preferred skills",
    "nice to have",
    "nice to have skills",
    "optional skills",
    "bonus skills",
}
LEARNING_GUIDES = {
    "HTML": (
        ["Learn semantic elements such as headings, lists, links, forms, and buttons.",
         "Recreate a simple page and check that its structure makes sense without styling.",
         "Add labels and useful alternative text to its form controls and images."],
        "Build a semantic form with labels, required fields, and helpful page headings.",
        "Create a one-page personal portfolio with an about section and contact form.",
    ),
    "CSS": (
        ["Practice selectors, the box model, spacing, and typography.",
         "Recreate a small card layout using Flexbox, then try the same with Grid.",
         "Use a media query to make the layout work on a narrow screen."],
        "Style a responsive card and navigation bar without fixed-width page layouts.",
        "Build a responsive portfolio page for desktop and mobile screens.",
    ),
    "JavaScript": (
        ["Practice variables, functions, arrays, objects, and conditional logic.",
         "Use browser events to respond to button clicks and form submissions.",
         "Fetch JSON data and handle loading and error cases."],
        "Write a small function that filters a list and show its results on a page.",
        "Build a searchable task list that saves its items in browser storage.",
    ),
    "Java": (
        ["Practice variables, primitive types, conditions, loops, and methods.",
         "Create classes with fields, constructors, and simple methods.",
         "Use lists and maps to store and look up program data."],
        "Write a command-line program that reads, validates, and summarizes a list of records.",
        "Build a small library checkout tracker using classes and collections.",
    ),
    "Python": (
        ["Practice values, conditions, loops, functions, and common collections.",
         "Read and write a small JSON or text file, handling invalid input.",
         "Split a program into functions and add a few unit tests."],
        "Write a script that validates and summarizes a small JSON dataset.",
        "Build a command-line expense tracker that saves entries to a file.",
    ),
    "React": (
        ["Build small components and pass data to them with props.",
         "Use state to handle an input, button click, and conditional display.",
         "Render a list with stable keys and show loading and error states."],
        "Turn a static list into a component with add, filter, and remove actions.",
        "Build a small reading-list app with search and completion status.",
    ),
    "TypeScript": (
        ["Practice primitive, array, object, and union types.",
         "Define interfaces or type aliases for the data used by a small app.",
         "Add types to component props and handle nullable values explicitly."],
        "Add types to a JavaScript utility and fix the type errors it reveals.",
        "Build a typed task tracker with a small, clearly defined task model.",
    ),
    "Node.js": (
        ["Learn how to run JavaScript outside the browser and use npm scripts.",
         "Create a small HTTP server and return JSON for one route.",
         "Handle invalid input and return suitable HTTP status codes."],
        "Create a server with one route that validates and returns a JSON object.",
        "Build a small local notes API with create and list operations.",
    ),
    "FastAPI": (
        ["Create a path operation and return a simple JSON response.",
         "Use a Pydantic model to validate request data.",
         "Add clear error responses and try the endpoints in the API docs."],
        "Create an endpoint that accepts a validated item and returns it.",
        "Build a small reading-list API with create and list endpoints.",
    ),
    "Flask": (
        ["Create a Flask app and return a response from a route.",
         "Accept JSON input and validate required fields.",
         "Return clear status codes for successful and invalid requests."],
        "Create a JSON route that accepts one item and rejects missing fields.",
        "Build a small bookmark API with add and list routes.",
    ),
    "SQL": (
        ["Practice SELECT, filtering, sorting, and limiting results.",
         "Use INSERT, UPDATE, and DELETE on a small practice dataset.",
         "Join two related tables and group results for a summary."],
        "Write queries to filter records, join related data, and count grouped results.",
        "Design a two-table event signup database and query attendance summaries.",
    ),
    "SQLite": (
        ["Create a database file and a table with a primary key.",
         "Use parameterized queries to insert and retrieve records.",
         "Commit changes safely and handle missing or invalid values."],
        "Write a short program that stores and lists records using parameters.",
        "Build a local reading log backed by a small SQLite database.",
    ),
    "PostgreSQL": (
        ["Practice table definitions, common data types, and constraints.",
         "Write parameterized queries and join related tables.",
         "Explore indexes and explain how they affect a query plan."],
        "Create related tables and query them with joins and aggregate functions.",
        "Build a small event registration database with constraints and reports.",
    ),
    "MongoDB": (
        ["Learn how documents and collections represent application data.",
         "Practice inserting, finding, updating, and deleting documents.",
         "Use a filter and projection to retrieve only the data you need."],
        "Create and query a collection of sample records with a few filter conditions.",
        "Build a small recipe collection with search by ingredient or category.",
    ),
    "Git": (
        ["Practice status, add, commit, and log in a disposable local repository.",
         "Create a branch, make a small change, and merge it back.",
         "Resolve a simple conflict and inspect the resulting history."],
        "Make a feature branch with several small commits and merge it locally.",
        "Track a small personal project with a clean history and useful commits.",
    ),
    "GitHub": (
        ["Create a repository and add a README that explains how to run the project.",
         "Push a branch and open a pull request describing a small change.",
         "Review a diff and respond to a review comment."],
        "Open a pull request for a tiny documentation or test improvement.",
        "Publish a small project with setup instructions and a sample screenshot.",
    ),
    "Docker": (
        ["Learn images, containers, ports, and environment variables.",
         "Write a Dockerfile for a small application and build the image.",
         "Run the container locally and inspect its logs."],
        "Containerize a small app and pass one configuration value through the environment.",
        "Package a tiny JSON API as a container with clear run instructions.",
    ),
    "REST APIs": (
        ["Practice HTTP methods, URLs, JSON, and common status codes.",
         "Call an API and inspect its request, response, and error behavior.",
         "Design a resource with clear create, read, update, and delete operations."],
        "Document example requests and responses for a small resource API.",
        "Design a simple inventory API with consistent resource URLs and errors.",
    ),
    "Linux": (
        ["Practice navigating directories and viewing or searching file contents.",
         "Use permissions and environment variables in a disposable project folder.",
         "Run a process and inspect its output and exit status."],
        "Write a small shell script that checks files and reports missing inputs.",
        "Create a script that organizes sample files into folders by extension.",
    ),
    "C++": (
        ["Practice variables, conditions, loops, functions, and standard input/output.",
         "Use vectors and strings to store and process a list of values.",
         "Split code into functions and compile with warnings enabled."],
        "Write a program that reads numbers and reports their minimum, maximum, and average.",
        "Build a command-line quiz that stores questions and scores in vectors.",
    ),
    "C": (
        ["Practice variables, conditions, loops, functions, and basic compilation.",
         "Use arrays and structs to organize a small set of values.",
         "Check return values and carefully manage any allocated memory."],
        "Write a program that reads a bounded list of values and prints a summary.",
        "Build a small command-line contact list using structs and file input/output.",
    ),
    "Data structures and algorithms": (
        ["Practice arrays, linked lists, stacks, queues, maps, and sets.",
         "Trace a search or sort by hand, then implement it and test edge cases.",
         "Compare time and space costs using simple Big-O descriptions."],
        "Implement linear search and binary search, then compare their requirements.",
        "Build a small route or word-frequency analyzer using suitable data structures.",
    ),
}


def _clause_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    left = max(
        text.rfind(separator, 0, start)
        for separator in ("\n", ".", "!", "?", ";")
    )
    right_candidates = [
        position
        for separator in ("\n", ".", "!", "?", ";")
        if (position := text.find(separator, end)) != -1
    ]
    return left + 1, min(right_candidates) if right_candidates else len(text)


def _has_nearby_marker(
    text: str,
    start: int,
    end: int,
    mentions: list[tuple[str, int, int]],
    marker_pattern: re.Pattern[str],
) -> bool:
    clause_start, clause_end = _clause_bounds(text, start, end)
    clause = text[clause_start:clause_end]
    target_start = start - clause_start
    target_end = end - clause_start
    for marker in marker_pattern.finditer(clause):
        if marker.end() <= target_start:
            if not any(
                start <= other_start < marker.start()
                for _, other_start, _ in mentions
                if clause_start <= other_start < clause_end
            ):
                return True
            between = clause[marker.end():target_start]
        elif marker.start() >= target_end:
            between = clause[target_end:marker.start()]
        else:
            return True

        if len(between) > 48:
            continue
        absolute_start = clause_start + min(marker.end(), target_start)
        absolute_end = clause_start + max(marker.start(), target_end)
        if any(
            other_start >= absolute_start and other_end <= absolute_end
            for _, other_start, other_end in mentions
            if (other_start, other_end) != (start, end)
        ):
            continue
        return True
    return False


def _heading_text(line: str) -> str:
    cleaned = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)
    cleaned = re.sub(r"\s*#+\s*$", "", cleaned)
    return re.sub(r"[\s:：\-–—.]+$", "", cleaned).strip().casefold()


def _section_priorities(text: str) -> dict[int, SkillPriority | None]:
    priorities: dict[int, SkillPriority | None] = {}
    current: SkillPriority | None = None
    offset = 0
    for line in text.splitlines(keepends=True):
        heading = _heading_text(line)
        section_label = heading.split(":", 1)[0].strip()
        has_inline_items = ":" in line or "：" in line
        is_explicit_heading = (
            section_label in _INLINE_SECTION_LABELS
            if has_inline_items
            else heading in _REQUIRED_HEADINGS | _PREFERRED_HEADINGS
        )
        if is_explicit_heading and section_label in _REQUIRED_HEADINGS:
            current = "required"
        elif is_explicit_heading and section_label in _PREFERRED_HEADINGS:
            current = "preferred"
        elif section_label in _OTHER_SECTION_HEADINGS:
            current = None
        line_priority = current
        if (
            has_inline_items
            and section_label in _REQUIRED_HEADINGS | _PREFERRED_HEADINGS
            and not is_explicit_heading
        ):
            line_priority = None
            current = None
        priorities[offset] = line_priority
        offset += len(line)
    if not priorities and text:
        priorities[0] = None
    return priorities


def _section_priority_for_position(
    text: str,
    start: int,
    priorities: dict[int, SkillPriority | None],
) -> SkillPriority | None:
    line_start = text.rfind("\n", 0, start) + 1
    return priorities.get(line_start)


def _classify_mentions(
    job_description: str,
    mentions: list[tuple[str, int, int]],
) -> dict[str, SkillPriority]:
    priorities: dict[str, SkillPriority] = {}
    section_priorities = _section_priorities(job_description)
    for skill, start, end in mentions:
        if _has_nearby_marker(job_description, start, end, mentions, _NEGATIVE_MENTION):
            continue
        in_required_section = _section_priority_for_position(
            job_description, start, section_priorities
        ) == "required"
        in_preferred_section = _section_priority_for_position(
            job_description, start, section_priorities
        ) == "preferred"
        marked_required = _has_nearby_marker(
            job_description, start, end, mentions, _REQUIRED_MENTION
        )
        marked_preferred = _has_nearby_marker(
            job_description, start, end, mentions, _PREFERRED_MENTION
        )
        if marked_required:
            priority: SkillPriority = "required"
        elif marked_preferred:
            priority = "preferred"
        elif in_required_section:
            priority = "required"
        elif in_preferred_section:
            priority = "preferred"
        else:
            priority = "required"
        current = priorities.get(skill)
        if skill not in priorities:
            priorities[skill] = priority
        elif current == "preferred" and priority == "required":
            priorities[skill] = "required"
    return priorities


def _roadmap_item(
    skill: str,
    priority: SkillPriority,
    learning_progress: dict[str, str],
) -> dict[str, str | list[str]]:
    guide = LEARNING_GUIDES.get(skill)
    if guide is None:
        guide = (
            [
                f"Learn the basic concepts and common uses of {skill}.",
                f"Follow a beginner example using {skill}, then recreate it without copying.",
                f"Review your work and write down what you can now do with {skill}.",
            ],
            f"Complete small exercises that use {skill}.",
            f"Build a small portfolio project that uses {skill} to solve one clear problem.",
        )
    return {
        "skill": skill,
        "priority": priority,
        "status": learning_progress.get(skill, "not_started"),
        "steps": guide[0],
        "practice_task": guide[1],
        "project_idea": guide[2],
    }


def analyze_job_description(
    job_description: str,
    candidate_skills: list[str],
    known_skills: list[str],
    learning_progress: dict[str, str] | None = None,
) -> dict[str, object]:
    skill_candidates = [*known_skills, *candidate_skills]
    mentions = _skill_mentions(job_description, skill_candidates)
    priorities = _classify_mentions(job_description, mentions)
    required_skills = [skill for skill, priority in priorities.items() if priority == "required"]
    preferred_skills = [skill for skill, priority in priorities.items() if priority == "preferred"]
    return _compare_job_skills(
        required_skills,
        preferred_skills,
        candidate_skills,
        learning_progress,
    )


def analyze_job_requirements(
    required_skills: list[str],
    preferred_skills: list[str],
    candidate_skills: list[str],
    known_skills: list[str],
    learning_progress: dict[str, str] | None = None,
) -> dict[str, object]:
    known_by_normalized = {
        _normalized(canonical_skill(skill)): canonical_skill(skill)
        for skill in [*known_skills, *candidate_skills]
        if skill.strip()
    }

    def recognized(skills: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for skill in skills:
            canonical = canonical_skill(skill)
            key = _normalized(canonical)
            if key in known_by_normalized and key not in seen:
                result.append(known_by_normalized[key])
                seen.add(key)
        return result

    required = recognized(required_skills)
    required_keys = {_normalized(skill) for skill in required}
    preferred = [
        skill
        for skill in recognized(preferred_skills)
        if _normalized(skill) not in required_keys
    ]
    return _compare_job_skills(required, preferred, candidate_skills, learning_progress)


def _compare_job_skills(
    required_skills: list[str],
    preferred_skills: list[str],
    candidate_skills: list[str],
    learning_progress: dict[str, str] | None,
) -> dict[str, object]:
    candidate_skill_names = {
        _normalized(canonical_skill(skill))
        for skill in candidate_skills
        if skill.strip()
    }
    matched_skills = [
        skill for skill in required_skills + preferred_skills
        if _normalized(skill) in candidate_skill_names
    ]
    missing_required_skills = [
        skill for skill in required_skills
        if _normalized(skill) not in candidate_skill_names
    ]
    missing_preferred_skills = [
        skill for skill in preferred_skills
        if _normalized(skill) not in candidate_skill_names
    ]
    missing_skills = missing_required_skills + missing_preferred_skills
    recognized_skills = required_skills + preferred_skills
    learning_progress = learning_progress or {}
    total_weight = len(required_skills) * 2 + len(preferred_skills)
    matched_weight = (
        (len(required_skills) - len(missing_required_skills)) * 2
        + len(preferred_skills)
        - len(missing_preferred_skills)
    )
    match_score = (
        round(matched_weight / total_weight * 100)
        if total_weight
        else None
    )

    if not recognized_skills:
        readiness_feedback = (
            "No catalogued skills were recognized in this description. "
            "Unrecognized requirements may be missed, so this baseline cannot "
            "estimate readiness."
        )
    else:
        match_percentage = round(len(matched_skills) / len(recognized_skills) * 100)
        readiness_feedback = (
            f"Your profile matches {len(matched_skills)} of "
            f"{len(recognized_skills)} recognized skills ({match_percentage}%). "
            "Unrecognized requirements may be missed; this is not an overall "
            "job-readiness score."
        )

    suggestions = [
        f"If you have experience with {skill}, add it to your profile; otherwise, consider developing it."
        for skill in missing_skills
    ]
    if not suggestions:
        suggestions.append(
            "Review the full job description for requirements beyond the recognized skills."
        )

    roadmap = [
        *(
            _roadmap_item(skill, "required", learning_progress)
            for skill in missing_required_skills
        ),
        *(
            _roadmap_item(skill, "preferred", learning_progress)
            for skill in missing_preferred_skills
        ),
    ]
    return {
        "match_score": match_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "missing_required_skills": missing_required_skills,
        "missing_preferred_skills": missing_preferred_skills,
        "readiness_feedback": readiness_feedback,
        "suggestions": suggestions,
        "learning_roadmap": roadmap,
    }
