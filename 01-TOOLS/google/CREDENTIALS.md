# Credenciales — Google

## Panel del proveedor

- URL: https://console.cloud.google.com (proyecto «notas-voz»)
- Cuenta: la cuenta de Google del dueño.

## Variables y archivos

| Nombre | Tipo | Dónde se genera | Rotación |
|--------|------|-----------------|----------|
| `OWNER_EMAIL` | no secreto | tu dirección de Gmail | — |
| `keys/client_secret.json` | secreto | Consola → Credenciales → ID de cliente OAuth (escritorio) | Si se filtra: bórralo en la consola y crea otro |
| `keys/token.json` | secreto | `uv run notas-voz-conectar-google` | Se renueva solo; si falla, repite el comando |

## Excepciones a la convención `<TOOL>_<VAR>`

- `OWNER_EMAIL`: es el destino de los correos, no una credencial de Google.

## Si se filtra una credencial

1. https://myaccount.google.com/permissions → quita el acceso a «notas-voz».
2. En la consola, borra el ID de cliente y crea uno nuevo (paso 4 del README).
3. Borra `keys/token.json` y repite `uv run notas-voz-conectar-google`.
4. Apunta aquí la fecha del incidente.
