# Source Conversion Notes

This skill is a progressive-disclosure conversion of the engineering-applicable parts of Galdren's "Secure AI & Agent Coding Policy":

https://galdren.com/secure-ai-agent-coding-policy/

## What Was Converted

The skill keeps controls that can directly guide coding, review, or production hardening:

- untrusted input handling and prompt boundaries
- safe model output handling
- tool and action authorization
- least privilege and minimal agent footprint
- human approval for high-impact actions
- reversible actions, rollback, and fail-safe behavior
- data classification, minimization, consent, and anonymization
- secrets management and endpoint security
- structured inputs and outputs
- threat modeling for AI-specific risks
- RAG, vector store, and data pipeline hardening
- logging, monitoring, anomaly detection, incident response, and safety regression testing
- supply chain, model update, inventory, and decommission practices
- dangerous pattern scanning and reusable safety controls

## What Was Not Treated As A Coding Skill

Some source policy areas are important but should not be resolved by a coding skill alone:

- legal interpretation of AI-specific regulations
- organization-specific exception approval
- physical security programs
- final compliance sign-off
- vendor governance decisions outside the target system

For those, this skill prompts the agent to surface facts, risks, and evidence for the responsible legal, security, compliance, or operations owner.

## Conversion Principles

- Convert broad policy into actionable engineering checks.
- Prefer enforceable controls outside the model over prompt-only rules.
- Route detail into references so `SKILL.md` stays small.
- Avoid copying the policy as a checklist when a review workflow or implementation pattern is more useful.
- Keep the skill repo-agnostic and portable across agent harnesses.
