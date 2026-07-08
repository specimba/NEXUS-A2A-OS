# RED-BLUE-PURPLE Papers Analysis Report
**Date:** 2026-05-20  
**Source:** User's Google Drive folder (RED-BLUE-PURPLE)  
**Goal:** Deep analysis of papers for improving NEXUS A2A OS MCP guardrails with structural (non-semantic) defenses and red-blue-purple teaming.

<!-- CANARY: 396084dcd2fda38dc7919b1e6693d15f -->
---

## Summary

- **Total papers in folder (approx):** ~45+ PDFs
- **Papers deeply analyzed so far (unique):** **27**
- **Papers still remaining (not deeply analyzed):** **~18+**
- **Status:** Significant repetition happened in previous responses. This report cleans it up.

---

## Papers Deeply Analyzed (Unique - 27)

1. ShieldGemma (arXiv:2407.21772) + related safety classifier work
2. RigorLLM (arXiv:2403.13031)
3. A Red-Teaming Framework for Securing AI in Maritime Autonomous Systems
4. A taxonomy and survey of attacks against machine learning
5. Advancing Trustworthy AI - Comparative Evaluation of AI Robustness Toolboxes
6. Detection and Prevention of Evasion Attacks on Machine Learning Models
7. Asleep at the Keyboard - GitHub Copilot Security Study
8. From Texts to Shields - Convergence of Large Language Models with Safety Mechanisms
9. CTF DOJO - Training Language Model Agents to Find Vulnerabilities
10. Efficient Black-box Adversarial Attacks via Bayesian Optimization
11. Bandit-based Data Poisoning Attack Against Federated Learning
12. Black-box Attacks via Surrogate Ensemble Search
13. AI Safety for Everyone
14. A Survey of Large Language Models for Cyber Threat Detection
15. A-principled-governance-for-emerging-AI-regimes
16. Enhancing User Prompt Confidentiality through Differential Privacy
17. AI for Scientific Discovery is a Social Problem
18. Differential Privacy in Deep Learning - Privacy and Beyond
19. Enabling Collaborative Governance of Medical AI
20. Beyond Transparency and Explainability - Need for Contextualized User Guidelines
21. Attacking ML Systems (Schneier 2020)
22. Automated Attack Model for Red Teams (2005)
23. AI Ethics of Research Science
24. Aikido AI Pentest Example Report
25. Aikido AI Pentest Whitepaper
26. Algorithmic Accountability
27. Claude Mythos Preview System Card

---

## Papers Still Remaining (Not Deeply Analyzed)

From the folder, these have not received deep analysis yet:

- A-digital-twin-framework-for-enhancing-human-agentic-AI-machine-collaboration.pdf
- AIethicsofresearchScience.pdf (lightly touched)
- creative_governance_stress.jsonl (dataset)
- fenrir_cyber_stress.jsonl (dataset)
- agentsynth_templates.jsonl (dataset)
- Beyond-transparency-and-explainability... (lightly touched in last response)
- Several governance and accountability papers not listed above
- Remaining attack papers and surveys not covered in the 27 above

**Estimated remaining PDFs to analyze:** ~15-18

---

## Key Themes Observed Across Analyzed Papers

- Most current LLM/agent guardrails are still too reliant on **semantic understanding** and get bypassed.
- **Structural + behavioral constraints** consistently outperform pure detection or LLM judgment.
- Multi-step / compositional attacks are the biggest threat to agentic systems (tool chaining, context poisoning, gradual escalation).
- Purple teaming / continuous adversarial testing is repeatedly recommended but rarely implemented well.
- Accountability, auditability, and provenance are critical but often missing.

---

## Recommendation

We have good coverage on:
- Attack taxonomies
- Limitations of semantic guardrails
- Need for structural + behavioral layers
- Red teaming / purple teaming value

**Next step:** Decide whether to finish the remaining ~15-18 papers or shift focus to synthesizing findings into concrete guardrail improvements for the NEXUS MCP server.

---

**Report generated to clean up repetition and give clear visibility.**