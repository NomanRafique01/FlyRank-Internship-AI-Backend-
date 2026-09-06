---
name: flyrank-assignment-solver
description: Use this skill whenever Noman Rafique shares a FlyRank Internship assignment PDF (any track — Backend, AI, etc.) and wants help solving it. Trigger this any time a PDF titled like "FLYRANK INTERNSHIP · ... · ASSIGNMENT Ax" is uploaded (Noman typically drops it straight into the repo's root directory), or Noman says things like "solve this assignment", "next week's assignment", "help me with this FlyRank task". Covers reading the assignment spec first, setting up the right folder inside the existing repo structure, writing the code stage-by-stage in a natural human style, committing after every single stage as it's completed (never one giant commit at the end), and asking separately before any tool/software installation. Use this for every FlyRank assignment in this internship, not just the first one — it is the standard workflow for all of them.
---

# FlyRank Assignment Solver

Noman (Noman Rafique) is a BS AI student doing an internship at FlyRank (Backend AI Engineering
track). Each week he gets a PDF assignment (e.g. "W1 · A3 — Containerize your stack", "W3 · A2 —
Connecting your CRUD to the database"). These assignments build on each other in the **same
GitHub repo** (`FlyRank-Internship-AI-Backend-`), continuing the same lane (currently: Python /
FastAPI).

Your job: read the PDF, then walk Noman through solving it **stage by stage**, exactly the way the
assignment itself is structured — never dump the whole solution in one go, and never make one
big commit at the end.

## 0. Where the assignment PDF comes from

Noman drops each new assignment PDF straight into the **root directory** of the repo
(`FlyRank-Internship-AI-Backend-/`) when he uploads it to chat. Always check/read that PDF fully
first before doing anything else — don't start folder setup or code based on assumptions about
what the assignment wants.

Every assignment PDF has this shape:
- Goal & purpose
- Tools — pick one lane (Noman is Python / FastAPI)
- The task — N stages, each with a checkpoint and a commit message
- Bonus stage (AI rematch) — **skip this unless Noman explicitly asks for it**
- Requirements & "Done means"
- Glossary

Read the whole document before writing any code. Note down:
- How many stages there are, and the exact commit message suggested for each stage
- What existed in the *previous* assignment's code (check the repo structure / ask if unsure) —
  these assignments are incremental, not standalone
- Whether new installs are required (Docker, a DB engine, a CLI tool, a Python package)

## 1. Folder setup — match the existing repo structure

Noman's repo is structured like:
```
FlyRank-Internship-AI-Backend-/
  Week1/
  Week2/
  Week3/
    A2-database/
    A3-docker/
  ...
```

Before creating anything, ask (or infer from earlier chat context) which Week this assignment
belongs to, and check what folders already exist. Then give Noman the exact PowerShell commands to
create the new folder inside the right Week, named to match the assignment code (e.g. `A3-docker`,
`A4-caching`). Never rename or touch folders from a previous assignment — this is an additive
process.

```powershell
cd C:\Users\pc\Desktop\FlyRank-Internship-AI-Backend-\WeekN
mkdir A<x>-<short-topic-name>
cd A<x>-<short-topic-name>
```

If this is a new Week with no folder yet, create the Week folder first.

## 2. Installations — always ask separately, never bundle

If the assignment needs something installed (Docker Desktop, Postgres, a Python package, DB
Browser, etc.), **stop and ask/tell Noman about that install as its own step**, before moving to
code. Do not mix "install X" and "write this code" into the same instruction block. Confirm the
install worked (version check, `docker ps`, etc.) before proceeding to the next stage.

## 3. Solve stage by stage — commit as each stage completes, no exceptions

This is the most important rule. For each stage in the PDF:

1. Explain in 1-2 plain sentences what this stage does and why (tie it back to the big idea — e.g.
   "same API, only the storage layer changes").
2. Give Noman the code/config needed for *only this stage* — don't leap ahead to later stages.
3. Give the exact checkpoint command(s) from the PDF so Noman can verify it works (curl, docker ps,
   psql, etc.).
4. After giving the checkpoint, **always explicitly ask Noman to confirm it works before
   continuing** — end every stage with a prompt like:
   > "Run the checkpoint above and let me know if it works — I'll give you the commit once it does."
5. As soon as Noman confirms that stage's checkpoint works, **immediately** give the commit command
   using the **exact commit message the PDF suggests** for that stage:
   ```powershell
   git add .
   git commit -m "Stage N: <exact message from PDF>"
   ```
   Then ask Noman to confirm the commit ran before moving to the next stage:
   > "Committed? Let's go to Stage N+1."
6. Only then move to the next stage.

**Hard rules — never break these:**
- ❌ Never say "we'll commit at the end" or "commit everything together after all stages."
- ❌ Never give code for Stage N+1 before Stage N's commit is done.
- ❌ Never batch multiple stages into one commit.
- ✅ One stage → one checkpoint → one commit → then and only then: next stage.

Every stage gets its own honest commit, made the moment that stage is verified working, in order,
as the PDF requires (this is graded — assignments explicitly ask for ≥6 commits, one per stage).

If Noman pastes an error, fix that stage's code before moving on — don't patch forward.

## 4. Code style — write it so it reads hand-written, not AI-generated

Noman is a student who writes his own code day to day. Generated code should look like something a
capable student would type, not like a code-generation tool's output. Concretely:

- Use plain section comments (`# ── Stage 2: Create ───`) sparingly — like Noman's own existing
  `main.py` already does — not a comment above every single line.
- Don't over-engineer: no unnecessary abstractions, extra config layers, or defensive code the
  assignment didn't ask for. Match the scope of what the stage actually requires.
- Keep variable/function names simple and conventional (`task`, `tasks`, `get_task`, `engine`) —
  the same naming already used in his prior assignments (check his uploaded screenshots/files for
  his existing style before introducing new patterns).
- Avoid boilerplate docstrings on every function unless the assignment's own checkpoint expects
  documentation.
- Reuse patterns from his own previous stage's code rather than introducing a stylistically
  different approach for the new stage (e.g. if A2 used SQLModel, don't switch to raw psycopg2 in
  A3 unless the assignment or Noman asks for that).

## 5. README and submission

Every assignment's final stage asks for a README update and a screenshot. Once all stages are
committed:
- Give Noman the README content matching what *this specific PDF* asks for (check its "Publish"
  stage for the exact required sections — they differ per assignment: e.g. A2 wants "why SQLite",
  A3 wants "why Docker" + `.env.example` + endpoint table + curl output + DB screenshot).
- Remind him to `git push` after the last stage's commit.
- If Noman asks how to submit, tell him to paste the GitHub repo link into the assignment's
  submission box on the FlyRank portal.

## 6. Bonus / AI-rematch stage

Only do this if Noman explicitly asks for it. By default, treat the assignment as done after the
core numbered stages (0 through the last non-bonus stage) are committed and pushed.

## 7. Tone

Keep responses short and directive — commands first, brief explanation, then wait for Noman's
confirmation/output before continuing. This matches how the rest of the internship conversation
has gone: step-by-step, verify-before-advancing, no giant walls of text.
