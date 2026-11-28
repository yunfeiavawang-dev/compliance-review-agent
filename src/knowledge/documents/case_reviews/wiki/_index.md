# Compliance Review Wiki — Topic Index

**Document ID:** WIKI-INDEX-001
**Version:** 1.0
**Last Updated:** 2024-12-06
**Owner:** Compliance Operations
**Classification:** Internal — Compliance Staff Only

---

This wiki supplements the weekly retrospectives (RETRO-*) with evergreen decision guidance organized by scenario type. Each page collects policy references, decision patterns, and anonymized case examples that the AI agent retrieves during reviews.

## Topics

| Slug | Title | Description |
|------|-------|-------------|
| expired_documents | Expired / Near-Expiry Documents | Handling identity documents that are expired or approaching expiry at submission time |
| sanctions_potential_match | Sanctions Fuzzy Match | Evaluating potential sanctions list matches, including transliteration and common-name false positives |
| pep_with_mitigants | PEP with Mitigating Factors | Assessing Politically Exposed Persons who present strong risk mitigants (cooling-off period, documented wealth) |
| cross_border_corporate | Cross-Border Corporate Structures | Reviewing corporate customers with multi-jurisdiction operations and complex ownership |

## How to Use

- **Analysts:** Reference these pages when encountering a scenario type for the first time, or when the AI agent cites a wiki page in its reasoning.
- **AI Agent:** These pages are chunked and ingested into the RAG knowledge base. The agent retrieves relevant sections via `search_policy` and `search_precedent` tools.
- **Compliance Officers:** Review and update pages quarterly, or when policy changes affect the decision patterns documented here.

## Maintenance

New entries are added via the `wiki_builder` module, which auto-categorizes closed cases and generates draft wiki entries for human review. See `src/knowledge/wiki_builder.py`.
