# Plan de pruebas y resultados — EVA3

Fecha de ejecución: 12-11-2026 · Rama `eva3-finalizacion-integral`.

## Entorno

- PostgreSQL 16.15 local, base de pruebas **independiente** (nunca `DATABASE_URL` de producción).
- Python 3.13, Django 6.1.3, DRF 3.18.3. Node 22 (local) para lint/build.
- GitHub Actions está bloqueado por facturación de la cuenta: **no es un fallo del proyecto**.
  Todo se ejecutó localmente con los mismos comandos del workflow (`.github/workflows/ci.yml`).

## Resultados obtenidos

| Validación | Comando | Resultado |
|---|---|---|
| Migraciones sin cambios pendientes | `makemigrations --check --dry-run` | ✅ No changes detected |
| Configuración | `manage.py check` | ✅ 0 issues |
| Configuración de producción | `check --deploy --fail-level WARNING` (DEBUG=False) | ✅ 0 issues |
| Suite Django | `manage.py test cotizador` | ✅ **296 pruebas, 0 fallos, 0 errores** |
| Cobertura (ramas) | `coverage run … && coverage report` | ✅ **91 %** (umbral CI: 85 %) |
| Dependencias Python | `pip-audit -r requirements.txt --strict` | ✅ sin vulnerabilidades (antes: 3 CVE en DRF) |
| Dependencias Node | `npm audit` | ✅ 0 vulnerabilidades |
| Lint frontend | `npm run lint` (oxlint) | ✅ 0 advertencias |
| Build frontend | `npm run build` | ✅ JS 288,9 kB (84,1 kB gzip); imagen principal 2,6 MB → 241 kB |
| Actualización de producción simulada | base creada con `main` + cotizaciones → `migrate` | ✅ totales idénticos antes/después |
| Reversión de migraciones | `migrate cotizador 0011` y vuelta | ✅ sin errores |
| E2E en navegador (Chrome headless) | flujo real frontend + API + PostgreSQL | ✅ sin errores de consola |

Línea base al iniciar la sesión: 224 pruebas OK. Se agregaron **72**: 8 de bootstrap,
28 de cotización/valor de carga/tipo de cambio, 36 de seguridad, permisos, CSV, Excel,
bitácora y restauración. Las 224 originales se conservaron.

## Cobertura del plan (qué se prueba)

| Área | Casos representativos | Archivo |
|---|---|---|
| Cálculos normales | cantidad, tarifas, totales, recomendación | `tests.py`, `test_matematica_cotizador.py` |
| Valor 0 / ausente / nulo / inactivo | `incluir_valor_carga=false` ignora el monto | `test_valor_carga.py`, `test_eva3_finalizacion.py` |
| USD y CLP | conversión con el dólar de la cotización, sin doble conversión | ambos |
| Redondeo | centavos USD, pesos CLP, 1 CLP ≈ 0,00 USD | `test_eva3_finalizacion.py` |
| Negativos, texto, >2 decimales, límites | rechazo con mensaje | `test_valor_carga.py` |
| Contingencia y tránsito | base + contingencia | `test_matematica_cotizador.py` |
| Historial | no recalcula con dólar posterior; filtros; paginación | `test_historial.py`, `test_eva3_*` |
| Permisos | matriz 7 endpoints × 4 perfiles | `test_eva3_seguridad_datos.py` |
| Autenticación | expiración, bloqueo por cuenta, revocación, usuarios inactivos | `test_seguridad_sesiones.py`, `test_eva3_seguridad_datos.py` |
| Excel | vacío, extensión, tamaño, encabezados, duplicados, negativos, mín>máx, fórmulas | `test_importador.py`, `test_robustez_importador.py` |
| Integridad PostgreSQL | CHECK y UNIQUE rechazan datos inválidos | `test_valor_carga.py`, `test_eva3_finalizacion.py` |
| Recuperación | importación fallida revierte; restauración y su reversión | `test_eva3_seguridad_datos.py` |
| Tipo de cambio | en línea, caché, respaldo, sin respaldo, JSON inválido, NaN | `test_robustez_tipo_cambio.py`, `test_eva3_finalizacion.py` |
| Despliegue | redeploy no toca tarifas, capacidades ni contraseñas | `test_bootstrap_production.py` |

## Esperado vs obtenido (casos clave, E2E)

Ruta Shanghai → San Antonio, 60.000 kg, contenedor 20' (23 TN), dólar 950,25.

| Caso | Esperado | Obtenido |
|---|---|---|
| Cantidad | ⌈60 / 23⌉ = 3 | 3 ✅ |
| Flete total | 3 × 1.600–2.800 = 4.800–8.400 USD | US$ 4.800 – 8.400 ✅ |
| Sin valor de carga | Total final = flete | US$ 4.800 – 8.400; CLP 4.561.200 – 7.982.100 ✅ |
| Con 300.000 CLP | 300.000 / 950,25 = 315,71 USD, sumado una vez | US$ 5.115,71 – 8.715,71 ✅ |
| CLP con valor | 4.561.200 + 300.000 | $4.861.200 – $8.282.100 ✅ |
| Fuente de tarifa | No visible bajo el resultado | No visible (verificado en el texto renderizado) ✅ |
| Exportación CSV | Solo registros autorizados, filtros aplicados | ✅ (archivo `cintac-historial-AAAA-MM-DD.csv`) |
| Restauración | Vuelve al estado previo y queda registrada | ✅ |

## Discrepancias encontradas y corregidas

1. **Historial vs. cotización con montos CLP muy pequeños:** el historial omitía el monto CLP
   cuando su equivalente redondeaba a 0,00 USD; la cotización sí lo sumaba. Unificado en
   `services/calculo_cotizacion.py`.
2. **CLP del flete en el historial** se mostraba como `8006295.00` y en la cotización como
   `8006295`. Unificado a pesos enteros.
3. **Respaldo del despliegue confundido con caché:** el registro de respaldo, recién creado
   con una fecha antigua, se presentaba como "valor vigente" durante 60 minutos. Ahora la
   caché exige fecha de referencia ≤ 5 días y se informa la antigüedad.
4. **Redeploy destructivo:** `bootstrap_production` restablecía la contraseña del
   administrador, forzaba superusuario y reescribía capacidades en cada despliegue.
5. **Exportación CSV** con punto decimal y separador `;`: Excel en español la interpretaba
   mal. Ahora usa coma decimal.

## Limitaciones de la evidencia

- No se ejecutaron pruebas de carga contra Render (servicio gratuito); existe el comando
  `probar_rendimiento` para hacerlo de forma controlada.
- La E2E se ejecutó en Chrome headless local, no en el despliegue de Render.
- No se midió accesibilidad con un lector de pantalla real; se aplicaron roles ARIA,
  etiquetas, foco visible y `prefers-reduced-motion`.
