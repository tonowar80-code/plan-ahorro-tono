---
type: spec
title: Spec — Transcribir notas de voz y guardarlas en Drive y correo
description: WHAT and WHY for the Telegram bot that turns voice notes into text and files them in Google Drive and email — problem, goals, behaviour, acceptance criteria.
tags: [sdd, spec]
timestamp: 2026-10-22T20:30:00Z
topic: sdd
slug: transcribir-notas-de-voz
status: planned
---

# Spec — Transcribir notas de voz y guardarlas en Drive y correo

> Slug: `transcribir-notas-de-voz` · Status: clarified · Created: 2026-10-22 · Aprobada por el dueño 2026-10-22 («Sí, la apruebo»); resto de la cadena en autopilot
> Inherits: [constitution](../constitution.md)

## Problem & why
El dueño (y unas pocas personas de su confianza) graban o reciben notas de voz que contienen
información que quieren conservar y poder leer o buscar más tarde. Hoy esa información se queda
atrapada en audios dentro del chat: para tenerla por escrito hay que escucharla y teclearla a mano,
y luego subirla o enviarla uno mismo. El objetivo es que basta con mandar el audio al bot.

## Cost of not building it
Cada nota de voz que se quiere conservar cuesta escucharla entera, escribirla (varios minutos por
minuto de audio), y copiarla a Drive y al correo. En la práctica, la mayoría no se transcribe y la
información se pierde o no se encuentra. El coste es tiempo del dueño, no dinero: si hay pocos audios
a la semana, el coste de no construirlo es bajo.

## The cheapest alternative
Telegram Premium (unos 5 € al mes) y WhatsApp ya transcriben notas de voz dentro de la app. Luego se
puede copiar el texto y pegarlo a mano en Drive y en un correo. Resuelve la transcripción, pero no el
archivado: sigue siendo manual, por audio, y las demás personas también tendrían que pagar Premium.
Tampoco deja una copia ordenada por persona. Por eso no basta si llegan audios con frecuencia.

## Goals
- Mandar una nota de voz al bot es lo único que hace falta para tenerla por escrito.
- Cada transcripción queda guardada en el Google Drive del dueño y llega a su correo, sin pasos manuales.
- El servicio no tiene coste por minuto de audio y el audio no se envía a empresas de transcripción.

## Non-goals / out of scope
- Leer o grabar chats privados entre personas (Telegram no lo permite).
- WhatsApp (posible ampliación futura).
- Estar en grupos.
- Resumir, traducir o analizar el texto: solo transcribir.
- Audios en idiomas distintos del español.
- Funcionar mientras el ordenador del dueño está apagado.
- Una web o panel para ver las transcripciones (se ven en Drive y en el correo).

## Users & context
- **El dueño**: usa Telegram en el móvil, no es técnico, y tiene un ordenador en casa donde vive el bot.
- **Personas autorizadas** (familia, amigos, equipo pequeño): el dueño las autoriza. Mandan audios
  al bot; sus transcripciones van al Drive y al correo **del dueño**, separadas por persona.

## Behaviour
- Main path: una persona autorizada manda (o reenvía) una nota de voz al bot. El bot responde al
  momento que la ha recibido. Cuando termina, guarda en el Drive del dueño, en la carpeta de esa persona,
  la transcripción como documento de Google Docs y el audio original, envía la transcripción al correo del dueño y contesta en Telegram con el
  texto (o su inicio si es largo) y el enlace al archivo de Drive.
- Edge cases:
  - Audio largo: el bot avisa de que tardará un poco y responde al terminar.
  - Varios audios seguidos: cada uno recibe su propia transcripción, en el orden en que llegaron.
  - Audio sin voz o inaudible: el bot lo dice y no crea archivo vacío ni envía correo.
  - Audio por encima del tamaño máximo que el bot puede descargar: el bot lo dice con claridad.
  - Archivo de audio enviado como documento (no como nota de voz): se trata igual.
  - Mensajes de texto, fotos u otras cosas: el bot explica que solo transcribe audios.
  - El ordenador estaba apagado: los audios recibidos mientras tanto se procesan al encenderlo.
- Gestión de acceso: el dueño autoriza o retira a una persona escribiéndole un comando al propio bot.
  Solo el dueño puede usar esos comandos.
- Error paths:
  - Persona no autorizada: respuesta amable de que no tiene acceso; su audio no se procesa ni se guarda.
  - Falla Drive o el correo: el bot avisa de qué ha fallado; la transcripción no se pierde y se reintenta.
  - Los mensajes de error no muestran detalles técnicos, contraseñas ni datos de otras personas.

## Acceptance criteria
- Given una persona autorizada, When manda una nota de voz en español, Then recibe en Telegram un
  aviso de recepción y, después, el texto transcrito; si es el dueño, también un enlace a Drive (los
  demás reciben aviso de que está guardado).
- Given una nota de voz procesada, When el dueño abre su Google Drive, Then dentro de la carpeta de la persona
  que la envió existen un documento de Google Docs con la transcripción y el audio original, ambos
  con fecha y hora en el nombre.
- Given una nota de voz procesada, When el dueño mira su correo, Then hay un email con la
  transcripción, quién la envió y cuándo.
- Given una persona no autorizada, When manda un audio, Then recibe un mensaje de que no tiene acceso
  y no se crea ningún archivo ni correo.
- Given el dueño, When autoriza o retira a una persona con un comando en el bot, Then a partir de ese
  momento esa persona puede o deja de poder usar el bot.
- Given una persona que no es el dueño, When usa el comando de autorizar o retirar, Then el bot lo
  rechaza y la lista de personas autorizadas no cambia.
- Given un audio sin voz, When se procesa, Then el bot dice que no ha encontrado voz y no se crea
  archivo ni correo.
- Given un mensaje que no es audio, When llega al bot, Then el bot explica que solo transcribe audios.
- Given que falla el envío a Drive o al correo, When termina la transcripción, Then el bot avisa del
  fallo y la transcripción se entrega cuando el servicio vuelve a funcionar.
- Given cualquier transcripción, When se procesa, Then el audio no se envía a ningún servicio externo
  de transcripción.

## Points to clarify
- **suposición tomada** — Un correo por cada nota de voz (no un resumen diario). *Base:* «siempre a
  los dos» sugiere entrega inmediata. *Riesgo:* con muchos audios el buzón se llena; cambiaría a resumen.
- **suposición tomada** — Los audios recibidos con el ordenador apagado se procesan al encenderlo si
  han pasado menos de 24 horas. *Base:* Telegram guarda los mensajes pendientes del bot un tiempo
  limitado. *Riesgo:* si el ordenador está apagado más de un día, esos audios se pierden y habría que
  reenviarlos.
- **suposición tomada** — El tamaño máximo del audio es el que Telegram deja descargar a un bot
  (20 MB: aproximadamente una hora o más de nota de voz). *Base:* límite de la plataforma. *Riesgo:* grabaciones más largas
  necesitarían otra vía de entrada.
- **suposición tomada** — La transcripción puede tardar varios minutos por audio en un ordenador
  normal. *Base:* el dueño eligió transcribir gratis en su máquina. *Riesgo:* si el ordenador es
  lento, la espera puede no ser aceptable y habría que revisar la elección.
- **decisión diferida** — WhatsApp y grupos de Telegram: fuera de este ciclo.
- **área no formulable** — Buscar dentro de las transcripciones antiguas: puede llegar a necesitarse,
  aún no está claro cómo.

## Resolved clarifications
- 2026-10-22 — ¿Se guarda el audio original? → Sí, texto y audio original en Drive.
- 2026-10-22 — ¿Formato en Drive? → Documento de Google Docs.
- 2026-10-22 — ¿Cómo se autoriza a una persona? → Con un comando en el propio bot, solo el dueño.

## Revisions
- 2026-10-22 (plan) — Criterio #1: el enlace de Drive solo se muestra al dueño, porque los demás no
  pueden abrir su Drive. Se avisa al dueño cuando alguien sin acceso escribe (sin el contenido).
