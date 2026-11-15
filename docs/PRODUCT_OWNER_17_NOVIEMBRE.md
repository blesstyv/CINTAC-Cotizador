# Requisitos finales del Product Owner — exposición 17-11-2026

## Fuente y aclaración del tránsito

La planilla compartida por el Product Owner consignaba **5 días como mínimo y 3 días como máximo**. Posteriormente, el responsable del proyecto confirmó para la implementación que el intervalo correcto es **3 días mínimo y 5 días máximo** para ambas rutas. Esta aclaración se registra expresamente; no es una corrección silenciosa de la fuente.

## Requisitos obligatorios

- Herramienta de uso **interno**, protegida por autenticación.
- Valor monetario de la carga **opcional**; cuando se incorpora, se suma **una sola vez** al flete. Desactivado o vacío = cero adicional.
- Contenedor 20 pies: **23 toneladas** de capacidad.
- Contenedor 40 pies: **25 toneladas** de capacidad.
- Cantidad de contenedores **calculada automáticamente** a partir del peso, nunca digitada.
- Puertos de origen y destino, peso en kg o toneladas y valor monetario opcional de la carga.
- No mostrar la fuente de tarifa debajo del resultado; las tarifas se actualizan manualmente desde administración.
- No agregar IVA adicional al flete internacional estimado.
- Incorporar las dos rutas internacionales hacia **Callao, Perú**.

## Valores confirmados para las dos rutas nuevas

| Origen | País origen | Destino | País destino | Tipo de ruta | 20' min (USD) | 20' max (USD) | 40' min (USD) | 40' max (USD) | Tránsito mínimo | Tránsito máximo |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| San Antonio | Chile | Callao | Perú | Directo | 900 | 900 | 970 | 970 | **3 días** | **5 días** |
| Valparaiso | Chile | Callao | Perú | Directo | 900 | 900 | 970 | 970 | **3 días** | **5 días** |

Las dos rutas comparten **un único puerto de destino Callao**. En el sistema se conserva la grafía `Valparaiso` ya utilizada por los registros existentes para no crear un puerto duplicado.

## Cómo se implementan

- La PR de aceptación permite elegir y mostrar el país de destino (Perú) en la administración y el cotizador.
- El comando `python manage.py incorporar_rutas_callao` crea las dos rutas y sus tarifas de forma **idempotente**.
- `backend/build.sh` lo ejecuta después de `bootstrap_production` en el próximo despliegue del backend a Render.
- Si una tarifa o tránsito de estas rutas ya existe y COMEX lo editó, el comando **no lo sobrescribe**.
- Si falta un puerto de origen, o si la ruta existente es incompatible, el comando interrumpe la transacción sin dejar escrituras parciales.
- PostgreSQL debe pasar de **16 a 18 rutas** y de **32 a 36 tarifas**, sin modificar las cotizaciones históricas.

## Pruebas incorporadas

- Dos rutas directas Chile → Callao, país destino Perú, tarifas correctas y tránsito 3–5.
- Repetir la carga sin duplicar puertos, rutas ni tarifas.
- Conservar tarifas y tránsitos editados posteriormente por COMEX.
- Rechazar el rango invertido original (5–3 días).
- Cantidad automática en límites de 23 y 25 toneladas.
- Equivalencia entre kg y toneladas.
- Rechazo de la cantidad manual enviada por API.

## Validación y despliegue

Los cambios de esta PR todavía deben comprobarse e integrarse a `main` para quedar publicados; no confundir código preparado con datos presentes en producción. GitHub Actions continúa bloqueado por un problema de facturación de la cuenta, independiente del software.

Una vez desplegado, comprobar por SQL y por API:
- 11 puertos, 18 rutas, 36 tarifas.
- Dos rutas a Callao con tránsito 3–5 y tipo `Directo`.
- Capacidad 20' = 23 TN y 40' = 25 TN.
- Cotización de 24 TN y 46 TN con selección automática y precios correctos.
- Integridad de usuarios, cotizaciones y tarifas previas.
