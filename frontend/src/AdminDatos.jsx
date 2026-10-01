import {
  useEffect,
  useState,
} from "react";

import "./AdminDatos.css";


function obtenerErrores(datos) {
  if (!datos) {
    return [
      "No fue posible completar la operación.",
    ];
  }

  if (
    Array.isArray(
      datos.errores
    )
  ) {
    return datos.errores;
  }

  if (datos.detail) {
    return [
      String(
        datos.detail
      ),
    ];
  }

  return [
    "No fue posible completar la operación.",
  ];
}


function AdminDatos({
  apiUrl,
  usuario,
  peticionAutenticada,
  onVolver,
  onCerrarSesion,
  onDatosActualizados,
  onPermisoRevocado,
}) {
  const [
    resumen,
    setResumen,
  ] = useState(null);

  const [
    cargandoResumen,
    setCargandoResumen,
  ] = useState(true);

  const [
    archivo,
    setArchivo,
  ] = useState(null);

  const [
    validando,
    setValidando,
  ] = useState(false);

  const [
    importando,
    setImportando,
  ] = useState(false);

  const [
    validacion,
    setValidacion,
  ] = useState(null);

  const [
    errores,
    setErrores,
  ] = useState([]);

  const [
    mensaje,
    setMensaje,
  ] = useState("");

  const [
    errorResumen,
    setErrorResumen,
  ] = useState("");


  /* ======================================
     COMPROBAR PERMISO
  ====================================== */

  const comprobarPermiso =
    (respuesta) => {
      if (
        respuesta.status === 403
      ) {
        if (
          onPermisoRevocado
        ) {
          void onPermisoRevocado();
        }

        return false;
      }

      return true;
    };


  /* ======================================
     CARGAR RESUMEN MANUALMENTE
  ====================================== */

  const cargarResumen =
    async () => {
      if (cargandoResumen) {
        return;
      }

      setCargandoResumen(
        true
      );

      setErrorResumen("");

      try {
        const respuesta =
          await peticionAutenticada(
            `${apiUrl}/administracion/resumen/`
          );

        if (
          !comprobarPermiso(
            respuesta
          )
        ) {
          return;
        }

        const datos =
          await respuesta.json();

        if (!respuesta.ok) {
          throw new Error(
            datos.detail ||
            "No fue posible consultar los datos maestros."
          );
        }

        setResumen(
          datos
        );
      } catch (error) {
        setErrorResumen(
          error.message
        );
      } finally {
        setCargandoResumen(
          false
        );
      }
    };


  /* ======================================
     CARGA INICIAL DEL RESUMEN
  ====================================== */

  useEffect(() => {
    let activo = true;

    const cargarResumenInicial =
      async () => {
        try {
          const respuesta =
            await peticionAutenticada(
              `${apiUrl}/administracion/resumen/`
            );

          if (
            respuesta.status === 403
          ) {
            if (
              onPermisoRevocado
            ) {
              void onPermisoRevocado();
            }

            return;
          }

          const datos =
            await respuesta.json();

          if (!respuesta.ok) {
            throw new Error(
              datos.detail ||
              "No fue posible consultar los datos maestros."
            );
          }

          if (activo) {
            setResumen(
              datos
            );

            setErrorResumen(
              ""
            );
          }
        } catch (error) {
          if (activo) {
            setErrorResumen(
              error.message
            );
          }
        } finally {
          if (activo) {
            setCargandoResumen(
              false
            );
          }
        }
      };

    void cargarResumenInicial();

    return () => {
      activo = false;
    };
  }, [
    apiUrl,
    peticionAutenticada,
    onPermisoRevocado,
  ]);


  /* ======================================
     SELECCIONAR ARCHIVO
  ====================================== */

  const seleccionarArchivo =
    (event) => {
      const seleccionado =
        event.target
          .files?.[0] ||
        null;

      setArchivo(
        seleccionado
      );

      setValidacion(null);
      setErrores([]);
      setMensaje("");
    };


  /* ======================================
     VALIDAR EXCEL
  ====================================== */

  const validarExcel =
    async () => {
      if (
        validando ||
        importando
      ) {
        return;
      }

      if (!archivo) {
        setErrores([
          "Seleccione un archivo Excel antes de continuar.",
        ]);

        return;
      }

      setValidando(
        true
      );

      setValidacion(null);
      setErrores([]);
      setMensaje("");

      const formulario =
        new FormData();

      formulario.append(
        "archivo",
        archivo
      );

      try {
        const respuesta =
          await peticionAutenticada(
            `${apiUrl}/administracion/validar-excel/`,
            {
              method: "POST",
              body: formulario,
            }
          );

        if (
          !comprobarPermiso(
            respuesta
          )
        ) {
          return;
        }

        const datos =
          await respuesta.json();

        if (!respuesta.ok) {
          setErrores(
            obtenerErrores(
              datos
            )
          );

          return;
        }

        setValidacion(
          datos
        );

        setMensaje(
          "El archivo superó todas las validaciones."
        );
      } catch (error) {
        setErrores([
          error.message,
        ]);
      } finally {
        setValidando(
          false
        );
      }
    };


  /* ======================================
     APLICAR IMPORTACIÓN
  ====================================== */

  const aplicarImportacion =
    async () => {
      if (
        validando ||
        importando
      ) {
        return;
      }

      if (
        !archivo ||
        !validacion?.valido
      ) {
        setErrores([
          "El archivo debe validarse correctamente antes de actualizar los datos.",
        ]);

        return;
      }

      const confirmado =
        window.confirm(
          "Se actualizarán los datos maestros utilizados por el cotizador. Antes de aplicar los cambios se generará un respaldo de la base de datos. ¿Desea continuar?"
        );

      if (!confirmado) {
        return;
      }

      setImportando(
        true
      );

      setErrores([]);
      setMensaje("");

      const formulario =
        new FormData();

      formulario.append(
        "archivo",
        archivo
      );

      try {
        const respuesta =
          await peticionAutenticada(
            `${apiUrl}/administracion/importar-excel/`,
            {
              method: "POST",
              body: formulario,
            }
          );

        if (
          !comprobarPermiso(
            respuesta
          )
        ) {
          return;
        }

        const datos =
          await respuesta.json();

        if (!respuesta.ok) {
          setErrores(
            obtenerErrores(
              datos
            )
          );

          return;
        }

        setMensaje(
          datos.detail ||
          "Los datos maestros fueron actualizados correctamente."
        );

        setValidacion(null);
        setArchivo(null);

        const inputArchivo =
          document.getElementById(
            "archivo-datos-cintac"
          );

        if (
          inputArchivo
        ) {
          inputArchivo.value =
            "";
        }

        setCargandoResumen(
          false
        );

        await cargarResumen();

        if (
          onDatosActualizados
        ) {
          onDatosActualizados();
        }
      } catch (error) {
        setErrores([
          error.message,
        ]);
      } finally {
        setImportando(
          false
        );
      }
    };


  /* ======================================
     INTERFAZ
  ====================================== */

  return (
    <div className="admin-page">
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
                USUARIO
              </span>

              <strong>
                {
                  usuario.nombre ||
                  usuario.username
                }
              </strong>
            </div>


            <button
              type="button"
              className="admin-header-button"
              onClick={
                onVolver
              }
              disabled={
                validando ||
                importando
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
              disabled={
                importando
              }
            >
              CERRAR SESIÓN
            </button>
          </div>
        </div>
      </header>


      <section className="admin-hero">
        <div className="admin-hero-inner">
          <span>
            COMERCIO EXTERIOR
          </span>

          <h1>
            Administración{" "}
            <strong>
              de datos
            </strong>
          </h1>

          <p>
            Gestión de la información
            utilizada por el cotizador
            logístico.
          </p>
        </div>
      </section>


      <main className="admin-main">
        <section className="admin-section">
          <div className="admin-section-heading">
            <div>
              <span className="admin-eyebrow">
                ESTADO ACTUAL
              </span>

              <h2>
                Datos maestros
              </h2>

              <p>
                Información disponible
                actualmente para generar
                cotizaciones.
              </p>
            </div>


            <button
              type="button"
              className="admin-refresh-button"
              onClick={
                cargarResumen
              }
              disabled={
                cargandoResumen ||
                validando ||
                importando
              }
            >
              {
                cargandoResumen
                  ? "ACTUALIZANDO..."
                  : "ACTUALIZAR"
              }
            </button>
          </div>


          {errorResumen && (
            <div className="admin-alert error">
              {errorResumen}
            </div>
          )}


          <div className="admin-summary-grid">
            <div className="admin-summary-card">
              <span>
                PUERTOS
              </span>

              <strong>
                {
                  resumen?.puertos ??
                  "—"
                }
              </strong>
            </div>


            <div className="admin-summary-card">
              <span>
                RUTAS
              </span>

              <strong>
                {
                  resumen?.rutas ??
                  "—"
                }
              </strong>
            </div>


            <div className="admin-summary-card">
              <span>
                TARIFAS
              </span>

              <strong>
                {
                  resumen?.tarifas ??
                  "—"
                }
              </strong>
            </div>


            <div className="admin-summary-card">
              <span>
                TIEMPOS DE TRÁNSITO
              </span>

              <strong>
                {
                  resumen
                    ?.tiemposTransito ??
                  "—"
                }
              </strong>
            </div>


            <div className="admin-summary-card">
              <span>
                TIPOS DE CONTENEDOR
              </span>

              <strong>
                {
                  resumen
                    ?.tiposContenedor ??
                  "—"
                }
              </strong>
            </div>
          </div>
        </section>


        <section className="admin-section">
          <div className="admin-section-heading">
            <div>
              <span className="admin-eyebrow">
                ACTUALIZACIÓN
              </span>

              <h2>
                Importar datos desde Excel
              </h2>

              <p>
                Seleccione la planilla
                CINTAC que contiene la
                hoja Tarifas Referencia.
              </p>
            </div>
          </div>


          <div className="admin-file-panel">
            <div className="admin-file-field">
              <label
                htmlFor="archivo-datos-cintac"
              >
                Archivo Excel
              </label>

              <input
                id="archivo-datos-cintac"
                type="file"
                accept=".xlsx"
                onChange={
                  seleccionarArchivo
                }
                disabled={
                  validando ||
                  importando
                }
              />

              <small>
                Formato permitido: .xlsx
              </small>
            </div>


            <div className="admin-selected-file">
              <span>
                ARCHIVO SELECCIONADO
              </span>

              <strong>
                {
                  archivo
                    ? archivo.name
                    : "Ningún archivo seleccionado"
                }
              </strong>
            </div>
          </div>


          <div className="admin-actions">
            <button
              type="button"
              className="admin-secondary-button"
              onClick={
                validarExcel
              }
              disabled={
                !archivo ||
                validando ||
                importando
              }
            >
              {
                validando
                  ? "VALIDANDO..."
                  : "VALIDAR ARCHIVO"
              }
            </button>


            <button
              type="button"
              className="admin-primary-button"
              onClick={
                aplicarImportacion
              }
              disabled={
                !validacion?.valido ||
                importando ||
                validando
              }
            >
              {
                importando
                  ? "ACTUALIZANDO..."
                  : "APLICAR ACTUALIZACIÓN"
              }
            </button>
          </div>


          {mensaje && (
            <div className="admin-alert success">
              <span>
                ✓
              </span>

              {mensaje}
            </div>
          )}


          {
            errores.length > 0 &&
            (
              <div className="admin-errors">
                <div className="admin-errors-header">
                  <strong>
                    El archivo no puede
                    procesarse
                  </strong>

                  <span>
                    {
                      errores.length
                    }{" "}
                    problema
                    {
                      errores.length !== 1
                        ? "s"
                        : ""
                    }
                  </span>
                </div>


                <div className="admin-errors-list">
                  {
                    errores.map(
                      (
                        error,
                        indice
                      ) => (
                        <div
                          className="admin-error-item"
                          key={
                            `${indice}-${error}`
                          }
                        >
                          <span>
                            !
                          </span>

                          <p>
                            {error}
                          </p>
                        </div>
                      )
                    )
                  }
                </div>
              </div>
            )
          }
        </section>


        {
          validacion?.valido &&
          (
            <section className="admin-section">
              <div className="admin-section-heading">
                <div>
                  <span className="admin-eyebrow">
                    VALIDACIÓN CORRECTA
                  </span>

                  <h2>
                    Vista previa
                  </h2>

                  <p>
                    Revise la información
                    antes de aplicar la
                    actualización.
                  </p>
                </div>


                <div className="admin-validation-total">
                  <strong>
                    {
                      validacion
                        .filasValidas
                    }
                  </strong>

                  <span>
                    FILAS VÁLIDAS
                  </span>
                </div>
              </div>


              <div className="admin-validation-grid">
                <div>
                  <span>
                    Rutas
                  </span>

                  <strong>
                    {
                      validacion
                        .resumen
                        .rutas
                    }
                  </strong>
                </div>


                <div>
                  <span>
                    Tarifas
                  </span>

                  <strong>
                    {
                      validacion
                        .resumen
                        .tarifas
                    }
                  </strong>
                </div>


                <div>
                  <span>
                    Tiempos de tránsito
                  </span>

                  <strong>
                    {
                      validacion
                        .resumen
                        .tiemposTransito
                    }
                  </strong>
                </div>
              </div>


              <div className="admin-table-container">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>
                        Ruta
                      </th>

                      <th>
                        País
                      </th>

                      <th>
                        Tipo
                      </th>

                      <th>
                        20&apos; Min
                      </th>

                      <th>
                        20&apos; Max
                      </th>

                      <th>
                        40&apos; Min
                      </th>

                      <th>
                        40&apos; Max
                      </th>

                      <th>
                        Tránsito
                      </th>

                      <th>
                        Fuente
                      </th>
                    </tr>
                  </thead>


                  <tbody>
                    {
                      validacion
                        .vistaPrevia
                        .map(
                          (fila) => (
                            <tr
                              key={
                                fila.fila
                              }
                            >
                              <td>
                                <strong>
                                  {
                                    fila.origen
                                  }
                                </strong>

                                <span className="admin-route-arrow">
                                  →
                                </span>

                                <strong>
                                  {
                                    fila.destino
                                  }
                                </strong>
                              </td>

                              <td>
                                {
                                  fila.pais
                                }
                              </td>

                              <td>
                                {
                                  fila.tipoRuta
                                }
                              </td>

                              <td>
                                US${" "}
                                {
                                  fila
                                    .tarifa20Min
                                }
                              </td>

                              <td>
                                US${" "}
                                {
                                  fila
                                    .tarifa20Max
                                }
                              </td>

                              <td>
                                US${" "}
                                {
                                  fila
                                    .tarifa40Min
                                }
                              </td>

                              <td>
                                US${" "}
                                {
                                  fila
                                    .tarifa40Max
                                }
                              </td>

                              <td>
                                {
                                  fila
                                    .transitoMin
                                }
                                {" - "}
                                {
                                  fila
                                    .transitoMax
                                }
                                {" días"}
                              </td>

                              <td>
                                {
                                  fila.fuente
                                }
                              </td>
                            </tr>
                          )
                        )
                    }
                  </tbody>
                </table>
              </div>


              {
                validacion
                  .filasValidas >
                  10 &&
                (
                  <p className="admin-preview-note">
                    Se muestran las
                    primeras 10 filas de
                    la planilla.
                  </p>
                )
              }
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
            Administración COMEX
          </div>
        </div>
      </footer>
    </div>
  );
}


export default AdminDatos;