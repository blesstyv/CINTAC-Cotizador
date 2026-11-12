# Arquitectura y modelo de datos — CINTAC-Cotizador

## 1. Arquitectura

```text
Navegador (React 19 + Vite 8)          Render Static Site  (CSP, HSTS, X-Frame-Options)
        │ HTTPS · JSON · Authorization: Token <clave>
        ▼
Django 6.1 + DRF 3.18 (Gunicorn)       Render Web Service  (CSP, HSTS, CORS exacto)
  ├─ views.py               HTTP de cotización (delgadas)
  ├─ historial_views.py     listado, detalle, exportación CSV
  ├─ gestion_views.py       Excel, bitácora, restauración
  ├─ auth_views.py          login/logout/sesión + bloqueo por cuenta
  ├─ usuario_views.py       administración de usuarios
  ├─ permissions.py         autorización por rol (siempre en backend)
  ├─ excepciones.py         errores uniformes, sin filtrar detalles
  └─ services/
       ├─ calculo_cotizacion.py   reglas financieras (fuente única)
       ├─ tipo_cambio.py          dólar en línea / caché / respaldo
       ├─ importador_datos.py     validación y aplicación del Excel
       └─ datos_maestros.py       instantáneas, comparación, restauración
        │
        ▼
PostgreSQL 16 (Render)   constraints CHECK/UNIQUE, FK PROTECT/CASCADE, índices
```

**Principio aplicado:** las vistas solo traducen HTTP; las reglas de negocio viven en
`services/` como funciones puras y probadas por separado. El backend es la autoridad
del resultado: el frontend nunca calcula totales que se guarden.

## 2. Reglas financieras (services/calculo_cotizacion.py)

| Regla | Implementación |
|---|---|
| Cantidad de contenedores | `ceil(peso_tn / capacidad_tn)` (sin cambios) |
| Flete total | `tarifa × cantidad` (mínimo y máximo, sin cambios) |
| Valor monetario de carga | Se suma **una sola vez**; inactivo, vacío o 0 ⇒ 0 |
| Total final | `flete total + valor de carga` (USD, 2 decimales, ROUND_HALF_UP) |
| Valor en CLP | `round(monto_clp / dólar_de_la_cotización, 2)` — una sola división |
| Total final en CLP | flete CLP + **monto CLP exacto** (sin ida y vuelta CLP→USD→CLP) |
| Historial | Lee la instantánea guardada; nunca usa tarifas ni dólares actuales |

## 3. Modelo de datos

| Modelo | Propósito | Integridad destacada |
|---|---|---|
| `PerfilUsuario` | Rol (USUARIO/ENCARGADO/ADMINISTRADOR) y autorización | OneToOne con `User`, índice `(rol, autorizado)` |
| `Puerto` | Puertos | UNIQUE `(nombre, pais)` |
| `TipoContenedor` | 20'/40' y capacidad | UNIQUE `codigo`, CHECK capacidad > 0 |
| `Ruta` | Origen → destino | FK PROTECT a puertos, UNIQUE par, CHECK origen ≠ destino |
| `Tarifa` | Mín./máx. por contenedor | UNIQUE `(ruta, contenedor)`, CHECK > 0 y máx ≥ mín |
| `TiempoTransito` | Días mín./máx. | OneToOne ruta, CHECK ≥ 1 y máx ≥ mín |
| `TipoCambio` | USD/CLP con fecha y fuente | UNIQUE `(monedas, fecha)`, CHECK > 0 |
| `Cotizacion` | **Instantánea** de cada cotización | 12 CHECK (ver abajo), FK PROTECT a usuario, 3 índices |
| `OperacionDatosMaestros` | Bitácora + respaldo de datos maestros | FK SET_NULL a usuario (conserva `usuario_username`), CHECK tipo y origen de restauración |

### Por qué `Cotizacion` repite datos (desnormalización intencional)

`Cotizacion` guarda origen, destino, tarifas, capacidad, dólar y totales **como texto y
números**, no como FK a `Ruta`/`Tarifa`. Es una decisión deliberada: una cotización es un
documento emitido; si mañana cambia la tarifa o se elimina una ruta, el historial debe
seguir mostrando exactamente lo que se informó. Las tablas maestras sí están normalizadas
(3FN): cada tarifa depende solo de `(ruta, contenedor)`.

### Constraints nuevas (migración 0012)

- `cot_total_final_min_ge_flete`, `cot_total_final_max_ge_flete`: el total final nunca es menor que el flete.
- `cot_valor_carga_sin_monto_cero`: sin monto ingresado no puede existir cargo en USD.
- `cot_valor_carga_usd_coherente`: en USD, el equivalente es igual al monto ingresado.

La migración 0012 agrega `total_final_min/max` y `total_final_min_clp/max_clp` y los
completa para registros existentes **con los datos del mismo registro** (verificado con
una base creada con el código de `main`: los totales del historial antes y después de
migrar son idénticos).

### Migración 0013

Crea `OperacionDatosMaestros`. No modifica tablas existentes.

## 4. Rendimiento (BD03)

Consultas revisadas: historial (`select_related("usuario")`), rutas (`select_related` +
`prefetch_related` de tarifas), usuarios (`select_related("perfil_cintac")`), admin de
Django (`list_select_related`), instantáneas (`prefetch_related("tarifas")`). No se
detectaron consultas N+1.

Medición con `EXPLAIN ANALYZE` sobre PostgreSQL 16 local con **60.000 cotizaciones**:

| Consulta | Plan | Tiempo |
|---|---|---|
| Historial completo (ENCARGADO, 500 filas) | Index Scan Backward `creada_en` | ~1 ms |
| Historial propio (USUARIO) | Index Scan `creada_en` + filtro | ~5 ms |
| Filtro por contenedor | Index Scan `creada_en` | ~0,6 ms |
| Filtro `origen ICONTAINS` | Seq Scan | ~24 ms |

Se probó un índice compuesto `(usuario_id, creada_en DESC, id DESC)`: el planificador
**no lo eligió** y el tiempo no mejoró, por lo que **no se agregó** (no se crean índices
sin evidencia). El filtro `ICONTAINS` requeriría un índice trigram (`pg_trgm`); con el
volumen esperado de CINTAC (miles de filas) 24 ms es aceptable y se deja como
recomendación.

## 5. Recuperación de datos (BD04)

| Concepto | Cómo se cubre |
|---|---|
| Rollback transaccional | Importación, restauración y bootstrap en `transaction.atomic`: un error revierte todo |
| Respaldo de información | Antes de importar o restaurar se guarda la instantánea completa de los datos maestros en `OperacionDatosMaestros.estado_previo` |
| Recuperación de datos anteriores | `POST /api/administracion/operaciones/<id>/restaurar/` (solo ADMINISTRADOR, `confirmar: true`); la restauración guarda a su vez el estado reemplazado ⇒ reversible |
| Respaldo completo de la base | Responsabilidad de Render PostgreSQL (ver recomendaciones: el plan gratuito no incluye PITR) |
