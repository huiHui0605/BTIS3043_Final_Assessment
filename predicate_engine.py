import re

# ---------------------------------------------------------------------------
# Keyword lists used by the crisp (predicate) query layer.
#
# Why keyword lists instead of, say, a machine-learning classifier:
# the assessment asks for predicate reasoning - i.e. a record either
# satisfies a defined condition or it doesn't. Matching against curated
# vocabulary lists is a simple, transparent and explainable way to
# implement that "yes/no" condition for topic relevance.
# ---------------------------------------------------------------------------

# Keyword lists for Scenario 1
# Terms that indicate a book is directly about Artificial Intelligence /
# intelligent systems (highest-priority match for Scenario 1).
KEYWORDS_AI = [
    "artificial intelligence", "intelligent system", "machine learning", "computer vision", 
    "robotics", "intelligent systems", "expert systems", "neural networks"
]

# Terms that indicate a book provides programming-language / software
# engineering foundations relevant to AI study (second-priority match).
KEYWORDS_PROGRAMMING = [
    "python", "java", "c++", "c how to program", "c language", "javascript", "programming", 
    "algorithm", "algorithms", "data structure", "data structures", "software engineering", "software design", "object-oriented", 
    "object oriented", "web development", "web programming", "software product", "visual basic", 
    "object oriented programming", "c#"
]

# Terms that indicate a book provides mathematical foundations relevant
# to AI study (third-priority match).
KEYWORDS_MATHEMATICS = [
    "mathematics", "mathematical", "maths", "statistics", "probability", "algebra", "calculus", 
    "optimization", "numerical", "decision analysis", "linear algebra", "discrete math", 
    "discrete mathematics", "applied math", "business math", "developmental math", 
    "advanced math", "actuarial math", "research methods for business"
]

# Strict exclusions for Scenario 1 to reject graphic design, Adobe software, digital arts, and vocational trades
# These titles/disciplines can superficially resemble a match (e.g. they
# may mention "algebra" or software tools) but are not genuinely relevant
# to an AI/programming/mathematics review, so they're screened out before
# any keyword matching happens.
EXCLUSIONS_SC1 = [
    "adobe", "illustrator", "indesign", "photoshop", "creative cloud", "dreamweaver", "premier pro", 
    "graphic design", "design collection", "3d animation", "3d modeling", "3d max", "fashion", 
    "algebra-based", "intermediate microeconomics (algebra)", "financial algebra"
]

# Scenario 2 keywords divided into direct security and generic security terms
# Terms that unambiguously indicate cybersecurity / secure-computing
# content - matching any one of these is enough to accept the record
# without needing further context checks.
DIRECT_SECURITY_KWS = [
    "cybersecurity", "cyber security", "cyber-security", "computer security", "network security",
    "information security", "cloud security", "system security", "systems security", "database security",
    "web security", "cryptography", "cryptographic", "cryptology", "encryption", "decryption",
    "cipher", "ciphers", "privacy", "data privacy", "information privacy", "information assurance",
    "security assurance", "secure computing", "secure systems", "secure system", "security systems",
    "security awareness", "ethical hacking", "hacking", "hacker", "penetration testing", "pen testing",
    "vulnerability assessment", "intrusion detection", "intrusion prevention",
    "firewall", "firewalls", "malware", "antivirus", "cybercrime", "security analyst"
]

# Generic words that are ambiguous on their own ("security"/"secure" could
# just as easily belong to finance, law or physical security) and
# therefore need extra "is this actually about computing?" context
# checking before they're accepted (see evaluate_scenario_2 below).
GENERIC_SECURITY_KWS = [
    "security", "secure"
]

# Related (but not directly-named) security terms: still relevant enough to satisfy
# the Scenario 2 predicate, but classified separately (not "Direct security relevance")
# during fuzzy evaluation.
RELATED_SECURITY_KWS = [
    "forensics", "computer forensics", "network forensics", "cyber forensics",
    "digital forensics", "incident response", "disaster recovery"
]

# Scenario 2 non-computing exclusions to eliminate finance, law, food, and social security
# Same idea as EXCLUSIONS_SC1: catches phrases that contain "security" but
# are clearly not about cybersecurity, so they don't slip through the
# GENERIC_SECURITY_KWS context check below.
EXCLUSIONS_SC2 = [
    "food security", "social security", "national security", "financial security",
    "job security", "homeland security", "securities law", "security analysis",
    "security analysis and portfolio", "port security", "auditing and assurance",
    "border security", "security guard", "security market", "security markets"
]

class PredicateEngine:
    """
    Implements the crisp (boolean/predicate) query layer of the system:
    for a given eBook record, decide PASS/REJECT against the fixed
    conditions defined for Scenario 1 or Scenario 2, and explain why.

    This is deliberately separate from FuzzyEngine: predicate logic
    answers "does this record satisfy the query?" (a hard yes/no),
    while the fuzzy layer (in fuzzy_engine.py) answers the softer
    question "how suitable is this record, by degree?" for records
    that already passed the predicate check.
    """
    def __init__(self):
        pass

    def clean_text(self, text):
        """Normalises a value to a lowercased, whitespace-trimmed string
        (or an empty string for anything that isn't already text), so
        every keyword comparison in this class works on consistent input."""
        if not isinstance(text, str):
            return ""
        return text.lower().strip()

    def check_keywords(self, text, keywords):
        """
        Returns the subset of `keywords` that appear in `text` as whole
        words/phrases (not as a substring of a longer, unrelated word).

        Why word-boundary regex instead of a plain substring check:
        a plain "kw in text" test would let "c" match inside "vaccine"
        or "algebra" match inside "prealgebra"-like false positives.
        \b boundaries are only added on a side of the keyword that
        starts/ends with an alphanumeric character, so multi-word
        phrases (e.g. "computer vision") still match correctly.
        """
        cleaned = self.clean_text(text)
        matched = []
        for kw in keywords:
            kw_clean = kw.lower()
            if not kw_clean:
                continue
            escaped = re.escape(kw_clean)
            lead_b = r'\b' if kw_clean[0].isalnum() else ''
            trail_b = r'\b' if kw_clean[-1].isalnum() else ''
            pattern = lead_b + escaped + trail_b
            if re.search(pattern, cleaned):
                matched.append(kw)
        return matched

    def evaluate_scenario_1(self, row, dataset_type):
        """
        Evaluates a row for Scenario 1 (AI, Programming, Math).
        dataset_type: 'A', 'B', or 'C'
        Returns: (passed, category, reason, predicate_details)
        """
        title = row.get('Title', '')
        title_cleaned = self.clean_text(title)

        # Step 1: check the title itself against the exclusion list first.
        # Exclusions are checked before inclusion keywords so that, e.g.,
        # an "Adobe Photoshop" book mentioning "3D modeling" is rejected
        # outright rather than accidentally matching a programming term.
        is_excl = False
        excl_reason = ""
        for excl in EXCLUSIONS_SC1:
            if excl in title_cleaned:
                is_excl = True
                excl_reason = f"Excluded: matches non-CS term '{excl}'"
                break

        # Step 2: if the title didn't trigger an exclusion, also check the
        # dataset-specific discipline/category classification text (each
        # dataset stores subject classification differently - see the
        # per-dataset branches below).
        if not is_excl:
            disc_text = ""
            if dataset_type == 'B':
                disc_text = " ".join([str(row.get(f'Discipline (Level {i})', '')) for i in range(1, 5)])
            elif dataset_type == 'C':
                disc_val = str(row.get('Discipline', ''))
                if disc_val != "IT, Programming, Web Development":
                    disc_text = str(row.get('Category', '')) + " " + disc_val
            disc_cleaned = self.clean_text(disc_text)
            for excl in EXCLUSIONS_SC1:
                if excl in disc_cleaned:
                    is_excl = True
                    excl_reason = f"Excluded: matches non-CS term '{excl}' in discipline"
                    break

        if is_excl:
            # Short-circuit: an excluded record automatically fails the
            # predicate, regardless of what its year/format would say.
            pred_details = {
                'topic_match': 'Fail',
                'year_match': 'Pass'
            }
            if dataset_type in ['B', 'C']:
                pred_details['format_match'] = 'Pass'
            return False, "None", excl_reason, pred_details

        # 1. Topic Predicate
        # Build the text to search: always the title, plus dataset-specific
        # extra context (discipline hierarchy for B, category/discipline for
        # C unless it's the generic "IT, Programming, Web Development"
        # bucket, or the recommending department for A which has no
        # discipline field of its own).
        text_to_check = title
        if dataset_type == 'B':
            text_to_check += " " + str(row.get('Discipline (Level 1)', '')) + " " + \
                             str(row.get('Discipline (Level 2)', '')) + " " + \
                             str(row.get('Discipline (Level 3)', '')) + " " + \
                             str(row.get('Discipline (Level 4)', ''))
        elif dataset_type == 'C':
            disc_val = str(row.get('Discipline', ''))
            if disc_val != "IT, Programming, Web Development":
                text_to_check += " " + str(row.get('Category', '')) + " " + disc_val
        elif dataset_type == 'A':
            text_to_check += " " + str(row.get('Recommended by', ''))

        ai_matches = self.check_keywords(text_to_check, KEYWORDS_AI)
        prog_matches = self.check_keywords(text_to_check, KEYWORDS_PROGRAMMING)
        math_matches = self.check_keywords(text_to_check, KEYWORDS_MATHEMATICS)

        topic_class = None
        relevance_reason = ""

        # Priority: AI > Programming > Math
        # A record that matches multiple categories is classified under
        # the highest-priority one, per the assessment's requirement to
        # distinguish "directly AI-related" from merely-supporting content.
        if ai_matches:
            topic_class = "Directly AI-related"
            relevance_reason = f"Matches AI terms: {', '.join(ai_matches)}"
        elif prog_matches:
            topic_class = "Programming Support"
            relevance_reason = f"Matches Programming terms: {', '.join(prog_matches)}"
        elif math_matches:
            topic_class = "Mathematical Support"
            relevance_reason = f"Matches Math terms: {', '.join(math_matches)}"

        topic_pass = topic_class is not None

        # Scenario 1 has no Year limit (predicate level)
        # Recency is treated as a soft/fuzzy preference for Scenario 1, not
        # a hard cutoff, so it always passes at the predicate stage.
        year_pass = True

        # Scenario 1 has no format limit (predicate level)
        # Likewise, eBook format suitability is only evaluated fuzzily.
        format_pass = True

        passed = topic_pass and year_pass and format_pass

        reasons = []
        if not topic_pass: reasons.append("No matching AI/Prog/Math topic keywords")

        reason_str = relevance_reason if passed else "; ".join(reasons)

        # predicate_details records which individual conditions passed/
        # failed, so the report generator can show a transparent
        # breakdown (not just the final PASS/REJECT verdict).
        pred_details = {
            'topic_match': 'Pass' if topic_pass else 'Fail',
            'year_match': 'Pass' if year_pass else 'Fail'
        }
        if dataset_type in ['B', 'C']:
            pred_details['format_match'] = 'Pass' if format_pass else 'Fail'

        return passed, topic_class if passed else "None", reason_str, pred_details

    def evaluate_scenario_2(self, row, dataset_type):
        """
        Evaluates a row for Scenario 2 (Cybersecurity & Secure Computing).
        dataset_type: 'A', 'B', or 'C'
        Returns: (passed, category, reason, predicate_details)
        """
        title = row.get('Title', '')
        title_lower = title.lower()

        # Check exclusion list first (same rationale as Scenario 1: catch
        # titles that merely contain "security"-adjacent words but are
        # about finance/law/physical security, not computing security).
        is_excl = False
        excl_reason = ""
        for excl in EXCLUSIONS_SC2:
            if excl in title_lower:
                is_excl = True
                excl_reason = f"Excluded: matches non-computing security term '{excl}'"
                break

        # Also check discipline/category if available
        if not is_excl:
            disc_text = ""
            if dataset_type == 'B':
                disc_text = " ".join([str(row.get(f'Discipline (Level {i})', '')) for i in range(1, 5)])
            elif dataset_type == 'C':
                disc_val = str(row.get('Discipline', ''))
                if disc_val != "IT, Programming, Web Development":
                    disc_text = str(row.get('Category', '')) + " " + disc_val
            disc_cleaned = self.clean_text(disc_text)
            for excl in EXCLUSIONS_SC2:
                if excl in disc_cleaned:
                    is_excl = True
                    excl_reason = f"Excluded: matches non-computing security term '{excl}' in discipline"
                    break

        if is_excl:
            pred_details = {
                'topic_match': 'Fail',
                'year_match': 'Pass'
            }
            if dataset_type in ['B', 'C']:
                pred_details['format_match'] = 'Pass'
            return False, "None", excl_reason, pred_details

        # 1. Topic Predicate
        # Same per-dataset context-building logic as evaluate_scenario_1.
        text_to_check = title
        if dataset_type == 'B':
            text_to_check += " " + str(row.get('Discipline (Level 1)', '')) + " " + \
                             str(row.get('Discipline (Level 2)', '')) + " " + \
                             str(row.get('Discipline (Level 3)', '')) + " " + \
                             str(row.get('Discipline (Level 4)', ''))
        elif dataset_type == 'C':
            disc_val = str(row.get('Discipline', ''))
            if disc_val != "IT, Programming, Web Development":
                text_to_check += " " + str(row.get('Category', '')) + " " + disc_val
        elif dataset_type == 'A':
            text_to_check += " " + str(row.get('Recommended by', ''))

        text_cleaned = self.clean_text(text_to_check)

        # Check direct security matches: unambiguous cybersecurity terms -
        # matching any of these is sufficient on its own.
        direct_matches = []
        for kw in DIRECT_SECURITY_KWS:
            if kw in text_cleaned:
                direct_matches.append(kw)

        # Check generic ("security"/"secure") matches - these need extra
        # context confirmation before being accepted (see below).
        generic_matches = []
        for kw in GENERIC_SECURITY_KWS:
            if kw in text_cleaned:
                generic_matches.append(kw)

        # Check related-but-not-directly-named security terms (forensics,
        # incident response, disaster recovery) - accepted as on-topic but
        # tracked separately for the fuzzy "relationship" label later.
        related_matches = []
        for kw in RELATED_SECURITY_KWS:
            if kw in text_cleaned:
                related_matches.append(kw)

        topic_pass = False
        topic_class = "None"
        relevance_reason = ""

        if direct_matches:
            topic_pass = True
            topic_class = "Cybersecurity / Secure Computing"
            relevance_reason = f"Matches cybersecurity terms: {', '.join(direct_matches)}"
        elif generic_matches:
            # A bare "security"/"secure" hit is only accepted if there's
            # separate evidence the record is actually about computing -
            # otherwise "security" alone is too ambiguous (could be
            # social/financial/national security, etc.).
            context_ok = False
            cs_words = ["computing", "computer", "engineering", "information technology", "cs/it", "it,", "software", "network", "digital", "data communication", "database"]

            # Check Category/Discipline if available
            disc_text = ""
            if dataset_type == 'B':
                disc_text = " ".join([str(row.get(f'Discipline (Level {i})', '')) for i in range(1, 5)])
            elif dataset_type == 'C':
                disc_val = str(row.get('Discipline', ''))
                if disc_val != "IT, Programming, Web Development":
                    disc_text = str(row.get('Category', '')) + " " + disc_val

            if disc_text:
                # Prefer checking the structured discipline/category text
                # when it's available - it's a more reliable signal than
                # scanning the free-text title.
                disc_cleaned = self.clean_text(disc_text)
                context_ok = any(w in disc_cleaned for w in cs_words)
            else:
                # No discipline, check title for context
                context_ok = any(w in title_lower for w in cs_words)

            if context_ok:
                topic_pass = True
                topic_class = "Cybersecurity / Secure Computing"
                relevance_reason = f"Matches security terms in CS context: {', '.join(generic_matches)}"
            else:
                relevance_reason = f"Excluded: generic security term '{', '.join(generic_matches)}' lacks computing context"
        elif related_matches:
            topic_pass = True
            topic_class = "Cybersecurity / Secure Computing"
            relevance_reason = f"Matches related security terms: {', '.join(related_matches)}"

        topic_pass = topic_pass

        # 2. Year Predicate (Copyright Year >= 2010)
        # Unlike Scenario 1, Scenario 2 does apply a hard recency cutoff at
        # the predicate level: records older than 2010 are rejected
        # outright, reflecting how quickly security guidance goes stale.
        year = None
        if dataset_type == 'A':
            year = row.get('Copyright Year', None)
        elif dataset_type == 'B':
            year = row.get('Copyright', None)
        elif dataset_type == 'C':
            year = row.get('Copyright Year', None)

        year_pass = True
        if year is not None and not np_isnan(year):
            year_pass = int(year) >= 2010

        # 3. Scenario 2 has no format limit (predicate level)
        format_pass = True

        passed = topic_pass and year_pass and format_pass

        reasons = []
        if not topic_pass: reasons.append(relevance_reason if relevance_reason else "No matching Cybersecurity keywords")
        if not year_pass: reasons.append(f"Year is older than 2010")

        reason_str = relevance_reason if passed else "; ".join(reasons)

        pred_details = {
            'topic_match': 'Pass' if topic_pass else 'Fail',
            'year_match': 'Pass' if year_pass else 'Fail'
        }
        if dataset_type in ['B', 'C']:
            pred_details['format_match'] = 'Pass' if format_pass else 'Fail'

        return passed, topic_class if passed else "None", reason_str, pred_details

def np_isnan(val):
    """Safe NaN check that tolerates non-numeric input (e.g. None or a
    string) by returning False instead of raising, since np.isnan() only
    accepts numeric types."""
    try:
        import numpy as np
        return np.isnan(val)
    except:
        return False
