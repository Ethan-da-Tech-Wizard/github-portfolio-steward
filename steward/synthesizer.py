# ==============================================================================
# Program: synthesizer.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 18, 2026
# Purpose: Deterministically synthesizes crisp, professional repository descriptions (<250 characters) and standardized GitHub topics based on codebase facts. Uses weighted heuristic scoring to generate search-optimized metadata.
# ==============================================================================
# Role: the pure-logic core of the steward. It takes RepoSummary + CodebaseFacts
# (from steward/scanner.py) and returns a MetadataRecommendation consumed by
# steward/cli.py and steward/updater.py. No network, no clock, no randomness:
# identical inputs always give identical text, which is what lets the CI and
# tests assert exact descriptions.
# Why heuristics and not an LLM: the tool must run offline for free and produce
# diff-stable output; the README's first real paragraph is the best signal.
import re
from typing import List, Optional, Set, Pattern
from steward.models import RepoSummary, CodebaseFacts, MetadataRecommendation


class MetadataSynthesizer:
    """
    ## Generates professional, search-optimized repository descriptions and standardized GitHub topics.
    ## Adheres to strict GitHub API limits and enforces exclusion filters.
    """

    ## Maximum allowed character length for GitHub repository descriptions.
    # GitHub rejects descriptions over 350 chars, but short ones render best on
    # cards; 245 leaves headroom for the '...' suffix and stays under the 250 goal.
    MAX_DESCRIPTION_LENGTH = 245

    ## Maximum character length for a single GitHub topic tag.
    # GitHub's own limit is 50; 35 keeps tags readable and avoids borderline cases.
    MAX_TOPIC_LENGTH = 35

    ## Regex for validating standard GitHub topic format: lowercase alphanumeric with single hyphens.
    # GitHub's topic grammar: lowercase letters/digits, single hyphens, no leading or
    # trailing hyphen. Anything else is rejected by the API, so we filter first.
    _TOPIC_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

    ## Domain keyword mapping based on repo name tokens.
    # Repo-name token -> topics. Matching on name tokens (split on - and _) gives a
    # cheap domain signal when the README is thin. Values are already valid topics.
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
        # Exclusions let the owner keep scratch or private-purpose repos out of the sweep.
        self.exclusion_patterns: List[Pattern] = []
        if exclusions:
            for pattern in exclusions:
                try:
                    self.exclusion_patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error:
                    # A user typing 'my_repo(old' should still exclude that literal name rather
                    # than crash the CLI with re.error.
                    ## If not a valid regex, treat as exact string match escaped.
                    self.exclusion_patterns.append(re.compile(re.escape(pattern), re.IGNORECASE))

    def is_excluded(self, repo_name: str) -> bool:
        """
        ## Evaluates whether a repository name matches any configured exclusion patterns.
        """
        # Match against both 'owner/name' and bare 'name' so patterns work either way.
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
        # Order matters: spaces/underscores become hyphens BEFORE the strip step, or
        # 'C++ Header' would collapse to 'cheader' instead of 'c-header'.
        topic = re.sub(r"[\s_]+", "-", topic)
        ## Strip non-alphanumeric characters except hyphens.
        topic = re.sub(r"[^a-z0-9\-]", "", topic)
        ## Deduplicate consecutive hyphens.
        topic = re.sub(r"-+", "-", topic)
        ## Strip leading or trailing hyphens.
        topic = topic.strip("-")

        # Over-long or empty results are dropped, never truncated: a cut-off tag would
        # be meaningless.
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
        # A set dedupes across the four sources below (language, frameworks, name, CI).
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

        # Python with no detected package manager marker is advertised as
        # zero-dependency, a deliberate portfolio selling point for stdlib-only tools.
        ## Check for zero dependencies in Python or C projects.
        if "Python" in facts.detected_languages and not facts.detected_frameworks:
            derived_topics.add("zero-dependencies")
        # Intentionally a no-op branch: documents that pip projects are NOT labelled
        # zero-dependency, rather than leaving the case implicit.
        elif "pip" in facts.detected_frameworks and not facts.file_count > 50:
            ## If pip is detected with standard setup, keep stdlib/zero-dependency potential.
            pass

        ## Match repo name tokens with domain topics.
        # Lowercase so 'Steward' and 'steward' hit the same keyword.
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

        # Existing topics are kept so applying a recommendation never removes tags the
        # owner added by hand.
        ## Merge existing repository topics.
        for existing in repo.topics:
            norm_existing = self.normalize_topic(existing)
            if norm_existing:
                derived_topics.add(norm_existing)

        ## Clean and sort topics deterministically.
        # Sorted for stable output and stable diffs in dry-run reports.
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
        # Priority order reflects trust: the author's own README sentence beats an old
        # GitHub description, which beats a name-derived fallback.
        ## Priority 1: High quality README snippet.
        if facts.readme_snippet:
            snippet = facts.readme_snippet.strip()
            ## If snippet has multiple sentences, take the first complete sentence.
            # Split after . ! or ? followed by whitespace so 'v1.2' and 'e.g.' mid-sentence
            # dots without a following space are left alone.
            sentence_match = re.split(r"(?<=[.!?])\s+", snippet)
            if sentence_match and len(sentence_match[0]) >= 20:
                first_sentence = sentence_match[0]
                if len(first_sentence) <= self.MAX_DESCRIPTION_LENGTH:
                    return first_sentence

            # Cut at a word boundary and add '...' so descriptions never end mid-word.
            # The -4 reserves room for the three dots plus a safety character.
            ## Truncate cleanly at word boundary if single sentence is too long.
            if len(snippet) <= self.MAX_DESCRIPTION_LENGTH:
                return snippet

            truncated = snippet[: self.MAX_DESCRIPTION_LENGTH - 4]
            last_space = truncated.rfind(" ")
            if last_space > 0:
                truncated = truncated[:last_space]
            return f"{truncated}..."

        # Reuse an existing description if it is already a sensible length; this avoids
        # churn where the tool rewrites text that was fine.
        ## Priority 2: Existing description if already concise and high quality.
        if repo.description and len(repo.description) >= 20 and len(repo.description) <= self.MAX_DESCRIPTION_LENGTH:
            return repo.description.strip()

        # Last resort: build 'Title - built with X - using Y.' from facts alone so every
        # repo ends up with some description.
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
            # Hard cap as a safety net; the final '.' keeps it a complete-looking sentence.
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

        # Compare stripped text so trailing whitespace alone never triggers an update.
        desc_changed = proposed_desc.strip() != current_desc.strip()

        proposed_topics = self.synthesize_topics(repo, facts)
        # Lowercased: GitHub stores topics lowercase, and comparison must match.
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
            # Fixed confidences, not statistical: a README gives a better description source,
            # so those recommendations are marked higher for reviewers skimming the report.
            confidence_score=0.95 if facts.has_readme else 0.85,
            reasoning=reasoning
        )
