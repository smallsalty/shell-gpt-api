import re

from app.skills.nl2bash_skills import NL2BASH_SKILLS


def select_relevant_skills(query: str, limit: int = 6) -> list[dict]:
    scored = []
    query_text = query.lower()
    query_tokens = set(re.findall(r"[a-z0-9_.:-]+|[\u4e00-\u9fff]{1,4}", query_text))

    for skill in NL2BASH_SKILLS:
        score = 0
        haystack = " ".join(
            [
                skill["category"],
                skill["intent"],
                " ".join(skill.get("patterns", [])),
                " ".join(skill.get("tips", [])),
            ]
        ).lower()
        for pattern in skill.get("patterns", []):
            pattern_text = pattern.lower()
            if pattern_text and pattern_text in query_text:
                score += 5
        for token in query_tokens:
            if len(token) > 1 and token in haystack:
                score += 1
        if score:
            scored.append((score, skill))

    scored.sort(key=lambda item: item[0], reverse=True)
    skills = [skill for _, skill in scored[:limit]]
    if not skills:
        skills = NL2BASH_SKILLS[:3]
    return skills


def build_skills_prompt(skills: list[dict]) -> str:
    blocks = []
    for skill in skills:
        templates = "; ".join(skill.get("command_templates", []))
        tips = "; ".join(skill.get("tips", []))
        blocks.append(
            f"- category={skill['category']}; intent={skill['intent']}; "
            f"templates={templates}; tips={tips}"
        )
    return "\n".join(blocks)

