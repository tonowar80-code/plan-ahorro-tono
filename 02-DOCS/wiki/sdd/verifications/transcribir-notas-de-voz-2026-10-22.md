---
type: verification
title: Verify — transcribir-notas-de-voz (2026-10-22)
tags: [sdd, verify]
timestamp: 2026-10-22T21:30:00Z
topic: sdd
slug: transcribir-notas-de-voz
---

# Verify — transcribir-notas-de-voz — 2026-10-22

**Verdict: PASS (con dos comprobaciones pendientes en el ordenador del dueño).**

`scripts/verify.sh`: `ruff format --check` limpio, `ruff check` limpio, `pytest` 46 passed.

## Criterios de aceptación → prueba

| # | Criterio | Prueba(s) | Estado |
|---|----------|-----------|--------|
| 1 | Recibido + texto (+ enlace si es el dueño) | `test_receipt_warns_for_long_audio`, `test_owner_voice_note_is_saved_mailed_and_answered`, `test_other_person_gets_text_but_not_the_owner_drive_link` | ✅ |
| 2 | Google Doc + audio en la carpeta de la persona, con fecha | `test_owner_voice_note_is_saved_mailed_and_answered`, `test_folder_is_created_once_per_person`, `test_save_creates_google_doc_and_audio`, `test_folders_are_found_or_created_under_root` | ✅ |
| 3 | Correo con texto, quién y cuándo | `test_owner_voice_note_is_saved_mailed_and_answered`, `test_gmail_sends_utf8_message` | ✅ |
| 4 | Sin acceso → aviso, nada creado | `test_refusal_for_unknown_person_and_notice_to_owner`, `test_owner_is_notified_only_the_first_time` | ✅ |
| 5 | El dueño autoriza/retira | `test_owner_authorizes_and_revokes_with_requested_name`, `test_owner_can_give_a_name` | ✅ |
| 5b | Otros no pueden cambiar la lista | `test_non_owner_cannot_manage_access[*]` | ✅ |
| 6 | Audio sin voz → nada creado | `test_no_speech_creates_nothing` | ✅ |
| 7 | Mensaje que no es audio → explica | `test_other_documents_and_text_are_not_audio` + handler `on_other` | ✅ |
| 8 | Fallo de Drive/correo → aviso y reintento sin duplicar | `test_drive_failure_warns_and_retry_delivers_once`, `test_mail_failure_warns_and_retry_sends_once`, `test_retry_while_still_failing_is_silent`, `test_retry_during_delivery_does_not_duplicate` | ✅ |
| 9 | Audio no va a servicios externos de transcripción | `test_transcribes_locally_in_spanish`, `test_transcriber_module_uses_no_network_client` | ✅ |

## Tareas

T001-T010 comprobadas (ver plan). Smoke: la app de Telegram se construye con sus 3 manejadores.

## No comprobado aquí (honestidad)

- **Modelo de voz real**: la red del entorno de desarrollo bloquea la descarga del modelo
  (HuggingFace, 403). Se comprueba la primera vez que el dueño ejecuta `uv run notas-voz`.
- **APIs reales de Telegram, Drive y Gmail**: no hay credenciales aquí. Se comprueban con
  `01-TOOLS/telegram/test_connection.sh` y `01-TOOLS/google/test_connection.sh`.
