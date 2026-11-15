# Requisitos finales del Product Owner — exposición 17-11-2026

## Fuente

Retroalimentación entregada por la profesora y tabla del Product Owner aportada por el equipo. Este documento mantiene las especificaciones recibidas, incluso cuando contienen una contradicción que debe aclararse.

## Funcionalidades solicitadas

- La herramienta es para uso **interno**; evitar integrarla a una página pública corporativa como un recurso abierto.
- Valor monetario de la carga opcional. Si se conoce, se suma **una sola vez** al total del flete; si no se conoce, se considera 0.
- Capacidad máxima: contenedor de **20 pies = 23 toneladas**; contenedor de **40 pies = 25 toneladas**.
- La cantidad de contenedores **se calcula a partir del peso**, no se introduce manualmente.
- Inputs: puerto de origen, puerto de destino, peso en kg o toneladas y valor de carga opcional.
- La fuente de tarifas no debe mostrarse debajo del cálculo. La información de tarifas se actualiza manualmente desde administración.
- El flete internacional se trata como flete sin IVA adicional en la estimación; no mezclar con posibles impuestos/cargos diferentes que no estén especificados.
- Agregar dos **rutas** nuevas y un **puerto** nuevo a la base existente, conforme a la tabla de cliente.

## Datos exactos recibidos

| Origen | País origen | Destino | País destino | Tipo de ruta | 20' min (USD) | 20' max (USD) | 40' min (USD) | 40' max (USD) | Tránsito min | Tránsito max |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| San Antonio | Chile | Callao | Perú | Directo | 900 | 900 | 970 | 970 | **5** | **3** |
| Valparaiso | Chile | Callao | Perú | Directo | 900 | 900 | 970 | 970 | **5** | **3** |

**Bloqueo de integridad de datos:** en el original se indica tránsito mínimo de 5 días y máximo de 3 días para ambas rutas. Un rango mínimo > máximo es matemáticamente inválido. El software debe rechazarlo y no se debe corregir silenciosamente. Solicitar confirmación explícita al Product Owner: ¿corresponde 3–5 días o existe otro dato correcto?

Hasta confirmar la duración, **no cargar rutas incompletas ni inventar tránsitos en PostgreSQL de producción**.

## Soporte implementado

- PostgreSQL ya contiene los tipos de contenedor 20' y 40' con capacidades 23 y 25 toneladas.
- El backend cuenta con API administrativa para crear rutas internacionales mediante campo `pais_destino`, validar tarifa y días, registrar operación y respaldar estado anterior.
- Antes de esta revisión, el frontend administrativo suponía Chile como país de destino. La rama `eva3-client-callao-17nov` agrega dicho campo visible y obligatorio, sin alterar rutas existentes.
- Se añadieron tests para dos rutas que comparten el puerto de Callao/Perú y para el rechazo del rango invertido original. Los números 2–4 usados en la primera prueba son **datos ficticios de laboratorio**, NO una corrección de la tabla del cliente.

## Verificación y publicación pendientes

1. Confirmar el rango de tránsito correcto con el Product Owner.
2. Validar build/lint de React y tests backend contra PostgreSQL de pruebas.
3. Fusionar únicamente una rama validada y publicar frontend/backend alineados.
4. Crear las dos rutas desde el módulo administrativo, con los días confirmados; verificar 18 rutas y 36 tarifas en la base final.
5. Cotizar cargas exactamente de 23, 24, 25, 26, 46 y 50 toneladas para asegurar el redondeo de contenedores según cada capacidad.
6. Verificar que el historial conserva importes, fecha, moneda y cantidad de contenedores y que la UI no solicite cantidad manual.
7. Conservar evidencias reproducibles de resultados esperados/obtenidos.

## Política de publicación

No fusionar ni desplegar código sin pruebas apropiadas. No transmitir contraseñas ni tokens por conversaciones. La base gratuita de Render tiene fecha de expiración configurada para el 21-11-2026: planificar migración/respaldo si la herramienta debe seguir operativa después de la evaluación.
