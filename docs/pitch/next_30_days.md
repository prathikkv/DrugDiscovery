# Next 30 Days — BioOrchestrator Action Plan

Prioritized by speed to first money / first signal.

---

## Week 1 — Get the Demo Live (Days 1–7)

**Goal:** Have a public URL you can share with anyone.

- [ ] Push repo to GitHub (public)
  ```bash
  git remote add origin https://github.com/yourusername/bioorchestrator.git
  git push -u origin main
  ```
- [ ] Deploy to Streamlit Community Cloud (free, 15 min — see docs/HOW_TO_RUN.md)
- [ ] Run generate_showcase_data.py so demos work without live API calls
  ```bash
  python scripts/generate_showcase_data.py
  ```
- [ ] Record a 3-minute Loom of the EGFR/NSCLC scenario
  - Hook: "Here's what a 15-minute drug target triage looks like vs. 2–4 weeks of manual work"
  - Show: Evidence Explorer → AI Insights → Scorecard → Audit Trail
  - End: "If you want to see this on one of your targets, DM me"

**Deliverable:** A URL you can put in every message, post, and email.

---

## Week 2 — First Outreach Wave (Days 8–14)

**Goal:** 10 DMs sent, 1 LinkedIn post published.

- [ ] Post LinkedIn Version 1 (linkedin_post.html → story-led version)
  - Post Tuesday or Wednesday 8–10am
  - Put demo URL and Loom in first comment, not post body
  - Reply to every comment in first 2 hours
- [ ] Send 10 cold DMs on LinkedIn
  - Target: "Director/VP Computational Biology" + "Biotech" + Series B-C
  - Use Template 1 (cold_dm_templates.html) — personalize with their disease area
  - Batch: 5 DMs on Day 8, 5 on Day 10
- [ ] Apply to 3 pharma AI job postings using resume_bullets.html content
  - Search: "AI Drug Discovery" OR "Computational Biology AI" at Pfizer, Genentech, Novartis, Roche

**Deliverable:** At least 1 positive reply to any of the above.

---

## Week 3–4 — Convert Conversations (Days 15–30)

**Goal:** 1 demo call booked. 1 follow-up outreach wave.

- [ ] Follow up on any DMs that didn't reply (use Template 5 — day 5 follow-up)
- [ ] Send 10 more DMs (new prospects)
- [ ] Send follow-up to any positive replies → book 30-min demo call
  - During call: run BioOrchestrator live on a target they suggest
  - Ask at end: "Would a 2-week free pilot on your top 3 targets be useful?"
- [ ] Post LinkedIn Version 3 (short-form poll) — mid-week engagement
- [ ] Apply to 5 more pharma AI roles (use interview_prep.html to prep for any callbacks)

**Deliverable:** 1 demo call completed. Ideally 1 "yes to free pilot."

---

## Month 2 — Branch Depending on Which Path Is Working

### If consulting / POC path is moving:
- [ ] Formalize the free pilot as a scoped 2-week engagement
  - Deliverable: 3 scored targets + audit-ready scorecard PDFs
  - Goal: get "this is valuable" feedback in writing
- [ ] After pilot: propose paid POC at $15K–$25K
  - Frame as: "We'll do your next 10 targets, configure for your internal gene panel, and deliver a compliance-ready report"
- [ ] Use the pilot output as a case study for the next 10 prospects
  - Even a 1-sentence quote from the scientist ("This cut our triage time significantly") is enough

### If job applications are moving:
- [ ] Prep system design walkthrough using interview_prep.html
  - Practice the 10-minute BioOrchestrator architecture pitch out loud
  - Know GWAS, GSEA, 21 CFR Part 11 cold
- [ ] Anchor salary at IC4: $200K–$240K base (Big Pharma) / $200K–$280K (Biotech)
- [ ] If recruiter asks for a number first: "I'm targeting $220K–$260K base depending on equity and scope"

---

## Key Metrics to Track

| Metric | Week 1 | Week 2 | Week 4 |
|--------|--------|--------|--------|
| Demo URL live | ✅ | ✅ | ✅ |
| LinkedIn post impressions | — | Post 1 live | Post 1 + poll |
| DMs sent | 0 | 10 | 20 |
| DM reply rate | — | >10% | >10% |
| Demo calls booked | 0 | 0 | 1+ |
| Job applications sent | 0 | 3 | 8+ |

---

## The One Message to Memorize

> "I built an end-to-end AI drug target triage platform that takes a gene symbol and produces a GO/NO-GO verdict — aggregating 6 live databases, running 5 parallel LLM reasoning modes, scoring across 7 dimensions, and producing a 21 CFR Part 11 compliant audit trail. The whole thing runs in 15 minutes vs. 2–4 weeks of manual analyst work. I'm looking for biotech teams who want to pilot it on their current target list."

Use this in: DMs, demo calls, job interviews, LinkedIn comments, email introductions.
