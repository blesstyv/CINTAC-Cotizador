import {
  useEffect,
  useMemo,
  useState,
} from "react";

import heroImage from "./assets/hero-cintac.jpg";
import "./App.css";


function App() {
  const [rutas, setRutas] = useState([]);
  const [tiposContenedor, setTiposContenedor] = useState([]);

  const [origen, setOrigen] = useState("");
  const [destino, setDestino] = useState("");
  const [tipoContenedor, setTipoContenedor] = useState("");

  const [pesoCarga, setPesoCarga] = useState("");
  const [unidadPeso, setUnidadPeso] = useState("kg");

  const [contingencia, setContingencia] = useState("0");
  const [tipoCambio, setTipoCambio] = useState("");

  const [cargandoDatos, setCargandoDatos] = useState(true);
  const [errorDatos, setErrorDatos] = useState("");

  const [mensaje, setMensaje] = useState("");
  const [resultado, setResultado] = useState(null);

  const [errores, setErrores] = useState({
    origen: false,
    destino: false,
    pesoCarga: false,
    contingencia: false,
    tipoCambio: false,
  });


  /* ======================================
     DATOS DESDE DJANGO
  ====================================== */

  useEffect(() => {
    const cargarDatos = async () => {
      setCargandoDatos(true);

      try {
        const [
          respuestaRutas,
          respuestaContenedores,
        ] = await Promise.all([
          fetch(
            "http://127.0.0.1:8000/api/rutas/"
          ),
          fetch(
            "http://127.0.0.1:8000/api/tipos-contenedor/"
          ),
        ]);

        if (
          !respuestaRutas.ok ||
          !respuestaContenedores.ok
        ) {
          throw new Error();
        }

        const [
          datosRutas,
          datosContenedores,
        ] = await Promise.all([
          respuestaRutas.json(),
          respuestaContenedores.json(),
        ]);

        setRutas(datosRutas);
        setTiposContenedor(datosContenedores);
        setErrorDatos("");
      } catch {
        setRutas([]);
        setTiposContenedor([]);

        setErrorDatos(
          "No fue posible cargar la información del cotizador."
        );
      } finally {
        setCargandoDatos(false);
      }
    };

    cargarDatos();
  }, []);


  /* ======================================
     PUERTOS Y RUTA
  ====================================== */

  const puertosOrigen = useMemo(
    () => [
      ...new Set(
        rutas.map(
          (ruta) => ruta.origen
        )
      ),
    ],
    [rutas]
  );


  const puertosDestino = useMemo(() => {
    if (!origen) {
      return [];
    }

    return [
      ...new Set(
        rutas
          .filter(
            (ruta) =>
              ruta.origen === origen
          )
          .map(
            (ruta) =>
              ruta.destino
          )
      ),
    ];
  }, [
    rutas,
    origen,
  ]);


  const rutaSeleccionada = useMemo(() => {
    if (
      !origen ||
      !destino
    ) {
      return null;
    }

    return (
      rutas.find(
        (ruta) =>
          ruta.origen === origen &&
          ruta.destino === destino
      ) || null
    );
  }, [
    rutas,
    origen,
    destino,
  ]);


  /* ======================================
     FORMATOS
  ====================================== */

  const formatearUSD = (valor) =>
    new Intl.NumberFormat(
      "es-CL",
      {
        maximumFractionDigits: 0,
      }
    ).format(valor);


  const formatearCLP = (valor) =>
    new Intl.NumberFormat(
      "es-CL",
      {
        maximumFractionDigits: 0,
      }
    ).format(valor);


  const formatearNumero = (valor) =>
    new Intl.NumberFormat(
      "es-CL",
      {
        maximumFractionDigits: 2,
      }
    ).format(valor);


  /* ======================================
     OPCIONES DE CONTENEDORES
  ====================================== */

  const recomendacion = useMemo(() => {
    if (
      !rutaSeleccionada ||
      pesoCarga === "" ||
      tiposContenedor.length === 0
    ) {
      return null;
    }

    const pesoNumero =
      Number(pesoCarga);

    if (
      !Number.isFinite(
        pesoNumero
      ) ||
      pesoNumero <= 0
    ) {
      return null;
    }

    const pesoTN =
      unidadPeso === "kg"
        ? pesoNumero / 1000
        : pesoNumero;

    const pesoKg =
      unidadPeso === "kg"
        ? pesoNumero
        : pesoNumero * 1000;


    const opciones =
      tiposContenedor
        .map((contenedor) => {
          const capacidadTN =
            Number(
              contenedor.capacidad_tn
            );

          if (
            !Number.isFinite(
              capacidadTN
            ) ||
            capacidadTN <= 0
          ) {
            return null;
          }

          const tarifa =
            rutaSeleccionada.tarifas.find(
              (item) =>
                item.tipoContenedor ===
                contenedor.codigo
            );

          if (!tarifa) {
            return null;
          }

          const tarifaMin =
            Number(
              tarifa.valorMinimo
            );

          const tarifaMax =
            Number(
              tarifa.valorMaximo
            );

          if (
            !Number.isFinite(
              tarifaMin
            ) ||
            !Number.isFinite(
              tarifaMax
            )
          ) {
            return null;
          }

          const cantidad =
            Math.ceil(
              pesoTN /
              capacidadTN
            );

          const totalMin =
            tarifaMin *
            cantidad;

          const totalMax =
            tarifaMax *
            cantidad;

          const costoPromedio =
            (
              totalMin +
              totalMax
            ) / 2;

          return {
            codigo:
              contenedor.codigo,

            nombre:
              contenedor.nombre,

            capacidadTN,

            cantidad,

            tarifaMin,
            tarifaMax,

            totalMin,
            totalMax,

            costoPromedio,

            fuente:
              tarifa.fuente,
          };
        })
        .filter(Boolean);


    if (
      opciones.length === 0
    ) {
      return null;
    }


    const sugerida =
      opciones.reduce(
        (
          mejor,
          actual
        ) =>
          actual.costoPromedio <
          mejor.costoPromedio
            ? actual
            : mejor
      );


    return {
      pesoTN,
      pesoKg,
      opciones,
      sugerida,
    };
  }, [
    rutaSeleccionada,
    pesoCarga,
    unidadPeso,
    tiposContenedor,
  ]);


  /* ======================================
     PRESELECCIÓN AUTOMÁTICA
  ====================================== */

  useEffect(() => {
    if (!recomendacion) {
      setTipoContenedor("");
      setResultado(null);
      return;
    }

    setTipoContenedor(
      recomendacion.sugerida.codigo
    );

    setResultado(null);
    setMensaje("");
  }, [recomendacion]);


  /* ======================================
     AUXILIARES
  ====================================== */

  const limpiarResultado = () => {
    setResultado(null);
    setMensaje("");
  };


  const limpiarError = (campo) => {
    setErrores(
      (actuales) => ({
        ...actuales,
        [campo]: false,
      })
    );
  };


  const nuevaCotizacion = () => {
    setOrigen("");
    setDestino("");
    setTipoContenedor("");

    setPesoCarga("");
    setUnidadPeso("kg");

    setContingencia("0");
    setTipoCambio("");

    setMensaje("");
    setResultado(null);

    setErrores({
      origen: false,
      destino: false,
      pesoCarga: false,
      contingencia: false,
      tipoCambio: false,
    });

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };


  /* ======================================
     COTIZAR
  ====================================== */

  const cotizar = (e) => {
    e.preventDefault();

    setMensaje("");
    setResultado(null);


    const nuevosErrores = {
      origen: !origen,
      destino: !destino,
      pesoCarga: !pesoCarga,
      contingencia: false,
      tipoCambio: false,
    };

    setErrores(
      nuevosErrores
    );


    if (
      nuevosErrores.origen ||
      nuevosErrores.destino ||
      nuevosErrores.pesoCarga
    ) {
      setMensaje(
        "Complete los campos obligatorios para realizar la cotización."
      );

      return;
    }


    const pesoNumero =
      Number(pesoCarga);

    if (
      !Number.isFinite(
        pesoNumero
      ) ||
      pesoNumero <= 0
    ) {
      setErrores(
        (actuales) => ({
          ...actuales,
          pesoCarga: true,
        })
      );

      setMensaje(
        "El peso total debe ser mayor que cero."
      );

      return;
    }


    if (!rutaSeleccionada) {
      setMensaje(
        "No existe información para la ruta seleccionada."
      );

      return;
    }


    if (!recomendacion) {
      setMensaje(
        "No existen opciones disponibles para esta operación."
      );

      return;
    }


    const opcionSeleccionada =
      recomendacion.opciones.find(
        (opcion) =>
          opcion.codigo ===
          tipoContenedor
      );


    if (!opcionSeleccionada) {
      setMensaje(
        "Seleccione un tipo de contenedor."
      );

      return;
    }


    const contingenciaNumero =
      Number(contingencia) || 0;


    if (
      !Number.isInteger(
        contingenciaNumero
      ) ||
      contingenciaNumero < 0
    ) {
      setErrores(
        (actuales) => ({
          ...actuales,
          contingencia: true,
        })
      );

      setMensaje(
        "El margen de contingencia debe ser un número entero igual o mayor que cero."
      );

      return;
    }


    let tipoCambioNumero = null;


    if (tipoCambio !== "") {
      tipoCambioNumero =
        Number(tipoCambio);

      if (
        !Number.isFinite(
          tipoCambioNumero
        ) ||
        tipoCambioNumero <= 0
      ) {
        setErrores(
          (actuales) => ({
            ...actuales,
            tipoCambio: true,
          })
        );

        setMensaje(
          "El tipo de cambio debe ser mayor que cero."
        );

        return;
      }
    }


    const totalMinCLP =
      tipoCambioNumero !== null
        ? opcionSeleccionada.totalMin *
          tipoCambioNumero
        : null;


    const totalMaxCLP =
      tipoCambioNumero !== null
        ? opcionSeleccionada.totalMax *
          tipoCambioNumero
        : null;


    const tieneTransito =
      rutaSeleccionada.transitoMin !== null &&
      rutaSeleccionada.transitoMax !== null;


    const transitoMin =
      tieneTransito
        ? rutaSeleccionada.transitoMin +
          contingenciaNumero
        : null;


    const transitoMax =
      tieneTransito
        ? rutaSeleccionada.transitoMax +
          contingenciaNumero
        : null;


    setResultado({
      origen:
        rutaSeleccionada.origen,

      destino:
        rutaSeleccionada.destino,

      pais:
        rutaSeleccionada.pais,

      tipoRuta:
        rutaSeleccionada.tipoRuta,

      pesoTN:
        recomendacion.pesoTN,

      pesoKg:
        recomendacion.pesoKg,

      tipoContenedor:
        opcionSeleccionada.codigo,

      nombreContenedor:
        opcionSeleccionada.nombre,

      capacidadTN:
        opcionSeleccionada.capacidadTN,

      cantidad:
        opcionSeleccionada.cantidad,

      tarifaMin:
        opcionSeleccionada.tarifaMin,

      tarifaMax:
        opcionSeleccionada.tarifaMax,

      totalMin:
        opcionSeleccionada.totalMin,

      totalMax:
        opcionSeleccionada.totalMax,

      esSugerida:
        opcionSeleccionada.codigo ===
        recomendacion.sugerida.codigo,

      transitoOriginalMin:
        rutaSeleccionada.transitoMin,

      transitoOriginalMax:
        rutaSeleccionada.transitoMax,

      transitoMin,
      transitoMax,

      contingencia:
        contingenciaNumero,

      fuente:
        opcionSeleccionada.fuente,

      tipoCambio:
        tipoCambioNumero,

      totalMinCLP,
      totalMaxCLP,
    });


    setErrores({
      origen: false,
      destino: false,
      pesoCarga: false,
      contingencia: false,
      tipoCambio: false,
    });
  };


  return (
    <div className="app">
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

          <div className="header-context">
            <span>
              IMPORTACIONES
            </span>

            <span className="context-divider"></span>

            <span>
              COMERCIO EXTERIOR
            </span>
          </div>
        </div>
      </header>


      <section
        className="hero"
        style={{
          backgroundImage:
            `url(${heroImage})`,
        }}
      >
        <div className="hero-overlay"></div>

        <div className="hero-accent"></div>

        <div className="hero-content">
          <div className="hero-kicker">
            COTIZADOR LOGÍSTICO
          </div>

          <h1>
            Cotiza tus operaciones

            <br />

            <strong>
              de importación
            </strong>
          </h1>

          <p>
            Consulta rutas, tarifas y
            tiempos estimados para tu
            operación.
          </p>

          <a
            href="#cotizador"
            className="hero-button"
          >
            INICIAR COTIZACIÓN
          </a>
        </div>
      </section>


      <section className="intro-strip">
        <div className="intro-inner">
          <div className="intro-title">
            Cotización logística CINTAC
          </div>

          <div className="intro-text">
            Ingrese los antecedentes de
            la operación para obtener
            una estimación.
          </div>
        </div>
      </section>


      <main
        className="main-container"
        id="cotizador"
      >
        <section className="quote-card">
          <div className="card-title">
            <div className="title-icon">
              01
            </div>

            <div>
              <span className="card-eyebrow">
                OPERACIÓN
              </span>

              <h2>
                Nueva cotización
              </h2>

              <p>
                Complete los antecedentes
                de la operación.
              </p>
            </div>
          </div>


          <form onSubmit={cotizar}>
            {cargandoDatos && (
              <div className="message-box">
                <p>
                  Cargando información del cotizador...
                </p>
              </div>
            )}

            {errorDatos && (
              <div className="message-box">
                <span className="message-icon">
                  !
                </span>

                <p>
                  {errorDatos}
                </p>
              </div>
            )}


            <section className="form-section">
              <div className="section-heading">
                <span className="section-line"></span>

                <div>
                  <h3>
                    Ruta de importación
                  </h3>

                  <p>
                    Seleccione origen y destino.
                  </p>
                </div>
              </div>


              <div className="form-grid">
                <div className="form-group">
                  <label>
                    Puerto de origen

                    <span className="required">
                      *
                    </span>
                  </label>

                  <select
                    className={
                      errores.origen
                        ? "campo-error"
                        : ""
                    }
                    value={origen}
                    disabled={
                      cargandoDatos ||
                      rutas.length === 0
                    }
                    onChange={(e) => {
                      setOrigen(
                        e.target.value
                      );

                      setDestino("");

                      limpiarError(
                        "origen"
                      );

                      limpiarError(
                        "destino"
                      );

                      limpiarResultado();
                    }}
                  >
                    <option value="">
                      Seleccione puerto
                    </option>

                    {puertosOrigen.map(
                      (puerto) => (
                        <option
                          key={puerto}
                          value={puerto}
                        >
                          {puerto}
                        </option>
                      )
                    )}
                  </select>
                </div>


                <div className="form-group">
                  <label>
                    Puerto de destino

                    <span className="required">
                      *
                    </span>
                  </label>

                  <select
                    className={
                      errores.destino
                        ? "campo-error"
                        : ""
                    }
                    value={destino}
                    disabled={!origen}
                    onChange={(e) => {
                      setDestino(
                        e.target.value
                      );

                      limpiarError(
                        "destino"
                      );

                      limpiarResultado();
                    }}
                  >
                    <option value="">
                      {origen
                        ? "Seleccione puerto"
                        : "Seleccione primero el origen"}
                    </option>

                    {puertosDestino.map(
                      (puerto) => (
                        <option
                          key={puerto}
                          value={puerto}
                        >
                          {puerto}
                        </option>
                      )
                    )}
                  </select>
                </div>
              </div>
            </section>


            <section className="form-section">
              <div className="section-heading">
                <span className="section-line"></span>

                <div>
                  <h3>
                    Carga total
                  </h3>
                </div>
              </div>


              <div className="form-grid single">
                <div className="form-group">
                  <label>
                    Peso total

                    <span className="required">
                      *
                    </span>
                  </label>

                  <div className="field-with-select">
                    <input
                      className={
                        errores.pesoCarga
                          ? "campo-error"
                          : ""
                      }
                      type="number"
                      min="0"
                      step="any"
                      value={pesoCarga}
                      onChange={(e) => {
                        setPesoCarga(
                          e.target.value
                        );

                        limpiarError(
                          "pesoCarga"
                        );

                        limpiarResultado();
                      }}
                      placeholder="Ej: 25000"
                    />

                    <select
                      value={unidadPeso}
                      onChange={(e) => {
                        setUnidadPeso(
                          e.target.value
                        );

                        limpiarResultado();
                      }}
                    >
                      <option value="kg">
                        kg
                      </option>

                      <option value="tn">
                        TN
                      </option>
                    </select>
                  </div>
                </div>
              </div>


              {recomendacion && (
                <div className="recommendation-box">
                  <div className="recommendation-header">
                    <div>
                      <span className="recommendation-eyebrow">
                        OPCIONES
                      </span>

                      <h4>
                        Contenedores
                      </h4>
                    </div>

                    <div className="load-summary">
                      {formatearNumero(
                        recomendacion.pesoTN
                      )}{" "}
                      TN
                    </div>
                  </div>


                  <div className="recommendation-options">
                    {recomendacion.opciones.map(
                      (opcion) => {
                        const sugerida =
                          opcion.codigo ===
                          recomendacion.sugerida.codigo;

                        const seleccionada =
                          opcion.codigo ===
                          tipoContenedor;

                        return (
                          <button
                            key={opcion.codigo}
                            type="button"
                            className={[
                              "recommendation-option",
                              sugerida
                                ? "suggested"
                                : "",
                              seleccionada
                                ? "selected"
                                : "",
                            ]
                              .filter(Boolean)
                              .join(" ")}
                            onClick={() => {
                              setTipoContenedor(
                                opcion.codigo
                              );

                              limpiarResultado();
                            }}
                          >
                            <div className="option-top">
                              <strong>
                                {opcion.nombre}
                              </strong>

                              <div className="option-labels">
                                {sugerida && (
                                  <span className="suggested-label">
                                    SUGERIDO
                                  </span>
                                )}

                                {seleccionada && (
                                  <span className="selected-label">
                                    SELECCIONADO
                                  </span>
                                )}
                              </div>
                            </div>


                            <div className="option-quantity">
                              {formatearNumero(
                                opcion.cantidad
                              )}{" "}
                              contenedor
                              {opcion.cantidad !== 1
                                ? "es"
                                : ""}
                            </div>


                            <div className="option-price">
                              US${" "}
                              {formatearUSD(
                                opcion.totalMin
                              )}
                              {" - "}
                              US${" "}
                              {formatearUSD(
                                opcion.totalMax
                              )}
                            </div>
                          </button>
                        );
                      }
                    )}
                  </div>
                </div>
              )}
            </section>


            <section className="form-section">
              <div className="section-heading">
                <span className="section-line"></span>

                <div>
                  <h3>
                    Tiempo de tránsito
                  </h3>
                </div>
              </div>


              <div className="form-grid single">
                <div className="form-group">
                  <label>
                    Margen de contingencia
                  </label>

                  <div className="input-with-unit">
                    <input
                      className={
                        errores.contingencia
                          ? "campo-error"
                          : ""
                      }
                      type="number"
                      min="0"
                      step="1"
                      value={contingencia}
                      onChange={(e) => {
                        setContingencia(
                          e.target.value
                        );

                        limpiarError(
                          "contingencia"
                        );

                        limpiarResultado();
                      }}
                    />

                    <span>
                      días
                    </span>
                  </div>
                </div>
              </div>
            </section>


            <section className="form-section">
              <div className="section-heading">
                <span className="section-line"></span>

                <div>
                  <h3>
                    Conversión monetaria
                  </h3>
                </div>
              </div>


              <div className="form-grid single">
                <div className="form-group">
                  <label>
                    Tipo de cambio

                    <span className="optional">
                      Opcional
                    </span>
                  </label>

                  <div className="input-with-unit">
                    <input
                      className={
                        errores.tipoCambio
                          ? "campo-error"
                          : ""
                      }
                      type="number"
                      min="0"
                      step="any"
                      value={tipoCambio}
                      onChange={(e) => {
                        setTipoCambio(
                          e.target.value
                        );

                        limpiarError(
                          "tipoCambio"
                        );

                        limpiarResultado();
                      }}
                      placeholder="Ej: 950"
                    />

                    <span>
                      CLP/USD
                    </span>
                  </div>
                </div>
              </div>
            </section>


            {mensaje && (
              <div className="message-box">
                <span className="message-icon">
                  !
                </span>

                <p>
                  {mensaje}
                </p>
              </div>
            )}


            <div className="form-actions">
              <span className="required-note">
                * Campos obligatorios
              </span>

              <div className="buttons-container">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={nuevaCotizacion}
                >
                  LIMPIAR
                </button>

                <button
                  type="submit"
                  className="primary-button"
                  disabled={
                    cargandoDatos ||
                    Boolean(errorDatos)
                  }
                >
                  <span>
                    COTIZAR OPERACIÓN
                  </span>

                  <span className="button-arrow">
                    →
                  </span>
                </button>
              </div>
            </div>
          </form>
        </section>


        <aside className="result-card">
          <div className="result-header">
            <span className="result-number">
              02
            </span>

            <div>
              <span className="result-eyebrow">
                RESULTADO
              </span>

              <h2>
                Cotización
              </h2>
            </div>
          </div>


          {!resultado ? (
            <div className="empty-result">
              <div className="result-symbol">
                $
              </div>

              <h3>
                Resultado de la operación
              </h3>

              <p>
                Complete los antecedentes
                para generar una
                cotización.
              </p>
            </div>
          ) : (
            <div className="result-content">
              <div className="route-summary">
                <span>
                  RUTA
                </span>

                <strong>
                  {resultado.origen}
                  {" → "}
                  {resultado.destino}
                </strong>

                <small>
                  {resultado.pais}
                  {" · "}
                  {resultado.tipoRuta}
                </small>
              </div>


              <div className="result-item">
                <span>
                  Carga total
                </span>

                <strong>
                  {formatearNumero(
                    resultado.pesoTN
                  )}{" "}
                  TN
                </strong>
              </div>


              <div className="result-item">
                <span>
                  Contenedor
                </span>

                <strong>
                  {resultado.cantidad}
                  {" × "}
                  {resultado.tipoContenedor}'
                </strong>
              </div>


              <div className="result-item vertical-result">
                <span>
                  Tarifa por contenedor
                </span>

                <strong>
                  US${" "}
                  {formatearUSD(
                    resultado.tarifaMin
                  )}
                  {" - "}
                  US${" "}
                  {formatearUSD(
                    resultado.tarifaMax
                  )}
                </strong>
              </div>


              <div className="total-result">
                <span>
                  TOTAL ESTIMADO DEL FLETE
                </span>

                <strong>
                  US${" "}
                  {formatearUSD(
                    resultado.totalMin
                  )}
                  {" - "}
                  US${" "}
                  {formatearUSD(
                    resultado.totalMax
                  )}
                </strong>
              </div>


              {resultado.tipoCambio && (
                <div className="conversion-box">
                  <span>
                    TOTAL EN CLP
                  </span>

                  <strong>
                    $
                    {formatearCLP(
                      resultado.totalMinCLP
                    )}
                    {" - $"}
                    {formatearCLP(
                      resultado.totalMaxCLP
                    )}
                  </strong>
                </div>
              )}


              {resultado.transitoOriginalMin !== null &&
              resultado.transitoOriginalMax !== null ? (
                <>
                  <div className="result-item">
                    <span>
                      Tránsito base
                    </span>

                    <strong>
                      {resultado.transitoOriginalMin}
                      {" - "}
                      {resultado.transitoOriginalMax}{" "}
                      días
                    </strong>
                  </div>

                  {resultado.contingencia > 0 && (
                    <div className="contingency-info">
                      + {resultado.contingencia} días
                    </div>
                  )}

                  <div className="result-item">
                    <span>
                      Tránsito estimado
                    </span>

                    <strong>
                      {resultado.transitoMin}
                      {" - "}
                      {resultado.transitoMax}{" "}
                      días
                    </strong>
                  </div>
                </>
              ) : (
                <div className="result-item">
                  <span>
                    Tránsito
                  </span>

                  <strong>
                    Sin información disponible
                  </strong>
                </div>
              )}


              <div className="result-item source-item">
                <span>
                  Fuente
                </span>

                <strong>
                  {resultado.fuente ||
                    "Sin referencia registrada"}
                </strong>
              </div>


              <button
                type="button"
                className="new-quote-button"
                onClick={nuevaCotizacion}
              >
                NUEVA COTIZACIÓN
              </button>
            </div>
          )}


          <div className="result-footer">
            <span></span>

            Información referencial para
            la operación logística
          </div>
        </aside>
      </main>


      <footer className="footer">
        <div className="footer-inner">
          <div className="footer-logo">
            CINTAC
          </div>

          <div className="footer-copy">
            Cotizador Logístico · Comercio
            Exterior
          </div>
        </div>
      </footer>
    </div>
  );
}


export default App;