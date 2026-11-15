# Auditoría de aceptación — CINTAC | 17 de noviembre de 2026

## Requisitos confirmados

- Se incorpora **opcionalmente** el valor de la carga al flete; cuando no se conoce, el adicional es cero.
- Contenedor de 20 pies = **23 TN** y de 40 pies = **25 TN**.
- Cantidad de contenedores calculada con redondeo hacia arriba a partir de kg o TN, sin entrada manual.
- Fuente de tarifas oculta debajo del resultado.
- No se agrega IVA al cálculo estimado del flete internacional.
- Herramienta interna de COMEX con roles.
- Dos rutas directas Chile → Callao (Perú), con tarifas 20' US$900 y 40' US$970.
- **Tránsito mínimo 3 y máximo 5 días**, rectificación confirmada expresamente para el proyecto. La planilla original consignaba 5 y 3, en orden invertido.

## Estado previo al despliegue (15-11-2026)

Se verificó mediante SQL de solo lectura en PostgreSQL de Render:

- 10 puertos, 16 rutas y 32 tarifas.
- 16 cotizaciones históricas, 3 usuarios activos en sus tres roles.
- 20 pies = 23 TN, 40 pies = 25 TN.
- 0 tránsitos con rango invertido.
- 0 tarifas de importes inválidos.
- 0 cotizaciones con error de suma del valor monetario de carga.
- Callao todavía no está en producción en el snapshot previo.

Los servicios React y Django publicaban el commit `e5eac17`.

## Cambios implementados en la PR #11

1. País destino explícito y obligatorio en el formulario para crear rutas, no presumir Chile.
2. País de destino en la API pública y en la lista de destinos del cotizador.
3. País origen y destino en administración.
4. Metadatos `noindex` para la herramienta interna (no sustituye la autenticación).
5. Comando `incorporar_rutas_callao`, invocado al final de `backend/build.sh`, que crea si faltan:
   - Un puerto Callao, Perú.
   - San Antonio, Chile → Callao, Perú. Directo. US$900/900 para 20', US$970/970 para 40', 3–5 días.
   - Valparaiso, Chile → Callao, Perú. Directo. Mismas tarifas y tránsito.
6. La carga se ejecuta dentro de transacción; en redeploy no sobrescribe registros ya existentes.
7. Pruebas nuevas de datos del cliente, límites 23/25 TN, conversión kg/TN, rechazo de cantidad manual, idempotencia y rechazo del antiguo rango invertido.

## Resultados de cálculo de borde (evaluación SQL con capacidades reales)

| Peso (TN) | Número contenedores 20' | Número contenedores 40' |
|---:|---:|---:|
| 23 | 1 | 1 |
| 23,001 | 2 | 1 |
| 24 | 2 | 1 |
| 25 | 2 | 1 |
| 26 | 2 | 2 |
| 46 | 2 | 2 |
| 50 | 3 | 2 |

## Objetivo de aceptación tras publicar

- 11 puertos, **18 rutas**, **36 tarifas**.
- Ambas rutas directas a Callao, Perú, tránsito **3–5 días**.
- Resultado para 24 TN: 20' 2 unidades = US$1.800; 40' 1 unidad = US$970.
- Resultado para 46 TN: 20' 2 unidades = US$1.800; 40' 2 unidades = US$1.940.
- Historial de cotizaciones anteriores intacto.
- Usuario, Encargado y Administrador conservados y autorizaciones correctas.
- Backend/frontend de Render sincronizados al mismo commit.

## Límites de verificación

La última ejecución completa documentada en `docs/PRUEBAS_Y_RESULTADOS.md` (13-11-2026) fue de **313 pruebas aprobadas** y 92 % de cobertura. Las nuevas pruebas de la PR #11 no han sido ejecutadas de manera independiente: GitHub Actions está bloqueado por facturación de la cuenta. Es necesario distinguir validaciones SQL, revisión de código y despliegue de una ejecución real de tests.

El servicio PostgreSQL gratuito de Render informa expiración el **21-11-2026**. Priorizar una estrategia de continuidad y respaldo.
