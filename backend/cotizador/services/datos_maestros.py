"""
Trazabilidad, comparación y recuperación de los datos maestros.

Conceptos que se distinguen explícitamente (BD04):

* Rollback transaccional: ``transaction.atomic`` revierte TODO si una
  importación falla a mitad de camino; la base nunca queda a medias.
* Respaldo de información: antes de cada importación o restauración se
  guarda en ``OperacionDatosMaestros.estado_previo`` una instantánea
  completa de puertos, rutas, tarifas, tránsitos y contenedores.
* Recuperación de datos anteriores: un administrador puede restaurar
  esa instantánea. La restauración también guarda el estado que
  reemplaza, por lo que es reversible.

Las cotizaciones del historial NO se tocan: guardan sus propios valores
(snapshots) y no dependen de las tarifas vigentes.
"""

import hashlib
from decimal import Decimal

from django.db import transaction

from cotizador.models import (
    OperacionDatosMaestros,
    Puerto,
    Ruta,
    Tarifa,
    TiempoTransito,
    TipoContenedor,
)


VERSION_INSTANTANEA = 1


class InstantaneaInvalida(Exception):
    pass


def calcular_sha256(ruta_archivo):
    resumen = hashlib.sha256()

    with open(ruta_archivo, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(65536), b""):
            resumen.update(bloque)

    return resumen.hexdigest()


def _dec(valor):
    return str(Decimal(valor).quantize(Decimal("0.01")))


# ----------------------------------------------------------------------
# Instantánea
# ----------------------------------------------------------------------


def capturar_estado():
    """Instantánea serializable (JSON) de todos los datos maestros."""
    rutas = (
        Ruta.objects
        .select_related(
            "puerto_origen",
            "puerto_destino",
            "tiempo_transito",
        )
        .prefetch_related("tarifas")
        .order_by("id")
    )

    datos_rutas = []

    for ruta in rutas:
        try:
            transito = {
                "dias_minimos": ruta.tiempo_transito.dias_minimos,
                "dias_maximos": ruta.tiempo_transito.dias_maximos,
            }
        except TiempoTransito.DoesNotExist:
            transito = None

        datos_rutas.append(
            {
                "origen": ruta.puerto_origen.nombre,
                "pais_origen": ruta.puerto_origen.pais,
                "destino": ruta.puerto_destino.nombre,
                "pais_destino": ruta.puerto_destino.pais,
                "tipo_ruta": ruta.tipo_ruta,
                "tarifas": [
                    {
                        "tipo_contenedor": tarifa.tipo_contenedor,
                        "valor_minimo": _dec(tarifa.valor_minimo),
                        "valor_maximo": _dec(tarifa.valor_maximo),
                        "fuente": tarifa.fuente,
                    }
                    for tarifa in sorted(
                        ruta.tarifas.all(),
                        key=lambda t: t.tipo_contenedor,
                    )
                ],
                "transito": transito,
            }
        )

    return {
        "version": VERSION_INSTANTANEA,
        "tiposContenedor": [
            {
                "codigo": tipo.codigo,
                "nombre": tipo.nombre,
                "capacidad_tn": _dec(tipo.capacidad_tn),
                "activo": tipo.activo,
            }
            for tipo in TipoContenedor.objects.order_by("codigo")
        ],
        "puertos": [
            {
                "nombre": puerto.nombre,
                "pais": puerto.pais,
            }
            for puerto in Puerto.objects.order_by("pais", "nombre")
        ],
        "rutas": datos_rutas,
    }


def resumir_estado(estado):
    if not estado:
        return {}

    return {
        "puertos": len(estado.get("puertos", [])),
        "rutas": len(estado.get("rutas", [])),
        "tarifas": sum(
            len(ruta.get("tarifas", []))
            for ruta in estado.get("rutas", [])
        ),
        "tiposContenedor": len(estado.get("tiposContenedor", [])),
    }


# ----------------------------------------------------------------------
# Comparación para la vista previa
# ----------------------------------------------------------------------


def comparar_con_estado_actual(filas):
    """
    Compara las filas validadas del Excel con la base actual.

    Devuelve el detalle por fila (nueva, modificada o sin cambios) con
    los valores actuales y propuestos, más un resumen. La importación
    nunca elimina rutas: las existentes que no vienen en el archivo se
    informan como conservadas.
    """
    rutas = (
        Ruta.objects
        .select_related(
            "puerto_origen",
            "puerto_destino",
            "tiempo_transito",
        )
        .prefetch_related("tarifas")
    )

    indice = {
        (
            ruta.puerto_origen.nombre,
            ruta.puerto_origen.pais,
            ruta.puerto_destino.nombre,
        ): ruta
        for ruta in rutas
    }

    detalle = []
    vistas = set()
    resumen = {
        "nuevas": 0,
        "modificadas": 0,
        "sinCambios": 0,
        "conservadas": 0,
    }

    for fila in filas:
        clave = (fila.origen, fila.pais_origen, fila.destino)
        vistas.add(clave)
        ruta = indice.get(clave)

        propuesto = {
            "tipoRuta": fila.tipo_ruta,
            "tarifa20Min": _dec(fila.tarifa20_min),
            "tarifa20Max": _dec(fila.tarifa20_max),
            "tarifa40Min": _dec(fila.tarifa40_min),
            "tarifa40Max": _dec(fila.tarifa40_max),
            "transitoMin": fila.transito_min,
            "transitoMax": fila.transito_max,
        }

        if ruta is None:
            resumen["nuevas"] += 1
            detalle.append(
                {
                    "fila": fila.numero_fila,
                    "origen": fila.origen,
                    "destino": fila.destino,
                    "estado": "nueva",
                    "cambios": [
                        {
                            "campo": campo,
                            "actual": None,
                            "propuesto": valor,
                        }
                        for campo, valor in propuesto.items()
                    ],
                }
            )
            continue

        tarifas = {
            tarifa.tipo_contenedor: tarifa
            for tarifa in ruta.tarifas.all()
        }

        try:
            transito = ruta.tiempo_transito
        except TiempoTransito.DoesNotExist:
            transito = None

        def _tarifa(codigo, atributo):
            tarifa = tarifas.get(codigo)
            return _dec(getattr(tarifa, atributo)) if tarifa else None

        actual = {
            "tipoRuta": ruta.tipo_ruta,
            "tarifa20Min": _tarifa("20", "valor_minimo"),
            "tarifa20Max": _tarifa("20", "valor_maximo"),
            "tarifa40Min": _tarifa("40", "valor_minimo"),
            "tarifa40Max": _tarifa("40", "valor_maximo"),
            "transitoMin": transito.dias_minimos if transito else None,
            "transitoMax": transito.dias_maximos if transito else None,
        }

        cambios = [
            {
                "campo": campo,
                "actual": actual[campo],
                "propuesto": propuesto[campo],
            }
            for campo in propuesto
            if actual[campo] != propuesto[campo]
        ]

        estado = "modificada" if cambios else "sin_cambios"
        resumen["modificadas" if cambios else "sinCambios"] += 1

        detalle.append(
            {
                "fila": fila.numero_fila,
                "origen": fila.origen,
                "destino": fila.destino,
                "estado": estado,
                "cambios": cambios,
            }
        )

    resumen["conservadas"] = sum(
        1 for clave in indice if clave not in vistas
    )

    return detalle, resumen


# ----------------------------------------------------------------------
# Restauración
# ----------------------------------------------------------------------


def _validar_instantanea(estado):
    if (
        not isinstance(estado, dict)
        or estado.get("version") != VERSION_INSTANTANEA
        or not isinstance(estado.get("rutas"), list)
        or not isinstance(estado.get("puertos"), list)
        or not isinstance(estado.get("tiposContenedor"), list)
    ):
        raise InstantaneaInvalida(
            "La instantánea seleccionada no tiene un formato válido."
        )

    if not estado["rutas"]:
        raise InstantaneaInvalida(
            "La instantánea no contiene rutas; no se restaurará "
            "una base vacía."
        )


@transaction.atomic
def restaurar_estado(estado):
    """
    Deja los datos maestros exactamente como en ``estado``.

    Se ejecuta en una sola transacción: si algo falla no queda ningún
    cambio parcial. Los tipos de contenedor ausentes se desactivan (no
    se borran). Las rutas que no existían en la instantánea se
    eliminan junto con sus tarifas y tránsito; el historial de
    cotizaciones no se ve afectado.
    """
    _validar_instantanea(estado)

    resumen = {
        "rutasRestauradas": 0,
        "rutasEliminadas": 0,
        "tarifasRestauradas": 0,
        "contenedoresActualizados": 0,
        "puertosEliminados": 0,
    }

    codigos = set()

    for tipo in estado["tiposContenedor"]:
        codigos.add(tipo["codigo"])
        TipoContenedor.objects.update_or_create(
            codigo=tipo["codigo"],
            defaults={
                "nombre": tipo["nombre"],
                "capacidad_tn": Decimal(tipo["capacidad_tn"]),
                "activo": bool(tipo["activo"]),
            },
        )
        resumen["contenedoresActualizados"] += 1

    TipoContenedor.objects.exclude(codigo__in=codigos).update(
        activo=False
    )

    puertos = {}

    for puerto in estado["puertos"]:
        obj, _ = Puerto.objects.get_or_create(
            nombre=puerto["nombre"],
            pais=puerto["pais"],
        )
        puertos[(puerto["nombre"], puerto["pais"])] = obj

    ids_rutas = set()

    for dato in estado["rutas"]:
        origen = puertos.get((dato["origen"], dato["pais_origen"]))
        destino = puertos.get((dato["destino"], dato["pais_destino"]))

        if origen is None:
            origen, _ = Puerto.objects.get_or_create(
                nombre=dato["origen"], pais=dato["pais_origen"]
            )
        if destino is None:
            destino, _ = Puerto.objects.get_or_create(
                nombre=dato["destino"], pais=dato["pais_destino"]
            )

        ruta, _ = Ruta.objects.update_or_create(
            puerto_origen=origen,
            puerto_destino=destino,
            defaults={"tipo_ruta": dato["tipo_ruta"]},
        )
        ids_rutas.add(ruta.id)
        resumen["rutasRestauradas"] += 1

        codigos_tarifa = set()

        for tarifa in dato["tarifas"]:
            codigos_tarifa.add(tarifa["tipo_contenedor"])
            Tarifa.objects.update_or_create(
                ruta=ruta,
                tipo_contenedor=tarifa["tipo_contenedor"],
                defaults={
                    "valor_minimo": Decimal(tarifa["valor_minimo"]),
                    "valor_maximo": Decimal(tarifa["valor_maximo"]),
                    "fuente": tarifa.get("fuente", ""),
                },
            )
            resumen["tarifasRestauradas"] += 1

        ruta.tarifas.exclude(
            tipo_contenedor__in=codigos_tarifa
        ).delete()

        if dato.get("transito"):
            TiempoTransito.objects.update_or_create(
                ruta=ruta,
                defaults={
                    "dias_minimos": dato["transito"]["dias_minimos"],
                    "dias_maximos": dato["transito"]["dias_maximos"],
                },
            )
        else:
            TiempoTransito.objects.filter(ruta=ruta).delete()

    sobrantes = Ruta.objects.exclude(id__in=ids_rutas)
    resumen["rutasEliminadas"] = sobrantes.count()
    sobrantes.delete()

    claves_puertos = set(puertos)
    huerfanos = [
        puerto.id
        for puerto in Puerto.objects.filter(
            rutas_origen__isnull=True,
            rutas_destino__isnull=True,
        )
        if (puerto.nombre, puerto.pais) not in claves_puertos
    ]
    resumen["puertosEliminados"] = len(huerfanos)
    Puerto.objects.filter(id__in=huerfanos).delete()

    return resumen


# ----------------------------------------------------------------------
# Registro de operaciones
# ----------------------------------------------------------------------


def registrar_operacion(
    tipo,
    usuario,
    estado=OperacionDatosMaestros.Estado.COMPLETADA,
    **campos,
):
    return OperacionDatosMaestros.objects.create(
        tipo=tipo,
        estado=estado,
        usuario=usuario,
        usuario_username=getattr(usuario, "username", "") or "",
        **campos,
    )
