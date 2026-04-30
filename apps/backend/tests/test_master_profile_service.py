from app.services.master_profile import (
    create_empty_master_profile,
    import_resume_data,
    resume_data_to_master_profile,
)


def test_resume_data_to_master_profile_maps_core_sections() -> None:
    resume_data = {
        "personalInfo": {
            "name": "Alice Doe",
            "title": "Platform Engineer",
            "email": "alice@example.com",
            "phone": "123",
            "location": "Paris",
            "website": "https://alice.dev",
            "linkedin": "alice-linkedin",
            "github": "alice-github",
        },
        "summary": "General platform profile",
        "workExperience": [
            {
                "id": 1,
                "title": "Engineer",
                "company": "Acme",
                "location": "Paris",
                "years": "2020 - Present",
                "description": ["Built APIs"],
            }
        ],
        "education": [],
        "personalProjects": [
            {
                "id": 1,
                "name": "Side Project",
                "role": "Creator",
                "years": "2024",
                "github": "repo",
                "website": None,
                "description": ["Built tool"],
            }
        ],
        "additional": {
            "technicalSkills": ["Python", "FastAPI"],
            "languages": ["French"],
            "certificationsTraining": ["AWS"],
            "awards": ["Ignored"],
        },
        "sectionMeta": [],
        "customSections": {},
    }

    profile = resume_data_to_master_profile(resume_data)

    assert profile["personalInfo"]["summary"] == "General platform profile"
    assert profile["projects"][0]["role"] == "Creator"
    assert profile["skills"] == ["Python", "FastAPI"]
    assert profile["certifications"] == ["AWS"]


def test_import_resume_data_merges_without_overwriting_existing_values() -> None:
    existing_profile = {
        "personalInfo": {
            "name": "Alice Doe",
            "title": "",
            "email": "alice@example.com",
            "phone": "",
            "location": "Paris",
            "website": None,
            "linkedin": None,
            "github": None,
            "summary": "",
        },
        "workExperience": [
            {
                "id": 3,
                "title": "Engineer",
                "company": "Acme",
                "location": "",
                "years": "2020 - Present",
                "description": ["Built APIs"],
                "technologies": ["Python"],
            }
        ],
        "projects": [],
        "education": [],
        "skills": ["Python"],
        "languages": [],
        "certifications": [],
    }
    resume_data = {
        "personalInfo": {
            "name": "Alice Doe",
            "title": "Platform Engineer",
            "email": "alice@example.com",
            "phone": "123",
            "location": "Paris",
            "website": None,
            "linkedin": None,
            "github": None,
        },
        "summary": "General platform profile",
        "workExperience": [
            {
                "id": 1,
                "title": "Engineer",
                "company": "Acme",
                "location": "Remote",
                "years": "2020 - Present",
                "description": ["Built APIs", "Shipped platform work"],
            },
            {
                "id": 2,
                "title": "Senior Engineer",
                "company": "Beta",
                "location": "Paris",
                "years": "2018 - 2020",
                "description": ["Led migration"],
            },
        ],
        "education": [],
        "personalProjects": [],
        "additional": {
            "technicalSkills": ["Python", "FastAPI"],
            "languages": ["French"],
            "certificationsTraining": ["AWS"],
            "awards": [],
        },
        "sectionMeta": [],
        "customSections": {},
    }

    merged = import_resume_data(existing_profile, resume_data)

    assert merged["personalInfo"]["title"] == "Platform Engineer"
    assert merged["personalInfo"]["phone"] == "123"
    assert merged["personalInfo"]["summary"] == "General platform profile"
    assert len(merged["workExperience"]) == 2
    assert merged["workExperience"][0]["description"] == [
        "Built APIs",
        "Shipped platform work",
    ]
    assert merged["skills"] == ["Python", "FastAPI"]
    assert merged["languages"] == ["French"]
    assert merged["certifications"] == ["AWS"]


def test_create_empty_master_profile_has_expected_shape() -> None:
    profile = create_empty_master_profile()

    assert profile["personalInfo"]["name"] == ""
    assert profile["workExperience"] == []
    assert profile["projects"] == []
    assert profile["skills"] == []
