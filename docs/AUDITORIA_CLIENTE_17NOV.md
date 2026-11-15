# Auditoría final de aceptación — CINTAC | 17 de noviembre de 2026

## Alcance y evidencia

Auditoría efectuada el **15-11-2026** sobre `main` (commit `e5eac1733faef9927d797fe9bef2f2000039e26d`), la base PostgreSQL de Render (consultas SQL de solo lectura), los estados de despliegue y las instrucciones del Product Owner entregadas por el equipo.

Se **sincronizó el frontend** de Render con el backend, ambos en el commit `e5eac17`. El build Vite de Render finalizó satisfactoriamente el 15-11: 26 módulos transformados, build en 612 ms y 0 vulnerabilidades de npm declaradas por el instalador. El backend ya estaba publicado en esa revisión.

## Criterios solicitados

| Requisito Product Owner | Inspección | Evidencia | Resultado |
|---|---|---|---|
| Carga monetaria opcional | Control explícito y servicio de cálculo backend | App.jsx, serializers.py, calculo_cotizacion.py, test_eva3_finalizacion.py | Implementado en main; E2E documentado en versión del 13-11 |
| Sin carga -> 0 adicional | total_final = flete | 16 cotizaciones reales sin discrepancias SQL | Validado por datos de producción |
| 20' = 23 TN | Modelo y base de datos | SQL sobre cotizador_tipocontenedor | 23,00 TN |
| 40' = 25 TN | Modelo y base de datos | SQL sobre cotizador_tipocontenedor | 25,00 TN |
| Cantidad automática | CEILING(peso/capacidad) en Django; API rechaza campos no admitidos | views.py, serializers.StrictSerializer | Implementado; prueba nueva agregada en rama |
| Origen / destino | React y Django | App.jsx, views.py | Implementado |
| Peso kg / TN | Cálculo decimal y selector | views.py, serializers.py | Implementado |
| Fuente de tarifas oculta | No presente en la interfaz de resultado | App.jsx | Implementado |
| Destinos Callao | No existe Callao en la base actual | SQL de rutas/puertos | **Pendiente** por tiempos incompatibles |
| Internalidad | Login y permisos + metadatos noindex | Login, DRF, index.html en rama | Control de acceso existente; noindex pendiente |
| Tarifas manuales | Administración puede crear/editar rutas, respaldar/restaurar | rutas_admin_views.py, services/datos_maestros.py | Implementado |

## Comprobaciones independientes ejecutadas

**Base de datos productiva (solo lectura):**

- 2 tipos activos: 20' = 23 toneladas y 40' = 25 toneladas.
- 10 puertos, 16 rutas, 32 tarifas, 16 tránsitos y 16 cotizaciones.
- No existen rutas con destino Callao ni puerto Callao.
- No existen tránsitos almacenados con máximo inferior al mínimo.
- 0 tarifas con importes no positivos o máximo < mínimo.
- 0 cotizaciones con total final inferior a flete.
- 0 registros donde valor de carga = 0 y total final difiera del flete.
- 0 registros donde valor de carga > 0 y total final USD no sea flete USD + valor USD.
- Usuarios activos: 1 administrador, 1 encargado y 1 usuario.

**Escenarios analíticos con capacidades reales de PostgreSQL:**

| Peso (TN) | 20' (23 TN) | 40' (25 TN) |
|---:|---:|---:|
| 23 | 1 | 1 |
| 23,001 | 2 | 1 |
| 24 | 2 | 1 |
| 25 | 2 | 1 |
| 26 | 2 | 2 |
| 46 | 2 | 2 |
| 50 | 3 | 2 |

Se verificó por SQL la fórmula `CEIL(peso_tn / capacidad_tn)`, la misma que utiliza `obtener_opciones` en Django. **No equivale a ejecutar estas entradas por el endpoint autenticado en la sesión actual**.

## Pruebas automatizadas

El informe `docs/PRUEBAS_Y_RESULTADOS.md` de la versión anterior del 13-11 registra **313 pruebas Django aprobadas** (PostgreSQL local), 92% cobertura, auditorías de dependencias, lint/build y E2E local. Esta es **evidencia documental del repositorio**, no una nueva ejecución de esta auditoría.

En `eva3-client-callao-17nov` se agregaron casos de:

- Cantidades automáticas con peso 23/25 toneladas y valores de borde.
- Equivalencia entre 23.001 kg y 23,001 TN.
- Rechazo de cantidad de contenedores escrita por cliente.
- Dos rutas Chile → Callao (Perú) compartiendo un puerto.
- Rechazo del rango invertido 5–3 días entregado por el Product Owner.
- País Perú expuesto por la API pública.

**Estado:** pruebas nuevas creadas y pendientes de ejecución. GitHub Actions aún falla antes de iniciar por bloqueo de facturación. No afirmar 100% de aprobación sin ejecutarlas.

## Desajuste en la fuente de cliente

Las dos filas enviadas indican, literalmente:

- Origen San Antonio (Chile) y Valparaiso (Chile); destino Callao (Perú); tipo Directo.
- Tarifa 20' mínimo/máximo: US$ 900 / 900.
- Tarifa 40' mínimo/máximo: US$ 970 / 970.
- Tiempo **mínimo 5** y **máximo 3** días.

Se debe solicitar confirmación al Product Owner. **No inventar ni invertir los tiempos sin dejar constancia**. El esquema actual y la API bloquean correctamente ese dato.

## Cambios preparados en la PR de aceptación

- País de destino explícito y requerido en la interfaz administrativa.
- País de destino devuelto por API y visible en la selección de puertos.
- Ambos países en la tabla de rutas.
- Metadatos `noindex` para una herramienta que no debe publicarse como página institucional abierta.
- Pruebas funcionales y de validación de Callao.
- Documentación exacta de los datos recibidos.

La PR está en modo draft y **no se ha desplegado**. No modifica las 16 cotizaciones existentes.

## Riesgos pendientes antes del martes

1. **Bloqueante:** confirmar tiempo de tránsito válido para Callao.
2. Agregar las dos rutas en producción con autorización explícita, respetando la validación y registrando respaldo/bitácora.
3. Ejecutar la suite Django y el build/lint del código de la rama nueva contra PostgreSQL de pruebas.
4. Verificar UI, roles y operaciones a través de sesión autenticada en la versión final; no se usaron credenciales de usuario en esta auditoría.
5. DB Render gratuita con fecha de expiración registrada para **2026-11-21**. Preservar disponibilidad y planificar respaldo/migración antes de esa fecha.
6. El login/roles protegen la herramienta; `noindex` no representa una protección de acceso.

## Alcance honesto

Se inspeccionaron código, despliegues, logs y datos; se ejecutaron comprobaciones SQL no destructivas y un build real de frontend mediante Render. No se ejecutó nuevamente la suite completa de Django ni un recorrido autenticado de todos los formularios y roles. Ningún hallazgo se debe presentar como una certificación absoluta del sistema.
