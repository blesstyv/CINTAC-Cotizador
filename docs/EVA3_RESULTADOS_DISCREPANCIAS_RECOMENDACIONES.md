# EVA3 — Resultados, discrepancias y recomendaciones

## 1. Resumen ejecutivo de pruebas

La solución se encuentra desplegada en Render con React, Django REST Framework y PostgreSQL 16. La última ejecución de integración continua sobre main completó 190 pruebas backend sin fallos, además del análisis estático y build del frontend.

## 2. Resultados obtenidos en producción

### RP-01 — Login administrador

**Esperado:** un usuario administrador autorizado inicia sesión y obtiene acceso al cotizador y funciones administrativas.

**Obtenido:** `admin_cintac` inició sesión correctamente en la aplicación pública.

**Resultado:** Aprobado.

### RP-02 — Cotización y persistencia

**Entrada:** Shanghai → Valparaíso, 9.999 kg, contenedor 20', contingencia 5 días.

**Esperado:** cálculo de tarifa, tránsito y persistencia histórica.

**Obtenido:** Cotización #1 guardada en PostgreSQL con rango USD 1.650–2.850 y tránsito estimado 31–39 días.

**Resultado:** Aprobado.

### RP-03 — Conversión CLP

**Entrada:** Shanghai → San Antonio, 100.000 kg, 5 contenedores de 20', contingencia 3 días.

**Esperado:** cálculo USD y equivalente CLP.

**Obtenido:** Cotización #2 guardada con USD 8.000–14.000 y CLP 7.814.560–13.675.480 usando 976,82 CLP/USD.

**Resultado:** Aprobado.

### RP-04 — Historial

**Esperado:** las cotizaciones generadas deben recuperarse desde PostgreSQL.

**Obtenido:** Historial muestra Cotización #1 y #2 con usuario, fecha, ruta, carga, contenedor y total USD.

**Resultado:** Aprobado.

## 3. Discrepancias detectadas y análisis de causa

| ID | Resultado esperado | Resultado inicial | Causa raíz | Acción correctiva | Estado |
|---|---|---|---|---|---|
| D-01 | PostgreSQL poblado al primer deploy | BD creada sin datos iniciales | `initialDeployHook` no produjo ejecución observable en el primer Blueprint | Bootstrap movido al flujo de build, de forma idempotente | Corregido |
| D-02 | Suite compatible con PostgreSQL | Una prueba extrema falló al persistir | Precisión de campos numéricos y entero de 32 bits insuficientes; SQLite no exponía el problema | Se ampliaron DecimalField y cantidad a PositiveBigIntegerField; migración 0009 | Corregido |
| D-03 | Conversión USD/CLP disponible | Primer intento sin conversión | Timeout del proveedor externo y ausencia de valor previo en caché | Respaldo persistente configurable + pruebas de no sobrescritura | Corregido |
| D-04 | Documentación refleje implementación actual | README describía bootstrap como acción de primer despliegue | Evolución del mecanismo de inicialización después del primer deploy | Actualizar documentación antes de cierre EVA3 | Pendiente documental |

## 4. Validación de correcciones

- D-01: datos iniciales creados en PostgreSQL y administrador activo.
- D-02: suite completa volvió a pasar contra PostgreSQL 16.
- D-03: segunda cotización mostró conversión CLP y quedó persistida.
- D-04: se corrige en la rama de evidencias EVA3 antes de integrarla a main.

## 5. Recomendaciones de mejora continua

1. Mantener GitHub Actions como puerta de calidad antes del despliegue.
2. Conservar PostgreSQL como único motor para evitar diferencias entre desarrollo y producción.
3. Mantener fallback de tipo de cambio y registrar fecha/fuente para trazabilidad.
4. Agregar monitoreo/alertas de disponibilidad del proveedor de tipo de cambio.
5. Ejecutar prueba de rendimiento en producción antes de la presentación y registrar promedio, P95, máximo y errores.
6. Mantener separación de roles y verificar manualmente Usuario, Encargado y Administrador.
7. Migrar la base gratuita de Render a un plan persistente si el proyecto pasa de demostración académica a uso real.
8. Definir una política periódica de respaldo para PostgreSQL antes de un uso operacional real.
9. Mantener una matriz de regresión y actualizarla cuando cambien capacidades, tarifas o reglas de negocio.
10. Registrar cada incidencia de producción con causa raíz y acción correctiva para generar evidencia de mejora continua.

## 6. Pendientes para cierre

- Validación manual de permisos por rol.
- Validación manual de creación/edición/desactivación de usuarios.
- Validación manual de importación Excel.
- Validación de filtros de historial.
- Validación responsive.
- Ejecución y registro de rendimiento/estrés en producción.
- Preparación del informe final y defensa.
