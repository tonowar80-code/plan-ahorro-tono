# Decisions log (append-only)

| Date | Decision | Options considered | Why |
|------|----------|--------------------|-----|
| 2026-10-22 | Telegram como plataforma | Telegram, WhatsApp, ambos | Gratis, sin cuenta de empresa; elección del dueño. |
| 2026-10-22 | Solo notas de voz que se envían al bot | notas de voz, charlas con el bot, grupos, grabaciones | Elección del dueño; los bots no pueden leer chats privados. |
| 2026-10-22 | Transcripción local, gratis, en español | OpenAI, Google Speech-to-Text, local | Elección del dueño: sin coste por minuto y el audio no sale de su ordenador. |
| 2026-10-22 | El bot corre en el ordenador del dueño | ordenador propio, servidor en internet | Elección del dueño: gratis; no responde con el ordenador apagado. |
| 2026-10-22 | Todo va al Drive y al correo del dueño, carpeta por persona | su correo, ambos correos | Elección del dueño. |
| 2026-10-22 | Constitución v1.0.0 ratificada | — | Sí explícito del dueño. |
| 2026-10-22 | Drive guarda Google Doc + audio original; acceso por comando del dueño en el bot | solo texto / .txt / lista en archivo | Respuestas del dueño en la fase specify. |
| 2026-10-22 | Cola persistente de trabajos con un solo trabajador | paralelo sin persistencia | Mantiene el orden, no pierde audios si falla Drive/correo y retoma al arrancar. |
| 2026-10-22 | Transcripción con faster-whisper (modelo `small` por defecto, configurable) | whisper original, vosk | Local, gratis, buen español en CPU. |
| 2026-10-22 | Drive con permiso `drive.file` y correo con Gmail `gmail.send` (OAuth de la cuenta del dueño) | SMTP con contraseña de aplicación | Un solo inicio de sesión de Google; el bot solo ve los archivos que crea; sin guardar contraseñas. |
| 2026-10-22 | El enlace de Drive solo se muestra al dueño; a los demás se les dice que está guardado | enlace a todos | Los demás no pueden abrir el Drive del dueño. Ajusta spec #1. |
| 2026-10-22 | Cuando alguien sin acceso escribe, el dueño recibe un aviso con su nombre y el comando para autorizarle (sin el contenido) | sin aviso | El dueño no técnico no tiene otra forma fácil de saber el número de esa persona. |
