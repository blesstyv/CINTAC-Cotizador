# CINTAC — Cotizador Logístico

Sistema web interno desarrollado para apoyar el proceso de cotización logística de importaciones del área de Comercio Exterior de CINTAC.

El prototipo centraliza información referencial de rutas, tarifas marítimas, tiempos de tránsito y tipos de contenedor, permitiendo generar estimaciones de flete mediante una interfaz web.

## Funcionalidades principales

- Autenticación de usuarios.
- Control de autorización y permisos.
- Cotización de operaciones de importación.
- Selección de puerto de origen y destino.
- Contenedores de 20' y 40'.
- Conversión entre kilogramos y toneladas.
- Cálculo de cantidad de contenedores.
- Rango mínimo y máximo de flete.
- Tiempo base de tránsito.
- Margen de contingencia aplicado al tiempo de tránsito.
- Conversión automática de USD a CLP.
- Administración de datos maestros.
- Validación de archivos Excel antes de importar.
- Vista previa de datos.
- Actualización transaccional de datos maestros.
- Respaldo de SQLite antes de una importación.
- Gestión dinámica de permisos.
- Control de expiración de sesiones.
- Manejo de pérdida de conexión con el backend.
- Diseño responsive.
- Pruebas automatizadas del backend.
- Pruebas de rendimiento y concurrencia.

## Arquitectura

El sistema utiliza una arquitectura cliente-servidor:

```text
Usuario
   ↓
React + Vite
   ↓ HTTP / JSON
Django REST Framework
   ↓
Lógica de negocio
   ↓
SQLite
```

### Frontend

- React
- Vite
- JavaScript
- CSS
- Oxlint

### Backend

- Python
- Django
- Django REST Framework
- django-cors-headers
- openpyxl
- python-dotenv

### Base de datos

El prototipo utiliza SQLite.

La base de datos local no se almacena en GitHub. Se genera durante la instalación mediante las migraciones de Django.

## Estructura general

```text
CINTAC-Cotizador/
│
├── backend/
│   ├── config/
│   ├── cotizador/
│   ├── manage.py
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Requisitos

Para ejecutar el proyecto se requiere:

- Python 3
- Node.js
- npm
- Git

## Instalación

### 1. Clonar el repositorio

```powershell
git clone https://github.com/blesstyv/CINTAC-Cotizador.git
cd CINTAC-Cotizador
```

### 2. Crear entorno virtual

En Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias del backend

```powershell
pip install -r backend\requirements.txt
```

### 4. Crear archivo de variables de entorno

```powershell
Copy-Item .env.example .env
```

Generar una clave segura:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Editar `.env` y reemplazar:

```text
DJANGO_SECRET_KEY=GENERAR_UNA_CLAVE_SEGURA
```

por la clave generada.

Configuración local de referencia:

```text
DJANGO_SECRET_KEY=TU_CLAVE_GENERADA
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
TOKEN_EXPIRATION_HOURS=8
```

El archivo `.env` está excluido del repositorio mediante `.gitignore`.

## Preparación del backend

Entrar al backend:

```powershell
cd backend
```

Comprobar configuración:

```powershell
python manage.py check
```

Crear las tablas:

```powershell
python manage.py migrate
```

Cargar los datos iniciales del cotizador:

```powershell
python manage.py cargar_datos
```

Crear un administrador local:

```powershell
python manage.py createsuperuser
```

Ejecutar el servidor:

```powershell
python manage.py runserver
```

Backend local:

```text
http://127.0.0.1:8000/
```

Administración de Django:

```text
http://127.0.0.1:8000/admin/
```

## Preparación del frontend

Desde una segunda terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend local:

```text
http://localhost:5173/
```

## API principal

La API está disponible bajo:

```text
/api/
```

Endpoints principales:

```text
POST /api/login/
GET  /api/sesion/
POST /api/logout/

GET  /api/tipos-contenedor/
GET  /api/rutas/
POST /api/opciones-contenedores/
POST /api/cotizar/

GET  /api/administracion/resumen/
POST /api/administracion/validar-excel/
POST /api/administracion/importar-excel/
```

Los endpoints protegidos requieren autenticación mediante token.

## Cotización logística

El flujo principal del sistema es:

```text
Inicio de sesión
      ↓
Selección de origen y destino
      ↓
Ingreso del peso de carga
      ↓
Conversión kg / TN
      ↓
Opciones de contenedor
      ↓
Selección 20' / 40'
      ↓
Margen de contingencia
      ↓
Cálculo del flete
      ↓
Resultado USD
      ↓
Conversión automática a CLP
```

El margen de contingencia modifica únicamente el tiempo estimado de tránsito y no el valor del flete.

## Administración de datos maestros

Los usuarios con permiso de gestión pueden actualizar los datos maestros mediante una planilla `.xlsx`.

El flujo implementado es:

```text
Seleccionar Excel
        ↓
Validar estructura y contenido
        ↓
Vista previa
        ↓
Confirmar actualización
        ↓
Crear respaldo de SQLite
        ↓
Aplicar actualización transaccional
        ↓
Actualizar información del cotizador
```

Si el archivo presenta inconsistencias, la importación se rechaza y la base de datos no se modifica.

También existe una herramienta por consola.

Solo validar:

```powershell
python manage.py importar_excel "ruta\archivo.xlsx"
```

Validar y aplicar:

```powershell
python manage.py importar_excel "ruta\archivo.xlsx" --aplicar
```

## Usuarios y permisos

El sistema distingue entre:

- usuarios autorizados para acceder al cotizador;
- usuarios autorizados para gestionar datos maestros;
- superusuarios de Django.

Los permisos son verificados también en backend, por lo que ocultar una opción en la interfaz no constituye el mecanismo de seguridad.

Un usuario al que se le revoca el permiso de gestión conserva acceso al cotizador si continúa autorizado, pero pierde acceso a Administración.

## Sesiones

La autenticación utiliza tokens de Django REST Framework.

La duración se configura mediante:

```text
TOKEN_EXPIRATION_HOURS
```

El valor de desarrollo definido en `.env.example` es:

```text
8 horas
```

Cuando un token expira, se invalida y el usuario debe iniciar sesión nuevamente.

## Manejo de errores de conexión

El frontend distingue entre:

- sesión inválida;
- falta de permisos;
- servidor temporalmente no disponible.

Una pérdida temporal de conexión con Django no elimina automáticamente la sesión local.

Cuando el backend vuelve a estar disponible, el usuario puede continuar trabajando mientras su token siga siendo válido.

## Pruebas backend

Desde:

```powershell
cd backend
```

Ejecutar:

```powershell
python manage.py check
python manage.py test cotizador
```

La batería automatizada contempla pruebas relacionadas con:

- modelos;
- rutas;
- tarifas;
- tiempos de tránsito;
- contenedores;
- cálculos;
- conversión de peso;
- cotización;
- autenticación;
- autorización;
- permisos;
- expiración de sesión;
- tipo de cambio;
- importación Excel;
- validación de archivos;
- rollback;
- respaldos;
- seguridad;
- robustez;
- integración entre componentes.

## Pruebas frontend

Desde:

```powershell
cd frontend
```

Ejecutar análisis estático:

```powershell
npm run lint -- --format=unix
```

Generar compilación de producción:

```powershell
npm run build
```

La versión preparada para entrega debe finalizar sin errores de lint y con compilación correcta.

## Pruebas de rendimiento

Con Django en ejecución:

```powershell
python manage.py probar_rendimiento --usuario NOMBRE_USUARIO
```

La herramienta mide los principales endpoints utilizando diferentes niveles de concurrencia.

Entrega métricas como:

- solicitudes exitosas;
- solicitudes fallidas;
- tiempo promedio;
- mediana;
- percentil 95;
- tiempo máximo;
- solicitudes por segundo;
- códigos HTTP.

Estas mediciones se ejecutan sobre el servidor de desarrollo y no representan un benchmark de infraestructura productiva.

## Seguridad

El proyecto contempla:

- `SECRET_KEY` mediante variable de entorno;
- `.env` excluido del repositorio;
- autenticación mediante tokens;
- expiración de tokens;
- validadores de contraseña de Django;
- permisos de acceso;
- permisos específicos para gestión de datos;
- comprobaciones de autorización en backend;
- limitación de intentos de login;
- CORS configurable;
- `ALLOWED_HOSTS` configurable;
- protección frente a framing;
- cookies HTTPOnly;
- configuración HTTPS/HSTS cuando `DEBUG=False`;
- actualización transaccional de datos;
- respaldo previo a importaciones.

Las contraseñas, tokens y claves privadas no deben incorporarse al repositorio.

## Archivos excluidos del repositorio

Entre otros:

```text
.env
.venv/
.venv*/
node_modules/
dist/
__pycache__/
backend/db.sqlite3
backend/backups/
```

Esto permite mantener fuera del control de versiones datos locales, dependencias generadas y configuración sensible.

## Alcance del prototipo

El desarrollo actual se concentra en cotizaciones marítimas de importación mediante contenedores de 20' y 40'.

Incluye:

- rutas de importación;
- tarifas referenciales;
- tiempos de tránsito;
- cantidad de contenedores;
- conversión de unidades;
- conversión USD/CLP;
- actualización administrativa de datos.

Las tarifas y tiempos almacenados son información de referencia para el funcionamiento del cotizador.

## Proyecto académico

Proyecto Integrado — Analista Programador.

Cliente: CINTAC.

Prototipo funcional desarrollado para apoyar el proceso de cotización logística del área de Comercio Exterior.