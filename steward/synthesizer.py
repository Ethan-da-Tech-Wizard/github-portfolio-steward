"""
Program: GitHub Portfolio Steward - Metadata Synthesizer
Programmer: Ethan-da-Tech-Wizard
Last Modified: 11/08/2026
Purpose: Deterministically synthesizes crisp, professional repository descriptions (<250 characters) and standardized GitHub topics based on codebase facts.
"""

import re
from typing import List, Optional, Set, Pattern
from steward.models import RepoSummary, CodebaseFacts, MetadataRecommendation


class MetadataSynthesizer:
    """
    ## Generates professional, search-optimized repository descriptions and standardized GitHub topics.
    ## Adheres to strict GitHub API limits and enforces exclusion filters.
    """

    ## Maximum allowed character length for GitHub repository descriptions.
    MAX_DESCRIPTION_LENGTH = 245

    ## Maximum character length for a single GitHub topic tag.
    MAX_TOPIC_LENGTH = 35

    ## Regex for validating standard GitHub topic format: lowercase alphanumeric with single hyphens.
    _TOPIC_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

    ## Domain keyword mapping based on repo name tokens.
    _NAME_KEYWORD_TOPICS = {
        "steward": ["portfolio", "automation", "codebase-analysis"],
        "portfolio": ["portfolio", "showcase"],
        "curator": ["curation", "metadata"],
        "cli": ["cli", "command-line"],
        "daemon": ["daemon", "background-service", "systemd"],
        "systemd": ["systemd", "linux"],
        "docker": ["docker", "containerization"],
        "agent": ["autonomous-agent", "automation"],
        "agents": ["multi-agent-systems", "automation"],
        "api": ["api", "rest-api"],
        "scraper": ["scraper", "data-extraction"],
        "crawler": ["crawler", "web-scraping"],
        "auth": ["authentication", "security"],
        "guard": ["security", "guardrail"],
        "monitor": ["monitoring", "telemetry"],
        "telemetry": ["telemetry", "metrics"],
        "engine": ["engine", "architecture"],
        "analyzer": ["analyzer", "static-analysis"],
        "parser": ["parser", "compiler"],
        "compiler": ["compiler", "language-design"],
        "kernel": ["kernel", "operating-system"],
        "firmware": ["firmware", "embedded"],
        "wasm": ["webassembly", "wasm"],
    }

    def __init__(self, exclusions: Optional[List[str]] = None):
        """
        ## Initialize synthesizer with optional regex or string exclusion patterns.
        """
        self.exclusion_patterns: List[Pattern] = []
        if exclusions:
            for pattern in exclusions:
                try:
                    self.exclusion_patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error:
                    ## If not a valid regex, treat as exact string match escaped.
                    self.exclusion_patterns.append(re.compile(re.escape(pattern), re.IGNORECASE))

    def is_excluded(self, repo_name: str) -> bool:
        """
        ## Evaluates whether a repository name matches any configured exclusion patterns.
        """
        name_only = repo_name.split("/")[-1]
        for pattern in self.exclusion_patterns:
            if pattern.search(repo_name) or pattern.search(name_only):
                return True
        return False

    def normalize_topic(self, raw_topic: str) -> Optional[str]:
        """
        ## Normalizes a candidate string into a valid GitHub topic tag.
        ## Converts to lowercase, substitutes non-alphanumeric characters with hyphens,
        ## and verifies bounds.
        """
        if not raw_topic:
            return None

        topic = raw_topic.strip().lower()
        ## Replace underscores and spaces with hyphens.
        topic = re.sub(r"[\s_]+", "-", topic)
        ## Strip non-alphanumeric characters except hyphens.
        topic = re.sub(r"[^a-z0-9\-]", "", topic)
        ## Deduplicate consecutive hyphens.
        topic = re.sub(r"-+", "-", topic)
        ## Strip leading or trailing hyphens.
        topic = topic.strip("-")

        if not topic or len(topic) > self.MAX_TOPIC_LENGTH:
            return None

        if self._TOPIC_PATTERN.match(topic):
            return topic
        return None

    def synthesize_topics(
        self,
        repo: RepoSummary,
        facts: CodebaseFacts
    ) -> List[str]:
        """
        ## Derives an optimal, deduplicated list of GitHub topic tags from codebase facts.
        """
        derived_topics: Set[str] = set()

        ## Include primary language.
        if repo.primary_language:
            norm_lang = self.normalize_topic(repo.primary_language)
            if norm_lang:
                derived_topics.add(norm_lang)

        ## Include detected languages from codebase scan.
        for lang in facts.detected_languages:
            norm_lang = self.normalize_topic(lang)
            if norm_lang:
                derived_topics.add(norm_lang)

        ## Include framework and ecosystem tags.
        for fw in facts.detected_frameworks:
            norm_fw = self.normalize_topic(fw)
            if norm_fw:
                derived_topics.add(norm_fw)

        ## Check for zero dependencies in Python or C projects.
        if "Python" in facts.detected_languages and not facts.detected_frameworks:
            derived_topics.add("zero-dependencies")
        elif "pip" in facts.detected_frameworks and not facts.file_count > 50:
            ## If pip is detected with standard setup, keep stdlib/zero-dependency potential.
            pass

        ## Match repo name tokens with domain topics.
        repo_short_name = repo.name.lower()
        tokens = re.split(r"[\-_]", repo_short_name)
        for token in tokens:
            if token in self._NAME_KEYWORD_TOPICS:
                for kw in self._NAME_KEYWORD_TOPICS[token]:
                    norm_kw = self.normalize_topic(kw)
                    if norm_kw:
                        derived_topics.add(norm_kw)

        ## Incorporate testing and CI indicators.
        if facts.has_ci:
            derived_topics.add("github-actions")
            derived_topics.add("ci-cd")

        ## Merge existing repository topics.
        for existing in repo.topics:
            norm_existing = self.normalize_topic(existing)
            if norm_existing:
                derived_topics.add(norm_existing)

        ## Clean and sort topics deterministically.
        sorted_topics = sorted(list(derived_topics))
        return sorted_topics

    def synthesize_description(
        self,
        repo: RepoSummary,
        facts: CodebaseFacts
    ) -> str:
        """
        ## Deterministically crafts a clear, active-voice repository description (<250 characters).
        """
        ## Priority 1: High quality README snippet.
        if facts.readme_snippet:
            snippet = facts.readme_snippet.strip()
            ## If snippet has multiple sentences, take the first complete sentence.
            sentence_match = re.split(r"(?<=[.!?])\s+", snippet)
            if sentence_match and len(sentence_match[0]) >= 20:
                first_sentence = sentence_match[0]
                if len(first_sentence) <= self.MAX_DESCRIPTION_LENGTH:
                    return first_sentence

            ## Truncate cleanly at word boundary if single sentence is too long.
            if len(snippet) <= self.MAX_DESCRIPTION_LENGTH:
                return snippet

            truncated = snippet[: self.MAX_DESCRIPTION_LENGTH - 4]
            last_space = truncated.rfind(" ")
            if last_space > 0:
                truncated = truncated[:last_space]
            return f"{truncated}..."

        ## Priority 2: Existing description if already concise and high quality.
        if repo.description and len(repo.description) >= 20 and len(repo.description) <= self.MAX_DESCRIPTION_LENGTH:
            return repo.description.strip()

        ## Priority 3: Fallback synthesized description from structural facts.
        name_words = [w.capitalize() for w in re.split(r"[\-_]", repo.name)]
        title = " ".join(name_words)

        primary_lang = repo.primary_language or (facts.detected_languages[0] if facts.detected_languages else "")
        framework_summary = ", ".join(facts.detected_frameworks[:2]) if facts.detected_frameworks else ""

        desc_parts = [title]
        if primary_lang:
            desc_parts.append(f"built with {primary_lang}")
        if framework_summary:
            desc_parts.append(f"using {framework_summary}")

        synthesized = " - ".join(desc_parts) + "."
        if len(synthesized) > self.MAX_DESCRIPTION_LENGTH:
            synthesized = synthesized[: self.MAX_DESCRIPTION_LENGTH - 1] + "."

        return synthesized

    def recommend(
        self,
        repo: RepoSummary,
        facts: CodebaseFacts
    ) -> MetadataRecommendation:
        """
        ## Compares existing repository metadata against proposed values and returns a recommendation.
        """
        proposed_desc = self.synthesize_description(repo, facts)
        current_desc = repo.description or ""

        desc_changed = proposed_desc.strip() != current_desc.strip()

        proposed_topics = self.synthesize_topics(repo, facts)
        current_topics_set = set(t.lower() for t in repo.topics)
        topics_to_add = [t for t in proposed_topics if t.lower() not in current_topics_set]

        reasoning: List[str] = []
        if not current_desc:
            reasoning.append("Repository lacks a description; synthesized from codebase analysis.")
        elif desc_changed:
            reasoning.append("Proposed clearer, standardized description based on README overview.")

        if topics_to_add:
            reasoning.append(f"Identified {len(topics_to_add)} missing searchable topics based on file markers.")

        return MetadataRecommendation(
            repo_name=repo.full_name or repo.name,
            current_description=repo.description,
            proposed_description=proposed_desc,
            description_changed=desc_changed,
            current_topics=repo.topics,
            proposed_topics=proposed_topics,
            topics_to_add=topics_to_add,
            confidence_score=0.95 if facts.has_readme else 0.85,
            reasoning=reasoning
        )
