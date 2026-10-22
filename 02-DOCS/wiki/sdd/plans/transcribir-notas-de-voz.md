---
type: plan
title: Plan — Transcribir notas de voz y guardarlas en Drive y correo
description: The structure-level implementation plan for the Telegram voice-note bot — contracts, shapes, flows.
tags: [sdd, plan]
timestamp: 2026-10-22T21:00:00Z
topic: sdd
slug: transcribir-notas-de-voz
status: approved
---

# Plan — Transcribir notas de voz y guardarlas en Drive y correo

> Spec: [../specs/transcribir-notas-de-voz.md](../specs/transcribir-notas-de-voz.md) · Constitution: [../constitution.md](../constitution.md) · Status: approved (autopilot)
> Last updated: 2026-10-22

## 0. Global Constraints

- **Language/runtime:** Python ≥ 3.12, `uv`, one committed `uv.lock`. Code in `src/notas_voz/`, tests in `tests/`.
- **Quality:** `scripts/verify.sh` = `ruff format --check` + `ruff check` + `pytest`, all clean.
- **Tests:** no network, no real accounts; Telegram, Whisper, Drive and Gmail are faked.
- **Privacy:** audio is transcribed locally (faster-whisper, `language="es"`); audio/transcripts only leave the machine to the owner's Drive and the owner's Gmail. Logs never contain transcript text, audio, tokens or passwords.
- **Access:** only the owner (`OWNER_TELEGRAM_ID`) and people on the allow-list are served; only the owner can change the list.
- **Secrets:** `01-TOOLS/telegram/.env`, `01-TOOLS/google/.env` and Google token/credential JSON files are gitignored; never committed.
- **Copy:** every bot message is Spanish, short, plain; the bot always answers.
- **Commits:** gitmoji + Conventional Commits; human authorship, no AI co-author trailer.

## 1. Context & constraints

- Acceptance criteria shaping the design: spec §Acceptance #1-#9 (all).
- Runs on the owner's computer: long polling (no public URL); messages that arrived while off are processed at start-up (spec suposición: < 24 h).
- Telegram lets a bot download files up to 20 MB (spec suposición tomada).
- Constitution §1-§5 in play; §2 forces fakes at every outside seam.
- Out of scope: WhatsApp, groups, summaries/translation, other languages, a web panel.

## 2. Architecture

```text
 Telegram (EXTERNAL)
     │ long polling
     ▼
 [bot.py] ── adapts updates ──► [core.VoiceNoteService] ──► [Transcriber]  (local faster-whisper)
     ▲  replies (text)                │        │
     │                                │        ├──────────► [Archive]  ──► Google Drive (EXTERNAL)
     └──── sequential worker queue    │        └──────────► [Mailer]   ──► Gmail (EXTERNAL)
                                      ▼
                                 [Store] SQLite in DATA_DIR (people, access requests, folders, jobs)
```

- **bot.py** (internal) — the only module that knows python-telegram-bot: routes commands, audio and other messages, downloads audio, feeds a single FIFO worker, sends replies.
- **core.VoiceNoteService** (internal) — all business rules; framework-free; returns reply texts.
- **Store** (internal) — persistence of allow-list, access requests, Drive folder ids, and jobs (the outbox that makes delivery retryable).
- **Transcriber** (internal, local) — audio file → Spanish text.
- **Archive / Mailer** (internal adapters over EXTERNAL Google APIs) — Drive upload (Google Doc + audio) and Gmail send.

**Top architectural decision:** a persisted job/outbox per voice note processed by one sequential worker. Chosen because the spec needs order preservation (edge case "varios audios seguidos"), survival across failures ("la transcripción no se pierde y se reintenta") and start-up catch-up, on a single home computer. Alternative (fire-and-forget per message in parallel) is simpler but loses order and loses work on failure — rejected.

## 3. Interfaces & contracts

```text
Transcriber.transcribe(audio_path: Path) -> str            # "" when no speech
Archive.ensure_folder(name: str) -> folder_id: str
Archive.save(folder_id, title: str, text: str, audio_path: Path, audio_mime: str) -> doc_link: str
Mailer.send(to: str, subject: str, body: str) -> None       # raises on failure

VoiceNoteService
  .is_allowed(user_id) -> bool                              # owner always True
  .refusal(user_id, name) -> (reply_to_user, notice_to_owner)
  .command(user_id, name: "autorizar"|"retirar"|"personas"|"start"|"ayuda", args) -> reply
  .check_size(size_bytes|None) -> reply|None                # > 20 MB → reply
  .register(user_id, name, chat_id, audio_path, mime) -> job_id
  .process(job_id) -> reply                                 # transcribe + deliver; never raises
  .retry_pending() -> list[(chat_id, reply)]                # re-deliver failed jobs
  .unfinished_jobs() -> list[job_id]                        # received but not transcribed
```

- `process` invariants: empty transcript → "no voz" reply, job deleted, no Drive/mail calls. Drive and mail are tracked independently (a retry never duplicates the half that succeeded). On full delivery local audio and transcript are deleted.
- Command invariants: non-owner calling `autorizar`/`retirar`/`personas` → refusal, list unchanged.
- The Drive link is shown only to the owner (other senders cannot open the owner's Drive); others are told it was saved. *(Spec revision, see decisions.)*

## 4. Data model & flow

SQLite at `DATA_DIR/notas_voz.db`:

- `people(user_id PK, name, added_at)`
- `requests(user_id PK, name, asked_at)` — last name seen from a refused sender, so `/autorizar <id>` can name them.
- `folders(user_id PK, folder_id)`
- `jobs(id PK, user_id, name, chat_id, received_at, audio_path, mime, transcript NULL, doc_link NULL, drive_done, mail_done)`

Flow: update → allowed? → size ok? → reply «Recibido» → download to `DATA_DIR/audio/<uuid>` → `register` → worker queue → `process` (transcribe in a thread) → reply. A background loop calls `retry_pending` every 5 minutes. At start-up `unfinished_jobs` are re-queued; pending Telegram updates are not dropped.

Names: Drive folder `Transcripciones/<Nombre> (<id>)`; files `AAAA-MM-DD HH.MM - <Nombre>` (Doc) and same name + audio extension. Email subject `Transcripción de <Nombre> — AAAA-MM-DD HH:MM`, body with sender, time, Drive link and text.

## 5. Testing strategy

| Spec acceptance | Level | Asserts | Fakes |
| --- | --- | --- | --- |
| #1 receipt + text + link | unit (core) + unit (bot routing) | `process` reply contains text and, for owner, link | Transcriber, Archive, Mailer |
| #2 Drive Doc + audio in person folder, dated name | unit (core) | Archive got folder `<Nombre> (<id>)`, dated title, audio path | Archive |
| #3 email with text, who, when | unit (core) | Mailer got owner address; subject/body content | Mailer |
| #4 unauthorized refused, nothing created | unit (core + bot) | refusal; no job, no Archive/Mailer calls | all |
| #5 owner authorizes/revokes | unit (core) | `is_allowed` flips | Store (real, tmp sqlite) |
| #5b non-owner cannot change list | unit (core) | refusal; list unchanged | — |
| #6 no speech | unit (core) | "no voz" reply; no Archive/Mailer calls | Transcriber returns "" |
| #7 non-audio | unit (bot routing) | `classify` → other; reply explains | — |
| #8 Drive/mail failure → warn + retry | unit (core) | warning reply; `retry_pending` delivers once, no duplicate | failing then healthy fakes |
| #9 no external transcription | unit | transcriber calls local model with `language="es"`; module imports no network client | model factory |

Real-API adapters (Drive/Gmail/Telegram) are thin and covered by `01-TOOLS/*/test_connection.sh` run by the owner with real credentials.

## 6. Sequencing & dependencies

Scaffold → Store → core (TDD per acceptance) → transcriber → Google adapters → bot wiring → tools/README → verify.

## 7. Risks & open decisions

1. **Transcription speed on the owner's PC** (trigger: slow CPU; impact: minutes per note). Mitigation: model size configurable (`WHISPER_MODEL`, default `small`), "tardará un poco" message.
2. **Google setup is the hardest step for a non-technical owner** (OAuth client, consent screen). Mitigation: step-by-step guide in `01-TOOLS/google/README.md` + one-command connect script.
3. **Live API behaviour untested here** (no credentials in the dev container). Mitigation: thin adapters + owner-run `test_connection.sh`; flagged in verify.
4. **Telegram drops pending updates after ~24 h.** Accepted per spec.

## Tasks
<!-- generated by tasks on 2026-10-22; IDs are stable, do not renumber -->

| ID | [P] | Task | Done-check | Depends-on | Trace |
| --- | --- | --- | --- | --- | --- |
| T001 |  | Scaffold uv project, ruff, pytest, `scripts/verify.sh`, `.gitignore` for data/ | `scripts/verify.sh` exits 0 on an empty test | — | constitution §1-2 |
| T002 |  | Store: people/requests/folders/jobs with tests | `pytest tests/test_store.py` green | T001 | plan §4 |
| T003 |  | Core access: owner/allow-list, commands, refusal (tests first) | tests for #4, #5, #5b green | T002 | spec #4 #5 |
| T004 |  | Core processing: process/deliver/no-voice/size (tests first) | tests for #1 #2 #3 #6 green | T003 | spec #1 #2 #3 #6 |
| T005 |  | Core retry: independent Drive/mail flags, retry_pending (tests first) | tests for #8 green, no duplicate delivery | T004 | spec #8 |
| T006 | [P] | Local transcriber (faster-whisper, es) | test #9 green | T001 | spec #9 |
| T007 | [P] | Google Archive + Gmail Mailer adapters + connect script | unit tests with fake service objects green | T001 | spec #2 #3 |
| T008 |  | Bot wiring: routing, download, FIFO worker, retry loop, start-up catch-up | tests for #7 and routing green; `python -c "import notas_voz.bot"` ok | T005 T006 T007 | spec #1 #4 #7 |
| T009 |  | 01-TOOLS/telegram + 01-TOOLS/google + README owner guide (Spanish) | files exist; `bash -n` on scripts passes | T007 T008 | constitution §5 |
| T010 |  | All done-checks + `scripts/verify.sh` green | every row checked; verify exits 0 | all | spec §Acceptance |

## Review Workload Forecast

| Dimension | Forecast | Why |
| --- | --- | --- |
| Estimated changed lines | 900-1200 | ~8 modules + tests + guides |
| Files / areas | ~20: src, tests, scripts, 01-TOOLS, README | greenfield |
| Review risk | medium | secrets handling, access control, outside APIs |
| Suggested delivery | exception | greenfield first feature over the 400-line budget; owner chose autopilot; lands on the session branch for the owner to merge |
