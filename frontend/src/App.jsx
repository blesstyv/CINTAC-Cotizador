import { useState } from "react";
import { tarifas } from "./data/tarifas";
import heroImage from "./assets/hero-cintac.jpg";
import "./App.css";

function App() {
  const [origen, setOrigen] = useState("");
  const [destino, setDestino] = useState("");
  const [tipoContenedor, setTipoContenedor] = useState("");
  const [cantidad, setCantidad] = useState("");
  const [contingencia, setContingencia] = useState("0");

  const [pesoCarga, setPesoCarga] = useState("");
  const [unidadPeso, setUnidadPeso] = useState("kg");
  const [tipoCambio, setTipoCambio] = useState("");

  const [mensaje, setMensaje] = useState("");
  const [resultado, setResultado] = useState(null);

  const [errores, setErrores] = useState({
    origen: false,
    destino: false,
    tipoContenedor: false,
    cantidad: false,
    contingencia: false,
    pesoCarga: false,
    tipoCambio: false,
  });

  const puertosOrigen = [
    ...new Set(tarifas.map((ruta) => ruta.origen)),
  ];

  const puertosDestino = origen
    ? [
        ...new Set(
          tarifas
            .filter((ruta) => ruta.origen === origen)
            .map((ruta) => ruta.destino)
        ),
      ]
    : [];

  const formatearUSD = (valor) =>
    new Intl.NumberFormat("es-CL", {
      maximumFractionDigits: 0,
    }).format(valor);

  const formatearCLP = (valor) =>
    new Intl.NumberFormat("es-CL", {
      maximumFractionDigits: 0,
    }).format(valor);

  const formatearNumero = (valor) =>
    new Intl.NumberFormat("es-CL", {
      maximumFractionDigits: 2,
    }).format(valor);

  const limpiarResultado = () => {
    setResultado(null);
    setMensaje("");
  };

  const limpiarError = (campo) => {
    setErrores((actuales) => ({
      ...actuales,
      [campo]: false,
    }));
  };

  const nuevaCotizacion = () => {
    setOrigen("");
    setDestino("");
    setTipoContenedor("");
    setCantidad("");
    setContingencia("0");
    setPesoCarga("");
    setUnidadPeso("kg");
    setTipoCambio("");
    setMensaje("");
    setResultado(null);

    setErrores({
      origen: false,
      destino: false,
      tipoContenedor: false,
      cantidad: false,
      contingencia: false,
      pesoCarga: false,
      tipoCambio: false,
    });

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  const cotizar = (e) => {
    e.preventDefault();

    setMensaje("");
    setResultado(null);

    const nuevosErrores = {
      origen: !origen,
      destino: !destino,
      tipoContenedor: !tipoContenedor,
      cantidad: !cantidad,
      contingencia: false,
      pesoCarga: false,
      tipoCambio: false,
    };

    setErrores(nuevosErrores);

    if (
      nuevosErrores.origen ||
      nuevosErrores.destino ||
      nuevosErrores.tipoContenedor ||
      nuevosErrores.cantidad
    ) {
      setMensaje(
        "Debe completar todos los datos obligatorios antes de realizar la cotización."
      );
      return;
    }

    const cantidadNumero = Number(cantidad);
    const contingenciaNumero = Number(contingencia) || 0;

    if (
      !Number.isInteger(cantidadNumero) ||
      cantidadNumero <= 0
    ) {
      setErrores((actuales) => ({
        ...actuales,
        cantidad: true,
      }));

      setMensaje(
        "La cantidad de contenedores debe ser un número entero mayor que cero."
      );
      return;
    }

    if (
      !Number.isInteger(contingenciaNumero) ||
      contingenciaNumero < 0
    ) {
      setErrores((actuales) => ({
        ...actuales,
        contingencia: true,
      }));

      setMensaje(
        "El margen de contingencia debe ser un número entero igual o mayor que cero."
      );
      return;
    }

    let pesoNumero = null;

    if (pesoCarga !== "") {
      pesoNumero = Number(pesoCarga);

      if (!Number.isFinite(pesoNumero) || pesoNumero <= 0) {
        setErrores((actuales) => ({
          ...actuales,
          pesoCarga: true,
        }));

        setMensaje(
          "El peso de la carga debe ser un valor mayor que cero."
        );
        return;
      }
    }

    let tipoCambioNumero = null;

    if (tipoCambio !== "") {
      tipoCambioNumero = Number(tipoCambio);

      if (
        !Number.isFinite(tipoCambioNumero) ||
        tipoCambioNumero <= 0
      ) {
        setErrores((actuales) => ({
          ...actuales,
          tipoCambio: true,
        }));

        setMensaje(
          "El tipo de cambio debe ser un valor mayor que cero."
        );
        return;
      }
    }

    const ruta = tarifas.find(
      (item) =>
        item.origen === origen &&
        item.destino === destino
    );

    if (!ruta) {
      setMensaje(
        "No existe información disponible para la ruta seleccionada."
      );
      return;
    }

    let tarifaMin;
    let tarifaMax;

    if (tipoContenedor === "20") {
      tarifaMin = ruta.tarifa20Min;
      tarifaMax = ruta.tarifa20Max;
    } else {
      tarifaMin = ruta.tarifa40Min;
      tarifaMax = ruta.tarifa40Max;
    }

    const totalMin = tarifaMin * cantidadNumero;
    const totalMax = tarifaMax * cantidadNumero;

    const transitoMin =
      ruta.transitoMin + contingenciaNumero;

    const transitoMax =
      ruta.transitoMax + contingenciaNumero;

    let pesoKg = null;
    let pesoTN = null;

    if (pesoNumero !== null) {
      if (unidadPeso === "kg") {
        pesoKg = pesoNumero;
        pesoTN = pesoNumero / 1000;
      } else {
        pesoTN = pesoNumero;
        pesoKg = pesoNumero * 1000;
      }
    }

    const capacidadReferenciaTN =
      cantidadNumero * 25;

    const superaReferencia =
      pesoTN !== null &&
      pesoTN > capacidadReferenciaTN;

    const totalMinCLP =
      tipoCambioNumero !== null
        ? totalMin * tipoCambioNumero
        : null;

    const totalMaxCLP =
      tipoCambioNumero !== null
        ? totalMax * tipoCambioNumero
        : null;

    setErrores({
      origen: false,
      destino: false,
      tipoContenedor: false,
      cantidad: false,
      contingencia: false,
      pesoCarga: false,
      tipoCambio: false,
    });

    setResultado({
      origen: ruta.origen,
      pais: ruta.pais,
      destino: ruta.destino,
      tipoRuta: ruta.tipoRuta,
      tipoContenedor,
      cantidad: cantidadNumero,
      tarifaMin,
      tarifaMax,
      totalMin,
      totalMax,
      transitoOriginalMin: ruta.transitoMin,
      transitoOriginalMax: ruta.transitoMax,
      transitoMin,
      transitoMax,
      contingencia: contingenciaNumero,
      fuente: ruta.fuente,
      pesoKg,
      pesoTN,
      capacidadReferenciaTN,
      superaReferencia,
      tipoCambio: tipoCambioNumero,
      totalMinCLP,
      totalMaxCLP,
    });
  };

  return (
    <div className="app">
      <header className="site-header">
        <div className="header-inner">
          <div className="cintac-brand">
            <div className="cintac-wordmark">
              CINTAC
              <span className="registered">®</span>
            </div>

          
          </div>

          <div className="header-context">
            <span>IMPORTACIONES</span>
            <span className="context-divider"></span>
            <span>COMERCIO EXTERIOR</span>
          </div>
        </div>
      </header>

      <section
        className="hero"
        style={{
          backgroundImage: `url(${heroImage})`,
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
            <strong>de importación</strong>
          </h1>

          <p>
            Consulta rutas, tarifas y tiempos de tránsito
            utilizando información logística de referencia.
          </p>

          <a href="#cotizador" className="hero-button">
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
            Selecciona los antecedentes de la operación
            para obtener un rango estimado del flete.
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
                Complete los antecedentes requeridos.
              </p>
            </div>
          </div>

          <form onSubmit={cotizar}>
            <section className="form-section">
              <div className="section-heading">
                <span className="section-line"></span>

                <div>
                  <h3>Ruta de importación</h3>

                  <p>
                    Seleccione el origen y destino de la operación.
                  </p>
                </div>
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label>
                    Puerto de origen
                    <span className="required">*</span>
                  </label>

                  <select
                    className={
                      errores.origen ? "campo-error" : ""
                    }
                    value={origen}
                    onChange={(e) => {
                      setOrigen(e.target.value);
                      setDestino("");

                      limpiarError("origen");
                      limpiarError("destino");
                      limpiarResultado();
                    }}
                  >
                    <option value="">
                      Seleccione puerto de origen
                    </option>

                    {puertosOrigen.map((puerto) => (
                      <option
                        key={puerto}
                        value={puerto}
                      >
                        {puerto}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>
                    Puerto de destino
                    <span className="required">*</span>
                  </label>

                  <select
                    className={
                      errores.destino ? "campo-error" : ""
                    }
                    value={destino}
                    disabled={!origen}
                    onChange={(e) => {
                      setDestino(e.target.value);
                      limpiarError("destino");
                      limpiarResultado();
                    }}
                  >
                    <option value="">
                      {origen
                        ? "Seleccione puerto de destino"
                        : "Seleccione primero el origen"}
                    </option>

                    {puertosDestino.map((puerto) => (
                      <option
                        key={puerto}
                        value={puerto}
                      >
                        {puerto}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </section>

            <section className="form-section">
              <div className="section-heading">
                <span className="section-line"></span>

                <div>
                  <h3>
                    Información del contenedor
                  </h3>

                  <p>
                    Indique el tipo y cantidad requerida.
                  </p>
                </div>
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label>
                    Tipo de contenedor
                    <span className="required">*</span>
                  </label>

                  <select
                    className={
                      errores.tipoContenedor
                        ? "campo-error"
                        : ""
                    }
                    value={tipoContenedor}
                    onChange={(e) => {
                      setTipoContenedor(e.target.value);
                      limpiarError("tipoContenedor");
                      limpiarResultado();
                    }}
                  >
                    <option value="">
                      Seleccione tipo
                    </option>

                    <option value="20">
                      Contenedor 20 pies
                    </option>

                    <option value="40">
                      Contenedor 40 pies
                    </option>
                  </select>
                </div>

                <div className="form-group">
                  <label>
                    Cantidad de contenedores
                    <span className="required">*</span>
                  </label>

                  <input
                    className={
                      errores.cantidad
                        ? "campo-error"
                        : ""
                    }
                    type="number"
                    min="1"
                    step="1"
                    value={cantidad}
                    onChange={(e) => {
                      setCantidad(e.target.value);
                      limpiarError("cantidad");
                      limpiarResultado();
                    }}
                    placeholder="Ej: 1"
                  />
                </div>
              </div>
            </section>

            <section className="form-section">
              <div className="section-heading">
                <span className="section-line"></span>

                <div>
                  <h3>Tiempo de tránsito</h3>

                  <p>
                    Puede incorporar días adicionales
                    de contingencia.
                  </p>
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
                        setContingencia(e.target.value);
                        limpiarError("contingencia");
                        limpiarResultado();
                      }}
                    />

                    <span>días</span>
                  </div>

                  <small>
                    Modifica únicamente la estimación
                    temporal y no el costo del flete.
                  </small>
                </div>
              </div>
            </section>

            <section className="form-section">
              <div className="section-heading">
                <span className="section-line"></span>

                <div>
                  <h3>
                    Carga y conversiones
                  </h3>

                  <p>
                    Información complementaria para la operación.
                  </p>
                </div>
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label>
                    Peso total de la carga
                    <span className="optional">
                      Opcional
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
                        setPesoCarga(e.target.value);
                        limpiarError("pesoCarga");
                        limpiarResultado();
                      }}
                      placeholder="Ej: 18000"
                    />

                    <select
                      value={unidadPeso}
                      onChange={(e) => {
                        setUnidadPeso(e.target.value);
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

                  <small>
                    Conversión automática entre kg y TN.
                  </small>
                </div>

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
                        setTipoCambio(e.target.value);
                        limpiarError("tipoCambio");
                        limpiarResultado();
                      }}
                      placeholder="Ej: 950"
                    />

                    <span>CLP/USD</span>
                  </div>

                  <small>
                    Utilice el tipo de cambio definido
                    para la operación.
                  </small>
                </div>
              </div>
            </section>

            {mensaje && (
              <div className="message-box">
                <span className="message-icon">
                  !
                </span>

                <p>{mensaje}</p>
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

              <h2>Cotización</h2>
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
                para generar una cotización.
              </p>
            </div>
          ) : (
            <div className="result-content">
              <div className="route-summary">
                <span>RUTA</span>

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
                <span>Contenedor</span>

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
                  US$ {formatearUSD(resultado.tarifaMin)}
                  {" - "}
                  US$ {formatearUSD(resultado.tarifaMax)}
                </strong>
              </div>

              <div className="total-result">
                <span>
                  TOTAL ESTIMADO DEL FLETE
                </span>

                <strong>
                  US$ {formatearUSD(resultado.totalMin)}
                  {" - "}
                  US$ {formatearUSD(resultado.totalMax)}
                </strong>

                <small>
                  Para {resultado.cantidad} contenedor
                  {resultado.cantidad !== 1 ? "es" : ""}
                </small>
              </div>

              {resultado.tipoCambio && (
                <div className="conversion-box">
                  <span>CONVERSIÓN A CLP</span>

                  <strong>
                    ${formatearCLP(resultado.totalMinCLP)}
                    {" - $"}
                    {formatearCLP(resultado.totalMaxCLP)}
                  </strong>

                  <small>
                    Tipo de cambio: $
                    {formatearCLP(resultado.tipoCambio)} CLP/USD
                  </small>
                </div>
              )}

              <div className="result-item">
                <span>Tránsito base</span>

                <strong>
                  {resultado.transitoOriginalMin}
                  {" - "}
                  {resultado.transitoOriginalMax} días
                </strong>
              </div>

              {resultado.contingencia > 0 && (
                <div className="contingency-info">
                  + {resultado.contingencia} días de contingencia
                </div>
              )}

              <div className="result-item">
                <span>
                  Tránsito estimado
                </span>

                <strong>
                  {resultado.transitoMin}
                  {" - "}
                  {resultado.transitoMax} días
                </strong>
              </div>

              <div className="capacity-box">
                <span>
                  REFERENCIA DE CAPACIDAD
                </span>

                <strong>
                  {resultado.capacidadReferenciaTN} TN
                </strong>

                <small>
                  {resultado.cantidad} × 25 TN por contenedor
                </small>
              </div>

              {resultado.pesoTN !== null && (
                <>
                  <div className="result-item">
                    <span>Peso en kg</span>

                    <strong>
                      {formatearNumero(resultado.pesoKg)} kg
                    </strong>
                  </div>

                  <div className="result-item">
                    <span>Peso en TN</span>

                    <strong>
                      {formatearNumero(resultado.pesoTN)} TN
                    </strong>
                  </div>

                  {resultado.superaReferencia && (
                    <div className="warning-box">
                      El peso informado supera la referencia
                      de 25 TN por contenedor.
                    </div>
                  )}
                </>
              )}

              <div className="result-item source-item">
                <span>
                  Fuente / referencia
                </span>

                <strong>
                  {resultado.fuente}
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
            Información referencial para la operación logística
          </div>
        </aside>
      </main>

      <footer className="footer">
        <div className="footer-inner">
          <div className="footer-logo">
            CINTAC
          </div>

          <div className="footer-copy">
            Cotizador Logístico · Comercio Exterior
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;