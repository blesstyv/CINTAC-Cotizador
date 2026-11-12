# CINTAC — Cotizador Logístico

Aplicación web para apoyar la cotización logística de importaciones de CINTAC. La solución está preparada para ejecutarse completamente en la web con React, Django REST Framework y PostgreSQL.

## Arquitectura de producción

```text
Usuario
  ↓ HTTPS
React + Vite — Render Static Site
  ↓ HTTPS / JSON
Django REST Framework — Render Web Service
  ↓
PostgreSQL — Render PostgreSQL
```

PostgreSQL es el único motor de base de datos del proyecto.

## Funcionalidades

- Inicio y cierre de sesión con token.
- Autorización y roles Usuario, Encargado y Administrador.
- Cotización por ruta, peso y tipo de contenedor.
- Cálculo de cantidad de contenedores.
- Tarifas mínimas y máximas.
- Tiempo de tránsito y contingencia.
- Conversión USD/CLP con fecha, estado y antigüedad del dólar utilizado.
- Valor monetario de la carga opcional (USD o CLP) con interruptor explícito: se suma una sola vez al flete; desactivado o vacío = 0.
- Desglose financiero completo: contenedor, cantidad, tarifas, flete, valor de carga, total final USD/CLP, tránsito y contingencia.
- Historial de cotizaciones como instantánea inmutable (no se recalcula con tarifas ni dólares posteriores).
- Exportación del historial a CSV respetando permisos y filtros, protegida contra inyección de fórmulas.
- Gestión de usuarios y permisos.
- Importación y validación de datos maestros desde Excel, con vista previa de cambios (actual vs propuesto) y confirmación.
- Actualización transaccional de datos: ante un error PostgreSQL revierte todos los cambios.
- Bitácora de operaciones sobre datos maestros con respaldo del estado anterior y restauración reversible (solo administrador).
- Diseño responsive.
- Health check del backend y de la conexión a PostgreSQL.
- Pruebas unitarias, de integración, robustez y seguridad.
- Pruebas de rendimiento y concurrencia.
- Integración continua mediante GitHub Actions.

## Tecnologías

### Frontend
- React 19
- Vite 8
- JavaScript
- CSS
- Oxlint

### Backend
- Python 3.13
- Django 6.1
- Django REST Framework
- Gunicorn
- WhiteNoise
- django-cors-headers
- openpyxl

### Persistencia e infraestructura
- PostgreSQL
- psycopg
- Render
- GitHub Actions

## Variables de entorno del backend

```text
DJANGO_SECRET_KEY=<clave segura>
DJANGO_DEBUG=False
DATABASE_URL=<URL PostgreSQL>
CORS_ALLOWED_ORIGINS=<orígenes exactos opcionales>
CORS_ALLOWED_ORIGIN_REGEXES=<regex opcional>
TOKEN_EXPIRATION_HOURS=8
LOGIN_MAX_FALLOS=10                    # opcional
LOGIN_BLOQUEO_SEGUNDOS=900             # opcional
TIPO_CAMBIO_REINTENTO_SEGUNDOS=300     # opcional
BOOTSTRAP_RESET_ADMIN_PASSWORD=        # opcional, solo para recuperar la clave
USD_CLP_FALLBACK_VALUE=<valor inicial de respaldo>
USD_CLP_FALLBACK_DATE=<AAAA-MM-DD>
USD_CLP_FALLBACK_SOURCE=<fuente del valor>
```

En Render, `DATABASE_URL` se obtiene directamente del servicio PostgreSQL y `DJANGO_SECRET_KEY` se genera como secreto.

## Variable del frontend

```text
VITE_API_URL=https://<backend>.onrender.com
```

El frontend agrega automáticamente `/api` a esta dirección.

## Despliegue en Render

El repositorio incluye `render.yaml`, que define:

- `cintac-cotizador-db`: PostgreSQL.
- `cintac-cotizador-api`: backend Django.
- `cintac-cotizador`: frontend React.
- Health check `/health/`.
- Migraciones automáticas.
- Archivos estáticos de Django.
- Inicialización de datos solo en una instalación nueva.
- Creación del administrador de producción (sin modificarlo en redeploys).
- Despliegue automático solo cuando los checks de GitHub pasan.

Para crear la infraestructura desde Render:

1. Crear un **Blueprint** a partir de este repositorio.
2. Utilizar la rama `main`.
3. Render detectará `render.yaml`.
4. Definir el secreto `DJANGO_SUPERUSER_PASSWORD`.
5. Aplicar el Blueprint.

El usuario administrador inicial se configura mediante:

```text
DJANGO_SUPERUSER_USERNAME=admin_cintac
DJANGO_SUPERUSER_EMAIL=admin@cintac.cl
DJANGO_SUPERUSER_PASSWORD=<secreto definido en Render>
```

La contraseña no se almacena en GitHub.

## Build del backend

Render ejecuta desde `backend/`:

```bash
bash build.sh
```

El script instala dependencias, recopila archivos estáticos y ejecuta las migraciones.

El servidor de producción utiliza:

```bash
gunicorn config.wsgi:application
```

## Inicialización

En el primer despliegue Render ejecuta:

```bash
python manage.py bootstrap_production
```

El comando es idempotente y seguro para cada redeploy:

- Carga los datos maestros solo si la base no tiene rutas.
- Crea tipos de contenedor faltantes sin modificar capacidades existentes.
- Crea el tipo de cambio de respaldo solo si no existe ninguno.
- Crea el administrador si no existe; si existe, **no** cambia su contraseña ni sus permisos y nunca eleva una cuenta común.
- Para restablecer la clave del administrador, desplegar una vez con `BOOTSTRAP_RESET_ADMIN_PASSWORD=true` y quitarla después.

## API

```text
POST /api/login/
GET  /api/sesion/
POST /api/logout/

GET  /api/tipos-contenedor/
GET  /api/rutas/
POST /api/opciones-contenedores/
POST /api/cotizar/   (opcional: incluir_valor_carga, valor_carga, moneda_valor_carga)

GET  /api/historial/               (?pagina=&por_pagina=&origen=&destino=&contenedor=&desde=&hasta=&usuario_id=)
GET  /api/historial/exportar/      (CSV, mismos filtros y permisos)
GET  /api/historial/<id>/

GET  /api/administracion/resumen/
POST /api/administracion/validar-excel/              (vista previa + comparación + SHA-256)
POST /api/administracion/importar-excel/             (opcional: archivo_sha256)
GET  /api/administracion/operaciones/                (bitácora)
POST /api/administracion/operaciones/<id>/restaurar/ (solo administrador, {"confirmar": true})
GET/POST /api/administracion/usuarios/
GET/PATCH /api/administracion/usuarios/<id>/
```

Health check:

```text
GET /health/
```

## Pruebas automáticas

GitHub Actions ejecuta las pruebas del backend contra PostgreSQL 16 y valida el frontend.

Backend:

```bash
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py check --deploy --fail-level WARNING   # con DJANGO_DEBUG=False
pip-audit -r requirements.txt --strict
coverage run manage.py test cotizador && coverage report   # mínimo 85 %
```

Frontend:

```bash
npm ci
npm audit --audit-level=high
npm run lint
npm run build
```

La rama `main` no debe desplegarse si estos checks fallan.

## Pruebas de rendimiento

El proyecto incluye:

```bash
python manage.py probar_rendimiento \
  --base-url https://<backend>.onrender.com \
  --usuario <usuario autorizado>
```

La prueba mide GET de sesión/rutas y POST de opciones/cotización con distintos niveles de concurrencia, informando promedio, P95, máximo, solicitudes por segundo y errores.

## Seguridad

- Secretos mediante variables de entorno.
- Contraseñas con hashing de Django.
- Token con expiración configurable.
- Autorización comprobada en backend.
- Roles y principio de mínimo privilegio.
- Throttling de login por IP y bloqueo por cuenta tras intentos fallidos.
- Revocación de sesiones al cambiar contraseña o rol.
- CSP, Referrer-Policy y COOP en la API; CSP y cabeceras de seguridad en el sitio estático.
- Errores no controlados respondidos con JSON genérico (sin trazas).
- CORS restringido.
- HTTPS, cookies seguras y HSTS en producción.
- Protección frente a framing.
- Validaciones de entrada.
- Importaciones dentro de transacciones atómicas.
- Tipo de cambio en línea con caché y valor de respaldo persistente para contingencias del proveedor.
- Archivos temporales eliminados después del procesamiento.
- Base de datos separada del código fuente.

## Documentación técnica

- [Arquitectura y modelo de datos](docs/ARQUITECTURA_Y_DATOS.md)
- [Seguridad](docs/SEGURIDAD.md)
- [Despliegue y rollback](docs/DESPLIEGUE.md)
- [Plan de pruebas y resultados](docs/PRUEBAS_Y_RESULTADOS.md)
- [Resumen para la defensa EVA3](docs/EVA3_DEFENSA.md)

## Repositorio

```text
CINTAC-Cotizador/
├── backend/
│   ├── config/
│   ├── cotizador/
│   ├── build.sh
│   └── manage.py
├── docs/
├── frontend/
│   ├── public/
│   ├── src/
│   └── package.json
├── .github/workflows/ci.yml
├── .env.example
├── render.yaml
└── README.md
```

## Proyecto académico

Proyecto Integrado — Analista Programador.

Cliente: CINTAC.

El alcance actual se centra en cotizaciones marítimas de importación mediante contenedores de 20 y 40 pies.
