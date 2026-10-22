# EVA3 — Implementación, entorno y seguridad

## 1. Arquitectura final

```text
Usuario
  ↓ HTTPS
React + Vite — Render Static Site
  ↓ HTTPS / JSON
Django REST Framework + Gunicorn — Render Web Service
  ↓
PostgreSQL 16 — Render
```

La aplicación usa PostgreSQL como único motor de persistencia.

## 2. Automatización del entorno

El archivo `render.yaml` declara:

- Base de datos PostgreSQL.
- Backend Django.
- Frontend React.
- Variables de entorno.
- Health check.
- Comandos de build/start.
- Referencias entre servicios.
- Despliegue automático sujeto a checks aprobados.

El backend ejecuta durante el build:

1. Instalación de dependencias.
2. `collectstatic`.
3. Migraciones.
4. Bootstrap idempotente de datos y administrador.

## 3. Integración continua

GitHub Actions valida cada cambio relevante mediante:

### Backend
- PostgreSQL 16 temporal.
- Instalación de dependencias.
- `makemigrations --check --dry-run`.
- `manage.py check`.
- Suite completa de tests.

### Frontend
- `npm ci`.
- `npm run lint`.
- `npm run build`.

Render está configurado con `checksPass`, por lo que un commit con CI fallido no debe convertirse en despliegue automático.

## 4. Seguridad aplicada

- Secretos fuera del repositorio.
- Contraseñas gestionadas por el sistema de autenticación de Django.
- Token con expiración.
- Control de acceso basado en roles.
- Permisos comprobados en backend.
- Throttling de login.
- CORS restringido.
- HTTPS y redirección segura en producción.
- HSTS.
- Cookies seguras/HttpOnly.
- Protección contra framing.
- `nosniff`.
- Validaciones de entrada.
- Constraints en PostgreSQL.
- Transacciones atómicas para importaciones.
- Principio de mínimo privilegio.
- Health check que comprueba conectividad real con la base de datos.

## 5. Persistencia y optimización

El modelo separa puertos, rutas, tarifas, tiempos de tránsito, tipos de contenedor, perfiles y tipos de cambio. Se utilizan:

- ForeignKey.
- OneToOneField.
- UniqueConstraint.
- CheckConstraint.
- Índices individuales y compuestos.
- PROTECT/CASCADE de acuerdo con la semántica de cada relación.

La entidad Cotizacion conserva un snapshot de los valores utilizados al cotizar. Esta duplicación es deliberada para trazabilidad histórica: cambios futuros de tarifas, rutas o tipo de cambio no deben modificar una cotización ya emitida.

## 6. Repetibilidad

Para recrear la infraestructura:

1. Conectar el repositorio a Render.
2. Crear Blueprint usando `render.yaml`.
3. Definir `DJANGO_SUPERUSER_PASSWORD`.
4. Aplicar Blueprint.
5. Esperar CI y despliegue.
6. Verificar `/health/`.
7. Iniciar sesión y ejecutar pruebas funcionales.

No se requiere editar manualmente URLs del frontend ni credenciales de base de datos.
