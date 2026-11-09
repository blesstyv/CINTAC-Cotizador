# EVA3 — Validación de estabilidad antes de publicar

**Objetivo:** asegurar que una actualización de la aplicación no sobrescriba datos maestros ni credenciales de la cuenta administradora y que solo el frontend autorizado pueda acceder a la API mediante CORS.

## Pruebas automatizadas añadidas

| ID | Caso | Resultado esperado | Estado |
| --- | --- | --- | --- |
| REG-01 | Primer `bootstrap_production` con base vacía | Crea los datos de ejemplo y un administrador | Incluido en suite; ejecución pendiente |
| REG-02 | Ejecutar bootstrap por segunda vez tras cambiar una capacidad | Conserva capacidad existente | Incluido en suite; ejecución pendiente |
| REG-03 | Ejecutar bootstrap tras cambiar contraseña del administrador | No restablece contraseña anterior | Incluido en suite; ejecución pendiente |
| REG-04 | Existe un usuario normal con el nombre de administrador configurado | Se rechaza el bootstrap sin elevar privilegios | Incluido en suite; ejecución pendiente |
| REG-05 | Aplicación web accede a API desde origen autorizado | CORS permite `https://cintac-cotizador.onrender.com` | Pendiente de verificar tras despliegue |
| REG-06 | API desde origen no autorizado | No se devuelve `Access-Control-Allow-Origin` para ese origen | Pendiente de verificar tras despliegue |

**Importante:** GitHub Actions está bloqueado a nivel de cuenta por facturación y no ejecuta jobs en este momento. Hasta correr los tests, estos casos **no se declaran aprobados**. La implementación propuesta permanece en rama y la versión pública no se modifica.

## Comandos para validar en entorno con PostgreSQL de pruebas

Desde la raíz del repositorio:

```powershell
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test cotizador.test_bootstrap_production -v 2
python manage.py test cotizador
```

Requiere `DATABASE_URL` de una base PostgreSQL **de pruebas**, nunca la de producción. No ejecutar estos comandos con credenciales de producción.

Frontend:

```powershell
cd frontend
npm ci
npm run lint
npm run build
npm audit --audit-level=high
```

## Lista de pruebas manuales para la presentación

| ID | Acción | Esperado | Evidencia |
| --- | --- | --- | --- |
| EVA3-01 | Login como administrador | Acceso a cotizador, historial y administración | Captura de menú |
| EVA3-02 | Login como encargado | Gestión de datos permitida; gestión de usuarios denegada | Capturas |
| EVA3-03 | Login como usuario estándar | Cotizador e historial disponibles; administración denegada | Capturas |
| EVA3-04 | Cotización de prueba | USD, contenedor, tránsito y contingencia coherentes | Captura de resultado |
| EVA3-05 | Consultar historial | Cotización anterior se recupera sin modificarla | Captura de historial |
| EVA3-06 | Aplicar filtros de historial | Resultados filtrados por parámetros correctos | Captura |
| EVA3-07 | Validar Excel sin importar | Reporta errores/estructura sin modificar datos | Captura |
| EVA3-08 | Intentar importar Excel inválido | Rechazo y estado de BD sin cambios | Captura + conteos |
| EVA3-09 | Probar pantalla móvil/tablet | Formularios visibles y navegación usable | Captura responsive |
| EVA3-10 | Cerrar sesión | Token anterior deja de autorizar acceso | Evidencia HTTP/API |
| EVA3-11 | Visitar `/health/` | HTTP 200 y `{"status":"ok"}` | Captura del endpoint |

En pruebas con importación válida, usar únicamente archivos de laboratorio controlados y verificar antes el alcance de la modificación. No sobrescribir tarifas de demostración justo antes de la defensa.

## Evidencia de despliegue

- Frontend: https://cintac-cotizador.onrender.com
- API: https://cintac-cotizador-api.onrender.com
- Health check: https://cintac-cotizador-api.onrender.com/health/
- Repositorio: https://github.com/blesstyv/CINTAC-Cotizador

Registrar en el informe para cada test: entrada, precondición, esperado, obtenido, estado, fecha, evidencia, discrepancia, causa y corrección.
