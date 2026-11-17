from werkzeug.security import generate_password_hash
import base_datos
from datos import COLEGIO, CLAVE_PRUEBA, SEDES, GRADOS, PERIODOS, USUARIOS, ACUDIENTES, MATERIAS, GRUPOS, NOTAS


def sembrar():
    anio = COLEGIO["anio"]
    colegio_id = base_datos.ejecutar(
        "INSERT INTO colegios (nombre, nombre_corto, municipio, departamento, lema, anio) VALUES (?, ?, ?, ?, ?, ?)",
        [COLEGIO["nombre"], COLEGIO["nombre_corto"], COLEGIO["municipio"], COLEGIO["departamento"], COLEGIO["lema"], anio],
    )

    sedes = {}
    for sede in SEDES:
        sedes[sede["nombre"]] = base_datos.ejecutar(
            "INSERT INTO sedes (colegio_id, nombre, jornada) VALUES (?, ?, ?)",
            [colegio_id, sede["nombre"], sede["jornada"]],
        )
    primera_sede = sedes[SEDES[0]["nombre"]]

    grados = {}
    orden = 0
    for grado in GRADOS:
        grados[grado["nombre"]] = base_datos.ejecutar(
            "INSERT INTO grados (colegio_id, nombre, nivel, orden) VALUES (?, ?, ?, ?)",
            [colegio_id, grado["nombre"], grado["nivel"], orden],
        )
        orden = orden + 1

    for periodo in PERIODOS:
        base_datos.ejecutar(
            "INSERT INTO periodos (colegio_id, anio, numero, nombre, fecha_inicio, fecha_fin, porcentaje, abierto) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [colegio_id, anio, periodo["numero"], periodo["nombre"], periodo["inicio"], periodo["fin"],
             periodo["porcentaje"], periodo["abierto"]],
        )

    clave_cifrada = generate_password_hash(CLAVE_PRUEBA)
    usuarios = {}
    for persona in USUARIOS:
        usuario_id = base_datos.ejecutar(
            "INSERT INTO usuarios (colegio_id, usuario, clave, nombre) VALUES (?, ?, ?, ?)",
            [colegio_id, persona["usuario"], clave_cifrada, persona["nombre"]],
        )
        usuarios[persona["usuario"]] = usuario_id
        for rol in persona["roles"]:
            base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [usuario_id, rol])

    for relacion in ACUDIENTES:
        base_datos.ejecutar(
            "INSERT INTO acudientes (colegio_id, acudiente_id, estudiante_id, parentesco) VALUES (?, ?, ?, ?)",
            [colegio_id, usuarios[relacion["acudiente"]], usuarios[relacion["estudiante"]], relacion["parentesco"]],
        )

    materias = {}
    for materia in MATERIAS:
        materias[materia["clave"]] = base_datos.ejecutar(
            "INSERT INTO materias (colegio_id, nombre, corto, area) VALUES (?, ?, ?, ?)",
            [colegio_id, materia["nombre"], materia["corto"], materia["area"]],
        )

    for grupo in GRUPOS:
        grupo_id = base_datos.ejecutar(
            "INSERT INTO grupos (colegio_id, anio, grado_id, sede_id, nombre, director_id) VALUES (?, ?, ?, ?, ?, ?)",
            [colegio_id, anio, grados[grupo["grado"]], primera_sede, grupo["nombre"], usuarios[grupo["director"]]],
        )
        for estudiante in grupo["estudiantes"]:
            base_datos.ejecutar(
                "INSERT INTO matriculas (colegio_id, anio, estudiante_id, grupo_id, fecha_matricula) VALUES (?, ?, ?, ?, ?)",
                [colegio_id, anio, usuarios[estudiante], grupo_id, PERIODOS[0]["inicio"]],
            )
        for materia in MATERIAS:
            base_datos.ejecutar(
                "INSERT INTO asignaciones (colegio_id, grupo_id, materia_id, docente_id, horas_semana) VALUES (?, ?, ?, ?, ?)",
                [colegio_id, grupo_id, materias[materia["clave"]], usuarios[materia["profesor"]], materia["horas"]],
            )

    conexion = base_datos.conectar()
    for estudiante in NOTAS:
        for clave in NOTAS[estudiante]:
            lista = NOTAS[estudiante][clave]
            for p in range(len(lista)):
                if lista[p] is not None:
                    conexion.execute(
                        "INSERT INTO notas (colegio_id, anio, estudiante_id, materia_id, periodo, valor) VALUES (?, ?, ?, ?, ?, ?)",
                        [colegio_id, anio, usuarios[estudiante], materias[clave], p + 1, lista[p]],
                    )
    conexion.commit()
    conexion.close()
