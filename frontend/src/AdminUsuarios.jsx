import {
  useEffect,
  useRef,
  useState,
} from "react";

import "./AdminUsuarios.css";


const FORMULARIO_INICIAL = {
  username: "",
  first_name: "",
  last_name: "",
  email: "",
  password: "",
  password_confirm: "",
  rol: "USUARIO",
  activo: true,
};


function extraerErrores(
  datos
) {
  if (!datos) {
    return [
      "No fue posible completar la operación.",
    ];
  }

  if (datos.detail) {
    return [
      String(
        datos.detail
      ),
    ];
  }

  const errores = [];

  Object.values(
    datos
  ).forEach(
    (valor) => {
      if (
        Array.isArray(
          valor
        )
      ) {
        valor.forEach(
          (mensaje) => {
            errores.push(
              String(
                mensaje
              )
            );
          }
        );

        return;
      }

      if (
        typeof valor ===
        "string"
      ) {
        errores.push(
          valor
        );

        return;
      }

      if (
        valor &&
        typeof valor ===
        "object"
      ) {
        Object.values(
          valor
        ).forEach(
          (contenido) => {
            if (
              Array.isArray(
                contenido
              )
            ) {
              contenido.forEach(
                (mensaje) => {
                  errores.push(
                    String(
                      mensaje
                    )
                  );
                }
              );
            }
          }
        );
      }
    }
  );

  if (
    errores.length === 0
  ) {
    errores.push(
      "No fue posible completar la operación."
    );
  }

  return errores;
}


function obtenerNombreRol(
  usuario
) {
  if (
    usuario?.rol ===
    "ADMINISTRADOR"
  ) {
    return "Administrador";
  }

  if (
    usuario?.rol ===
    "ENCARGADO"
  ) {
    return "Encargado";
  }

  return "Usuario";
}


function AdminUsuarios({
  apiUrl,
  usuarioActual,
  peticionAutenticada,
  onPermisoRevocado,
}) {
  const [
    usuarios,
    setUsuarios,
  ] = useState([]);

  const [
    cargando,
    setCargando,
  ] = useState(true);

  const [
    guardando,
    setGuardando,
  ] = useState(false);

  const [
    errores,
    setErrores,
  ] = useState([]);

  const [
    mensaje,
    setMensaje,
  ] = useState("");

  const [
    busqueda,
    setBusqueda,
  ] = useState("");

  const [
    filtroRol,
    setFiltroRol,
  ] = useState("");

  const [
    formulario,
    setFormulario,
  ] = useState(
    FORMULARIO_INICIAL
  );

  const [
    usuarioEditando,
    setUsuarioEditando,
  ] = useState(null);

  const [
    mostrarFormulario,
    setMostrarFormulario,
  ] = useState(false);

  const guardandoRef =
    useRef(false);

  const cargandoRef =
    useRef(false);

  const formularioRef =
    useRef(null);


  /* ======================================
     PERMISOS
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
     DESPLAZAR AL FORMULARIO
  ====================================== */

  const desplazarAlFormulario =
    () => {
      window.setTimeout(
        () => {
          formularioRef.current
            ?.scrollIntoView({
              behavior:
                "smooth",

              block:
                "start",
            });
        },
        50
      );
    };


  /* ======================================
     LISTAR USUARIOS
  ====================================== */

  const cargarUsuarios =
  async (
    busquedaActual = "",
    rolActual = ""
  ) => {
    if (
      cargandoRef.current
    ) {
      return;
    }

    cargandoRef.current =
      true;

    setCargando(
      true
    );

    setErrores([]);

    try {
      const parametros =
        new URLSearchParams();

      if (
        busquedaActual.trim()
      ) {
        parametros.set(
          "q",
          busquedaActual.trim()
        );
      }

      if (
        rolActual
      ) {
        parametros.set(
          "rol",
          rolActual
        );
      }

      const query =
        parametros.toString();

      const url = query
        ? (
          `${apiUrl}/administracion/usuarios/?${query}`
        )
        : (
          `${apiUrl}/administracion/usuarios/`
        );

      const respuesta =
        await peticionAutenticada(
          url
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
          "No fue posible cargar los usuarios."
        );
      }

      setUsuarios(
        datos.usuarios || []
      );

    } catch (error) {
      setErrores([
        error.message ||
        "No fue posible cargar los usuarios.",
      ]);

    } finally {
      cargandoRef.current =
        false;

      setCargando(
        false
      );
    }
  };


  useEffect(() => {
    void cargarUsuarios();
  }, []);


  /* ======================================
     FORMULARIO
  ====================================== */

  const actualizarCampo =
    (
      campo,
      valor
    ) => {
      setFormulario(
        (actual) => ({
          ...actual,

          [campo]:
            valor,
        })
      );

      setErrores([]);
      setMensaje("");
    };


  const abrirNuevoUsuario =
    () => {
      setFormulario(
        FORMULARIO_INICIAL
      );

      setUsuarioEditando(
        null
      );

      setErrores([]);
      setMensaje("");

      setMostrarFormulario(
        true
      );

      desplazarAlFormulario();
    };


  const cerrarFormulario =
    () => {
      setFormulario(
        FORMULARIO_INICIAL
      );

      setUsuarioEditando(
        null
      );

      setMostrarFormulario(
        false
      );

      setErrores([]);
    };


  const editarUsuario =
    (usuario) => {
      if (
        usuario.protegido
      ) {
        return;
      }

      setUsuarioEditando(
        usuario
      );

      setFormulario({
        username:
          usuario.username || "",

        first_name:
          usuario.firstName || "",

        last_name:
          usuario.lastName || "",

        email:
          usuario.email || "",

        password:
          "",

        password_confirm:
          "",

        rol:
          usuario.rol ||
          "USUARIO",

        activo:
          Boolean(
            usuario.activo
          ),
      });

      setErrores([]);
      setMensaje("");

      setMostrarFormulario(
        true
      );

      desplazarAlFormulario();
    };


  /* ======================================
     VALIDACIÓN FRONTEND
  ====================================== */

  const validarFormulario =
    () => {
      const problemas = [];

      if (
        !usuarioEditando &&
        !formulario
          .username
          .trim()
      ) {
        problemas.push(
          "Debe ingresar un nombre de usuario."
        );
      }

      if (
        !formulario
          .first_name
          .trim()
      ) {
        problemas.push(
          "Debe ingresar el nombre."
        );
      }

      if (
        !formulario
          .last_name
          .trim()
      ) {
        problemas.push(
          "Debe ingresar el apellido."
        );
      }

      if (
        !formulario
          .email
          .trim()
      ) {
        problemas.push(
          "Debe ingresar el correo electrónico."
        );
      }

      if (
        !formulario.rol
      ) {
        problemas.push(
          "Debe seleccionar un rol."
        );
      }

      if (
        !usuarioEditando
      ) {
        if (
          !formulario.password
        ) {
          problemas.push(
            "Debe ingresar una contraseña."
          );
        }

        if (
          !formulario
            .password_confirm
        ) {
          problemas.push(
            "Debe confirmar la contraseña."
          );
        }
      }

      if (
        formulario.password ||
        formulario
          .password_confirm
      ) {
        if (
          formulario.password !==
          formulario
            .password_confirm
        ) {
          problemas.push(
            "Las contraseñas no coinciden."
          );
        }
      }

      return problemas;
    };


  /* ======================================
     GUARDAR
  ====================================== */

  const guardarUsuario =
  async (
    event
  ) => {
    event.preventDefault();

    if (
      guardandoRef.current
    ) {
      return;
    }

    const problemas =
      validarFormulario();

    if (
      problemas.length > 0
    ) {
      setErrores(
        problemas
      );

      return;
    }

    guardandoRef.current =
      true;

    setGuardando(
      true
    );

    setErrores([]);
    setMensaje("");

    const editando =
      Boolean(
        usuarioEditando
      );

    const payload = {
      first_name:
        formulario
          .first_name
          .trim(),

      last_name:
        formulario
          .last_name
          .trim(),

      email:
        formulario
          .email
          .trim(),

      rol:
        formulario.rol,

      activo:
        Boolean(
          formulario.activo
        ),
    };

    if (!editando) {
      payload.username =
        formulario
          .username
          .trim();

      payload.password =
        formulario.password;

      payload.password_confirm =
        formulario
          .password_confirm;
    }

    if (
      editando &&
      formulario.password
    ) {
      payload.password =
        formulario.password;

      payload.password_confirm =
        formulario
          .password_confirm;
    }

    try {
      const url = editando
        ? (
          `${apiUrl}/administracion/usuarios/${usuarioEditando.id}/`
        )
        : (
          `${apiUrl}/administracion/usuarios/`
        );

      const respuesta =
        await peticionAutenticada(
          url,
          {
            method:
              editando
                ? "PATCH"
                : "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify(
                payload
              ),
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
          extraerErrores(
            datos
          )
        );

        return;
      }

      setMensaje(
        datos.detail ||
        (
          editando
            ? (
              "Usuario actualizado correctamente."
            )
            : (
              "Usuario creado correctamente."
            )
        )
      );

      setFormulario(
        FORMULARIO_INICIAL
      );

      setUsuarioEditando(
        null
      );

      setMostrarFormulario(
        false
      );

      await cargarUsuarios(
        busqueda,
        filtroRol
      );

      window.scrollTo({
        top:
          formularioRef
            .current
            ?.parentElement
            ?.offsetTop ||
          0,

        behavior:
          "smooth",
      });

    } catch (error) {
      setErrores([
        error.message ||
        "No fue posible guardar el usuario.",
      ]);

    } finally {
      guardandoRef.current =
        false;

      setGuardando(
        false
      );
    }
  };


  /* ======================================
     ACTIVAR / DESACTIVAR
  ====================================== */

  const cambiarEstado =
  async (
    usuario
  ) => {
    if (
      guardandoRef.current ||
      usuario.protegido
    ) {
      return;
    }

    const nuevoEstado =
      !usuario.activo;

    const accion =
      nuevoEstado
        ? "activar"
        : "desactivar";

    const confirmado =
      window.confirm(
        (
          `¿Desea ${accion} al usuario `
          + `${usuario.username}?`
        )
      );

    if (!confirmado) {
      return;
    }

    guardandoRef.current =
      true;

    setGuardando(
      true
    );

    setErrores([]);
    setMensaje("");

    try {
      const respuesta =
        await peticionAutenticada(
          (
            `${apiUrl}/administracion/usuarios/`
            + `${usuario.id}/`
          ),
          {
            method:
              "PATCH",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                activo:
                  nuevoEstado,
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
          extraerErrores(
            datos
          )
        );

        return;
      }

      setMensaje(
        nuevoEstado
          ? (
            "Usuario activado correctamente."
          )
          : (
            "Usuario desactivado correctamente."
          )
      );

      await cargarUsuarios(
        busqueda,
        filtroRol
      );

    } catch (error) {
      setErrores([
        error.message ||
        "No fue posible modificar el usuario.",
      ]);

    } finally {
      guardandoRef.current =
        false;

      setGuardando(
        false
      );
    }
  };


  /* ======================================
     BUSCAR
  ====================================== */

  const ejecutarBusqueda =
    (event) => {
      event.preventDefault();

      void cargarUsuarios(
        busqueda,
        filtroRol
      );
    };


  const limpiarBusqueda =
    () => {
      setBusqueda("");
      setFiltroRol("");

      void cargarUsuarios(
        "",
        ""
      );
    };


  /* ======================================
     INTERFAZ
  ====================================== */

  return (
    <section className="users-section">
      <div className="users-heading">
        <div>
          <span className="admin-eyebrow">
            SEGURIDAD Y ACCESOS
          </span>

          <h2>
            Gestión de usuarios
          </h2>

          <p>
            Creación, edición,
            roles y estado de las
            cuentas autorizadas para
            utilizar el cotizador.
          </p>
        </div>

        <button
          type="button"
          className="users-new-button"
          onClick={
            abrirNuevoUsuario
          }
          disabled={
            guardando
          }
          aria-expanded={
            mostrarFormulario &&
            !usuarioEditando
          }
        >
          NUEVO USUARIO
        </button>
      </div>


      <form
        className="users-filters"
        onSubmit={
          ejecutarBusqueda
        }
      >
        <div className="users-filter-field">
          <label
            htmlFor="buscar-usuario"
          >
            Buscar
          </label>

          <input
            id="buscar-usuario"
            type="text"
            value={
              busqueda
            }
            onChange={(event) => {
              setBusqueda(
                event.target.value
              );
            }}
            placeholder="Usuario, nombre o correo"
          />
        </div>


        <div className="users-filter-field">
          <label
            htmlFor="filtro-rol"
          >
            Rol
          </label>

          <select
            id="filtro-rol"
            value={
              filtroRol
            }
            onChange={(event) => {
              setFiltroRol(
                event.target.value
              );
            }}
          >
            <option value="">
              Todos
            </option>

            <option value="USUARIO">
              Usuario
            </option>

            <option value="ENCARGADO">
              Encargado
            </option>

            <option value="ADMINISTRADOR">
              Administrador
            </option>
          </select>
        </div>


        <div className="users-filter-actions">
          <button
            type="submit"
            className="users-secondary-button"
            disabled={
              cargando
            }
          >
            BUSCAR
          </button>

          <button
            type="button"
            className="users-link-button"
            onClick={
              limpiarBusqueda
            }
            disabled={
              cargando
            }
          >
            LIMPIAR
          </button>
        </div>
      </form>


      {mensaje && (
        <div className="users-alert success">
          {mensaje}
        </div>
      )}


      {
        errores.length > 0 &&
        !mostrarFormulario &&
        (
          <div className="users-alert error">
            {
              errores.map(
                (
                  error,
                  indice
                ) => (
                  <p
                    key={
                      `${indice}-${error}`
                    }
                  >
                    {error}
                  </p>
                )
              )
            }
          </div>
        )
      }


      <div className="users-table-wrapper">
        <table className="users-table">
          <thead>
            <tr>
              <th>
                Usuario
              </th>

              <th>
                Nombre
              </th>

              <th>
                Correo
              </th>

              <th>
                Rol
              </th>

              <th>
                Estado
              </th>

              <th>
                Acciones
              </th>
            </tr>
          </thead>

          <tbody>
            {
              cargando
                ? (
                  <tr>
                    <td
                      colSpan="6"
                      className="users-empty"
                    >
                      Cargando usuarios...
                    </td>
                  </tr>
                )
                : (
                  usuarios.length === 0
                    ? (
                      <tr>
                        <td
                          colSpan="6"
                          className="users-empty"
                        >
                          No se encontraron usuarios.
                        </td>
                      </tr>
                    )
                    : (
                      usuarios.map(
                        (usuario) => (
                          <tr
                            key={
                              usuario.id
                            }
                          >
                            <td>
                              <strong>
                                {
                                  usuario.username
                                }
                              </strong>

                              {
                                usuario.id ===
                                  usuarioActual?.id &&
                                (
                                  <span className="users-you">
                                    TÚ
                                  </span>
                                )
                              }
                            </td>

                            <td>
                              {
                                usuario.nombre
                              }
                            </td>

                            <td>
                              {
                                usuario.email ||
                                "—"
                              }
                            </td>

                            <td>
                              <span
                                className={
                                  (
                                    "users-role "
                                    + (
                                      usuario
                                        .rol
                                        ?.toLowerCase() ||
                                      ""
                                    )
                                  )
                                }
                              >
                                {
                                  obtenerNombreRol(
                                    usuario
                                  )
                                }
                              </span>
                            </td>

                            <td>
                              <span
                                className={
                                  (
                                    "users-status "
                                    + (
                                      usuario.activo
                                        ? "active"
                                        : "inactive"
                                    )
                                  )
                                }
                              >
                                {
                                  usuario.activo
                                    ? "ACTIVO"
                                    : "INACTIVO"
                                }
                              </span>
                            </td>

                            <td>
                              <div className="users-row-actions">
                                <button
                                  type="button"
                                  className="users-table-button"
                                  onClick={() => {
                                    editarUsuario(
                                      usuario
                                    );
                                  }}
                                  disabled={
                                    guardando ||
                                    usuario.protegido
                                  }
                                >
                                  EDITAR
                                </button>

                                <button
                                  type="button"
                                  className={
                                    (
                                      "users-table-button "
                                      + (
                                        usuario.activo
                                          ? "danger"
                                          : "success"
                                      )
                                    )
                                  }
                                  onClick={() => {
                                    void cambiarEstado(
                                      usuario
                                    );
                                  }}
                                  disabled={
                                    guardando ||
                                    usuario.protegido ||
                                    usuario.id ===
                                      usuarioActual?.id
                                  }
                                >
                                  {
                                    usuario.activo
                                      ? "DESACTIVAR"
                                      : "ACTIVAR"
                                  }
                                </button>
                              </div>
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
        mostrarFormulario &&
        (
          <div
            className="users-form-panel"
            ref={
              formularioRef
            }
          >
            <div className="users-form-heading">
              <div>
                <span className="admin-eyebrow">
                  {
                    usuarioEditando
                      ? "EDITAR CUENTA"
                      : "NUEVA CUENTA"
                  }
                </span>

                <h3>
                  {
                    usuarioEditando
                      ? (
                        `Editar ${usuarioEditando.username}`
                      )
                      : (
                        "Crear usuario"
                      )
                  }
                </h3>

                <p>
                  {
                    usuarioEditando
                      ? (
                        "Actualice los datos, rol, contraseña o estado de la cuenta."
                      )
                      : (
                        "Complete los antecedentes del nuevo usuario."
                      )
                  }
                </p>
              </div>

              <button
                type="button"
                className="users-close-button"
                onClick={
                  cerrarFormulario
                }
                disabled={
                  guardando
                }
                aria-label="Cerrar formulario"
              >
                ×
              </button>
            </div>


            {
              errores.length > 0 &&
              (
                <div className="users-alert error">
                  {
                    errores.map(
                      (
                        error,
                        indice
                      ) => (
                        <p
                          key={
                            `${indice}-${error}`
                          }
                        >
                          {error}
                        </p>
                      )
                    )
                  }
                </div>
              )
            }


            <form
              className="users-form"
              onSubmit={
                guardarUsuario
              }
            >
              <div className="users-form-grid">
                <div className="users-form-field">
                  <label>
                    Usuario *
                  </label>

                  <input
                    type="text"
                    value={
                      formulario.username
                    }
                    onChange={(event) => {
                      actualizarCampo(
                        "username",
                        event.target.value
                      );
                    }}
                    disabled={
                      Boolean(
                        usuarioEditando
                      ) ||
                      guardando
                    }
                    autoComplete="off"
                  />
                </div>


                <div className="users-form-field">
                  <label>
                    Correo electrónico *
                  </label>

                  <input
                    type="email"
                    value={
                      formulario.email
                    }
                    onChange={(event) => {
                      actualizarCampo(
                        "email",
                        event.target.value
                      );
                    }}
                    disabled={
                      guardando
                    }
                    autoComplete="off"
                  />
                </div>


                <div className="users-form-field">
                  <label>
                    Nombre *
                  </label>

                  <input
                    type="text"
                    value={
                      formulario.first_name
                    }
                    onChange={(event) => {
                      actualizarCampo(
                        "first_name",
                        event.target.value
                      );
                    }}
                    disabled={
                      guardando
                    }
                  />
                </div>


                <div className="users-form-field">
                  <label>
                    Apellido *
                  </label>

                  <input
                    type="text"
                    value={
                      formulario.last_name
                    }
                    onChange={(event) => {
                      actualizarCampo(
                        "last_name",
                        event.target.value
                      );
                    }}
                    disabled={
                      guardando
                    }
                  />
                </div>


                <div className="users-form-field">
                  <label>
                    Rol *
                  </label>

                  <select
                    value={
                      formulario.rol
                    }
                    onChange={(event) => {
                      actualizarCampo(
                        "rol",
                        event.target.value
                      );
                    }}
                    disabled={
                      guardando
                    }
                  >
                    <option value="USUARIO">
                      Usuario
                    </option>

                    <option value="ENCARGADO">
                      Encargado
                    </option>

                    <option value="ADMINISTRADOR">
                      Administrador
                    </option>
                  </select>
                </div>


                <div className="users-form-field users-checkbox-field">
                  <label>
                    Estado
                  </label>

                  <label className="users-checkbox">
                    <input
                      type="checkbox"
                      checked={
                        formulario.activo
                      }
                      onChange={(event) => {
                        actualizarCampo(
                          "activo",
                          event.target.checked
                        );
                      }}
                      disabled={
                        guardando ||
                        (
                          usuarioEditando?.id ===
                          usuarioActual?.id
                        )
                      }
                    />

                    <span>
                      Usuario activo
                    </span>
                  </label>
                </div>


                <div className="users-form-field">
                  <label>
                    {
                      usuarioEditando
                        ? "Nueva contraseña"
                        : "Contraseña *"
                    }
                  </label>

                  <input
                    type="password"
                    value={
                      formulario.password
                    }
                    onChange={(event) => {
                      actualizarCampo(
                        "password",
                        event.target.value
                      );
                    }}
                    disabled={
                      guardando
                    }
                    autoComplete="new-password"
                  />

                  {
                    usuarioEditando &&
                    (
                      <small>
                        Déjela vacía para
                        conservar la actual.
                      </small>
                    )
                  }
                </div>


                <div className="users-form-field">
                  <label>
                    {
                      usuarioEditando
                        ? "Confirmar nueva contraseña"
                        : "Confirmar contraseña *"
                    }
                  </label>

                  <input
                    type="password"
                    value={
                      formulario
                        .password_confirm
                    }
                    onChange={(event) => {
                      actualizarCampo(
                        "password_confirm",
                        event.target.value
                      );
                    }}
                    disabled={
                      guardando
                    }
                    autoComplete="new-password"
                  />
                </div>
              </div>


              <div className="users-form-actions">
                <button
                  type="button"
                  className="users-secondary-button"
                  onClick={
                    cerrarFormulario
                  }
                  disabled={
                    guardando
                  }
                >
                  CANCELAR
                </button>

                <button
                  type="submit"
                  className="users-primary-button"
                  disabled={
                    guardando
                  }
                >
                  {
                    guardando
                      ? "GUARDANDO..."
                      : (
                        usuarioEditando
                          ? "GUARDAR CAMBIOS"
                          : "CREAR USUARIO"
                      )
                  }
                </button>
              </div>
            </form>
          </div>
        )
      }
    </section>
  );
}


export default AdminUsuarios;