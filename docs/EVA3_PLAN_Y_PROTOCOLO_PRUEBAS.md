# EVA3 — Plan y protocolo de pruebas

## 1. Objetivo

Validar que CINTAC Cotizador cumple los procesos funcionales, de seguridad, persistencia, administración y despliegue definidos para la solución web, incluyendo casos normales, casos de borde, fallos de dependencias externas y pruebas de rendimiento.

## 2. Entorno bajo prueba

- Frontend: React + Vite en Render Static Site.
- Backend: Django REST Framework + Gunicorn en Render Web Service.
- Base de datos: PostgreSQL 16 en Render.
- CI: GitHub Actions.
- URL pública: https://cintac-cotizador.onrender.com
- Health check: https://cintac-cotizador-api.onrender.com/health/

## 3. Protocolo general

Para cada prueba se debe registrar:

1. ID y objetivo.
2. Precondiciones.
3. Datos de entrada.
4. Resultado esperado.
5. Resultado obtenido.
6. Estado: Aprobada / Fallida / Pendiente.
7. Evidencia.
8. Discrepancia detectada, cuando corresponda.
9. Causa raíz.
10. Acción correctiva o recomendación.

Las pruebas automatizadas se ejecutan en GitHub Actions contra PostgreSQL 16. Las pruebas funcionales manuales se ejecutan en la aplicación desplegada en Render.

## 4. Matriz de cobertura

| ID | Área | Escenario | Tipo | Estado actual |
|---|---|---|---|---|
| PT-01 | Autenticación | Login válido | Manual + automatizada | Aprobada |
| PT-02 | Autenticación | Login inválido | Automatizada | Aprobada |
| PT-03 | Seguridad | Limitación de intentos de login | Automatizada | Aprobada |
| PT-04 | Sesión | Cierre de sesión invalida token | Automatizada | Aprobada |
| PT-05 | Sesión | Token expirado o inválido | Automatizada | Aprobada |
| PT-06 | Roles | Administrador accede a gestión de usuarios y datos | Manual + automatizada | Parcial: automatizada aprobada |
| PT-07 | Roles | Usuario estándar no accede a administración | Manual + automatizada | Parcial: automatizada aprobada |
| PT-08 | Usuarios | Crear/editar/desactivar usuario | Manual + automatizada | Parcial: automatizada aprobada |
| PT-09 | Cotizador | Carga de rutas y destinos | Manual + automatizada | Aprobada |
| PT-10 | Cotizador | Conversión kg/TN | Manual + automatizada | Aprobada |
| PT-11 | Cotizador | Límites de capacidad de contenedores 20'/40' | Automatizada de borde | Aprobada |
| PT-12 | Cotizador | Recomendación de contenedor | Manual + automatizada | Aprobada |
| PT-13 | Cotizador | Cálculo tarifa mínima/máxima | Manual + automatizada | Aprobada |
| PT-14 | Cotizador | Contingencia modifica tránsito y no tarifa | Manual + automatizada | Aprobada |
| PT-15 | Moneda | Conversión USD/CLP en línea | Automatizada | Aprobada |
| PT-16 | Moneda | Fallo proveedor externo y uso de respaldo | Manual + automatizada | Aprobada |
| PT-17 | Persistencia | Guardar cotización en PostgreSQL | Manual + automatizada | Aprobada |
| PT-18 | Historial | Listar cotizaciones persistidas | Manual + automatizada | Aprobada |
| PT-19 | Historial | Filtros por usuario/ruta/contenedor/fecha | Manual + automatizada | Pendiente manual |
| PT-20 | Administración | Validar Excel correcto | Manual + automatizada | Pendiente manual |
| PT-21 | Administración | Importar Excel correcto | Manual + automatizada | Pendiente manual |
| PT-22 | Administración | Excel inválido no modifica datos | Automatizada de robustez | Aprobada |
| PT-23 | Administración | Error durante importación revierte transacción | Automatizada de integración | Aprobada |
| PT-24 | Base de datos | Restricciones, FK, unicidad y checks | Automatizada | Aprobada |
| PT-25 | Despliegue | Health check API + PostgreSQL | Producción | Aprobada |
| PT-26 | Despliegue | Migraciones sin cambios pendientes | CI | Aprobada |
| PT-27 | Frontend | Lint | CI | Aprobada |
| PT-28 | Frontend | Build de producción | CI | Aprobada |
| PT-29 | Responsive | Navegación y formularios en viewport reducido | Manual | Pendiente |
| PT-30 | Rendimiento | Latencia promedio/P95 con concurrencia | Estrés | Pendiente ejecución en producción |
| PT-31 | Robustez | Valores extremos de peso y precisión numérica | Automatizada de borde | Aprobada |
| PT-32 | Seguridad | Acceso no autorizado a endpoints protegidos | Automatizada | Aprobada |

## 5. Criterios de aceptación

- Pruebas funcionales principales: 100% aprobadas.
- Suite automatizada: 100% aprobada.
- Sin migraciones pendientes.
- Sin errores de lint ni build.
- Endpoints protegidos deben rechazar accesos sin autorización.
- Importaciones inválidas no deben modificar datos.
- Health check debe responder correctamente con conexión a PostgreSQL.
- Prueba de rendimiento debe registrar promedio, P95, máximo, throughput y errores.

## 6. Evidencia automatizada vigente

Ejecución GitHub Actions del 22-10-2026 sobre la rama main:

- 190 pruebas detectadas.
- 190 pruebas ejecutadas.
- 190 pruebas aprobadas.
- Tiempo de ejecución backend: 20,535 s.
- Django system check: sin problemas.
- Verificación de migraciones: aprobada.
- Frontend lint: aprobado.
- Frontend build: aprobado.

## 7. Evidencias manuales ya realizadas

- Acceso web con administrador.
- Cotización Shanghai → Valparaíso.
- Persistencia de Cotización #1.
- Cotización Shanghai → San Antonio.
- Conversión USD/CLP y persistencia de Cotización #2.
- Visualización de ambas operaciones en Historial.

Las pruebas manuales pendientes se completarán antes de cerrar la documentación final.
