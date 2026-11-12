# Seguridad — CINTAC-Cotizador

## Dependencias (S01)

| Paquete | Antes | Ahora | Motivo |
|---|---|---|---|
| Django | 6.1.1 | **6.1.3** | Versión de seguridad del 3-nov-2026 (6 vulnerabilidades) |
| djangorestframework | 3.18.1 | **3.18.3** | `pip-audit`: 3 CVE corregidas en 3.18.2 |
| psycopg[binary] | 3.3.6 | 3.3.8 | Parche de errores (misma rama) |

No se actualizaron versiones mayores (p. ej., Gunicorn 27) por no existir aviso de
seguridad y para no introducir riesgo antes de la defensa.
Resultado actual: `pip-audit --strict` sin vulnerabilidades; `npm audit` 0 vulnerabilidades.

## Autenticación (S02)

- Token DRF con expiración (`TOKEN_EXPIRATION_HOURS`, 8 h); al expirar se elimina.
- Un nuevo login invalida el token anterior; logout elimina el token.
- **Nuevo:** bloqueo por cuenta tras `LOGIN_MAX_FALLOS` (10) intentos fallidos durante
  `LOGIN_BLOQUEO_SEGUNDOS` (900 s), independiente de la IP. La clave en caché es un hash
  SHA-256 del usuario (no se guardan nombres).
- Límite por IP existente: 5 intentos/minuto.
- **Nuevo:** cambiar la contraseña o el rol de un usuario revoca sus sesiones activas.
- Usuarios desactivados: rechazados por DRF y por los permisos; desactivar revoca tokens.
- Mensaje de error idéntico para usuario inexistente y contraseña incorrecta.
- Contraseñas: validadores de Django (largo, comunes, numéricas, similitud) y hash PBKDF2.

## Roles y permisos (S03)

Verificados en el backend (`permissions.py`) y cubiertos por una matriz automatizada
(`MatrizPermisosTests`):

| Endpoint | USUARIO | ENCARGADO | ADMINISTRADOR | Anónimo |
|---|---|---|---|---|
| Cotizar, rutas | ✔ | ✔ | ✔ | 401 |
| Historial / exportar | Solo propio | Todos | Todos | 401 |
| Datos maestros, bitácora | 403 | ✔ | ✔ | 401 |
| Restaurar datos maestros | 403 | 403 | ✔ | 401 |
| Usuarios | 403 | 403 | ✔ | 401 |

Anti-escalada: serializadores estrictos rechazan campos no declarados (`is_superuser`,
`is_staff`…); un usuario no puede quitarse su propio rol de administrador; debe quedar
al menos un administrador activo; los superusuarios solo se gestionan por consola.
El bootstrap de Render **ya no eleva** una cuenta existente ni cambia su contraseña.

## Protección web (S04)

| Control | API Django | Frontend (Render static) |
|---|---|---|
| HTTPS / redirect | `SECURE_SSL_REDIRECT` | Render |
| HSTS | 1 año, subdominios | `max-age=31536000` (render.yaml) |
| CSP | `SECURE_CSP` (Django 6): `default-src 'self'`, `frame-ancestors 'none'` | `script-src 'self'`, `connect-src` solo la API |
| Clickjacking | `X-Frame-Options: DENY` | `X-Frame-Options: DENY` |
| MIME sniffing | `nosniff` | `nosniff` |
| Referrer | `strict-origin-when-cross-origin` | igual |
| COOP | `same-origin` | — |
| Permissions-Policy | — | cámara, micrófono y geolocalización deshabilitados |
| Cookies | Secure, HttpOnly, SameSite=Lax | — (el token vive en `sessionStorage`) |
| CORS | Origen exacto `https://cintac-cotizador.onrender.com` | — |
| XSS | JSON + React escapa por defecto; sin `dangerouslySetInnerHTML` | — |
| CSRF | No aplica a la API con token en cabecera; activo en `/admin/` | — |
| Entradas | Serializadores estrictos, límites de dígitos y decimales, tamaño de solicitud 6 MB | Validación previa |
| Errores | Manejador uniforme: JSON genérico y traza solo en el log | Mensajes amigables |
| CSV | Prefijo `'` ante `= + - @ \t \r` (CSV injection) | — |
| Excel | Solo `.xlsx`, ≤ 5 MB, rechaza fórmulas, temporales eliminados | — |

## Secretos

`DJANGO_SECRET_KEY` generado por Render; `DJANGO_SUPERUSER_PASSWORD` con `sync: false`;
`DATABASE_URL` desde el servicio PostgreSQL. `.env` está en `.gitignore`. Las pruebas usan
una base PostgreSQL local independiente y credenciales ficticias.

## Riesgos pendientes

1. El bloqueo por cuenta y el límite por IP usan la caché en memoria de cada proceso de
   Gunicorn; con varios workers el límite efectivo se multiplica. Recomendado: Redis.
2. El límite por IP usa `X-Forwarded-For` completo (comportamiento por defecto de DRF);
   un atacante puede variarlo. Se mitiga con el bloqueo por cuenta. Ajustar
   `NUM_PROXIES` requiere confirmar la cadena de proxies de Render.
3. El token se guarda en `sessionStorage` (se borra al cerrar la pestaña); una cookie
   HttpOnly sería más robusta frente a XSS, pero implica rediseñar CORS/CSRF.
4. Si el Blueprint se aplica, la variable antigua `CORS_ALLOWED_ORIGIN_REGEXES` debe
   borrarse manualmente en Render: Render no elimina variables que ya no estén en el YAML.
