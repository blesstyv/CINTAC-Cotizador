import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import heroImage
  from "./assets/hero-cintac.jpg";

import AdminDatos
  from "./AdminDatos";

import HistorialCotizaciones
  from "./HistorialCotizaciones";

import "./App.css";
import "./Login.css";


const API_BASE_URL =
  import.meta.env.VITE_API_URL;

if (!API_BASE_URL) {
  throw new Error(
    "No se configuró VITE_API_URL."
  );
}

const API_URL =
  `${API_BASE_URL.replace(
    /\/$/,
    ""
  )}/api`;

const TOKEN_KEY =
  "cintac_token";

const USER_KEY =
  "cintac_usuario";

const MENSAJE_SERVIDOR_NO_DISPONIBLE =
  "No fue posible conectar con el servidor. Verifique la conexión e intente nuevamente.";


function recopilarMensajes(valor) {
  if (
    valor === null ||
    valor === undefined
  ) {
    return [];
  }

  if (
    typeof valor === "string"
  ) {
    return [valor];
  }

  if (
    Array.isArray(valor)
  ) {
    return valor.flatMap(
      recopilarMensajes
    );
  }

  if (
    typeof valor === "object"
  ) {
    return Object.values(
      valor
    ).flatMap(
      recopilarMensajes
    );
  }

  return [
    String(valor),
  ];
}


function extraerMensajeError(
  datos,
  mensajePredeterminado,
) {
  if (!datos) {
    return mensajePredeterminado;
  }

  if (datos.detail) {
    const mensajes =
      recopilarMensajes(
        datos.detail
      );

    if (
      mensajes.length > 0
    ) {
      return mensajes.join(" ");
    }
  }

  const mensajes =
    recopilarMensajes(
      datos
    );

  return (
    mensajes.join(" ") ||
    mensajePredeterminado
  );
}


function obtenerMensajeError(
  error,
  mensajePredeterminado,
) {
  if (
    error instanceof TypeError ||
    error?.message ===
      "Failed to fetch"
  ) {
    return (
      MENSAJE_SERVIDOR_NO_DISPONIBLE
    );
  }

  return (
    error?.message ||
    mensajePredeterminado
  );
}


function cargarUsuarioGuardado() {
  try {
    const contenido =
      sessionStorage.getItem(
        USER_KEY
      );

    if (!contenido) {
      return null;
    }

    return JSON.parse(
      contenido
    );

  } catch {
    sessionStorage.removeItem(
      USER_KEY
    );

    return null;
  }
}


function guardarUsuario(usuario) {
  if (!usuario) {
    return;
  }

  sessionStorage.setItem(
    USER_KEY,
    JSON.stringify(
      usuario
    )
  );
}


function obtenerNombreRol(usuario) {
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
}


// Convierte el valor de carga escrito por el usuario a un
// número canónico ("1250000.50") para enviarlo a la API.
// - CLP: formato chileno, punto para miles y coma decimal
//   (300.000 · 1.250.000,50 · 300000). Máximo 12 dígitos
//   enteros y 2 decimales.
// - USD: punto o coma como separador decimal (350.50 ·
//   350,50). Máximo 10 dígitos enteros y 2 decimales.
// Devuelve null si el texto no es válido.
const MAX_DIGITOS_VALOR_CARGA = {
  USD: 10,
  CLP: 12,
};

function normalizarValorCarga(
  texto,
  moneda
) {
  const limpio =
    String(texto)
      .trim()
      .replace(/\s/g, "")
      .replace(/^\$/, "");

  if (limpio === "") {
    return "0";
  }

  let entero;
  let decimales = "";

  if (moneda === "CLP") {
    const coincidencia =
      limpio.match(
        /^(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?$/
      );

    if (!coincidencia) {
      return null;
    }

    entero =
      coincidencia[1].replace(/\./g, "");

    decimales =
      coincidencia[2] || "";

  } else {
    const coincidencia =
      limpio.match(
        /^(\d+)(?:[.,](\d{1,2}))?$/
      );

    if (!coincidencia) {
      return null;
    }

    entero =
      coincidencia[1];

    decimales =
      coincidencia[2] || "";
  }

  entero =
    entero.replace(/^0+(?=\d)/, "");

  if (
    entero.length >
    MAX_DIGITOS_VALOR_CARGA[moneda]
  ) {
    return null;
  }

  return decimales
    ? `${entero}.${decimales}`
    : entero;
}


function App() {
  const [
    token,
    setToken,
  ] = useState(
    () =>
      sessionStorage.getItem(
        TOKEN_KEY
      ) || ""
  );

  const [
    usuario,
    setUsuario,
  ] = useState(
    () =>
      cargarUsuarioGuardado()
  );

  const [
    verificandoSesion,
    setVerificandoSesion,
  ] = useState(
    Boolean(token)
  );

  const [
    reintentoSesion,
    setReintentoSesion,
  ] = useState(0);

  const [
    errorSesion,
    setErrorSesion,
  ] = useState("");

  const [
    loginUsuario,
    setLoginUsuario,
  ] = useState("");

  const [
    loginPassword,
    setLoginPassword,
  ] = useState("");

  const [
    loginError,
    setLoginError,
  ] = useState("");

  const [
    iniciandoSesion,
    setIniciandoSesion,
  ] = useState(false);

  const [
    vistaActiva,
    setVistaActiva,
  ] = useState(
    "cotizador"
  );

  const [
    versionDatos,
    setVersionDatos,
  ] = useState(0);

  const [
    rutas,
    setRutas,
  ] = useState([]);

  const [
    origen,
    setOrigen,
  ] = useState("");

  const [
    destino,
    setDestino,
  ] = useState("");

  const [
    tipoContenedor,
    setTipoContenedor,
  ] = useState("");

  const [
    pesoCarga,
    setPesoCarga,
  ] = useState("");

  const [
    unidadPeso,
    setUnidadPeso,
  ] = useState("kg");

  const [
    contingencia,
    setContingencia,
  ] = useState("0");

  const [
    valorCarga,
    setValorCarga,
  ] = useState("");

  const [
    monedaValorCarga,
    setMonedaValorCarga,
  ] = useState("USD");

  const [
    recomendacion,
    setRecomendacion,
  ] = useState(null);

  const [
    cargandoDatos,
    setCargandoDatos,
  ] = useState(false);

  const [
    cargandoOpciones,
    setCargandoOpciones,
  ] = useState(false);

  const [
    cotizando,
    setCotizando,
  ] = useState(false);

  const [
    errorDatos,
    setErrorDatos,
  ] = useState("");

  const [
    mensaje,
    setMensaje,
  ] = useState("");

  const [
    resultado,
    setResultado,
  ] = useState(null);

  const [
    errores,
    setErrores,
  ] = useState({
    origen: false,
    destino: false,
    pesoCarga: false,
    contingencia: false,
    valorCarga: false,
  });


  const usuarioId =
    usuario?.id ?? null;

  const loginEnCursoRef =
    useRef(false);

  const cotizacionEnCursoRef =
    useRef(false);

  const claveOpcionesRef =
    useRef("");


  const formatearUSD =
    (valor) =>
      new Intl.NumberFormat(
        "es-CL",
        {
          maximumFractionDigits:
            0,
        }
      ).format(
        Number(valor)
      );


  // Muestra decimales sólo cuando el monto tiene centavos
  // (por ejemplo, un valor de carga de 350,50 USD).
  const formatearMontoUSD =
    (valor) => {
      const numero =
        Number(valor);

      const tieneCentavos =
        Math.round(
          numero * 100
        ) % 100 !== 0;

      return new Intl.NumberFormat(
        "es-CL",
        {
          minimumFractionDigits:
            tieneCentavos ? 2 : 0,

          maximumFractionDigits:
            tieneCentavos ? 2 : 0,
        }
      ).format(
        numero
      );
    };


  const formatearMontoCLP =
    (valor) =>
      new Intl.NumberFormat(
        "es-CL",
        {
          maximumFractionDigits:
            2,
        }
      ).format(
        Number(valor)
      );


  const formatearCLP =
    (valor) =>
      new Intl.NumberFormat(
        "es-CL",
        {
          maximumFractionDigits:
            0,
        }
      ).format(
        Number(valor)
      );


  const formatearNumero =
    (valor) =>
      new Intl.NumberFormat(
        "es-CL",
        {
          maximumFractionDigits:
            3,
        }
      ).format(
        Number(valor)
      );


  const formatearTipoCambio =
    (valor) =>
      new Intl.NumberFormat(
        "es-CL",
        {
          minimumFractionDigits:
            2,

          maximumFractionDigits:
            2,
        }
      ).format(
        Number(valor)
      );


  const formatearFecha =
    (fecha) => {
      if (!fecha) {
        return "Sin fecha";
      }

      const partes =
        fecha.split("-");

      if (
        partes.length !== 3
      ) {
        return fecha;
      }

      return (
        `${partes[2]}-` +
        `${partes[1]}-` +
        `${partes[0]}`
      );
    };


  const limpiarSesion =
    useCallback(
      () => {
        sessionStorage.removeItem(
          TOKEN_KEY
        );

        sessionStorage.removeItem(
          USER_KEY
        );

        setToken("");
        setUsuario(null);
        setVerificandoSesion(false);
        setErrorSesion("");
        setVistaActiva("cotizador");

        setRutas([]);
        setOrigen("");
        setDestino("");
        setTipoContenedor("");
        setPesoCarga("");
        setUnidadPeso("kg");
        setContingencia("0");
        setValorCarga("");
        setMonedaValorCarga("USD");
        setRecomendacion(null);
        setResultado(null);
        setMensaje("");
        setErrorDatos("");
        setCargandoDatos(false);
        setCargandoOpciones(false);
        setCotizando(false);

        claveOpcionesRef.current =
          "";

        setErrores({
          origen: false,
          destino: false,
          pesoCarga: false,
          contingencia: false,
          valorCarga: false,
        });
      },
      []
    );


  const peticionAutenticada =
    useCallback(
      async (
        url,
        opciones = {}
      ) => {
        try {
          const respuesta =
            await fetch(
              url,
              {
                ...opciones,

                headers: {
                  ...opciones.headers,

                  Authorization:
                    `Token ${token}`,
                },
              }
            );

          if (
            respuesta.status ===
            401
          ) {
            limpiarSesion();

            throw new Error(
              "La sesión expiró o ya no es válida."
            );
          }

          return respuesta;

        } catch (error) {
          if (
            error?.name ===
            "AbortError"
          ) {
            throw error;
          }

          if (
            error instanceof
              TypeError ||
            error?.message ===
              "Failed to fetch"
          ) {
            throw new Error(
              MENSAJE_SERVIDOR_NO_DISPONIBLE
            );
          }

          throw error;
        }
      },
      [
        token,
        limpiarSesion,
      ]
    );


  useEffect(
    () => {
      if (!token) {
        return undefined;
      }

      let activo = true;

      const temporizador =
        window.setTimeout(
          () => {
            const verificarSesion =
              async () => {
                setVerificandoSesion(
                  true
                );

                try {
                  const respuesta =
                    await fetch(
                      `${API_URL}/sesion/`,
                      {
                        headers: {
                          Authorization:
                            `Token ${token}`,
                        },
                      }
                    );

                  if (
                    respuesta.status ===
                      401 ||
                    respuesta.status ===
                      403
                  ) {
                    if (activo) {
                      limpiarSesion();
                    }

                    return;
                  }

                  if (!respuesta.ok) {
                    throw new Error(
                      "No fue posible validar la sesión."
                    );
                  }

                  const datos =
                    await respuesta.json();

                  if (!activo) {
                    return;
                  }

                  setUsuario(datos);

                  guardarUsuario(
                    datos
                  );

                  setErrorSesion("");
                  setErrorDatos("");

                } catch (error) {
                  if (!activo) {
                    return;
                  }

                  const texto =
                    obtenerMensajeError(
                      error,
                      "No fue posible validar la sesión."
                    );

                  setErrorSesion(
                    texto
                  );

                  setErrorDatos(
                    texto
                  );

                } finally {
                  if (activo) {
                    setVerificandoSesion(
                      false
                    );
                  }
                }
              };

            void verificarSesion();
          },
          0
        );

      return () => {
        activo = false;

        window.clearTimeout(
          temporizador
        );
      };
    },
    [
      token,
      limpiarSesion,
      reintentoSesion,
    ]
  );


  useEffect(
    () => {
      if (
        !token ||
        !usuarioId
      ) {
        return undefined;
      }

      const actualizarPermisos =
        async () => {
          try {
            const respuesta =
              await fetch(
                `${API_URL}/sesion/`,
                {
                  headers: {
                    Authorization:
                      `Token ${token}`,
                  },
                }
              );

            if (
              respuesta.status ===
                401 ||
              respuesta.status ===
                403
            ) {
              limpiarSesion();
              return;
            }

            if (!respuesta.ok) {
              return;
            }

            const datos =
              await respuesta.json();

            setUsuario(datos);
            guardarUsuario(datos);

            setErrorSesion("");
            setErrorDatos("");

            setVistaActiva(
              (vistaActual) => {
                if (
                  vistaActual ===
                    "administracion" &&
                  !datos
                    .puedeGestionarDatos
                ) {
                  return "cotizador";
                }

                return vistaActual;
              }
            );

            setVersionDatos(
              (actual) =>
                actual + 1
            );

          } catch (error) {
            const texto =
              obtenerMensajeError(
                error,
                MENSAJE_SERVIDOR_NO_DISPONIBLE
              );

            setErrorSesion(
              texto
            );

            setErrorDatos(
              texto
            );
          }
        };


      const manejarFoco =
        () => {
          void actualizarPermisos();
        };


      window.addEventListener(
        "focus",
        manejarFoco
      );

      return () => {
        window.removeEventListener(
          "focus",
          manejarFoco
        );
      };
    },
    [
      token,
      usuarioId,
      limpiarSesion,
    ]
  );


  const iniciarSesion =
    async (
      event
    ) => {
      event.preventDefault();

      if (
        loginEnCursoRef.current ||
        iniciandoSesion
      ) {
        return;
      }

      setLoginError("");

      if (
        !loginUsuario.trim() ||
        !loginPassword
      ) {
        setLoginError(
          "Ingrese usuario y contraseña."
        );

        return;
      }

      loginEnCursoRef.current =
        true;

      setIniciandoSesion(true);

      try {
        const respuesta =
          await fetch(
            `${API_URL}/login/`,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body:
                JSON.stringify({
                  username:
                    loginUsuario.trim(),

                  password:
                    loginPassword,
                }),
            }
          );

        let datos = null;

        try {
          datos =
            await respuesta.json();

        } catch {
          datos = null;
        }

        if (!respuesta.ok) {
          throw new Error(
            extraerMensajeError(
              datos,
              "No fue posible iniciar sesión."
            )
          );
        }

        sessionStorage.setItem(
          TOKEN_KEY,
          datos.token
        );

        guardarUsuario(
          datos.usuario
        );

        setToken(
          datos.token
        );

        setUsuario(
          datos.usuario
        );

        setVistaActiva(
          "cotizador"
        );

        setLoginUsuario("");
        setLoginPassword("");
        setLoginError("");
        setErrorSesion("");
        setErrorDatos("");

      } catch (error) {
        setLoginError(
          obtenerMensajeError(
            error,
            "No fue posible iniciar sesión."
          )
        );

      } finally {
        loginEnCursoRef.current =
          false;

        setIniciandoSesion(false);
      }
    };


  const cerrarSesion =
    async () => {
      if (token) {
        try {
          await fetch(
            `${API_URL}/logout/`,
            {
              method: "POST",

              headers: {
                Authorization:
                  `Token ${token}`,
              },
            }
          );

        } catch {
          /*
           * Aunque el servidor no responda,
           * la sesión local puede cerrarse.
           */
        }
      }

      limpiarSesion();
    };


  useEffect(
    () => {
      if (
        !token ||
        !usuarioId
      ) {
        return undefined;
      }

      let activo = true;

      const temporizador =
        window.setTimeout(
          () => {
            const cargarRutas =
              async () => {
                setCargandoDatos(
                  true
                );

                try {
                  const respuesta =
                    await peticionAutenticada(
                      `${API_URL}/rutas/`
                    );

                  let datos = null;

                  try {
                    datos =
                      await respuesta.json();

                  } catch {
                    datos = null;
                  }

                  if (!respuesta.ok) {
                    throw new Error(
                      extraerMensajeError(
                        datos,
                        "No fue posible cargar la información del cotizador."
                      )
                    );
                  }

                  if (!activo) {
                    return;
                  }

                  setRutas(datos);
                  setErrorDatos("");

                } catch (error) {
                  if (
                    activo &&
                    token
                  ) {
                    setErrorDatos(
                      obtenerMensajeError(
                        error,
                        "No fue posible cargar la información del cotizador."
                      )
                    );
                  }

                } finally {
                  if (activo) {
                    setCargandoDatos(
                      false
                    );
                  }
                }
              };

            void cargarRutas();
          },
          0
        );

      return () => {
        activo = false;

        window.clearTimeout(
          temporizador
        );
      };
    },
    [
      token,
      usuarioId,
      versionDatos,
      peticionAutenticada,
    ]
  );


  const puertosOrigen =
    useMemo(
      () => [
        ...new Set(
          rutas.map(
            (ruta) =>
              ruta.origen
          )
        ),
      ],
      [
        rutas,
      ]
    );


  const puertosDestino =
    useMemo(
      () => {
        if (!origen) {
          return [];
        }

        return [
          ...new Set(
            rutas
              .filter(
                (ruta) =>
                  ruta.origen ===
                  origen
              )
              .map(
                (ruta) =>
                  ruta.destino
              )
          ),
        ];
      },
      [
        rutas,
        origen,
      ]
    );


  const rutaSeleccionada =
    useMemo(
      () => {
        if (
          !origen ||
          !destino
        ) {
          return null;
        }

        return (
          rutas.find(
            (ruta) =>
              ruta.origen ===
                origen &&
              ruta.destino ===
                destino
          ) || null
        );
      },
      [
        rutas,
        origen,
        destino,
      ]
    );


  useEffect(
    () => {
      if (
        !token ||
        !rutaSeleccionada ||
        pesoCarga === ""
      ) {
        return undefined;
      }

      const pesoNumero =
        Number(
          pesoCarga
        );

      if (
        !Number.isFinite(
          pesoNumero
        ) ||
        pesoNumero <= 0
      ) {
        return undefined;
      }

      const claveSolicitud =
        [
          versionDatos,
          rutaSeleccionada.id,
          pesoCarga,
          unidadPeso,
        ].join("|");

      if (
        claveOpcionesRef.current ===
        claveSolicitud
      ) {
        return undefined;
      }

      const controlador =
        new AbortController();

      const temporizador =
        window.setTimeout(
          () => {
            const cargarOpciones =
              async () => {
                claveOpcionesRef.current =
                  claveSolicitud;

                setCargandoOpciones(
                  true
                );

                try {
                  const respuesta =
                    await peticionAutenticada(
                      `${API_URL}/opciones-contenedores/`,
                      {
                        method:
                          "POST",

                        headers: {
                          "Content-Type":
                            "application/json",
                        },

                        body:
                          JSON.stringify({
                            ruta_id:
                              rutaSeleccionada.id,

                            peso_carga:
                              pesoCarga,

                            unidad_peso:
                              unidadPeso,
                          }),

                        signal:
                          controlador.signal,
                      }
                    );

                  const datos =
                    await respuesta.json();

                  if (!respuesta.ok) {
                    throw new Error(
                      extraerMensajeError(
                        datos,
                        "No fue posible obtener las opciones de contenedor."
                      )
                    );
                  }

                  if (
                    controlador.signal.aborted
                  ) {
                    return;
                  }

                  setRecomendacion(
                    datos
                  );

                  setTipoContenedor(
                    datos.sugerida
                  );

                  setMensaje("");
                  setErrorDatos("");

                } catch (error) {
                  if (
                    error?.name !==
                    "AbortError"
                  ) {
                    if (
                      claveOpcionesRef.current ===
                      claveSolicitud
                    ) {
                      claveOpcionesRef.current =
                        "";
                    }

                    setMensaje(
                      obtenerMensajeError(
                        error,
                        "No fue posible obtener las opciones de contenedor."
                      )
                    );
                  }

                } finally {
                  if (
                    !controlador.signal.aborted
                  ) {
                    setCargandoOpciones(
                      false
                    );
                  }
                }
              };

            void cargarOpciones();
          },
          450
        );

      return () => {
        window.clearTimeout(
          temporizador
        );

        controlador.abort();
      };
    },
    [
      token,
      rutaSeleccionada,
      pesoCarga,
      unidadPeso,
      versionDatos,
      peticionAutenticada,
    ]
  );


  const reiniciarOpcionesContenedor =
    () => {
      claveOpcionesRef.current =
        "";

      setRecomendacion(null);
      setTipoContenedor("");
      setResultado(null);
      setMensaje("");
      setCargandoOpciones(false);
    };


  const limpiarResultado =
    () => {
      setResultado(null);
      setMensaje("");
    };


  const limpiarError =
    (campo) => {
      setErrores(
        (actuales) => ({
          ...actuales,

          [campo]:
            false,
        })
      );
    };


  const nuevaCotizacion =
    () => {
      setOrigen("");
      setDestino("");
      setTipoContenedor("");
      setPesoCarga("");
      setUnidadPeso("kg");
      setContingencia("0");
      setValorCarga("");
      setMonedaValorCarga("USD");
      setRecomendacion(null);
      setMensaje("");
      setResultado(null);

      claveOpcionesRef.current =
        "";

      setErrores({
        origen: false,
        destino: false,
        pesoCarga: false,
        contingencia: false,
        valorCarga: false,
      });

      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    };


  const abrirAdministracion =
    async () => {
      setMensaje("");

      try {
        const respuesta =
          await peticionAutenticada(
            `${API_URL}/sesion/`
          );

        const datos =
          await respuesta.json();

        if (!respuesta.ok) {
          throw new Error(
            extraerMensajeError(
              datos,
              "No fue posible comprobar los permisos del usuario."
            )
          );
        }

        setUsuario(datos);

        guardarUsuario(
          datos
        );

        if (
          !datos
            .puedeGestionarDatos
        ) {
          setVistaActiva(
            "cotizador"
          );

          setMensaje(
            "El usuario no tiene permiso para acceder a Administración."
          );

          return;
        }

        setVistaActiva(
          "administracion"
        );

      } catch (error) {
        setMensaje(
          obtenerMensajeError(
            error,
            "No fue posible acceder a Administración."
          )
        );
      }
    };


  const abrirHistorial =
    () => {
      setVistaActiva(
        "historial"
      );
    };


  const manejarPermisoRevocado =
    useCallback(
      async () => {
        try {
          const respuesta =
            await peticionAutenticada(
              `${API_URL}/sesion/`
            );

          if (respuesta.ok) {
            const datos =
              await respuesta.json();

            setUsuario(datos);

            guardarUsuario(
              datos
            );
          }

        } catch {
          /*
           * Se conserva la sesión si
           * solamente falla la conexión.
           */

        } finally {
          setVistaActiva(
            "cotizador"
          );
        }
      },
      [
        peticionAutenticada,
      ]
    );


  const cotizar =
    async (
      event
    ) => {
      event.preventDefault();

      if (
        cotizacionEnCursoRef.current ||
        cotizando
      ) {
        return;
      }

      setMensaje("");
      setResultado(null);

      const nuevosErrores = {
        origen:
          !origen,

        destino:
          !destino,

        pesoCarga:
          !pesoCarga,

        contingencia:
          false,

        valorCarga:
          false,
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

      if (!rutaSeleccionada) {
        setMensaje(
          "No existe información para la ruta seleccionada."
        );

        return;
      }

      const pesoNumero =
        Number(
          pesoCarga
        );

      if (
        !Number.isFinite(
          pesoNumero
        ) ||
        pesoNumero <= 0
      ) {
        setErrores(
          (actuales) => ({
            ...actuales,

            pesoCarga:
              true,
          })
        );

        setMensaje(
          "El peso total debe ser mayor que cero."
        );

        return;
      }

      if (
        !recomendacion ||
        !tipoContenedor
      ) {
        setMensaje(
          "Seleccione una opción de contenedor."
        );

        return;
      }

      const contingenciaNumero =
        Number(
          contingencia
        );

      if (
        !Number.isInteger(
          contingenciaNumero
        ) ||
        contingenciaNumero < 0
      ) {
        setErrores(
          (actuales) => ({
            ...actuales,

            contingencia:
              true,
          })
        );

        setMensaje(
          "El margen de contingencia debe ser un número entero igual o mayor que cero."
        );

        return;
      }

      // Valor de carga opcional: vacío equivale a 0.
      const valorCargaNormalizado =
        normalizarValorCarga(
          valorCarga,
          monedaValorCarga
        );

      if (
        valorCargaNormalizado === null
      ) {
        setErrores(
          (actuales) => ({
            ...actuales,

            valorCarga:
              true,
          })
        );

        setMensaje(
          monedaValorCarga === "CLP"
            ? "El valor de carga en CLP debe ser un monto válido (por ejemplo 300.000 o 1.250.000,50), sin negativos y con máximo dos decimales."
            : "El valor de carga en USD debe ser un número igual o mayor que cero, con máximo dos decimales."
        );

        return;
      }

      cotizacionEnCursoRef.current =
        true;

      setCotizando(true);

      try {
        const respuesta =
          await peticionAutenticada(
            `${API_URL}/cotizar/`,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body:
                JSON.stringify({
                  ruta_id:
                    rutaSeleccionada.id,

                  peso_carga:
                    pesoCarga,

                  unidad_peso:
                    unidadPeso,

                  tipo_contenedor:
                    tipoContenedor,

                  contingencia:
                    contingenciaNumero,

                  valor_carga:
                    valorCargaNormalizado,

                  moneda_valor_carga:
                    monedaValorCarga,
                }),
            }
          );

        const datos =
          await respuesta.json();

        if (!respuesta.ok) {
          throw new Error(
            extraerMensajeError(
              datos,
              "No fue posible generar la cotización."
            )
          );
        }

        setResultado(datos);
        setMensaje("");
        setErrorDatos("");

        setErrores({
          origen: false,
          destino: false,
          pesoCarga: false,
          contingencia: false,
          valorCarga: false,
        });

      } catch (error) {
        setMensaje(
          obtenerMensajeError(
            error,
            "No fue posible generar la cotización."
          )
        );

      } finally {
        cotizacionEnCursoRef.current =
          false;

        setCotizando(false);
      }
    };


  if (verificandoSesion) {
    return (
      <div className="session-screen">
        <div className="session-loader">
          <div className="cintac-wordmark login-wordmark">
            CINTAC
          </div>

          <p>
            Validando sesión...
          </p>
        </div>
      </div>
    );
  }


  if (
    token &&
    !usuario &&
    errorSesion
  ) {
    return (
      <div className="session-screen">
        <div className="session-loader">
          <div className="cintac-wordmark login-wordmark">
            CINTAC
          </div>

          <h2>
            Servidor no disponible
          </h2>

          <p>
            {errorSesion}
          </p>

          <button
            type="button"
            className="primary-button"
            onClick={() => {
              setErrorSesion("");

              setReintentoSesion(
                (actual) =>
                  actual + 1
              );
            }}
          >
            REINTENTAR
          </button>

          <button
            type="button"
            className="secondary-button"
            onClick={
              limpiarSesion
            }
          >
            VOLVER AL LOGIN
          </button>
        </div>
      </div>
    );
  }


  if (
    !token ||
    !usuario
  ) {
    return (
      <div
        className="login-page"
        style={{
          backgroundImage:
            `url(${heroImage})`,
        }}
      >
        <div className="login-overlay">
        </div>

        <div className="login-shell">
          <div className="login-brand-panel">
            <div className="login-brand">
              CINTAC
            </div>

            <div className="login-kicker">
              COMERCIO EXTERIOR
            </div>

            <h1>
              Cotizador Logístico
            </h1>

            <p>
              Plataforma interna para
              operaciones de importación.
            </p>
          </div>


          <div className="login-card">
            <div className="login-card-header">
              <span>
                ACCESO
              </span>

              <h2>
                Iniciar sesión
              </h2>

              <p>
                Ingrese sus credenciales
                autorizadas.
              </p>
            </div>


            <form
              className="login-form"
              onSubmit={
                iniciarSesion
              }
            >
              <div className="login-field">
                <label
                  htmlFor="login-usuario"
                >
                  Usuario
                </label>

                <input
                  id="login-usuario"
                  type="text"
                  value={
                    loginUsuario
                  }
                  onChange={(event) => {
                    setLoginUsuario(
                      event.target.value
                    );

                    setLoginError("");
                  }}
                  autoComplete="username"
                  placeholder="Usuario"
                  disabled={
                    iniciandoSesion
                  }
                />
              </div>


              <div className="login-field">
                <label
                  htmlFor="login-password"
                >
                  Contraseña
                </label>

                <input
                  id="login-password"
                  type="password"
                  value={
                    loginPassword
                  }
                  onChange={(event) => {
                    setLoginPassword(
                      event.target.value
                    );

                    setLoginError("");
                  }}
                  autoComplete="current-password"
                  placeholder="Contraseña"
                  disabled={
                    iniciandoSesion
                  }
                />
              </div>


              {loginError && (
                <div className="login-error">
                  <span>
                    !
                  </span>

                  <p>
                    {loginError}
                  </p>
                </div>
              )}


              <button
                type="submit"
                className="login-button"
                disabled={
                  iniciandoSesion
                }
              >
                {
                  iniciandoSesion
                    ? "INGRESANDO..."
                    : "INGRESAR"
                }
              </button>
            </form>


            <div className="login-footer">
              Acceso exclusivo para
              usuarios autorizados
            </div>
          </div>
        </div>
      </div>
    );
  }


  if (
    vistaActiva ===
    "historial"
  ) {
    return (
      <HistorialCotizaciones
        apiUrl={
          API_URL
        }

        usuario={
          usuario
        }

        peticionAutenticada={
          peticionAutenticada
        }

        onVolver={() => {
          setVistaActiva(
            "cotizador"
          );
        }}

        onCerrarSesion={
          cerrarSesion
        }
      />
    );
  }


  if (
    vistaActiva ===
      "administracion" &&
    usuario
      .puedeGestionarDatos
  ) {
    return (
      <AdminDatos
        apiUrl={
          API_URL
        }

        usuario={
          usuario
        }

        peticionAutenticada={
          peticionAutenticada
        }

        onVolver={() => {
          setVistaActiva(
            "cotizador"
          );
        }}

        onCerrarSesion={
          cerrarSesion
        }

        onDatosActualizados={() => {
          setVersionDatos(
            (actual) =>
              actual + 1
          );
        }}

        onPermisoRevocado={
          manejarPermisoRevocado
        }
      />
    );
  }


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


          <div className="header-user">
            <div className="user-info">
              <span>
                {
                  obtenerNombreRol(
                    usuario
                  )
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
                abrirHistorial
              }
            >
              HISTORIAL
            </button>


            {
              usuario
                .puedeGestionarDatos &&
              (
                <button
                  type="button"
                  className="admin-header-button"
                  onClick={() => {
                    void abrirAdministracion();
                  }}
                >
                  ADMINISTRACIÓN
                </button>
              )
            }


            <button
              type="button"
              className="logout-button"
              onClick={
                cerrarSesion
              }
            >
              CERRAR SESIÓN
            </button>
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
        <div className="hero-overlay">
        </div>

        <div className="hero-accent">
        </div>

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
            Ingrese los antecedentes
            de la operación para
            obtener una estimación.
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


          <form
            onSubmit={
              cotizar
            }
          >
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
                <span className="section-line">
                </span>

                <div>
                  <h3>
                    Ruta de importación
                  </h3>

                  <p>
                    Seleccione origen y
                    destino.
                  </p>
                </div>
              </div>


              <div className="form-grid">
                <div className="form-group">
                  <label
                    htmlFor="origen"
                  >
                    Puerto de origen

                    <span className="required">
                      *
                    </span>
                  </label>

                  <select
                    id="origen"
                    className={
                      errores.origen
                        ? "campo-error"
                        : ""
                    }
                    value={
                      origen
                    }
                    disabled={
                      cargandoDatos ||
                      rutas.length === 0
                    }
                    onChange={(event) => {
                      setOrigen(
                        event.target.value
                      );

                      setDestino("");

                      limpiarError(
                        "origen"
                      );

                      limpiarError(
                        "destino"
                      );

                      reiniciarOpcionesContenedor();
                    }}
                  >
                    <option value="">
                      Seleccione puerto
                    </option>

                    {
                      puertosOrigen.map(
                        (puerto) => (
                          <option
                            key={
                              puerto
                            }
                            value={
                              puerto
                            }
                          >
                            {puerto}
                          </option>
                        )
                      )
                    }
                  </select>
                </div>


                <div className="form-group">
                  <label
                    htmlFor="destino"
                  >
                    Puerto de destino

                    <span className="required">
                      *
                    </span>
                  </label>

                  <select
                    id="destino"
                    className={
                      errores.destino
                        ? "campo-error"
                        : ""
                    }
                    value={
                      destino
                    }
                    disabled={
                      !origen
                    }
                    onChange={(event) => {
                      setDestino(
                        event.target.value
                      );

                      limpiarError(
                        "destino"
                      );

                      reiniciarOpcionesContenedor();
                    }}
                  >
                    <option value="">
                      {
                        origen
                          ? "Seleccione puerto"
                          : "Seleccione primero el origen"
                      }
                    </option>

                    {
                      puertosDestino.map(
                        (puerto) => (
                          <option
                            key={
                              puerto
                            }
                            value={
                              puerto
                            }
                          >
                            {puerto}
                          </option>
                        )
                      )
                    }
                  </select>
                </div>
              </div>
            </section>


            <section className="form-section">
              <div className="section-heading">
                <span className="section-line">
                </span>

                <div>
                  <h3>
                    Carga total
                  </h3>
                </div>
              </div>


              <div className="form-grid">
                <div className="form-group">
                  <label
                    htmlFor="peso-carga"
                  >
                    Peso total

                    <span className="required">
                      *
                    </span>
                  </label>

                  <div className="field-with-select">
                    <input
                      id="peso-carga"
                      className={
                        errores.pesoCarga
                          ? "campo-error"
                          : ""
                      }
                      type="number"
                      min="0"
                      step="any"
                      value={
                        pesoCarga
                      }
                      onChange={(event) => {
                        setPesoCarga(
                          event.target.value
                        );

                        limpiarError(
                          "pesoCarga"
                        );

                        reiniciarOpcionesContenedor();
                      }}
                      placeholder="Ej: 25000"
                    />

                    <select
                      aria-label="Unidad de peso"
                      value={
                        unidadPeso
                      }
                      onChange={(event) => {
                        setUnidadPeso(
                          event.target.value
                        );

                        reiniciarOpcionesContenedor();
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


                <div className="form-group">
                  <label
                    htmlFor="valor-carga"
                  >
                    Valor de carga

                    <span className="optional">
                      Opcional
                    </span>
                  </label>

                  <div className="field-with-select">
                    <input
                      id="valor-carga"
                      className={
                        errores.valorCarga
                          ? "campo-error"
                          : ""
                      }
                      type="text"
                      inputMode="decimal"
                      autoComplete="off"
                      value={
                        valorCarga
                      }
                      onChange={(event) => {
                        setValorCarga(
                          event.target.value
                        );

                        limpiarError(
                          "valorCarga"
                        );

                        limpiarResultado();
                      }}
                      onBlur={() => {
                        // En CLP se muestra con separador
                        // de miles chileno al salir del campo.
                        if (
                          monedaValorCarga !== "CLP"
                        ) {
                          return;
                        }

                        const normalizado =
                          normalizarValorCarga(
                            valorCarga,
                            "CLP"
                          );

                        if (
                          normalizado &&
                          String(valorCarga).trim() !== ""
                        ) {
                          setValorCarga(
                            new Intl.NumberFormat(
                              "es-CL",
                              {
                                maximumFractionDigits:
                                  2,
                              }
                            ).format(
                              Number(normalizado)
                            )
                          );
                        }
                      }}
                      placeholder={
                        monedaValorCarga === "CLP"
                          ? "Ej: 300.000"
                          : "Ej: 350.50"
                      }
                      aria-describedby="valor-carga-ayuda"
                      aria-invalid={
                        errores.valorCarga
                      }
                    />

                    <select
                      aria-label="Moneda del valor de carga"
                      value={
                        monedaValorCarga
                      }
                      onChange={(event) => {
                        setMonedaValorCarga(
                          event.target.value
                        );

                        limpiarError(
                          "valorCarga"
                        );

                        limpiarResultado();
                      }}
                    >
                      <option value="USD">
                        USD
                      </option>

                      <option value="CLP">
                        CLP
                      </option>
                    </select>
                  </div>

                  <small
                    id="valor-carga-ayuda"
                    className="field-hint"
                  >
                    {
                      monedaValorCarga === "CLP"
                        ? "Formato chileno (300.000 o 1.250.000,50). Se convierte a USD con el dólar observado de la cotización. Si se deja vacío, se considera 0."
                        : "Se suma al total estimado. Si se deja vacío, se considera 0."
                    }
                  </small>
                </div>
              </div>


              {cargandoOpciones && (
                <div className="loading-inline">
                  Cargando opciones...
                </div>
              )}


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
                      {
                        formatearNumero(
                          recomendacion
                            .pesoTN
                        )
                      }{" "}
                      TN
                    </div>
                  </div>


                  <div className="recommendation-options">
                    {
                      recomendacion
                        .opciones
                        .map(
                          (opcion) => {
                            const sugerida =
                              opcion.codigo ===
                              recomendacion.sugerida;

                            const seleccionada =
                              opcion.codigo ===
                              tipoContenedor;

                            return (
                              <button
                                key={
                                  opcion.codigo
                                }
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
                                  .filter(
                                    Boolean
                                  )
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
                                    {
                                      opcion.nombre
                                    }
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
                                  {
                                    formatearNumero(
                                      opcion.cantidad
                                    )
                                  }{" "}
                                  contenedor
                                  {
                                    opcion.cantidad !==
                                    1
                                      ? "es"
                                      : ""
                                  }
                                </div>


                                <div className="option-price">
                                  US${" "}
                                  {
                                    formatearUSD(
                                      opcion.totalMin
                                    )
                                  }

                                  {" - "}

                                  US${" "}
                                  {
                                    formatearUSD(
                                      opcion.totalMax
                                    )
                                  }
                                </div>
                              </button>
                            );
                          }
                        )
                    }
                  </div>
                </div>
              )}
            </section>


            <section className="form-section">
              <div className="section-heading">
                <span className="section-line">
                </span>

                <div>
                  <h3>
                    Tiempo de tránsito
                  </h3>
                </div>
              </div>


              <div className="form-grid single">
                <div className="form-group">
                  <label
                    htmlFor="contingencia"
                  >
                    Margen de contingencia
                  </label>

                  <div className="input-with-unit">
                    <input
                      id="contingencia"
                      className={
                        errores.contingencia
                          ? "campo-error"
                          : ""
                      }
                      type="number"
                      min="0"
                      step="1"
                      value={
                        contingencia
                      }
                      onChange={(event) => {
                        setContingencia(
                          event.target.value
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
                  onClick={
                    nuevaCotizacion
                  }
                  disabled={
                    cotizando
                  }
                >
                  LIMPIAR
                </button>

                <button
                  type="submit"
                  className="primary-button"
                  disabled={
                    cargandoDatos ||
                    cargandoOpciones ||
                    cotizando ||
                    Boolean(
                      errorDatos
                    )
                  }
                >
                  <span>
                    {
                      cotizando
                        ? "COTIZANDO..."
                        : "COTIZAR OPERACIÓN"
                    }
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
                {
                  resultado?.historialId
                    ? ` #${resultado.historialId}`
                    : ""
                }
              </h2>
            </div>

            {
              resultado?.historialId && (
                <span
                  className="result-saved-badge"
                  title="Guardada automáticamente en el historial"
                >
                  Guardada
                </span>
              )
            }
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
                  {
                    resultado.origen
                  }

                  {" → "}

                  {
                    resultado.destino
                  }
                </strong>

                <small>
                  {
                    resultado.pais
                  }

                  {" · "}

                  {
                    resultado.tipoRuta
                  }
                </small>
              </div>


              <div className="result-stats">
                <div className="result-stat">
                  <span>
                    Carga total
                  </span>

                  <strong>
                    {
                      formatearNumero(
                        resultado.pesoTN
                      )
                    }{" "}
                    TN
                  </strong>
                </div>


                <div className="result-stat">
                  <span>
                    Contenedores
                  </span>

                  <strong>
                    {
                      resultado.cantidad
                    }

                    {" × "}

                    {
                      resultado
                        .tipoContenedor
                    }
                    &apos;
                  </strong>

                  {
                    resultado.esSugerida && (
                      <em className="result-badge">
                        Recomendado
                      </em>
                    )
                  }
                </div>
              </div>


              <div className="cost-breakdown">
                <span className="result-section-title">
                  DESGLOSE DE COSTOS
                </span>

                <div className="cost-row">
                  <span>
                    Tarifa por contenedor
                  </span>

                  <strong>
                    US${" "}
                    {
                      formatearUSD(
                        resultado.tarifaMin
                      )
                    }

                    {" – "}

                    {
                      formatearUSD(
                        resultado.tarifaMax
                      )
                    }
                  </strong>
                </div>


                <div className="cost-row">
                  <span>
                    Flete (
                    {
                      resultado.cantidad
                    }{" "}
                    {
                      resultado.cantidad === 1
                        ? "contenedor"
                        : "contenedores"
                    }
                    )
                  </span>

                  <strong>
                    US${" "}
                    {
                      formatearUSD(
                        resultado.totalMin
                      )
                    }

                    {" – "}

                    {
                      formatearUSD(
                        resultado.totalMax
                      )
                    }
                  </strong>
                </div>


                {
                  Number(
                    resultado.valorCargaIngresado ??
                    resultado.valorCarga
                  ) > 0 && (
                    <div className="cost-row cost-row-added">
                      <span>
                        Valor de carga
                      </span>

                      <strong>
                        {
                          resultado
                            .monedaValorCarga ===
                          "CLP"
                            ? (
                              <>
                                + $
                                {
                                  formatearMontoCLP(
                                    resultado
                                      .valorCargaIngresado
                                  )
                                }{" "}
                                CLP

                                <small className="cost-row-equivalent">
                                  ≈ US${" "}
                                  {
                                    formatearMontoUSD(
                                      resultado.valorCarga
                                    )
                                  }
                                </small>
                              </>
                            )
                            : (
                              <>
                                + US${" "}
                                {
                                  formatearMontoUSD(
                                    resultado.valorCarga
                                  )
                                }
                              </>
                            )
                        }
                      </strong>
                    </div>
                  )
                }
              </div>


              <div className="total-result">
                <span>
                  TOTAL ESTIMADO
                </span>

                <strong>
                  US${" "}
                  {
                    formatearMontoUSD(
                      resultado.totalFinalMin ??
                      resultado.totalMin
                    )
                  }

                  {" – "}

                  {
                    formatearMontoUSD(
                      resultado.totalFinalMax ??
                      resultado.totalMax
                    )
                  }
                </strong>

                {
                  Number(
                    resultado.valorCarga
                  ) > 0 && (
                    <small>
                      Incluye flete y valor de carga
                    </small>
                  )
                }
              </div>


              {
                resultado
                  .conversionDisponible
                  ? (
                    <div className="conversion-box">
                      <span>
                        EQUIVALENTE REFERENCIAL EN CLP
                      </span>

                      <strong>
                        $
                        {
                          formatearCLP(
                            resultado
                              .totalFinalMinCLP ??
                            resultado
                              .totalMinCLP
                          )
                        }

                        {" – $"}

                        {
                          formatearCLP(
                            resultado
                              .totalFinalMaxCLP ??
                            resultado
                              .totalMaxCLP
                          )
                        }
                      </strong>


                      <div className="exchange-rate-details">
                        <div className="exchange-rate-row">
                          <span>
                            Dólar observado
                          </span>

                          <strong>
                            $
                            {
                              formatearTipoCambio(
                                resultado
                                  .tipoCambio
                              )
                            }{" "}
                            CLP/USD
                          </strong>
                        </div>


                        <div className="exchange-rate-row">
                          <span>
                            Fecha de referencia
                          </span>

                          <strong>
                            {
                              formatearFecha(
                                resultado
                                  .fechaTipoCambio
                              )
                            }
                          </strong>
                        </div>


                        <div className="exchange-rate-row">
                          <span>
                            Estado
                          </span>

                          <strong>
                            {
                              resultado
                                .modoTipoCambio ===
                              "respaldo"
                                ? "Último valor disponible"
                                : resultado
                                    .modoTipoCambio ===
                                  "cache"
                                ? "Valor en caché (ver fecha)"
                                : "Consultado en fuente externa"
                            }
                          </strong>
                        </div>


                        <div className="exchange-rate-source">
                          {
                            resultado
                              .fuenteTipoCambio ||
                            "Fuente de tipo de cambio no informada"
                          }
                        </div>
                        <p className="exchange-rate-source">
                          Conversión referencial: verifique la fecha del dólar antes de utilizar estos montos en una operación real.
                        </p>
                      </div>
                    </div>
                  )
                  : (
                    resultado
                      .mensajeConversion &&
                    (
                      <div className="message-box conversion-warning">
                        <span className="message-icon">
                          !
                        </span>

                        <p>
                          {
                            resultado
                              .mensajeConversion
                          }
                        </p>
                      </div>
                    )
                  )
              }


              <div className="transit-summary">
                <span className="result-section-title">
                  TIEMPO DE TRÁNSITO
                </span>

                {
                  resultado
                    .transitoOriginalMin !==
                    null &&
                  resultado
                    .transitoOriginalMax !==
                    null
                    ? (
                      <>
                        <div className="cost-row transit-row">
                          <span>
                            Tránsito estimado
                          </span>

                          <strong>
                            {
                              resultado
                                .transitoMin
                            }

                            {" – "}

                            {
                              resultado
                                .transitoMax
                            }{" "}
                            días
                          </strong>
                        </div>

                        {
                          resultado
                            .contingencia >
                            0 && (
                            <small className="transit-detail">
                              Base{" "}
                              {
                                resultado
                                  .transitoOriginalMin
                              }

                              {" – "}

                              {
                                resultado
                                  .transitoOriginalMax
                              }{" "}
                              días + {
                                resultado
                                  .contingencia
                              }{" "}
                              {
                                resultado
                                  .contingencia === 1
                                  ? "día"
                                  : "días"
                              }{" "}
                              de contingencia
                            </small>
                          )
                        }
                      </>
                    )
                    : (
                      <div className="cost-row transit-row">
                        <span>
                          Tránsito
                        </span>

                        <strong>
                          Sin información disponible
                        </strong>
                      </div>
                    )
                }
              </div>


              <div className="result-actions">
                <button
                  type="button"
                  className="new-quote-button"
                  onClick={
                    abrirHistorial
                  }
                >
                  VER HISTORIAL
                </button>


                <button
                  type="button"
                  className="new-quote-button new-quote-button-primary"
                  onClick={
                    nuevaCotizacion
                  }
                >
                  NUEVA COTIZACIÓN
                </button>
              </div>
            </div>
          )}


          <div className="result-footer">
            <span>
            </span>

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
            Cotizador Logístico ·
            Comercio Exterior
          </div>
        </div>
      </footer>
    </div>
  );
}


export default App;