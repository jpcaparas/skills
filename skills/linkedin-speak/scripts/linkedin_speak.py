#!/usr/bin/env python3
"""
Deterministic LinkedIn-speak translator.

Usage examples:
    python3 scripts/linkedin_speak.py "I got a new job."
    python3 scripts/linkedin_speak.py --mode reverse "Thrilled to announce..."
    python3 scripts/linkedin_speak.py --mode both --format json "We launched the dashboard."
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote


OPENERS = [
    "Thrilled to share",
    "Excited to announce",
    "Honored to share",
    "Proud to share",
    "Grateful to share",
]

REFLECTIONS = [
    "Moments like this are a reminder that growth compounds when you keep showing up.",
    "It was a strong reminder that progress is rarely a solo sport.",
    "Experiences like this reinforce how much execution, curiosity, and trust matter.",
    "This was another lesson in what aligned teams can unlock together.",
]

GRATITUDE = [
    "Grateful for the people who made this possible.",
    "Appreciative of everyone who invested time, trust, and candor along the way.",
    "Proud of the team effort behind this milestone.",
    "Thankful for the opportunity to learn, build, and keep raising the bar.",
]

CLOSERS = [
    "Onward.",
    "More to come.",
    "The work continues.",
    "Excited for what comes next.",
]

EMOJIS = ["🚀", "✨", "🙌", "💡", "🔥"]

GENERIC_TAGS = [
    "GrowthMindset",
    "Leadership",
    "Collaboration",
    "Innovation",
    "LearningInPublic",
    "CareerDevelopment",
]

TOPIC_TAGS = {
    "job": ["CareerGrowth", "NewBeginnings", "Leadership"],
    "role": ["CareerGrowth", "Leadership", "Opportunity"],
    "hired": ["Talent", "Leadership", "Hiring"],
    "joined": ["CareerGrowth", "NewBeginnings", "Teamwork"],
    "launch": ["Launch", "Execution", "Innovation"],
    "launched": ["Launch", "Execution", "Innovation"],
    "release": ["Launch", "Execution", "ProductManagement"],
    "released": ["Launch", "Execution", "ProductManagement"],
    "ship": ["Execution", "ProductManagement", "Innovation"],
    "shipped": ["Execution", "ProductManagement", "Innovation"],
    "dashboard": ["Analytics", "DataStrategy", "Innovation"],
    "data": ["Analytics", "DataStrategy", "DecisionMaking"],
    "project": ["ProjectManagement", "Execution", "GrowthMindset"],
    "learned": ["ContinuousLearning", "GrowthMindset", "Curiosity"],
    "study": ["ContinuousLearning", "GrowthMindset", "Curiosity"],
    "course": ["ContinuousLearning", "Upskilling", "GrowthMindset"],
    "fixed": ["ProblemSolving", "Execution", "Resilience"],
    "bug": ["ProblemSolving", "Engineering", "Execution"],
    "migration": ["Engineering", "Execution", "Modernization"],
    "speak": ["PublicSpeaking", "LearningInPublic", "Community"],
    "spoke": ["PublicSpeaking", "LearningInPublic", "Community"],
    "meetup": ["Community", "LearningInPublic", "Networking"],
    "team": ["Teamwork", "Leadership", "Collaboration"],
    "customer": ["CustomerExperience", "Execution", "Innovation"],
}

ACTION_PATTERNS = [
    (re.compile(r"\b(got a new job|new job|joined|accepted a role)\b", re.I), "I'm starting a new chapter with a new role."),
    (re.compile(r"\b(launched|launch|released|release|shipped|ship)\b", re.I), "we officially brought something meaningful into the world."),
    (re.compile(r"\b(finished|completed|wrapped)\b", re.I), "I crossed the finish line on an important piece of work."),
    (re.compile(r"\b(learned|studied|course|certification)\b", re.I), "I invested in learning and leveling up."),
    (re.compile(r"\b(fixed|debugged|bug)\b", re.I), "I turned a challenge into momentum."),
    (re.compile(r"\b(spoke|presented|talked)\b", re.I), "I had the chance to share ideas with a great room of people."),
    (re.compile(r"\b(built|created|made)\b", re.I), "I built something that felt genuinely useful."),
]

HYPE_PATTERNS = [
    re.compile(r"\b(thrilled|excited|honored|proud|grateful)\s+to\s+(share|announce)\b[:,!]?\s*", re.I),
    re.compile(r"\b(starting|stepping into)\s+(a\s+)?new chapter\b[:,!]?\s*", re.I),
    re.compile(r"\b(grateful|thankful|appreciative)\s+for\b[^.?!]*[.?!]?", re.I),
    re.compile(r"\b(moments like this|experiences like this|this was another lesson)[^.?!]*[.?!]?", re.I),
    re.compile(r"\b(onward|more to come|the work continues|excited for what comes next)\b[.?!]?", re.I),
]

REVERSE_REWRITES = [
    (re.compile(r"\bI'?m starting a new chapter with a new role\b", re.I), "I got a new job"),
    (re.compile(r"\bwe officially brought something meaningful into the world\b", re.I), "We launched it"),
    (re.compile(r"\bI crossed the finish line on an important piece of work\b", re.I), "I finished the project"),
    (re.compile(r"\bI invested in learning and leveling up\b", re.I), "I learned something new"),
    (re.compile(r"\bI turned a challenge into momentum\b", re.I), "I fixed the problem"),
    (re.compile(r"\bI had the chance to share ideas with a great room of people\b", re.I), "I gave a talk"),
    (re.compile(r"\bI built something that felt genuinely useful\b", re.I), "I built something useful"),
]


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def stable_index(text: str, size: int, salt: str) -> int:
    digest = hashlib.sha256(f"{salt}:{text}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % size


def choose(options: list[str], text: str, salt: str) -> str:
    return options[stable_index(text, len(options), salt)]


def read_input_text(args: argparse.Namespace) -> str:
    if args.text:
        return normalize_whitespace(args.text)
    if args.input_file:
        return normalize_whitespace(Path(args.input_file).read_text(encoding="utf-8"))
    if not sys.stdin.isatty():
        return normalize_whitespace(sys.stdin.read())
    raise SystemExit("Provide text, --input-file, or stdin.")


def detect_tags(text: str, target_count: int) -> list[str]:
    lowered = text.lower()
    tags: list[str] = []
    for keyword, candidates in TOPIC_TAGS.items():
        if keyword in lowered:
            for candidate in candidates:
                if candidate not in tags:
                    tags.append(candidate)
    for fallback in GENERIC_TAGS:
        if fallback not in tags:
            tags.append(fallback)
    return tags[:target_count]


def restate_action(text: str) -> str:
    for pattern, statement in ACTION_PATTERNS:
        if pattern.search(text):
            return statement
    cleaned = text.rstrip(".!?")
    if cleaned[:1].islower():
        cleaned = cleaned[:1].upper() + cleaned[1:]
    if cleaned:
        return cleaned + "."
    return "I moved something important forward."


def translate(text: str, intensity: int = 3, include_hashtags: bool = True, include_emoji: bool = True) -> str:
    normalized = normalize_whitespace(text)
    opener = choose(OPENERS, normalized, "opener")
    reflection = choose(REFLECTIONS, normalized, "reflection")
    gratitude = choose(GRATITUDE, normalized, "gratitude")
    closer = choose(CLOSERS, normalized, "closer")
    emoji = choose(EMOJIS, normalized, "emoji")

    statements = [
        f"{opener} that {restate_action(normalized)}",
    ]

    if intensity >= 2:
        statements.append(reflection)
    if intensity >= 3:
        statements.append(gratitude)
    if intensity >= 4:
        statements.append("Pushing through ambiguity, aligning people, and staying close to the work still matters.")
    if intensity >= 5:
        statements.append(closer)

    body = " ".join(statement.strip() for statement in statements if statement.strip())
    if include_emoji:
        body = f"{body} {emoji}".strip()

    if include_hashtags:
        tag_count = 2 + min(max(intensity, 1), 5)
        hashtags = " ".join(f"#{tag}" for tag in detect_tags(normalized, tag_count))
        body = f"{body} {hashtags}".strip()

    return normalize_whitespace(body)


def reverse(text: str) -> str:
    stripped = normalize_whitespace(text)
    stripped = re.sub(r"#[A-Za-z][A-Za-z0-9_]*", "", stripped)
    stripped = re.sub(r"[\U0001F300-\U0001FAFF]", "", stripped)
    for pattern, replacement in REVERSE_REWRITES:
        stripped = pattern.sub(replacement, stripped)
    for pattern in HYPE_PATTERNS:
        stripped = pattern.sub("", stripped)
    stripped = re.sub(r"\bthat\s+(i|we)\b", lambda match: match.group(1).upper(), stripped, flags=re.I)
    stripped = re.sub(r"\b(officially|incredibly|meaningful|rewarding|amazing|impactful)\b", "", stripped, flags=re.I)
    stripped = re.sub(r"\b(journey|chapter|momentum|alignment|execution|growth)\b", "", stripped, flags=re.I)
    stripped = re.sub(r"\s+", " ", stripped)
    stripped = stripped.strip(" .,!?:;-")
    if not stripped:
        return "This is an overblown LinkedIn post with very little concrete information."
    if not stripped.endswith("."):
        stripped += "."
    return stripped[:1].upper() + stripped[1:]


def build_kagi_compare_url(text: str, mode: str) -> str:
    target = "linkedin" if mode != "reverse" else "en"
    source = "en" if mode != "reverse" else "linkedin"
    return (
        "https://translate.kagi.com/?from="
        f"{source}&to={target}&text={quote(text)}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Translate plain text into LinkedIn-speak or reverse it.")
    parser.add_argument("text", nargs="?", help="Input text to translate.")
    parser.add_argument("--input-file", help="Read input text from a file.")
    parser.add_argument("--mode", choices=["translate", "reverse", "both"], default="translate")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--intensity", type=int, default=3, help="Parody intensity from 1 to 5.")
    parser.add_argument("--no-hashtags", action="store_true", help="Do not append hashtags.")
    parser.add_argument("--no-emoji", action="store_true", help="Do not append emoji.")
    parser.add_argument("--compare-kagi-url", action="store_true", help="Include a prefilled Kagi Translate comparison URL.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    text = read_input_text(args)
    intensity = min(5, max(1, args.intensity))

    translated = translate(text, intensity=intensity, include_hashtags=not args.no_hashtags, include_emoji=not args.no_emoji)
    reversed_text = reverse(text if args.mode == "reverse" else translated)
    compare_url = build_kagi_compare_url(text, args.mode)

    if args.mode == "translate":
        payload = translated
    elif args.mode == "reverse":
        payload = reverse(text)
    else:
        payload = {
            "translation": translated,
            "reverse": reverse(translated),
        }

    if args.format == "json":
        response = {
            "mode": args.mode,
            "input": text,
            "metadata": {
                "intensity": intensity,
                "hashtags_included": not args.no_hashtags,
                "emoji_included": not args.no_emoji,
            },
        }
        if args.mode == "both":
            response.update(payload)
        else:
            response["output"] = payload
        if args.compare_kagi_url:
            response["metadata"]["kagi_compare_url"] = compare_url
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return 0

    if args.mode == "both":
        print("LinkedIn-speak:")
        print(payload["translation"])
        print()
        print("Reverse:")
        print(payload["reverse"])
    else:
        print(payload)

    if args.compare_kagi_url:
        print()
        print(f"Kagi compare URL: {compare_url}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
