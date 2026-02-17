# Lessons Learned

This document summarizes key lessons from building the Personal AI Employee project for Hackathon 0.

## 1. File-based coordination is practical and debuggable

Using markdown files in an Obsidian vault as the shared protocol made workflows transparent.  
It was easy to inspect state transitions (`Needs_Action` -> `Pending_Approval` -> `Done`) without extra tooling.

## 2. Human-in-the-loop approval is essential

Autonomy works best when scoped by risk.  
Approval gates reduced the chance of unsafe actions for emails, payments, and public posts.

## 3. Browser-session automations require strict secret hygiene

Playwright session state can contain live cookies and tokens.  
Ignoring session folders in `.gitignore` is mandatory before committing or pushing.

## 4. Placeholder-based config prevents accidental leaks

Replacing default/demo credentials with placeholders (for README, compose files, skill docs) helps avoid scanner alerts and accidental credential reuse.

## 5. Reliability needs explicit fallback logic

Retries, graceful degradation, offline queues, and health checks are not optional in always-on agents.  
Without them, transient API/network failures cause noisy and brittle behavior.

## 6. Multi-platform integrations evolve at different speeds

API-first integrations (e.g., Gmail, Odoo read paths) stabilize faster than browser-driven integrations.  
A phased approach (working core + scaffolded channels) kept delivery momentum.

## 7. Auditability improves trust

Structured action logs and vault artifacts made it easier to verify behavior, prepare evidence packs, and review decisions.

## 8. Skills improve reuse and consistency

Packaging repeated workflows as skills reduced prompt drift and made operations easier to repeat across tasks.

## Next Improvements

- Strengthen end-to-end approval execution tests
- Add pre-commit secret scanning checks
- Expand integration tests for social watchers/posters
- Add deployment hardening and runbook documentation
