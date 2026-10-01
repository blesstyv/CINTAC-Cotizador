# CINTAC — Cotizador Logístico

Sistema web interno desarrollado para apoyar el proceso de cotización logística de importaciones del área de Comercio Exterior de CINTAC.

El prototipo centraliza información referencial de rutas, tarifas marítimas, tiempos de tránsito y tipos de contenedor, permitiendo generar una estimación de flete de forma rápida y controlada.

## Funcionalidades principales

- Autenticación de usuarios.
- Control de autorización y permisos.
- Cotización de operaciones de importación.
- Selección de puerto de origen y destino.
- Contenedores de 20' y 40'.
- Conversión de peso entre kg y toneladas.
- Cálculo automático de cantidad de contenedores.
- Rango mínimo y máximo de flete.
- Tiempo base y margen de contingencia.
- Conversión automática de USD a CLP.
- Administración de datos maestros.
- Validación de archivos Excel antes de importar.
- Vista previa de información a actualizar.
- Actualización transaccional de datos.
- Creación de respaldo de SQLite antes de una importación.
- Gestión dinámica de permisos.
- Manejo de pérdida de conexión con el backend.
- Diseño responsive.

## Arquitectura

El proyecto utiliza una arquitectura cliente-servidor:

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