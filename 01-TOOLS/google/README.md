# Google (Drive y Gmail)

> Guarda cada transcripción y su audio en tu Google Drive y te la envía por Gmail.

## Cuándo se usa

Cada vez que el bot termina una transcripción.

## Puesta en marcha (una sola vez, unos 15 minutos)

Google pide crear un «proyecto» propio para que el bot pueda usar tu cuenta. Es gratis.

1. Entra en https://console.cloud.google.com con tu cuenta de Google y crea un proyecto
   (por ejemplo «notas-voz»).
2. Menú **APIs y servicios → Biblioteca**: activa **Google Drive API** y **Gmail API**.
3. Menú **APIs y servicios → Pantalla de consentimiento de OAuth** (o «Google Auth Platform»):
   - Tipo de usuario: **Externo**. Nombre de la app: «notas-voz». Tu correo como contacto.
   - En **Usuarios de prueba** (Audience), añade tu propia dirección de Gmail.
   - **Publica la app** («Publicar app» → En producción). Si la dejas «en pruebas», Google
     caduca el permiso cada 7 días y el bot dejaría de guardar. Google mostrará un aviso de
     «app no verificada» al conectar: es normal porque la app es tuya; pulsa
     «Configuración avanzada → Ir a notas-voz».
4. Menú **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth**:
   - Tipo: **Aplicación de escritorio**. Descarga el JSON.
   - Guárdalo como `01-TOOLS/google/keys/client_secret.json`.
5. En esta carpeta: `cp .env.example .env && chmod 600 .env` y escribe tu Gmail en `OWNER_EMAIL`.
6. Desde la carpeta del proyecto: `uv run notas-voz-conectar-google`. Se abre el navegador:
   entra con tu cuenta y acepta. Debe terminar con `OK — Google conectado`.
7. `./test_connection.sh` — crea una carpeta de prueba en Drive y te envía un correo de prueba.

## Scripts

| Script | Qué hace | Ejemplo |
|--------|----------|---------|
| `test_connection.sh` | Prueba Drive y Gmail de verdad (crea carpeta y envía un correo a ti). | `./test_connection.sh` |

## Notas

- Permisos mínimos: el bot solo ve los archivos de Drive que él mismo crea, y en Gmail solo puede
  enviar (no leer).
- Gratis dentro de los límites normales de Drive y Gmail.
- Todo queda en `Mi unidad → Transcripciones → <Nombre> (<número>)`.
