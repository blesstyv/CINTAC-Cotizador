import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import "./HistorialCotizaciones.css";


const FILTROS_INICIALES = {
  usuario_id: "",
  origen: "",
  destino: "",
  contenedor: "",
  desde: "",
  hasta: "",
};


function formatearUSD(valor) {
  if (
    valor === null ||
    valor === undefined ||
    valor === ""
  ) {
    return "—";
  }

  return new Intl.NumberFormat(
    "es-CL",
    {
      maximumFractionDigits: 0,
    }
  ).format(Number(valor));
}


function formatearCLP(valor) {
  if (
    valor === null ||
    valor === undefined ||
    valor === ""
  ) {
    return "—";
  }

  return new Intl.NumberFormat(
    "es-CL",
    {
      maximumFractionDigits: 0,
    }
  ).format(Number(valor));
}


// Monto USD con centavos sólo cuando existen
// (por ejemplo, un total que incluye valor de carga).
function formatearMontoUSD(valor) {
  if (
    valor === null ||
    valor === undefined ||
    valor === ""
  ) {
    return "—";
  }

  const numero =
    Number(valor);

  const decimales =
    Math.round(numero * 100) % 100 !== 0
      ? 2
      : 0;

  return new Intl.NumberFormat(
    "es-CL",
    {
      minimumFractionDigits:
        decimales,

      maximumFractionDigits:
        decimales,
    }
  ).format(numero);
}


function tieneValorCarga(cotizacion) {
  return (
    Number(
      cotizacion?.valorCarga ?? 0
    ) > 0
  );
}


function formatearNumero(
  valor,
  decimales = 3
) {
  if (
    valor === null ||
    valor === undefined ||
    valor === ""
  ) {
    return "—";
  }

  return new Intl.NumberFormat(
    "es-CL",
    {
      maximumFractionDigits:
        decimales,
    }
  ).format(Number(valor));
}


function formatearFechaHora(valor) {
  if (!valor) {
    return "—";
  }

  const fecha =
    new Date(valor);

  if (
    Number.isNaN(
      fecha.getTime()
    )
  ) {
    return valor;
  }

  return new Intl.DateTimeFormat(
    "es-CL",
    {
      dateStyle: "short",
      timeStyle: "short",
    }
  ).format(fecha);
}


function formatearFecha(valor) {
  if (!valor) {
    return "—";
  }

  const partes =
    valor.split("-");

  if (
    partes.length !== 3
  ) {
    return valor;
  }

  return (
    `${partes[2]}-` +
    `${partes[1]}-` +
    `${partes[0]}`
  );
}


function obtenerMensajeError(
  datos,
  predeterminado
) {
  if (
    datos?.detail
  ) {
    return String(
      datos.detail
    );
  }

  return predeterminado;
}


function escaparCeldaCsv(valor) {
  const texto = String(valor ?? "");
  const seguro = /^\s*[=+@-]/.test(texto)
    ? "'" + texto
    : texto;

  return '"' + seguro.replace(/"/g, '""') + '"';
}


function HistorialCotizaciones({
  apiUrl,
  usuario,
  peticionAutenticada,
  onVolver,
  onCerrarSesion,
}) {
  const [
    cotizaciones,
    setCotizaciones,
  ] = useState([]);

  const [
    total,
    setTotal,
  ] = useState(0);

  const [
    puedeVerTodas,
    setPuedeVerTodas,
  ] = useState(false);

  const [
    cargando,
    setCargando,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");

  const [
    filtros,
    setFiltros,
  ] = useState(
    FILTROS_INICIALES
  );

  const [
    usuariosDisponibles,
    setUsuariosDisponibles,
  ] = useState([]);

  const [
    detalle,
    setDetalle,
  ] = useState(null);

  const [
    cargandoDetalle,
    setCargandoDetalle,
  ] = useState(false);

  const consultaEnCursoRef =
    useRef(false);

  const detalleEnCursoRef =
    useRef(false);


  const exportarHistorialCsv = () => {
    if (cargando || cotizaciones.length === 0) {
      return;
    }

    const encabezado = [
      "ID",
      "Fecha",
      "Usuario",
      "Origen",
      "Destino",
      "Peso (TN)",
      "Contenedor",
      "Cantidad",
      "Total minimo USD",
      "Total maximo USD",
      "Total minimo CLP",
      "Total maximo CLP",
      "Transito minimo (dias)",
      "Transito maximo (dias)",
    ];

    const filas = cotizaciones.map((item) => [
      item.id,
      item.fecha,
      item.usuario?.username || "",
      item.origen,
      item.destino,
      item.pesoTN,
      item.tipoContenedor,
      item.cantidad,
      item.totalMin,
      item.totalMax,
      item.totalMinCLP,
      item.totalMaxCLP,
      item.transitoMin,
      item.transitoMax,
    ]);

    const contenido = "\uFEFF" + [
      encabezado,
      ...filas,
    ].map((fila) =>
      fila.map(escaparCeldaCsv).join(";")
    ).join("\r\n");

    const archivo = new Blob([contenido], {
      type: "text/csv;charset=utf-8;",
    });
    const direccion = URL.createObjectURL(archivo);
    const enlace = document.createElement("a");
    enlace.href = direccion;
    enlace.download = "cintac-historial.csv";
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    window.setTimeout(
      () => URL.revokeObjectURL(direccion),
      1000
    );
  };


  const rolVisible =
    useMemo(
      () => {
        if (
          usuario?.rol ===
          "ADMINISTRADOR"
        ) {
          return "ADMINISTRADOR";
        }

        if (
          usuario?.rol ===
          "ENCARGADO"
        ) {
          return "ENCARGADO";
        }

        return "USUARIO";
      },
      [
        usuario,
      ]
    );


  const actualizarFiltro =
    (
      campo,
      valor
    ) => {
      setFiltros(
        (actuales) => ({
          ...actuales,
          [campo]: valor,
        })
      );

      setError("");
    };


  const construirParametros =
    useCallback(
      (filtrosActuales) => {
        const parametros =
          new URLSearchParams();

        Object.entries(
          filtrosActuales
        ).forEach(
          ([
            clave,
            valor,
          ]) => {
            if (
              valor !== null &&
              valor !== undefined &&
              String(valor)
                .trim() !== ""
            ) {
              parametros.set(
                clave,
                String(valor).trim()
              );
            }
          }
        );

        return parametros;
      },
      []
    );


  const cargarHistorial =
    useCallback(
      async (
        filtrosActuales =
          FILTROS_INICIALES,
        conservarUsuarios = true
      ) => {
        if (
          consultaEnCursoRef.current
        ) {
          return;
        }

        consultaEnCursoRef.current =
          true;

        setCargando(true);
        setError("");

        try {
          const parametros =
            construirParametros(
              filtrosActuales
            );

          const query =
            parametros.toString();

          const url = query
            ? (
              `${apiUrl}/historial/?${query}`
            )
            : (
              `${apiUrl}/historial/`
            );

          const respuesta =
            await peticionAutenticada(
              url
            );

          const datos =
            await respuesta.json();

          if (!respuesta.ok) {
            throw new Error(
              obtenerMensajeError(
                datos,
                "No fue posible consultar el historial."
              )
            );
          }

          const registros =
            datos.cotizaciones ||
            [];

          setCotizaciones(
            registros
          );

          setTotal(
            datos.total || 0
          );

          setPuedeVerTodas(
            Boolean(
              datos.puedeVerTodas
            )
          );

          setUsuariosDisponibles(
            (actuales) => {
              if (
                conservarUsuarios &&
                actuales.length > 0
              ) {
                return actuales;
              }

              const mapa =
                new Map();

              registros.forEach(
                (cotizacion) => {
                  const usuarioRegistro =
                    cotizacion.usuario;

                  if (
                    usuarioRegistro?.id
                  ) {
                    mapa.set(
                      usuarioRegistro.id,
                      usuarioRegistro
                    );
                  }
                }
              );

              return [
                ...mapa.values(),
              ].sort(
                (
                  primero,
                  segundo
                ) =>
                  (
                    primero.nombre ||
                    primero.username
                  ).localeCompare(
                    segundo.nombre ||
                    segundo.username,
                    "es"
                  )
              );
            }
          );

        } catch (
          errorConsulta
        ) {
          setError(
            errorConsulta.message ||
            "No fue posible consultar el historial."
          );

        } finally {
          consultaEnCursoRef.current =
            false;

          setCargando(false);
        }
      },
      [
        apiUrl,
        peticionAutenticada,
        construirParametros,
      ]
    );


  useEffect(
    () => {
      const temporizador =
        window.setTimeout(
          () => {
            void cargarHistorial(
              FILTROS_INICIALES,
              false
            );
          },
          0
        );

      return () => {
        window.clearTimeout(
          temporizador
        );
      };
    },
    [
      cargarHistorial,
    ]
  );


  const aplicarFiltros =
    (event) => {
      event.preventDefault();

      setDetalle(null);

      void cargarHistorial(
        filtros,
        true
      );
    };


  const limpiarFiltros =
    () => {
      setFiltros(
        FILTROS_INICIALES
      );

      setDetalle(null);

      void cargarHistorial(
        FILTROS_INICIALES,
        false
      );
    };


  const verDetalle =
    async (
      cotizacionId
    ) => {
      if (
        detalleEnCursoRef.current
      ) {
        return;
      }

      detalleEnCursoRef.current =
        true;

      setCargandoDetalle(true);
      setError("");

      try {
        const respuesta =
          await peticionAutenticada(
            `${apiUrl}/historial/${cotizacionId}/`
          );

        const datos =
          await respuesta.json();

        if (!respuesta.ok) {
          throw new Error(
            obtenerMensajeError(
              datos,
              "No fue posible consultar el detalle."
            )
          );
        }

        setDetalle(
          datos.cotizacion
        );

        window.setTimeout(
          () => {
            document
              .getElementById(
                "detalle-historial"
              )
              ?.scrollIntoView({
                behavior: "smooth",
                block: "start",
              });
          },
          50
        );

      } catch (
        errorDetalle
      ) {
        setError(
          errorDetalle.message ||
          "No fue posible consultar el detalle."
        );

      } finally {
        detalleEnCursoRef.current =
          false;

        setCargandoDetalle(false);
      }
    };


  return (
    <div className="history-page">
      <header className="site-header">
        <div className="header-inner">
          <div className="cintac-brand">
            <div className="cintac-wordmark">
              CINTAC

              <span className="registered">
                ®
              </span>
            </div>
          </div>


          <div className="header-user">
            <div className="user-info">
              <span>
                {rolVisible}
              </span>

              <strong>
                {
                  usuario?.nombre ||
                  usuario?.username
                }
              </strong>
            </div>

            <button
              type="button"
              className="history-header-button"
              onClick={
                onVolver
              }
            >
              VOLVER AL COTIZADOR
            </button>

            <button
              type="button"
              className="logout-button"
              onClick={
                onCerrarSesion
              }
            >
              CERRAR SESIÓN
            </button>
          </div>
        </div>
      </header>


      <section className="history-hero">
        <div className="history-hero-inner">
          <span>
            COMERCIO EXTERIOR
          </span>

          <h1>
            Historial de{" "}
            <strong>
              cotizaciones
            </strong>
          </h1>

          <p>
            Consulta las operaciones
            generadas anteriormente
            en el cotizador logístico.
          </p>
        </div>
      </section>


      <main className="history-main">
        <section className="history-section">
          <div className="history-heading">
            <div>
              <span className="history-eyebrow">
                REGISTROS
              </span>

              <h2>
                {
                  puedeVerTodas
                    ? "Cotizaciones registradas"
                    : "Mis cotizaciones"
                }
              </h2>

              <p>
                {
                  puedeVerTodas
                    ? (
                      "Revise las cotizaciones generadas por los usuarios autorizados."
                    )
                    : (
                      "Revise las cotizaciones generadas desde su cuenta."
                    )
                }
              </p>
            </div>


            <div className="history-counter">
              <strong>
                {total}
              </strong>

              <span>
                REGISTROS
              </span>
            </div>
          </div>


          <form
            className="history-filters"
            onSubmit={
              aplicarFiltros
            }
          >
            {
              puedeVerTodas &&
              (
                <div className="history-filter-field">
                  <label>
                    Usuario
                  </label>

                  <select
                    value={
                      filtros.usuario_id
                    }
                    onChange={(event) => {
                      actualizarFiltro(
                        "usuario_id",
                        event.target.value
                      );
                    }}
                  >
                    <option value="">
                      Todos
                    </option>

                    {
                      usuariosDisponibles.map(
                        (
                          usuarioFiltro
                        ) => (
                          <option
                            key={
                              usuarioFiltro.id
                            }
                            value={
                              usuarioFiltro.id
                            }
                          >
                            {
                              usuarioFiltro.nombre ||
                              usuarioFiltro.username
                            }
                          </option>
                        )
                      )
                    }
                  </select>
                </div>
              )
            }


            <div className="history-filter-field">
              <label>
                Origen
              </label>

              <input
                type="text"
                value={
                  filtros.origen
                }
                onChange={(event) => {
                  actualizarFiltro(
                    "origen",
                    event.target.value
                  );
                }}
                placeholder="Ej: Shanghai"
              />
            </div>


            <div className="history-filter-field">
              <label>
                Destino
              </label>

              <input
                type="text"
                value={
                  filtros.destino
                }
                onChange={(event) => {
                  actualizarFiltro(
                    "destino",
                    event.target.value
                  );
                }}
                placeholder="Ej: Valparaiso"
              />
            </div>


            <div className="history-filter-field">
              <label>
                Contenedor
              </label>

              <select
                value={
                  filtros.contenedor
                }
                onChange={(event) => {
                  actualizarFiltro(
                    "contenedor",
                    event.target.value
                  );
                }}
              >
                <option value="">
                  Todos
                </option>

                <option value="20">
                  20&apos;
                </option>

                <option value="40">
                  40&apos;
                </option>
              </select>
            </div>


            <div className="history-filter-field">
              <label>
                Desde
              </label>

              <input
                type="date"
                value={
                  filtros.desde
                }
                onChange={(event) => {
                  actualizarFiltro(
                    "desde",
                    event.target.value
                  );
                }}
              />
            </div>


            <div className="history-filter-field">
              <label>
                Hasta
              </label>

              <input
                type="date"
                value={
                  filtros.hasta
                }
                onChange={(event) => {
                  actualizarFiltro(
                    "hasta",
                    event.target.value
                  );
                }}
              />
            </div>


            <div className="history-filter-actions">
              <button
                type="submit"
                className="history-primary-button"
                disabled={
                  cargando
                }
              >
                {
                  cargando
                    ? "BUSCANDO..."
                    : "BUSCAR"
                }
              </button>

              <button
                type="button"
                className="history-secondary-button"
                onClick={
                  limpiarFiltros
                }
                disabled={
                  cargando
                }
              >
                LIMPIAR
              </button>

              <button
                type="button"
                className="history-secondary-button"
                onClick={exportarHistorialCsv}
                disabled={
                  cargando ||
                  cotizaciones.length === 0
                }
                title="Exporta únicamente los registros cargados según los filtros y permisos de esta cuenta"
              >
                EXPORTAR CSV
              </button>
            </div>
          </form>


          {error && (
            <div className="history-alert">
              <span>
                !
              </span>

              <p>
                {error}
              </p>
            </div>
          )}


          <div className="history-table-container">
            <table className="history-table">
              <thead>
                <tr>
                  <th>
                    N°
                  </th>

                  <th>
                    Fecha
                  </th>

                  {
                    puedeVerTodas &&
                    (
                      <th>
                        Usuario
                      </th>
                    )
                  }

                  <th>
                    Ruta
                  </th>

                  <th>
                    Carga
                  </th>

                  <th>
                    Contenedor
                  </th>

                  <th>
                    Total USD
                  </th>

                  <th>
                    Tránsito
                  </th>

                  <th>
                    Acción
                  </th>
                </tr>
              </thead>


              <tbody>
                {
                  cargando
                    ? (
                      <tr>
                        <td
                          colSpan={
                            puedeVerTodas
                              ? 9
                              : 8
                          }
                          className="history-empty"
                        >
                          Cargando historial...
                        </td>
                      </tr>
                    )
                    : (
                      cotizaciones.length ===
                      0
                        ? (
                          <tr>
                            <td
                              colSpan={
                                puedeVerTodas
                                  ? 9
                                  : 8
                              }
                              className="history-empty"
                            >
                              No existen cotizaciones
                              para los filtros seleccionados.
                            </td>
                          </tr>
                        )
                        : (
                          cotizaciones.map(
                            (
                              cotizacion
                            ) => (
                              <tr
                                key={
                                  cotizacion.id
                                }
                              >
                                <td>
                                  <strong>
                                    #
                                    {
                                      cotizacion.id
                                    }
                                  </strong>
                                </td>

                                <td>
                                  {
                                    formatearFechaHora(
                                      cotizacion.fecha
                                    )
                                  }
                                </td>

                                {
                                  puedeVerTodas &&
                                  (
                                    <td>
                                      {
                                        cotizacion
                                          .usuario
                                          ?.nombre ||
                                        cotizacion
                                          .usuario
                                          ?.username
                                      }
                                    </td>
                                  )
                                }

                                <td>
                                  <strong>
                                    {
                                      cotizacion.origen
                                    }
                                  </strong>

                                  <span className="history-route-arrow">
                                    →
                                  </span>

                                  <strong>
                                    {
                                      cotizacion.destino
                                    }
                                  </strong>
                                </td>

                                <td>
                                  {
                                    formatearNumero(
                                      cotizacion.pesoTN
                                    )
                                  }{" "}
                                  TN
                                </td>

                                <td>
                                  {
                                    cotizacion.cantidad
                                  }{" "}
                                  ×{" "}
                                  {
                                    cotizacion
                                      .tipoContenedor
                                  }
                                  &apos;
                                </td>

                                <td>
                                  US${" "}
                                  {
                                    formatearMontoUSD(
                                      cotizacion.totalFinalMin ??
                                      cotizacion.totalMin
                                    )
                                  }

                                  {" - "}

                                  US${" "}
                                  {
                                    formatearMontoUSD(
                                      cotizacion.totalFinalMax ??
                                      cotizacion.totalMax
                                    )
                                  }
                                </td>

                                <td>
                                  {
                                    cotizacion
                                      .transitoMin !==
                                      null &&
                                    cotizacion
                                      .transitoMax !==
                                      null
                                      ? (
                                        <>
                                          {
                                            cotizacion
                                              .transitoMin
                                          }

                                          {" - "}

                                          {
                                            cotizacion
                                              .transitoMax
                                          }{" "}
                                          días
                                        </>
                                      )
                                      : "—"
                                  }
                                </td>

                                <td>
                                  <button
                                    type="button"
                                    className="history-detail-button"
                                    onClick={() => {
                                      void verDetalle(
                                        cotizacion.id
                                      );
                                    }}
                                    disabled={
                                      cargandoDetalle
                                    }
                                  >
                                    VER DETALLE
                                  </button>
                                </td>
                              </tr>
                            )
                          )
                        )
                    )
                }
              </tbody>
            </table>
          </div>


          {
            total > 500 &&
            (
              <p className="history-limit-note">
                Se muestran los 500
                registros más recientes
                que coinciden con los
                filtros seleccionados.
              </p>
            )
          }
        </section>


        {
          detalle &&
          (
            <section
              className="history-detail"
              id="detalle-historial"
            >
              <div className="history-detail-heading">
                <div>
                  <span className="history-eyebrow">
                    DETALLE
                  </span>

                  <h2>
                    Cotización #
                    {
                      detalle.id
                    }
                  </h2>

                  <p>
                    Generada el{" "}
                    {
                      formatearFechaHora(
                        detalle.fecha
                      )
                    }
                  </p>
                </div>

                <button
                  type="button"
                  className="history-close-button"
                  onClick={() => {
                    setDetalle(null);
                  }}
                  aria-label="Cerrar detalle"
                >
                  ×
                </button>
              </div>


              <div className="history-detail-grid">
                <div className="history-detail-block">
                  <span>
                    USUARIO
                  </span>

                  <strong>
                    {
                      detalle
                        .usuario
                        ?.nombre ||
                      detalle
                        .usuario
                        ?.username
                    }
                  </strong>

                  <small>
                    {
                      detalle
                        .usuario
                        ?.username
                    }
                  </small>
                </div>


                <div className="history-detail-block">
                  <span>
                    RUTA
                  </span>

                  <strong>
                    {
                      detalle.origen
                    }

                    {" → "}

                    {
                      detalle.destino
                    }
                  </strong>

                  <small>
                    {
                      detalle.paisOrigen
                    }

                    {" · "}

                    {
                      detalle.tipoRuta
                    }
                  </small>
                </div>


                <div className="history-detail-block">
                  <span>
                    CARGA
                  </span>

                  <strong>
                    {
                      formatearNumero(
                        detalle.pesoTN
                      )
                    }{" "}
                    TN
                  </strong>

                  <small>
                    {
                      formatearNumero(
                        detalle.pesoKg
                      )
                    }{" "}
                    kg
                  </small>
                </div>


                <div className="history-detail-block">
                  <span>
                    CONTENEDOR
                  </span>

                  <strong>
                    {
                      detalle.cantidad
                    }{" "}
                    ×{" "}
                    {
                      detalle
                        .tipoContenedor
                    }
                    &apos;
                  </strong>

                  <small>
                    Capacidad considerada:{" "}
                    {
                      formatearNumero(
                        detalle.capacidadTN,
                        2
                      )
                    }{" "}
                    TN
                  </small>
                </div>


                <div className="history-detail-block">
                  <span>
                    TARIFA POR CONTENEDOR
                  </span>

                  <strong>
                    US${" "}
                    {
                      formatearUSD(
                        detalle.tarifaMin
                      )
                    }

                    {" - "}

                    US${" "}
                    {
                      formatearUSD(
                        detalle.tarifaMax
                      )
                    }
                  </strong>

                  <small>
                    {
                      detalle.fuente ||
                      "Sin fuente informada"
                    }
                  </small>
                </div>


                {
                  tieneValorCarga(detalle) && (
                    <div className="history-detail-block">
                      <span>
                        VALOR DE CARGA
                      </span>

                      <strong>
                        {
                          detalle.monedaValorCarga ===
                          "CLP"
                            ? `$${formatearNumero(detalle.valorCargaIngresado, 2)} CLP`
                            : `US$ ${formatearMontoUSD(detalle.valorCarga)}`
                        }
                      </strong>

                      <small>
                        {
                          detalle.monedaValorCarga ===
                          "CLP"
                            ? `Equivale a US$ ${formatearMontoUSD(detalle.valorCarga)}`
                            : "Ingresado en USD"
                        }
                      </small>
                    </div>
                  )
                }


                <div className="history-detail-block emphasized">
                  <span>
                    TOTAL ESTIMADO USD
                  </span>

                  <strong>
                    US${" "}
                    {
                      formatearMontoUSD(
                        detalle.totalFinalMin ??
                        detalle.totalMin
                      )
                    }

                    {" - "}

                    US${" "}
                    {
                      formatearMontoUSD(
                        detalle.totalFinalMax ??
                        detalle.totalMax
                      )
                    }
                  </strong>

                  <small>
                    {
                      tieneValorCarga(detalle)
                        ? `Flete US$ ${formatearUSD(detalle.totalMin)} - US$ ${formatearUSD(detalle.totalMax)} + valor de carga`
                        : detalle.esSugerida
                          ? (
                            "Opción sugerida por el cotizador"
                          )
                          : (
                            "Opción seleccionada por el usuario"
                          )
                    }
                  </small>
                </div>


                <div className="history-detail-block">
                  <span>
                    TRÁNSITO
                  </span>

                  <strong>
                    {
                      detalle.transitoMin !==
                        null &&
                      detalle.transitoMax !==
                        null
                        ? (
                          `${detalle.transitoMin} - ${detalle.transitoMax} días`
                        )
                        : "Sin información"
                    }
                  </strong>

                  <small>
                    Contingencia:{" "}
                    {
                      detalle.contingencia
                    }{" "}
                    días
                  </small>
                </div>


                <div className="history-detail-block">
                  <span>
                    CONVERSIÓN CLP
                  </span>

                  {
                    detalle
                      .conversionDisponible
                      ? (
                        <>
                          <strong>
                            $
                            {
                              formatearCLP(
                                detalle.totalFinalMinCLP ??
                                detalle.totalMinCLP
                              )
                            }

                            {" - $"}

                            {
                              formatearCLP(
                                detalle.totalFinalMaxCLP ??
                                detalle.totalMaxCLP
                              )
                            }
                          </strong>

                          <small>
                            Tipo de cambio: $
                            {
                              formatearNumero(
                                detalle.tipoCambio,
                                2
                              )
                            }{" "}
                            ·{" "}
                            {
                              formatearFecha(
                                detalle.fechaTipoCambio
                              )
                            }
                          </small>
                        </>
                      )
                      : (
                        <>
                          <strong>
                            No disponible
                          </strong>

                          <small>
                            La cotización se
                            registró únicamente
                            en USD.
                          </small>
                        </>
                      )
                  }
                </div>
              </div>
            </section>
          )
        }
      </main>


      <footer className="footer">
        <div className="footer-inner">
          <div className="footer-logo">
            CINTAC
          </div>

          <div className="footer-copy">
            Cotizador Logístico ·
            Historial de operaciones
          </div>
        </div>
      </footer>
    </div>
  );
}


export default HistorialCotizaciones;