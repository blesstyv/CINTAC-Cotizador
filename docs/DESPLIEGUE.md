# Despliegue y rollback — CINTAC-Cotizador

## Compatibilidad con Render

- `build.sh` no cambia: instala dependencias, `collectstatic`, `migrate`, `bootstrap_production`.
- Migraciones nuevas: **0012** (agrega 4 columnas nulas, las completa con datos del mismo
  registro y crea 4 constraints), **0013** (tabla nueva) y **0014** (nuevo tipo de operación
en la bitácora). Todas son aditivas.
  Validado: base creada con el código de `main` + cotizaciones (sin valor, USD y CLP),
  luego `migrate` con esta rama ⇒ totales del historial idénticos.
- `bootstrap_production` es idempotente: en un redeploy **no** recarga datos maestros, no
  cambia capacidades, no cambia la contraseña del administrador y no eleva cuentas.
- Sin dependencias nuevas de sistema. Python 3.13 y Node 24 (Render) compatibles.

## Variables de entorno

Todas las nuevas son **opcionales** (tienen valor por defecto):

| Variable | Defecto | Uso |
|---|---|---|
| `LOGIN_MAX_FALLOS` | 10 | Intentos fallidos antes de bloquear la cuenta |
| `LOGIN_BLOQUEO_SEGUNDOS` | 900 | Duración del bloqueo |
| `TIPO_CAMBIO_REINTENTO_SEGUNDOS` | 300 | Espera antes de reintentar la fuente del dólar tras una falla |
| `CINTAC_LOG_LEVEL` | INFO | Nivel de log de la aplicación |
| `BOOTSTRAP_RESET_ADMIN_PASSWORD` | (vacío) | `true` **solo** durante un despliegue para restablecer la clave del administrador con `DJANGO_SUPERUSER_PASSWORD`; desactivar después |

Cambios en `render.yaml` (**requieren autorización antes de aplicar el Blueprint**):

1. `CORS_ALLOWED_ORIGIN_REGEXES` → `CORS_ALLOWED_ORIGINS=https://cintac-cotizador.onrender.com`.
   Después de sincronizar, **borrar manualmente** `CORS_ALLOWED_ORIGIN_REGEXES` en el panel
   del servicio API (Render no elimina variables por sí solo).
2. Cabeceras del sitio estático: CSP, HSTS, X-Frame-Options, nosniff, Referrer-Policy,
   Permissions-Policy y caché inmutable para `/assets/*`.

## Procedimiento recomendado de publicación

1. Revisar el PR de `eva3-finalizacion-integral` → `main`.
2. **Antes de fusionar:** en Render, crear un respaldo manual o exportar la base
   (`pg_dump` con la URL externa) — el plan gratuito no tiene respaldo automático.
3. Fusionar a `main`. Con `autoDeployTrigger: checksPass`, el despliegue depende de que
   GitHub Actions finalice; si Actions sigue bloqueado por facturación, desplegar
   manualmente con *Manual Deploy* en Render.
4. Verificar: `GET /health/` → `{"status":"ok"}`, login de cada rol, una cotización con y
   sin valor de carga, historial y exportación CSV.
5. Aplicar/sincronizar el Blueprint y borrar `CORS_ALLOWED_ORIGIN_REGEXES`.

## Plan de rollback

| Situación | Acción |
|---|---|
| Error de interfaz o lógica sin tocar datos | Render → servicio → *Rollback* al despliegue anterior. Las columnas nuevas son nulas o tienen valores coherentes; el código anterior las ignora. |
| Revertir el código en Git | `git revert -m 1 <merge>` y desplegar. |
| Revertir migraciones (solo si es imprescindible) | `python manage.py migrate cotizador 0011` elimina las columnas `total_final_*` (el historial vuelve a calcularse con el método anterior, con el mismo resultado) y la bitácora. **Hacerlo solo con respaldo previo**: se pierde la bitácora. |
| Datos maestros erróneos tras una importación | Administración → Bitácora → *Restaurar estado anterior* (reversible). |
| Pérdida de la clave del administrador | Desplegar una vez con `BOOTSTRAP_RESET_ADMIN_PASSWORD=true` y luego quitarla. |

## Secretos

Ningún secreto está en el repositorio. `.env.example` solo contiene marcadores.
Las pruebas de esta rama se ejecutaron contra PostgreSQL local con credenciales ficticias;
no se usó `DATABASE_URL` de producción ni se ejecutaron cargas contra Render.
