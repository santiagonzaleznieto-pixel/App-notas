import secrets
from werkzeug.security import generate_password_hash
import base_datos
from datos import GRADOS

LETRAS = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"


def preguntar(texto, por_defecto):
    respuesta = input(texto + " [" + por_defecto + "]: ").strip()
    if respuesta == "":
        return por_defecto
    return respuesta


def sin_tildes(texto):
    cambios = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
    limpio = ""
    for letra in texto.lower():
        if letra in cambios:
            limpio = limpio + cambios[letra]
        elif letra in "abcdefghijklmnopqrstuvwxyz0123456789":
            limpio = limpio + letra
    return limpio


def usuario_disponible(base):
    candidato = base
    numero = 2
    while base_datos.buscar_usuario(candidato) is not None:
        candidato = base + str(numero)
        numero = numero + 1
    return candidato


def clave_temporal():
    clave = ""
    for i in range(10):
        clave = clave + secrets.choice(LETRAS)
    return clave


def crear():
    base_datos.crear_tablas(base_datos.TABLAS)
    print("Nuevo colegio en la plataforma")
    nombre = preguntar("Nombre completo del colegio", "Institución Educativa Nueva")
    corto = preguntar("Nombre corto", nombre)
    municipio = preguntar("Municipio", "Pijao")
    departamento = preguntar("Departamento", "Quindío")
    anio = int(preguntar("Año escolar", "2027"))
    administrador = preguntar("Nombre de la persona administradora", "Administración del colegio")

    colegio_id = base_datos.ejecutar(
        "INSERT INTO colegios (nombre, nombre_corto, municipio, departamento, anio) VALUES (?, ?, ?, ?, ?)",
        [nombre, corto, municipio, departamento, anio],
    )
    base_datos.ejecutar("INSERT INTO sedes (colegio_id, nombre, jornada) VALUES (?, ?, ?)", [colegio_id, "Sede Principal", "Mañana"])
    orden = 0
    for grado in GRADOS:
        base_datos.ejecutar(
            "INSERT INTO grados (colegio_id, nombre, nivel, orden) VALUES (?, ?, ?, ?)",
            [colegio_id, grado["nombre"], grado["nivel"], orden],
        )
        orden = orden + 1
    fechas = [["01-26", "04-03"], ["04-06", "06-12"], ["07-06", "09-11"], ["09-14", "11-27"]]
    nombres = ["Primer período", "Segundo período", "Tercer período", "Cuarto período"]
    for i in range(4):
        base_datos.ejecutar(
            "INSERT INTO periodos (colegio_id, anio, numero, nombre, fecha_inicio, fecha_fin, porcentaje, abierto) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [colegio_id, anio, i + 1, nombres[i], str(anio) + "-" + fechas[i][0], str(anio) + "-" + fechas[i][1], 25, 1],
        )

    usuario = usuario_disponible("admin." + sin_tildes(corto.split(" ")[-1]))
    clave = clave_temporal()
    usuario_id = base_datos.ejecutar(
        "INSERT INTO usuarios (colegio_id, usuario, clave, nombre, debe_cambiar_clave) VALUES (?, ?, ?, ?, 1)",
        [colegio_id, usuario, generate_password_hash(clave), administrador],
    )
    base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [usuario_id, "administrador"])

    print("")
    print("Colegio creado con el número " + str(colegio_id) + ".")
    print("Usuario administrador: " + usuario)
    print("Clave temporal: " + clave + "  (se pedirá cambiarla al entrar)")
    print("Revisa en Administración las fechas de los períodos, las materias y los grupos.")


crear()
