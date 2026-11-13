import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import AdminRutas
  from "./AdminRutas";

import AdminUsuarios
  from "./AdminUsuarios";

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


const NOMBRES_CAMPOS = {
  tipoRuta: "Tipo de ruta",
  tarifa20Min: "Tarifa 20' mín.",
  tarifa20Max: "Tarifa 20' máx.",
  tarifa40Min: "Tarifa 40' mín.",
  tarifa40Max: "Tarifa 40' máx.",
  transitoMin: "Tránsito mín.",
  transitoMax: "Tránsito máx.",
};


function formatearValorCampo(
  campo,
  valor
) {
  if (
    valor === null ||
    valor === undefined ||
    valor === ""
  ) {
    return "—";
  }

  if (campo.startsWith("tarifa")) {
    return `US$ ${new Intl.NumberFormat(
      "es-CL",
      {
        maximumFractionDigits: 2,
      }
    ).format(Number(valor))}`;
  }

  if (campo.startsWith("transito")) {
    return `${valor} días`;
  }

  return String(valor);
}


function formatearFechaHora(
  iso
) {
  try {
    return new Intl.DateTimeFormat(
      "es-CL",
      {
        dateStyle: "short",
        timeStyle: "short",
      }
    ).format(new Date(iso));
  } catch {
    return iso;
  }
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


  const [
    operaciones,
    setOperaciones,
  ] = useState([]);

  const [
    puedeRestaurar,
    setPuedeRestaurar,
  ] = useState(false);

  const [
    cargandoOperaciones,
    setCargandoOperaciones,
  ] = useState(true);

  const [
    errorOperaciones,
    setErrorOperaciones,
  ] = useState("");

  const [
    restaurandoId,
    setRestaurandoId,
  ] = useState(null);

  // Aumenta cuando una importación o restauración cambia los
  // datos maestros, para que la tabla de rutas se recargue.
  const [
    versionDatos,
    setVersionDatos,
  ] = useState(0);


  const resumenEnCursoRef =
    useRef(false);

  const validacionEnCursoRef =
    useRef(false);

  const importacionEnCursoRef =
    useRef(false);


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


  const cargarOperaciones =
    useCallback(
      async (
        estaActivo = () => true
      ) => {
        try {
          const respuesta =
            await peticionAutenticada(
              `${apiUrl}/administracion/operaciones/`
            );

          if (
            respuesta.status === 403
          ) {
            return;
          }

          const datos =
            await respuesta.json();

          if (!estaActivo()) {
            return;
          }

          if (!respuesta.ok) {
            setErrorOperaciones(
              obtenerErrores(datos)[0]
            );

            return;
          }

          setErrorOperaciones("");

          setOperaciones(
            datos.operaciones || []
          );

          setPuedeRestaurar(
            Boolean(
              datos.puedeRestaurar
            )
          );

        } catch (error) {
          if (estaActivo()) {
            setErrorOperaciones(
              error.message ||
              "No fue posible cargar la bitácora."
            );
          }

        } finally {
          if (estaActivo()) {
            setCargandoOperaciones(false);
          }
        }
      },
      [
        apiUrl,
        peticionAutenticada,
      ]
    );


  useEffect(() => {
    let activo = true;

    const cargarOperacionesIniciales =
      async () => {
        await cargarOperaciones(
          () => activo
        );
      };

    void cargarOperacionesIniciales();

    return () => {
      activo = false;
    };
  }, [
    cargarOperaciones,
  ]);


  const restaurarOperacion =
  async (operacion) => {
    if (
      restaurandoId !== null ||
      importacionEnCursoRef.current
    ) {
      return;
    }

    const confirmado =
      window.confirm(
        `Se restaurarán los datos maestros al estado anterior a la operación #${operacion.id} (${operacion.tipoNombre}, ${formatearFechaHora(operacion.fecha)}).\n\nLas rutas creadas después se eliminarán y las tarifas volverán a sus valores previos. El historial de cotizaciones no se modifica.\n\nAntes de restaurar se guardará el estado actual, por lo que podrá revertir esta acción. ¿Desea continuar?`
      );

    if (!confirmado) {
      return;
    }

    setRestaurandoId(operacion.id);
    setErrores([]);
    setMensaje("");

    try {
      const respuesta =
        await peticionAutenticada(
          `${apiUrl}/administracion/operaciones/${operacion.id}/restaurar/`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                confirmar: true,
              }),
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
          obtenerErrores(datos)
        );

        return;
      }

      setMensaje(
        datos.detail ||
        "Datos maestros restaurados."
      );

      await cargarResumen();
      await cargarOperaciones();

      setVersionDatos(
        (actual) => actual + 1
      );

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
      setRestaurandoId(null);
    }
  };


  const cargarResumen =
  async () => {
    if (
      resumenEnCursoRef.current
    ) {
      return;
    }

    resumenEnCursoRef.current =
      true;

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
      resumenEnCursoRef.current =
        false;

      setCargandoResumen(
        false
      );
    }
  };


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


  const validarExcel =
  async () => {
    if (
      validacionEnCursoRef.current ||
      importacionEnCursoRef.current
    ) {
      return;
    }

    if (!archivo) {
      setErrores([
        "Seleccione un archivo Excel antes de continuar.",
      ]);

      return;
    }

    validacionEnCursoRef.current =
      true;

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
            method:
              "POST",

            body:
              formulario,
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
      validacionEnCursoRef.current =
        false;

      setValidando(
        false
      );
    }
  };


  const aplicarImportacion =
  async () => {
    if (
      importacionEnCursoRef.current ||
      validacionEnCursoRef.current
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

    importacionEnCursoRef.current =
      true;

    const cambios =
      validacion.resumenCambios;

    const detalleCambios =
      cambios
        ? `\n\n• Rutas nuevas: ${cambios.nuevas}\n• Rutas modificadas: ${cambios.modificadas}\n• Sin cambios: ${cambios.sinCambios}\n• Rutas existentes que se conservan: ${cambios.conservadas}`
        : "";

    const confirmado =
      window.confirm(
        `Se actualizarán los datos maestros utilizados por el cotizador.${detalleCambios}\n\nLa operación es transaccional (si falla, no se aplica ningún cambio) y se guardará un respaldo del estado actual que un administrador podrá restaurar. ¿Desea continuar?`
      );

    if (!confirmado) {
      importacionEnCursoRef.current =
        false;

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

    if (validacion.archivoSha256) {
      formulario.append(
        "archivo_sha256",
        validacion.archivoSha256
      );
    }

    try {
      const respuesta =
        await peticionAutenticada(
          `${apiUrl}/administracion/importar-excel/`,
          {
            method:
              "POST",

            body:
              formulario,
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

      if (inputArchivo) {
        inputArchivo.value =
          "";
      }

      await cargarResumen();
      await cargarOperaciones();

      setVersionDatos(
        (actual) => actual + 1
      );

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
      importacionEnCursoRef.current =
        false;

      setImportando(
        false
      );
    }
  };


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
                {
                  usuario.rolNombre ||
                  "USUARIO"
                }
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
              CINTAC
            </strong>
          </h1>

          <p>
            Gestión de datos,
            accesos y configuración
            operativa del cotizador.
          </p>
        </div>
      </section>


      <main className="admin-main">
        {
          usuario
            .puedeGestionarUsuarios &&
          (
            <AdminUsuarios
              apiUrl={
                apiUrl
              }

              usuarioActual={
                usuario
              }

              peticionAutenticada={
                peticionAutenticada
              }

              onPermisoRevocado={
                onPermisoRevocado
              }
            />
          )
        }


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


        <AdminRutas
          apiUrl={apiUrl}
          peticionAutenticada={peticionAutenticada}
          version={versionDatos}
          onCambio={() => {
            void cargarResumen();
            void cargarOperaciones();

            if (onDatosActualizados) {
              onDatosActualizados();
            }
          }}
        />


        <section className="admin-section">
          <div className="admin-section-heading">
            <div>
              <span className="admin-eyebrow">
                ACTUALIZACIÓN MASIVA
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

              {
                validacion.resumenCambios && (
                  <div className="admin-diff">
                    <h3 className="admin-diff-title">
                      Cambios respecto de los datos actuales
                    </h3>

                    <div className="admin-validation-grid admin-diff-grid">
                      <div>
                        <span>Rutas nuevas</span>
                        <strong>{validacion.resumenCambios.nuevas}</strong>
                      </div>

                      <div>
                        <span>Rutas modificadas</span>
                        <strong>{validacion.resumenCambios.modificadas}</strong>
                      </div>

                      <div>
                        <span>Sin cambios</span>
                        <strong>{validacion.resumenCambios.sinCambios}</strong>
                      </div>

                      <div>
                        <span>Se conservan (no vienen en el archivo)</span>
                        <strong>{validacion.resumenCambios.conservadas}</strong>
                      </div>
                    </div>

                    {
                      validacion.comparacion?.length > 0
                        ? (
                          <div className="admin-table-container">
                            <table className="admin-table admin-diff-table">
                              <caption className="sr-only">
                                Comparación entre los valores actuales y los propuestos por el archivo
                              </caption>

                              <thead>
                                <tr>
                                  <th scope="col">Fila</th>
                                  <th scope="col">Ruta</th>
                                  <th scope="col">Estado</th>
                                  <th scope="col">Campo</th>
                                  <th scope="col">Actual</th>
                                  <th scope="col">Propuesto</th>
                                </tr>
                              </thead>

                              <tbody>
                                {
                                  validacion.comparacion.flatMap(
                                    (item) =>
                                      item.cambios.map(
                                        (cambio, indice) => (
                                          <tr
                                            key={`${item.fila}-${cambio.campo}`}
                                          >
                                            <td>
                                              {indice === 0 ? item.fila : ""}
                                            </td>

                                            <td>
                                              {
                                                indice === 0
                                                  ? `${item.origen} → ${item.destino}`
                                                  : ""
                                              }
                                            </td>

                                            <td>
                                              {
                                                indice === 0 && (
                                                  <span
                                                    className={
                                                      item.estado === "nueva"
                                                        ? "admin-badge admin-badge-new"
                                                        : "admin-badge admin-badge-changed"
                                                    }
                                                  >
                                                    {
                                                      item.estado === "nueva"
                                                        ? "Nueva"
                                                        : "Modificada"
                                                    }
                                                  </span>
                                                )
                                              }
                                            </td>

                                            <td>
                                              {NOMBRES_CAMPOS[cambio.campo] || cambio.campo}
                                            </td>

                                            <td className="admin-diff-old">
                                              {formatearValorCampo(cambio.campo, cambio.actual)}
                                            </td>

                                            <td className="admin-diff-new">
                                              {formatearValorCampo(cambio.campo, cambio.propuesto)}
                                            </td>
                                          </tr>
                                        )
                                      )
                                  )
                                }
                              </tbody>
                            </table>
                          </div>
                        )
                        : (
                          <p className="admin-preview-note">
                            El archivo no modifica ningún valor actual.
                          </p>
                        )
                    }
                  </div>
                )
              }
            </section>
          )
        }


        <section
          className="admin-section"
          aria-labelledby="titulo-bitacora"
        >
          <div className="admin-section-heading">
            <div>
              <span className="admin-eyebrow">
                TRAZABILIDAD
              </span>

              <h2 id="titulo-bitacora">
                Bitácora de cambios
              </h2>

              <p>
                Cada importación guarda quién la realizó, el archivo y un respaldo del estado anterior.
                {
                  puedeRestaurar
                    ? " Como administrador puede restaurar ese estado."
                    : " Solo un administrador puede restaurar un estado anterior."
                }
              </p>
            </div>
          </div>

          {
            cargandoOperaciones
              ? (
                <p
                  className="admin-preview-note"
                  role="status"
                >
                  Cargando bitácora...
                </p>
              )
              : errorOperaciones
                ? (
                  <p
                    className="admin-preview-note"
                    role="alert"
                  >
                    {errorOperaciones}
                  </p>
                )
                : operaciones.length === 0
                  ? (
                    <p className="admin-preview-note">
                      Aún no se registran importaciones ni restauraciones.
                    </p>
                  )
                  : (
                    <div className="admin-table-container">
                      <table className="admin-table">
                        <caption className="sr-only">
                          Últimas operaciones sobre los datos maestros
                        </caption>

                        <thead>
                          <tr>
                            <th scope="col">#</th>
                            <th scope="col">Fecha</th>
                            <th scope="col">Operación</th>
                            <th scope="col">Usuario</th>
                            <th scope="col">Archivo</th>
                            <th scope="col">Resultado</th>
                            <th scope="col">
                              <span className="sr-only">Acciones</span>
                            </th>
                          </tr>
                        </thead>

                        <tbody>
                          {
                            operaciones.map(
                              (operacion) => (
                                <tr key={operacion.id}>
                                  <td>{operacion.id}</td>

                                  <td>{formatearFechaHora(operacion.fecha)}</td>

                                  <td>
                                    {operacion.tipoNombre}
                                    {
                                      operacion.detalle && (
                                        <small className="admin-op-note">
                                          {operacion.detalle}
                                        </small>
                                      )
                                    }
                                    {
                                      operacion.restauradaDesde && (
                                        <small className="admin-op-note">
                                          desde #{operacion.restauradaDesde}
                                        </small>
                                      )
                                    }
                                  </td>

                                  <td>{operacion.usuario || "—"}</td>

                                  <td
                                    title={operacion.archivoSha256 || ""}
                                  >
                                    {operacion.archivo || "—"}
                                  </td>

                                  <td>
                                    <span
                                      className={
                                        operacion.estado === "COMPLETADA"
                                          ? "admin-badge admin-badge-ok"
                                          : "admin-badge admin-badge-error"
                                      }
                                    >
                                      {
                                        operacion.estado === "COMPLETADA"
                                          ? "Completada"
                                          : "Fallida (revertida)"
                                      }
                                    </span>
                                  </td>

                                  <td>
                                    {
                                      puedeRestaurar &&
                                      operacion.restaurable && (
                                        <button
                                          type="button"
                                          className="admin-restore-button"
                                          onClick={() =>
                                            restaurarOperacion(operacion)
                                          }
                                          disabled={
                                            restaurandoId !== null ||
                                            importando
                                          }
                                          aria-label={`Restaurar el estado anterior a la operación ${operacion.id}`}
                                        >
                                          {
                                            restaurandoId === operacion.id
                                              ? "Restaurando..."
                                              : "Restaurar estado anterior"
                                          }
                                        </button>
                                      )
                                    }
                                  </td>
                                </tr>
                              )
                            )
                          }
                        </tbody>
                      </table>
                    </div>
                  )
          }
        </section>
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