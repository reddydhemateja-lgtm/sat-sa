# SAT-SA — Supervisory Analytics Tool for SOC Assessment

**Smart India Hackathon 2026 · Problem Statement SIH26157**
**Organisation:** NTRO / NCIIPC

A supervisory analytics tool that processes periodic SOC operational evidence submitted by Critical Sector Entities (CSEs) to identify patterns requiring supervisory attention. The tool supports human supervisors — every finding is evidence-linked, explainable, and subject to supervisory review. It does not make final decisions.

---

## Table of Contents

1. [What the tool does](#what-the-tool-does)
2. [Core workflow](#core-workflow)
3. [Features](#features)
4. [Architecture](#architecture)
5. [Technology stack](#technology-stack)
6. [Quick start](#quick-start)
7. [Directory structure](#directory-structure)
8. [Data model](#data-model)
9. [Analytics engine](#analytics-engine)
10. [Configuration](#configuration)
11. [API overview](#api-overview)
12. [Deployment](#deployment)
13. [Security](#security)
14. [Screenshots](#screenshots)
15. [Team](#team)
16. [License](#license)

---

## What the tool does

NCIIPC assesses the cyber resilience of Critical Sector Entities. Today, supervisory reviews often involve manually examining samples of SOC alerts and case-management records.

**SAT-SA automates the analysis of that operational evidence.** It ingests periodic CSE submissions, validates them, applies a set of explainable analytics rules, and produces prioritised findings for supervisory review.

The tool identifies indicators — it does not produce verdicts. Every finding is traceable to the underlying alert, case, or investigation record.

---

## Core workflow
