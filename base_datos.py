import os
import sqlite3
from werkzeug.security import generate_password_hash
from datos import COLEGIO, MUNICIPIO, DEPARTAMENTO, ANIO, PERIODOS, USUARIOS, MATERIAS, NOTAS

CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))
ARCHIVO = os.path.join(CARPETA_PROYECTO, "plataforma.db")

TABLAS = """
CREATE TABLE IF NOT EXISTS colegios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    municipio TEXT NOT NULL,
    departamento TEXT NOT NULL,
    anio INTEGER NOT NULL,
    periodos INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    usuario TEXT NOT NULL UNIQUE,
    clave TEXT NOT NULL,
    nombre TEXT NOT NULL,
    rol TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS materias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    nombre TEXT NOT NULL,
    corto TEXT NOT NULL,
    profesor TEXT NOT NULL REFERENCES usuarios(usuario)
);

CREATE TABLE IF NOT EXISTS notas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    estudiante TEXT NOT NULL REFERENCES usuarios(usuario),
    materia_id INTEGER NOT NULL REFERENCES materias(id),
    periodo INTEGER NOT NULL,
    valor REAL,
    UNIQUE (estudiante, materia_id, periodo)
);
"""


def conectar():
    conexion = sqlite3.connect(ARCHIVO)
    conexion.row_factory = sqlite3.Row
    return conexion


def consultar(sql, valores):
    conexion = conectar()
    filas = conexion.execute(sql, valores).fetchall()
    conexion.close()
    lista = []
    for fila in filas:
        lista.append(dict(fila))
    return lista


def ejecutar(sql, valores):
    conexion = conectar()
    conexion.execute(sql, valores)
    conexion.commit()
    conexion.close()


def preparar_base():
    conexion = conectar()
    conexion.executescript(TABLAS)
    conexion.close()
    if len(consultar("SELECT id FROM colegios", [])) == 0:
        cargar_datos_iniciales()


def cargar_datos_iniciales():
    conexion = conectar()
    cursor = conexion.execute(
        "INSERT INTO colegios (nombre, municipio, departamento, anio, periodos) VALUES (?, ?, ?, ?, ?)",
        [COLEGIO, MUNICIPIO, DEPARTAMENTO, ANIO, PERIODOS],
    )
    colegio_id = cursor.lastrowid

    for persona in USUARIOS:
        conexion.execute(
            "INSERT INTO usuarios (colegio_id, usuario, clave, nombre, rol) VALUES (?, ?, ?, ?, ?)",
            [colegio_id, persona["usuario"], generate_password_hash(persona["clave"]), persona["nombre"], persona["rol"]],
        )

    nuevos_ids = {}
    for materia in MATERIAS:
        cursor = conexion.execute(
            "INSERT INTO materias (colegio_id, nombre, corto, profesor) VALUES (?, ?, ?, ?)",
            [colegio_id, materia["nombre"], materia["corto"], materia["profesor"]],
        )
        nuevos_ids[materia["id"]] = cursor.lastrowid

    for estudiante in NOTAS:
        for codigo in NOTAS[estudiante]:
            lista = NOTAS[estudiante][codigo]
            for p in range(len(lista)):
                if lista[p] is not None:
                    conexion.execute(
                        "INSERT INTO notas (colegio_id, estudiante, materia_id, periodo, valor) VALUES (?, ?, ?, ?, ?)",
                        [colegio_id, estudiante, nuevos_ids[codigo], p + 1, lista[p]],
                    )

    conexion.commit()
    conexion.close()


def buscar_colegio(colegio_id):
    filas = consultar("SELECT * FROM colegios WHERE id = ?", [colegio_id])
    if len(filas) == 0:
        return None
    return filas[0]


def todos_los_usuarios():
    return consultar("SELECT * FROM usuarios ORDER BY id", [])


def usuarios_del_colegio(colegio_id):
    return consultar("SELECT * FROM usuarios WHERE colegio_id = ? ORDER BY id", [colegio_id])


def materias_del_colegio(colegio_id):
    return consultar("SELECT * FROM materias WHERE colegio_id = ? ORDER BY id", [colegio_id])


def notas_del_colegio(colegio_id, periodos):
    notas = {}
    materias = materias_del_colegio(colegio_id)
    for persona in usuarios_del_colegio(colegio_id):
        if persona["rol"] == "estudiante":
            notas[persona["usuario"]] = {}
            for materia in materias:
                lista = []
                for p in range(periodos):
                    lista.append(None)
                notas[persona["usuario"]][materia["id"]] = lista

    filas = consultar("SELECT estudiante, materia_id, periodo, valor FROM notas WHERE colegio_id = ?", [colegio_id])
    for fila in filas:
        if fila["estudiante"] in notas:
            notas[fila["estudiante"]][fila["materia_id"]][fila["periodo"] - 1] = fila["valor"]
    return notas


def guardar_nota(colegio_id, estudiante, materia_id, periodo, valor):
    ejecutar(
        "INSERT OR REPLACE INTO notas (colegio_id, estudiante, materia_id, periodo, valor) VALUES (?, ?, ?, ?, ?)",
        [colegio_id, estudiante, materia_id, periodo, valor],
    )
