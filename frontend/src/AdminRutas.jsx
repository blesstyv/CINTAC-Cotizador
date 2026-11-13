import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";


const FORMULARIO_VACIO = {
  origen: "",
  pais_origen: "",
  destino: "",
  tipo_ruta: "Directo / Transbordo",
  tarifa20_min: "",
  tarifa20_max: "",
  tarifa40_min: "",
  tarifa40_max: "",
  transito_min: "",
  transito_max: "",
};

const CAMPOS_NUMERICOS = [
  ["tarifa20_min", "Tarifa 20' mínima (US$)", "0.01"],
  ["tarifa20_max", "Tarifa 20' máxima (US$)", "0.01"],
  ["tarifa40_min", "Tarifa 40' mínima (US$)", "0.01"],
  ["tarifa40_max", "Tarifa 40' máxima (US$)", "0.01"],
  ["transito_min", "Tránsito mínimo (días)", "1"],
  ["transito_max", "Tránsito máximo (días)", "1"],
];


function formatearUSD(valor) {
  if (valor === null || valor === undefined) {
    return "—";
  }

  return new Intl.NumberFormat("es-CL", {
    maximumFractionDigits: 2,
  }).format(Number(valor));
}


// Convierte la respuesta de validación del backend en mensajes.
function extraerErrores(datos) {
  if (!datos || typeof datos !== "object") {
    return ["No fue posible completar la operación."];
  }

  if (datos.detail) {
    return [String(datos.detail)];
  }

  const mensajes = Object.values(datos)
    .flat()
    .map((mensaje) => String(mensaje));

  return mensajes.length > 0
    ? mensajes
    : ["No fue posible completar la operación."];
}


function validarFormulario(formulario, editando) {
  const errores = [];

  if (!editando) {
    if (!formulario.origen.trim()) {
      errores.push("Ingrese el puerto de origen.");
    }

    if (!formulario.pais_origen.trim()) {
      errores.push("Ingrese el país de origen.");
    }

    if (!formulario.destino.trim()) {
      errores.push("Seleccione o ingrese el puerto de destino.");
    }
  }

  CAMPOS_NUMERICOS.forEach(([campo, etiqueta]) => {
    const numero = Number(formulario[campo]);

    if (
      String(formulario[campo]).trim() === "" ||
      !Number.isFinite(numero) ||
      numero <= 0
    ) {
      errores.push(`${etiqueta}: ingrese un valor mayor que cero.`);
    }
  });

  if (errores.length > 0) {
    return errores;
  }

  [["20", "tarifa20"], ["40", "tarifa40"]].forEach(([codigo, base]) => {
    if (
      Number(formulario[`${base}_max`]) <
      Number(formulario[`${base}_min`])
    ) {
      errores.push(
        `La tarifa máxima de ${codigo}' no puede ser menor que la mínima.`
      );
    }
  });

  if (
    !Number.isInteger(Number(formulario.transito_min)) ||
    !Number.isInteger(Number(formulario.transito_max))
  ) {
    errores.push("Los días de tránsito deben ser números enteros.");
  } else if (
    Number(formulario.transito_max) < Number(formulario.transito_min)
  ) {
    errores.push("El tránsito máximo no puede ser menor que el mínimo.");
  }

  return errores;
}


function AdminRutas({
  apiUrl,
  peticionAutenticada,
  version,
  onCambio,
}) {
  const [rutas, setRutas] = useState([]);
  const [tiposRuta, setTiposRuta] = useState([
    "Directo",
    "Transbordo",
    "Directo / Transbordo",
  ]);
  const [cargando, setCargando] = useState(true);
  const [errorCarga, setErrorCarga] = useState("");
  const [modo, setModo] = useState(null); // null | "crear" | "editar"
  const [rutaEditada, setRutaEditada] = useState(null);
  const [formulario, setFormulario] = useState(FORMULARIO_VACIO);
  const [errores, setErrores] = useState([]);
  const [mensaje, setMensaje] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [busqueda, setBusqueda] = useState("");

  const guardadoEnCursoRef = useRef(false);
  const formularioRef = useRef(null);


  const cargarRutas = useCallback(
    async (estaActivo = () => true) => {
      try {
        const respuesta = await peticionAutenticada(
          `${apiUrl}/administracion/rutas/`
        );

        if (respuesta.status === 403) {
          return;
        }

        const datos = await respuesta.json();

        if (!estaActivo()) {
          return;
        }

        if (!respuesta.ok) {
          setErrorCarga(extraerErrores(datos)[0]);
          return;
        }

        setErrorCarga("");
        setRutas(datos.rutas || []);

        if (Array.isArray(datos.tiposRuta) && datos.tiposRuta.length > 0) {
          setTiposRuta(datos.tiposRuta);
        }

      } catch (error) {
        if (estaActivo()) {
          setErrorCarga(
            error.message || "No fue posible cargar las rutas."
          );
        }

      } finally {
        if (estaActivo()) {
          setCargando(false);
        }
      }
    },
    [apiUrl, peticionAutenticada]
  );


  useEffect(() => {
    let activo = true;

    const cargarInicial = async () => {
      await cargarRutas(() => activo);
    };

    void cargarInicial();

    return () => {
      activo = false;
    };
  }, [cargarRutas, version]);


  const actualizarCampo = (campo, valor) => {
    setFormulario((actual) => ({
      ...actual,
      [campo]: valor,
    }));

    setErrores([]);
  };


  const abrirCrear = () => {
    setModo("crear");
    setRutaEditada(null);
    setFormulario(FORMULARIO_VACIO);
    setErrores([]);
    setMensaje("");

    window.setTimeout(() => {
      formularioRef.current?.querySelector("input")?.focus();
    }, 0);
  };


  const abrirEditar = (ruta) => {
    setModo("editar");
    setRutaEditada(ruta);
    setFormulario({
      origen: ruta.origen,
      pais_origen: ruta.paisOrigen,
      destino: ruta.destino,
      tipo_ruta: ruta.tipoRuta,
      tarifa20_min: ruta.tarifa20Min ?? "",
      tarifa20_max: ruta.tarifa20Max ?? "",
      tarifa40_min: ruta.tarifa40Min ?? "",
      tarifa40_max: ruta.tarifa40Max ?? "",
      transito_min: ruta.transitoMin ?? "",
      transito_max: ruta.transitoMax ?? "",
    });
    setErrores([]);
    setMensaje("");

    window.setTimeout(() => {
      formularioRef.current?.scrollIntoView({
        block: "center",
      });
      formularioRef.current?.querySelector("select")?.focus();
    }, 0);
  };


  const cerrarFormulario = () => {
    setModo(null);
    setRutaEditada(null);
    setErrores([]);
  };


  const guardar = async (event) => {
    event.preventDefault();

    if (guardadoEnCursoRef.current) {
      return;
    }

    const editando = modo === "editar";

    const erroresLocales = validarFormulario(formulario, editando);

    if (erroresLocales.length > 0) {
      setErrores(erroresLocales);
      return;
    }

    const numericos = {
      tarifa20_min: String(formulario.tarifa20_min),
      tarifa20_max: String(formulario.tarifa20_max),
      tarifa40_min: String(formulario.tarifa40_min),
      tarifa40_max: String(formulario.tarifa40_max),
      transito_min: Number(formulario.transito_min),
      transito_max: Number(formulario.transito_max),
    };

    const cuerpo = editando
      ? {
        tipo_ruta: formulario.tipo_ruta,
        ...numericos,
      }
      : {
        origen: formulario.origen.trim(),
        pais_origen: formulario.pais_origen.trim(),
        destino: formulario.destino.trim(),
        tipo_ruta: formulario.tipo_ruta,
        ...numericos,
      };

    const descripcion = editando
      ? `Se actualizarán las tarifas y el tránsito de ${rutaEditada.origen} → ${rutaEditada.destino}.`
      : `Se creará la ruta ${cuerpo.origen} (${cuerpo.pais_origen}) → ${cuerpo.destino}.`;

    const confirmado = window.confirm(
      `${descripcion}\n\nEl cambio se aplica de inmediato en el cotizador y queda registrado en la bitácora con un respaldo del estado anterior. Las cotizaciones ya guardadas no cambian. ¿Desea continuar?`
    );

    if (!confirmado) {
      return;
    }

    guardadoEnCursoRef.current = true;
    setGuardando(true);
    setErrores([]);
    setMensaje("");

    try {
      const respuesta = await peticionAutenticada(
        editando
          ? `${apiUrl}/administracion/rutas/${rutaEditada.id}/`
          : `${apiUrl}/administracion/rutas/`,
        {
          method: editando ? "PATCH" : "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(cuerpo),
        }
      );

      const datos = await respuesta.json();

      if (!respuesta.ok) {
        setErrores(extraerErrores(datos));
        return;
      }

      setMensaje(datos.detail || "Cambios guardados.");
      setModo(null);
      setRutaEditada(null);

      await cargarRutas();

      if (onCambio) {
        onCambio();
      }

    } catch (error) {
      setErrores([
        error.message || "No fue posible guardar los cambios.",
      ]);

    } finally {
      guardadoEnCursoRef.current = false;
      setGuardando(false);
    }
  };


  const destinosConocidos = [
    ...new Set(rutas.map((ruta) => ruta.destino)),
  ].sort();

  const texto = busqueda.trim().toLowerCase();

  const rutasVisibles = texto
    ? rutas.filter((ruta) =>
      `${ruta.origen} ${ruta.paisOrigen} ${ruta.destino}`
        .toLowerCase()
        .includes(texto)
    )
    : rutas;

  const editando = modo === "editar";


  return (
    <section
      className="admin-section"
      aria-labelledby="titulo-rutas"
    >
      <div className="admin-section-heading">
        <div>
          <span className="admin-eyebrow">
            GESTIÓN MANUAL
          </span>

          <h2 id="titulo-rutas">
            Puertos, rutas y tarifas
          </h2>

          <p>
            Agregue un puerto creando su ruta, o actualice las tarifas y los días de tránsito. Los cambios se aplican de inmediato en el cotizador.
          </p>
        </div>

        <button
          type="button"
          className="admin-primary-button"
          onClick={abrirCrear}
          disabled={guardando || modo === "crear"}
        >
          NUEVA RUTA
        </button>
      </div>


      {mensaje && (
        <p
          className="rutas-mensaje"
          role="status"
        >
          ✓ {mensaje}
        </p>
      )}


      {modo && (
        <form
          ref={formularioRef}
          className="rutas-form"
          onSubmit={guardar}
          noValidate
          aria-label={
            editando
              ? "Editar ruta"
              : "Nueva ruta"
          }
        >
          <h3>
            {
              editando
                ? `Editar ${rutaEditada.origen} → ${rutaEditada.destino}`
                : "Nueva ruta"
            }
          </h3>

          <div className="rutas-form-grid">
            <div className="rutas-field">
              <label htmlFor="ruta-origen">
                Puerto de origen
              </label>

              <input
                id="ruta-origen"
                type="text"
                maxLength={100}
                autoComplete="off"
                value={formulario.origen}
                onChange={(event) =>
                  actualizarCampo("origen", event.target.value)
                }
                disabled={editando || guardando}
                placeholder="Ej: Singapur"
              />
            </div>

            <div className="rutas-field">
              <label htmlFor="ruta-pais">
                País de origen
              </label>

              <input
                id="ruta-pais"
                type="text"
                maxLength={100}
                autoComplete="off"
                value={formulario.pais_origen}
                onChange={(event) =>
                  actualizarCampo("pais_origen", event.target.value)
                }
                disabled={editando || guardando}
                placeholder="Ej: Singapur"
              />
            </div>

            <div className="rutas-field">
              <label htmlFor="ruta-destino">
                Puerto de destino (Chile)
              </label>

              <input
                id="ruta-destino"
                type="text"
                maxLength={100}
                autoComplete="off"
                list="ruta-destinos-conocidos"
                value={formulario.destino}
                onChange={(event) =>
                  actualizarCampo("destino", event.target.value)
                }
                disabled={editando || guardando}
                placeholder="Ej: San Antonio"
              />

              <datalist id="ruta-destinos-conocidos">
                {destinosConocidos.map((destino) => (
                  <option
                    key={destino}
                    value={destino}
                  />
                ))}
              </datalist>
            </div>

            <div className="rutas-field">
              <label htmlFor="ruta-tipo">
                Tipo de ruta
              </label>

              <select
                id="ruta-tipo"
                value={formulario.tipo_ruta}
                onChange={(event) =>
                  actualizarCampo("tipo_ruta", event.target.value)
                }
                disabled={guardando}
              >
                {tiposRuta.map((tipo) => (
                  <option
                    key={tipo}
                    value={tipo}
                  >
                    {tipo}
                  </option>
                ))}
              </select>
            </div>

            {CAMPOS_NUMERICOS.map(([campo, etiqueta, paso]) => (
              <div
                className="rutas-field"
                key={campo}
              >
                <label htmlFor={`ruta-${campo}`}>
                  {etiqueta}
                </label>

                <input
                  id={`ruta-${campo}`}
                  type="number"
                  min={paso}
                  step={paso}
                  inputMode={
                    paso === "1"
                      ? "numeric"
                      : "decimal"
                  }
                  value={formulario[campo]}
                  onChange={(event) =>
                    actualizarCampo(campo, event.target.value)
                  }
                  disabled={guardando}
                />
              </div>
            ))}
          </div>

          {errores.length > 0 && (
            <ul
              className="rutas-errores"
              role="alert"
            >
              {errores.map((error) => (
                <li key={error}>
                  {error}
                </li>
              ))}
            </ul>
          )}

          <div className="rutas-form-actions">
            <button
              type="button"
              className="admin-secondary-button"
              onClick={cerrarFormulario}
              disabled={guardando}
            >
              CANCELAR
            </button>

            <button
              type="submit"
              className="admin-primary-button"
              disabled={guardando}
            >
              {
                guardando
                  ? "GUARDANDO..."
                  : editando
                    ? "GUARDAR CAMBIOS"
                    : "CREAR RUTA"
              }
            </button>
          </div>
        </form>
      )}


      <div className="rutas-busqueda">
        <label htmlFor="rutas-buscar">
          Buscar ruta
        </label>

        <input
          id="rutas-buscar"
          type="search"
          value={busqueda}
          onChange={(event) =>
            setBusqueda(event.target.value)
          }
          placeholder="Puerto o país"
        />
      </div>


      {
        cargando
          ? (
            <p
              className="admin-preview-note"
              role="status"
            >
              Cargando rutas...
            </p>
          )
          : errorCarga
            ? (
              <p
                className="admin-preview-note"
                role="alert"
              >
                {errorCarga}
              </p>
            )
            : rutasVisibles.length === 0
              ? (
                <p className="admin-preview-note">
                  {
                    rutas.length === 0
                      ? "Aún no existen rutas. Cree la primera con NUEVA RUTA o importe la planilla Excel."
                      : "Ninguna ruta coincide con la búsqueda."
                  }
                </p>
              )
              : (
                <div className="admin-table-container">
                  <table className="admin-table">
                    <caption className="sr-only">
                      Rutas vigentes con sus tarifas y días de tránsito
                    </caption>

                    <thead>
                      <tr>
                        <th scope="col">Ruta</th>
                        <th scope="col">País</th>
                        <th scope="col">Tipo</th>
                        <th scope="col">20&apos; (US$)</th>
                        <th scope="col">40&apos; (US$)</th>
                        <th scope="col">Tránsito</th>
                        <th scope="col">
                          <span className="sr-only">Acciones</span>
                        </th>
                      </tr>
                    </thead>

                    <tbody>
                      {rutasVisibles.map((ruta) => (
                        <tr key={ruta.id}>
                          <td>
                            <strong>{ruta.origen}</strong>
                            <span className="admin-route-arrow">→</span>
                            <strong>{ruta.destino}</strong>
                          </td>

                          <td>{ruta.paisOrigen}</td>

                          <td>{ruta.tipoRuta}</td>

                          <td>
                            {formatearUSD(ruta.tarifa20Min)}
                            {" – "}
                            {formatearUSD(ruta.tarifa20Max)}
                          </td>

                          <td>
                            {formatearUSD(ruta.tarifa40Min)}
                            {" – "}
                            {formatearUSD(ruta.tarifa40Max)}
                          </td>

                          <td>
                            {
                              ruta.transitoMin !== null
                                ? `${ruta.transitoMin} – ${ruta.transitoMax} días`
                                : "—"
                            }
                          </td>

                          <td>
                            <button
                              type="button"
                              className="admin-restore-button"
                              onClick={() => abrirEditar(ruta)}
                              disabled={guardando}
                              aria-label={`Editar la ruta ${ruta.origen} a ${ruta.destino}`}
                            >
                              Editar
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
      }
    </section>
  );
}


export default AdminRutas;
