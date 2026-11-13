# EVA3 — Resumen técnico para la defensa

## Retroalimentación de la profesora (atendida)

| Solicitud | Implementación | Evidencia |
|---|---|---|
| Incorporar el valor monetario de la carga al total | Interruptor "Incluir valor monetario de la carga" + monto USD/CLP; el backend suma el valor una sola vez | `services/calculo_cotizacion.py`, E2E |
| Sin valor ⇒ 0 | Inactivo, vacío o 0 ⇒ 0 (backend) | `ControlExplicitoValorCargaTests` |
| No sumar cargos cuando es 0 | Total final = flete total | idem |
| Quitar "Fuente de tarifa" bajo el resultado | Retirada del resultado y del detalle del historial; el dato se conserva en la base y en la API | E2E (`fuenteTarifaVisible: false`) |

## Aviso "Formalidades exposición" (10-11-2026) — cumplimiento

| Requisito | Estado | Dónde se demuestra |
|---|---|---|
| Valor de la carga opcional, se digita si se conoce | ✅ | Interruptor "Incluir valor de la carga" + monto USD/CLP; vacío o desactivado = 0 |
| Contenedor 20' = 23 ton, 40' = máx. 25 ton (confirmado por el cliente) | ✅ | `TipoContenedor`; el bootstrap no las sobrescribe |
| No ingresar cantidad de contenedores; calcularla según el peso | ✅ | No existe ese campo; `ceil(peso / capacidad)` en el backend |
| Ingresar puerto de origen y destino, peso (ton y/o kg) y valor de la carga | ✅ | Formulario del cotizador |
| Agregar 2 puertos requeridos por el cliente | ⚠️ Función lista; **faltan los datos** | Administración → "Puertos, rutas y tarifas" → NUEVA RUTA. Los puertos se cargan en minutos cuando el cliente confirme nombre, tarifas y tránsito |
| Quitar la fuente de las tarifas (el admin actualiza manualmente) | ✅ | Sin "Fuente" en cotizador, historial ni administración; edición manual de tarifas con bitácora |

## Relación con la rúbrica

| Criterio | Aporte de esta versión | Evidencia |
|---|---|---|
| 3.1.1.1 Interfaces vs negocio | Desglose completo: contenedor, cantidad, tarifa, flete, valor de carga, total USD, CLP, dólar (fecha, estado, antigüedad), tránsito y contingencia | capturas E2E, `App.jsx` |
| 3.1.1.2 Estética y función | Interruptor accesible, tarjetas consistentes con la identidad CINTAC, diseño responsive | capturas escritorio/móvil |
| 3.1.2.3 Estructura de BD | 2 migraciones aditivas, 4 constraints nuevas, bitácora con FK SET_NULL | `ARQUITECTURA_Y_DATOS.md` |
| 3.1.2.4 Normalización y optimización | Maestros en 3FN; historial desnormalizado justificado; EXPLAIN con 60.000 filas; índice evaluado y descartado con evidencia | idem §4 |
| 3.1.3.5 Seguridad avanzada | Bloqueo por cuenta, revocación de tokens, CSP, CORS exacto, anti-escalada, CSV injection, errores sin filtrar detalles, dependencias parchadas | `SEGURIDAD.md` |
| 3.1.3.6 Colaboración y documentación | Commits atómicos y descriptivos en rama; documentación por área | `git log`, `docs/` |
| 3.1.4.7 Entorno reproducible | `.env.example` corregido, bootstrap idempotente, CI con las mismas validaciones locales | `DESPLIEGUE.md` |
| 3.1.4.8 Documentación de implementación | Variables, publicación y rollback probados | `DESPLIEGUE.md` |
| 3.1.5.9 Cobertura del plan | 296 pruebas, 91 % de cobertura de ramas | `PRUEBAS_Y_RESULTADOS.md` |
| 3.1.5.10 Ejecución del protocolo | Comandos y resultados reales registrados | idem |
| 3.1.5.11 Validación de resultados | E2E con cálculo manual verificado | idem |
| 3.1.6.12 Esperado vs obtenido | Tabla de casos clave | idem |
| 3.1.6.13 Recomendaciones | Ver abajo | — |
| 3.1.6.14 Defensa | Este documento | — |
| 3.1.6.15 Informe final | `docs/` completo | — |

## Preguntas probables y respuesta corta

- **¿Por qué el valor de carga no se multiplica por contenedor?** Es el valor de la mercadería
  de la operación, no un costo por unidad de transporte; se suma una sola vez.
- **¿Por qué en CLP no se convierte dos veces?** El total CLP suma el monto CLP exacto
  ingresado; solo el total USD usa la conversión (una división, redondeo a centavos).
- **¿Qué pasa si cambia el dólar mañana?** El historial muestra la instantánea guardada al
  cotizar; nunca recalcula con valores actuales.
- **¿Qué pasa si se importa un Excel erróneo?** La vista previa muestra los cambios antes de
  confirmar; la importación es atómica y queda un respaldo restaurable por un administrador.
- **¿Qué pasa en un redeploy de Render?** El bootstrap no toca tarifas, capacidades ni
  contraseñas; está cubierto por pruebas.
- **¿Por qué GitHub Actions no está en verde?** Bloqueo de facturación de la cuenta; las mismas
  validaciones se ejecutaron localmente con resultados registrados.

## Recomendaciones técnicas

1. Respaldos automáticos de PostgreSQL (plan pagado de Render o `pg_dump` programado).
2. Redis como caché compartida para límites de login con varios workers.
3. Índice trigram (`pg_trgm`) si el historial supera las decenas de miles de filas y se usan
   mucho los filtros por texto.
4. Pruebas E2E automatizadas en CI (Playwright) cuando Actions esté disponible.
5. Token en cookie HttpOnly a mediano plazo.

## Pendientes que requieren decisión del equipo

- Autorizar la fusión a `main`, la sincronización del Blueprint y el borrado de
  `CORS_ALLOWED_ORIGIN_REGEXES` en Render.
- Restauración limitada a ADMINISTRADOR (el ENCARGADO puede ver la bitácora). Confirmar si
  el negocio prefiere otra regla.
