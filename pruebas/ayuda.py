import os
import sys
import tempfile

CARPETA_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CARPETA_PROYECTO)

import base_datos

base_datos.ARCHIVO = os.path.join(tempfile.mkdtemp(), "prueba.db")

from nucleo import app

app.config["TESTING"] = True

FALLAS = []


def entrar(usuario):
    cliente = app.test_client()
    respuesta = cliente.post("/", data={"usuario": usuario, "clave": "pijao2026"})
    if respuesta.status_code != 302:
        raise SystemExit("No se pudo entrar como " + usuario)
    return cliente


def revisar(descripcion, condicion):
    if condicion:
        print("  bien  " + descripcion)
    else:
        print("  FALLA " + descripcion)
        FALLAS.append(descripcion)


def destino(respuesta):
    return respuesta.headers.get("Location", "")


def terminar():
    print("")
    if len(FALLAS) == 0:
        print("Todas las pruebas pasaron.")
    else:
        print(str(len(FALLAS)) + " pruebas fallaron.")
        raise SystemExit(1)
