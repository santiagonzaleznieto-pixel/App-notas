from datetime import date, timedelta
from flask import g, render_template, request, redirect
from nucleo import (app, agregar_menu, tiene_rol, tiene_alguno, numero, hoy, ahora, registrar,
                    puede_ver_grupo, puede_ver_estudiante, estudiante_del_colegio, grupo_del_estudiante,
                    DIRECTIVOS)
import base_datos

HORAS_SOCIALES = 80
HORAS_CONSTITUCIONALES = 50
MAXIMO_HORAS_DIA = 8
NIVEL_MEDIA = "Media"
ROLES_HORAS = ["coordinador", "rector", "administrador", "docente", "director", "orientador"]
GESTIONAN_PROYECTOS = ["coordinador", "administrador"]
EMITEN_CERTIFICADOS = ["secretaria", "administrador", "rector", "coordinador"]
TIPOS_HORAS = {"social": "Servicio social", "constitucional": "Estudios constitucionales"}
ESTADOS_HORAS = {"pendiente": "Pendiente", "aprobada": "Aprobada", "rechazada": "Rechazada"}
CLASES_ESTADOS = {"pendiente": "atencion", "aprobada": "bien", "rechazada": "mal"}
CERTIFICADO_DE_TIPO = {"social": "servicio_social", "constitucional": "estudios_constitucionales"}
CAMPOS_PROYECTO = ["nombre", "descripcion", "entidad_aliada", "lugar", "responsable_id", "cupos", "activo"]

TABLAS_HORAS = """
CREATE TABLE IF NOT EXISTS proyectos_sociales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    anio INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    descripcion TEXT NOT NULL DEFAULT '',
    entidad_aliada TEXT NOT NULL DEFAULT '',
    lugar TEXT NOT NULL DEFAULT '',
    responsable_id INTEGER NOT NULL REFERENCES usuarios(id),
    cupos INTEGER NOT NULL,
    activo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS inscripciones_sociales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    proyecto_id INTEGER NOT NULL REFERENCES proyectos_sociales(id),
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    inscrito_en TEXT NOT NULL,
    UNIQUE (proyecto_id, estudiante_id)
);

CREATE TABLE IF NOT EXISTS horas_registradas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('social', 'constitucional')),
    proyecto_id INTEGER REFERENCES proyectos_sociales(id),
    fecha TEXT NOT NULL,
    horas REAL NOT NULL,
    actividad TEXT NOT NULL,
    evidencia TEXT NOT NULL DEFAULT '',
    estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'aprobada', 'rechazada')),
    registrado_por INTEGER NOT NULL REFERENCES usuarios(id),
    registrado_en TEXT NOT NULL,
    revisado_por INTEGER REFERENCES usuarios(id),
    revisado_en TEXT NOT NULL DEFAULT '',
    observacion TEXT NOT NULL DEFAULT ''
);
"""

CONSULTA_PROYECTOS = (
    "SELECT proyectos_sociales.*, usuarios.nombre AS responsable, "
    "(SELECT COUNT(*) FROM inscripciones_sociales WHERE inscripciones_sociales.proyecto_id = proyectos_sociales.id) AS inscritos "
    "FROM proyectos_sociales JOIN usuarios ON usuarios.id = proyectos_sociales.responsable_id "
)

CONSULTA_REGISTROS = (
    "SELECT horas_registradas.*, estudiantes.nombre AS estudiante, proyectos_sociales.nombre AS proyecto, "
    "proyectos_sociales.responsable_id AS responsable_id, revisores.nombre AS revisor "
    "FROM horas_registradas JOIN usuarios AS estudiantes ON estudiantes.id = horas_registradas.estudiante_id "
    "LEFT JOIN proyectos_sociales ON proyectos_sociales.id = horas_registradas.proyecto_id "
    "LEFT JOIN usuarios AS revisores ON revisores.id = horas_registradas.revisado_por "
)

PROYECTOS_EJEMPLO = [
    {"clave": "alfabetizacion", "nombre": "Alfabetización digital para adultos mayores",
     "descripcion": "Los estudiantes enseñan a los adultos mayores del municipio a usar el celular, WhatsApp, el correo "
                    "y los trámites en línea, con guías sencillas preparadas en la clase de Tecnología.",
     "entidad": "Biblioteca Pública Municipal de Pijao", "lugar": "Sala de sistemas de la biblioteca municipal",
     "responsable": "j.estrada", "cupos": 8},
    {"clave": "huerta", "nombre": "Huerta escolar y café",
     "descripcion": "Recuperación de la huerta del colegio: semilleros de café, hortalizas y aromáticas, compostaje y "
                    "registro del crecimiento de las plantas para el proyecto ambiental escolar.",
     "entidad": "Asociación de caficultores de Pijao", "lugar": "Huerta del colegio, sede principal",
     "responsable": "s.grajales", "cupos": 10},
    {"clave": "cultura", "nombre": "Apoyo en la Casa de la Cultura",
     "descripcion": "Acompañamiento a los talleres de lectura, música y danza para niños, préstamo de libros y apoyo en "
                    "la organización de los eventos culturales del municipio.",
     "entidad": "Casa de la Cultura de Pijao", "lugar": "Casa de la Cultura, parque principal",
     "responsable": "a.trejos", "cupos": 6},
]

INSCRIPCIONES_EJEMPLO = [
    {"estudiante": "esteban.ramirez", "proyecto": "alfabetizacion", "fecha": "2026-02-02"},
    {"estudiante": "luisa.montoya", "proyecto": "alfabetizacion", "fecha": "2026-02-02"},
    {"estudiante": "valentina.arias", "proyecto": "alfabetizacion", "fecha": "2026-03-02"},
    {"estudiante": "andres.quintero", "proyecto": "huerta", "fecha": "2026-02-03"},
    {"estudiante": "kevin.largo", "proyecto": "huerta", "fecha": "2026-02-03"},
    {"estudiante": "juan.restrepo", "proyecto": "huerta", "fecha": "2026-03-03"},
    {"estudiante": "daniela.cardona", "proyecto": "cultura", "fecha": "2026-02-04"},
    {"estudiante": "melany.osorio", "proyecto": "cultura", "fecha": "2026-03-04"},
    {"estudiante": "sharon.loaiza", "proyecto": "cultura", "fecha": "2026-03-04"},
]

HORAS_EJEMPLO = [
    {"estudiante": "luisa.montoya", "tipo": "social", "proyecto": "alfabetizacion", "inicio": "2026-02-07", "sesiones": 20, "horas": 4, "extra": 2},
    {"estudiante": "luisa.montoya", "tipo": "constitucional", "proyecto": "", "inicio": "2026-02-11", "sesiones": 12, "horas": 4, "extra": 2},
    {"estudiante": "esteban.ramirez", "tipo": "social", "proyecto": "alfabetizacion", "inicio": "2026-02-14", "sesiones": 16, "horas": 4, "extra": 0},
    {"estudiante": "esteban.ramirez", "tipo": "constitucional", "proyecto": "", "inicio": "2026-02-11", "sesiones": 10, "horas": 4, "extra": 0},
    {"estudiante": "andres.quintero", "tipo": "social", "proyecto": "huerta", "inicio": "2026-03-07", "sesiones": 5, "horas": 4, "extra": 0},
    {"estudiante": "daniela.cardona", "tipo": "social", "proyecto": "cultura", "inicio": "2026-02-21", "sesiones": 11, "horas": 4, "extra": 0},
    {"estudiante": "daniela.cardona", "tipo": "constitucional", "proyecto": "", "inicio": "2026-02-11", "sesiones": 6, "horas": 5, "extra": 0},
    {"estudiante": "melany.osorio", "tipo": "social", "proyecto": "cultura", "inicio": "2026-03-14", "sesiones": 3, "horas": 4, "extra": 0},
    {"estudiante": "melany.osorio", "tipo": "constitucional", "proyecto": "", "inicio": "2026-08-05", "sesiones": 2, "horas": 5, "extra": 0},
    {"estudiante": "juan.restrepo", "tipo": "social", "proyecto": "huerta", "inicio": "2026-03-14", "sesiones": 2, "horas": 3, "extra": 0},
    {"estudiante": "valentina.arias", "tipo": "social", "proyecto": "alfabetizacion", "inicio": "2026-03-21", "sesiones": 4, "horas": 4, "extra": 0},
    {"estudiante": "sharon.loaiza", "tipo": "social", "proyecto": "cultura", "inicio": "2026-04-11", "sesiones": 2, "horas": 4, "extra": 0},
]

PENDIENTES_EJEMPLO = [
    {"estudiante": "esteban.ramirez", "tipo": "social", "proyecto": "alfabetizacion", "fecha": "2026-11-14", "horas": 4,
     "actividad": "Clase de trámites en línea: citas médicas y certificados de la EPS",
     "evidencia": "Planilla de asistencia firmada por seis adultos mayores"},
    {"estudiante": "andres.quintero", "tipo": "social", "proyecto": "huerta", "fecha": "2026-11-13", "horas": 3,
     "actividad": "Trasplante de colinos de café a bolsas y abonado de las eras",
     "evidencia": "Fotos en la bitácora de la huerta"},
    {"estudiante": "esteban.ramirez", "tipo": "constitucional", "proyecto": "", "fecha": "2026-11-12", "horas": 4,
     "actividad": "Foro: la Constitución de 1991 y los jóvenes",
     "evidencia": "Relatoría del foro entregada al profesor de Ciencias Sociales"},
]

ACTIVIDADES_EJEMPLO = {
    "alfabetizacion": ["Clase de manejo básico del celular con adultos mayores", "Taller de WhatsApp y videollamadas",
                       "Acompañamiento para pedir citas médicas en línea", "Práctica de correo electrónico y fotos"],
    "huerta": ["Preparación de eras y abono orgánico", "Siembra de colinos de café en el semillero",
               "Riego, deshierbe y registro de crecimiento", "Compostaje con residuos del restaurante escolar"],
    "cultura": ["Apoyo en el taller de lectura para niños", "Organización y préstamo de libros",
                "Acompañamiento al ensayo de danza folclórica", "Logística del evento cultural del fin de semana"],
    "constitucional": ["Cátedra de Constitución: estructura del Estado", "Taller sobre derechos fundamentales y la tutela",
                       "Foro sobre mecanismos de participación ciudadana", "Gobierno escolar y elección del personero",
                       "Lectura y análisis de la Constitución de 1991"],
}

EVIDENCIAS_EJEMPLO = {
    "alfabetizacion": "Planilla de asistencia firmada por la bibliotecaria",
    "huerta": "Registro fotográfico y bitácora de la huerta",
    "cultura": "Constancia de la coordinadora de la Casa de la Cultura",
    "constitucional": "Lista de asistencia y taller resuelto",
}

base_datos.crear_tablas(TABLAS_HORAS)

agregar_menu("horas", "Horas sociales", "/horas", ROLES_HORAS,
             "Proyectos de servicio social, aprobación de horas y avance de 10° y 11°.")
agregar_menu("mis_horas", "Mis horas sociales", "/mis-horas", ["estudiante"],
             "Tu avance hacia las 80 horas sociales y las 50 constitucionales.")


@app.template_filter("cifra_horas")
def cifra_horas(valor):
    if valor is None:
        return "0"
    if valor == int(valor):
        return str(int(valor))
    return str(round(valor, 1)).replace(".", ",")


def entero(texto, minimo, maximo):
    valor = numero(texto, minimo, maximo)
    if valor is None or valor != int(valor):
        return None
    return int(valor)


def fecha_valida(texto):
    if len(texto) != 10 or texto[4] != "-" or texto[7] != "-":
        return False
    for posicion in range(10):
        if posicion != 4 and posicion != 7 and texto[posicion] not in "0123456789":
            return False
    mes = int(texto[5:7])
    dia = int(texto[8:10])
    if mes < 1 or mes > 12 or dia < 1 or dia > 31:
        return False
    return True


def tabla_existe(nombre):
    fila = base_datos.consultar_uno("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", [nombre])
    return fila is not None


def es_de_media(grupo):
    return grupo is not None and grupo["nivel"] == NIVEL_MEDIA


def grados_de_media():
    ids = []
    ultimo = None
    for grado in base_datos.grados_del_colegio(g.colegio["id"]):
        if grado["nivel"] == NIVEL_MEDIA:
            ids.append(grado["id"])
            if ultimo is None or grado["orden"] > ultimo:
                ultimo = grado["orden"]
    return {"ids": ids, "ultimo": ultimo}


def es_ultimo_grado(grupo):
    if not es_de_media(grupo):
        return False
    ultimo = grados_de_media()["ultimo"]
    for grado in base_datos.grados_del_colegio(g.colegio["id"]):
        if grado["id"] == grupo["grado_id"]:
            return grado["orden"] == ultimo
    return False


def resumen_de(estudiante_id):
    resumen = {
        "social": {
            "titulo": "Servicio social estudiantil",
            "norma": "Resolución 4210 de 1996: mínimo " + str(HORAS_SOCIALES) + " horas en un proyecto pedagógico durante 10° y 11°.",
            "meta": HORAS_SOCIALES,
        },
        "constitucional": {
            "titulo": "Estudios constitucionales",
            "norma": "Ley 107 de 1994: " + str(HORAS_CONSTITUCIONALES) + " horas de estudios constitucionales.",
            "meta": HORAS_CONSTITUCIONALES,
        },
    }
    for tipo in resumen:
        for estado in ESTADOS_HORAS:
            resumen[tipo][estado] = 0
    filas = base_datos.consultar(
        "SELECT tipo, estado, SUM(horas) AS total FROM horas_registradas "
        "WHERE colegio_id = ? AND estudiante_id = ? GROUP BY tipo, estado",
        [g.colegio["id"], estudiante_id],
    )
    for fila in filas:
        if fila["tipo"] in resumen and fila["estado"] in ESTADOS_HORAS:
            resumen[fila["tipo"]][fila["estado"]] = round(fila["total"], 1)
    for tipo in resumen:
        datos = resumen[tipo]
        porcentaje = int(datos["aprobada"] * 100 / datos["meta"])
        if porcentaje > 100:
            porcentaje = 100
        faltan = round(datos["meta"] - datos["aprobada"], 1)
        if faltan < 0:
            faltan = 0
        datos["porcentaje"] = porcentaje
        datos["faltan"] = faltan
        datos["cumplido"] = datos["aprobada"] >= datos["meta"]
    return resumen


def registros_de(estudiante_id):
    return base_datos.consultar(
        CONSULTA_REGISTROS + "WHERE horas_registradas.colegio_id = ? AND horas_registradas.estudiante_id = ? "
        "ORDER BY horas_registradas.fecha DESC, horas_registradas.id DESC",
        [g.colegio["id"], estudiante_id],
    )


def buscar_registro(registro_id):
    if registro_id is None:
        return None
    return base_datos.consultar_uno(
        CONSULTA_REGISTROS + "WHERE horas_registradas.id = ? AND horas_registradas.colegio_id = ?",
        [registro_id, g.colegio["id"]],
    )


def pendientes_para(yo):
    filas = []
    if tiene_rol(yo, "coordinador"):
        filas = base_datos.consultar(
            CONSULTA_REGISTROS + "WHERE horas_registradas.colegio_id = ? AND horas_registradas.estado = 'pendiente' "
            "ORDER BY horas_registradas.fecha, horas_registradas.id",
            [g.colegio["id"]],
        )
    elif tiene_rol(yo, "docente"):
        filas = base_datos.consultar(
            CONSULTA_REGISTROS + "WHERE horas_registradas.colegio_id = ? AND horas_registradas.estado = 'pendiente' "
            "AND horas_registradas.tipo = 'social' AND proyectos_sociales.responsable_id = ? "
            "ORDER BY horas_registradas.fecha, horas_registradas.id",
            [g.colegio["id"], yo["id"]],
        )
    for fila in filas:
        grupo = grupo_del_estudiante(fila["estudiante_id"])
        fila["grupo"] = ""
        if grupo is not None:
            fila["grupo"] = grupo["nombre"]
    return filas


def puede_revisar(yo, registro):
    if yo is None or registro is None or registro["colegio_id"] != yo["colegio_id"]:
        return False
    if tiene_rol(yo, "coordinador"):
        return True
    return registro["tipo"] == "social" and tiene_rol(yo, "docente") and registro["responsable_id"] == yo["id"]


def responsable_de_alguno(yo):
    fila = base_datos.consultar_uno(
        "SELECT id FROM proyectos_sociales WHERE colegio_id = ? AND responsable_id = ? LIMIT 1",
        [g.colegio["id"], yo["id"]],
    )
    return fila is not None


def completar_proyecto(proyecto):
    proyecto["libres"] = proyecto["cupos"] - proyecto["inscritos"]
    if proyecto["libres"] < 0:
        proyecto["libres"] = 0
    porcentaje = int(proyecto["inscritos"] * 100 / proyecto["cupos"])
    if porcentaje > 100:
        porcentaje = 100
    proyecto["porcentaje"] = porcentaje
    return proyecto


def proyectos_del_anio():
    lista = []
    filas = base_datos.consultar(
        CONSULTA_PROYECTOS + "WHERE proyectos_sociales.colegio_id = ? AND proyectos_sociales.anio = ? ORDER BY proyectos_sociales.nombre",
        [g.colegio["id"], g.colegio["anio"]],
    )
    for proyecto in filas:
        lista.append(completar_proyecto(proyecto))
    return lista


def buscar_proyecto(proyecto_id):
    if proyecto_id is None:
        return None
    proyecto = base_datos.consultar_uno(
        CONSULTA_PROYECTOS + "WHERE proyectos_sociales.id = ? AND proyectos_sociales.colegio_id = ?",
        [proyecto_id, g.colegio["id"]],
    )
    if proyecto is None:
        return None
    return completar_proyecto(proyecto)


def proyectos_inscritos(estudiante_id):
    return base_datos.consultar(
        CONSULTA_PROYECTOS + "JOIN inscripciones_sociales AS mia ON mia.proyecto_id = proyectos_sociales.id "
        "WHERE mia.estudiante_id = ? AND proyectos_sociales.colegio_id = ? "
        "ORDER BY proyectos_sociales.anio DESC, proyectos_sociales.nombre",
        [estudiante_id, g.colegio["id"]],
    )


def esta_inscrito(estudiante_id, proyecto_id):
    fila = base_datos.consultar_uno(
        "SELECT id FROM inscripciones_sociales WHERE colegio_id = ? AND estudiante_id = ? AND proyecto_id = ?",
        [g.colegio["id"], estudiante_id, proyecto_id],
    )
    return fila is not None


def inscritos_del_proyecto(proyecto_id):
    inscritos = base_datos.consultar(
        "SELECT usuarios.id, usuarios.nombre, usuarios.colegio_id, inscripciones_sociales.inscrito_en, "
        "(SELECT SUM(horas) FROM horas_registradas WHERE horas_registradas.estudiante_id = usuarios.id "
        "AND horas_registradas.proyecto_id = inscripciones_sociales.proyecto_id AND horas_registradas.estado = 'aprobada') AS aprobadas, "
        "(SELECT SUM(horas) FROM horas_registradas WHERE horas_registradas.estudiante_id = usuarios.id "
        "AND horas_registradas.proyecto_id = inscripciones_sociales.proyecto_id AND horas_registradas.estado = 'pendiente') AS pendientes "
        "FROM inscripciones_sociales JOIN usuarios ON usuarios.id = inscripciones_sociales.estudiante_id "
        "WHERE inscripciones_sociales.proyecto_id = ? AND inscripciones_sociales.colegio_id = ? ORDER BY usuarios.nombre",
        [proyecto_id, g.colegio["id"]],
    )
    for persona in inscritos:
        persona["grupo"] = ""
        grupo = grupo_del_estudiante(persona["id"])
        if grupo is not None:
            persona["grupo"] = grupo["nombre"]
        persona["visible"] = puede_ver_estudiante(g.yo, base_datos.buscar_usuario_por_id(persona["id"]))
    return inscritos


def horas_del_dia(estudiante_id, fecha):
    fila = base_datos.consultar_uno(
        "SELECT SUM(horas) AS total FROM horas_registradas WHERE colegio_id = ? AND estudiante_id = ? AND fecha = ? AND estado != 'rechazada'",
        [g.colegio["id"], estudiante_id, fecha],
    )
    if fila is None or fila["total"] is None:
        return 0
    return round(fila["total"], 1)


def es_docente_activo(usuario_id):
    for docente in base_datos.usuarios_con_rol(g.colegio["id"], "docente"):
        if docente["id"] == usuario_id:
            return True
    return False


def nombre_repetido(nombre, anio, proyecto_id):
    fila = base_datos.consultar_uno(
        "SELECT id FROM proyectos_sociales WHERE colegio_id = ? AND anio = ? AND lower(nombre) = lower(?)",
        [g.colegio["id"], anio, nombre],
    )
    return fila is not None and fila["id"] != proyecto_id


def valores_proyecto(origen):
    valores = {}
    for campo in CAMPOS_PROYECTO:
        valor = origen.get(campo, "")
        if valor is None:
            valor = ""
        valores[campo] = str(valor)
    return valores


def revisar_proyecto(formulario, proyecto):
    errores = []
    nombre = formulario.get("nombre", "").strip()
    descripcion = formulario.get("descripcion", "").strip()
    entidad = formulario.get("entidad_aliada", "").strip()
    lugar = formulario.get("lugar", "").strip()
    responsable_id = entero(formulario.get("responsable_id", ""), 1, 1000000000)
    cupos = entero(formulario.get("cupos", ""), 1, 200)
    anio = g.colegio["anio"]
    proyecto_id = None
    activo = 1
    if proyecto is not None:
        anio = proyecto["anio"]
        proyecto_id = proyecto["id"]
        if formulario.get("activo", "") != "1":
            activo = 0

    if len(nombre) < 5 or len(nombre) > 120:
        errores.append("El nombre del proyecto debe tener entre 5 y 120 caracteres.")
    elif nombre_repetido(nombre, anio, proyecto_id):
        errores.append("Ya existe un proyecto con ese nombre en " + str(anio) + ".")
    if len(descripcion) < 10 or len(descripcion) > 1000:
        errores.append("Describe el proyecto pedagógico (entre 10 y 1000 caracteres).")
    if len(lugar) < 3 or len(lugar) > 150:
        errores.append("Escribe el lugar donde se presta el servicio (entre 3 y 150 caracteres).")
    if len(entidad) > 150:
        errores.append("El nombre de la entidad aliada es muy largo (máximo 150 caracteres).")
    if responsable_id is None or not es_docente_activo(responsable_id):
        errores.append("Elige como responsable a un docente activo del colegio.")
    if cupos is None:
        errores.append("Los cupos deben ser un número entero entre 1 y 200.")
    elif proyecto is not None and cupos < proyecto["inscritos"]:
        errores.append("El proyecto ya tiene " + str(proyecto["inscritos"]) + " inscritos: los cupos no pueden ser menos.")

    datos = {"nombre": nombre, "descripcion": descripcion, "entidad_aliada": entidad, "lugar": lugar,
             "responsable_id": responsable_id, "cupos": cupos, "activo": activo}
    return {"errores": errores, "datos": datos}


def revisar_registro(formulario, estudiante_id):
    errores = []
    tipo = formulario.get("tipo", "")
    fecha = formulario.get("fecha", "").strip()
    horas = numero(formulario.get("horas", ""), 0.5, MAXIMO_HORAS_DIA)
    actividad = formulario.get("actividad", "").strip()
    evidencia = formulario.get("evidencia", "").strip()
    proyecto_id = None

    if tipo not in TIPOS_HORAS:
        errores.append("Elige si son horas de servicio social o de estudios constitucionales.")
    elif tipo == "social":
        proyecto_id = entero(formulario.get("proyecto_id", ""), 1, 1000000000)
        if proyecto_id is None or not esta_inscrito(estudiante_id, proyecto_id):
            errores.append("Para horas de servicio social elige un proyecto en el que estés inscrito.")
            proyecto_id = None
    if not fecha_valida(fecha):
        errores.append("Escribe la fecha con el formato AAAA-MM-DD.")
    elif fecha > hoy():
        errores.append("La fecha no puede ser futura.")
    if horas is None:
        errores.append("Las horas deben ser un número entre 0,5 y " + str(MAXIMO_HORAS_DIA) + ".")
    else:
        horas = round(horas, 1)
    if len(actividad) < 5 or len(actividad) > 300:
        errores.append("Describe la actividad que hiciste (entre 5 y 300 caracteres).")
    if len(evidencia) < 3 or len(evidencia) > 300:
        errores.append("Escribe la evidencia: una descripción o un enlace (entre 3 y 300 caracteres).")
    if len(errores) == 0:
        del_dia = horas_del_dia(estudiante_id, fecha)
        if del_dia + horas > MAXIMO_HORAS_DIA:
            errores.append("Ese día ya tienes " + cifra_horas(del_dia) + " horas registradas y en un día no se pueden pasar de "
                           + str(MAXIMO_HORAS_DIA) + ".")

    datos = {"tipo": tipo, "proyecto_id": proyecto_id, "fecha": fecha, "horas": horas,
             "actividad": actividad, "evidencia": evidencia}
    return {"errores": errores, "datos": datos}


def certificados_vigentes(estudiante_id):
    codigos = {"social": "", "constitucional": ""}
    if not tabla_existe("certificados"):
        return codigos
    for tipo in codigos:
        fila = base_datos.consultar_uno(
            "SELECT codigo FROM certificados WHERE colegio_id = ? AND estudiante_id = ? AND tipo = ? AND anulado = 0 "
            "ORDER BY id DESC LIMIT 1",
            [g.colegio["id"], estudiante_id, CERTIFICADO_DE_TIPO[tipo]],
        )
        if fila is not None:
            codigos[tipo] = fila["codigo"]
    return codigos


def ficha_de(estudiante):
    grupo = grupo_del_estudiante(estudiante["id"])
    return {
        "estudiante": estudiante,
        "grupo": grupo,
        "de_media": es_de_media(grupo),
        "ultimo_grado": es_ultimo_grado(grupo),
        "resumen": resumen_de(estudiante["id"]),
        "registros": registros_de(estudiante["id"]),
        "inscripciones": proyectos_inscritos(estudiante["id"]),
        "certificados": certificados_vigentes(estudiante["id"]),
    }


def avance_de_grupos():
    media = grados_de_media()
    lista = []
    for grupo in base_datos.grupos_del_colegio(g.colegio["id"], g.colegio["anio"]):
        if grupo["grado_id"] in media["ids"] and puede_ver_grupo(g.yo, grupo):
            filas = []
            sociales = 0
            constitucionales = 0
            for estudiante in base_datos.estudiantes_del_grupo(grupo["id"]):
                resumen = resumen_de(estudiante["id"])
                if resumen["social"]["cumplido"]:
                    sociales = sociales + 1
                if resumen["constitucional"]["cumplido"]:
                    constitucionales = constitucionales + 1
                filas.append({"estudiante": estudiante, "resumen": resumen})
            lista.append({"grupo": grupo, "filas": filas, "ultimo": grupo["orden_grado"] == media["ultimo"],
                          "sociales": sociales, "constitucionales": constitucionales})
    return lista


def alertas_de(grupos):
    alertas = []
    for item in grupos:
        if item["ultimo"]:
            for fila in item["filas"]:
                social = fila["resumen"]["social"]
                constitucional = fila["resumen"]["constitucional"]
                faltantes = []
                if not social["cumplido"]:
                    faltantes.append(cifra_horas(social["faltan"]) + " horas de servicio social")
                if not constitucional["cumplido"]:
                    faltantes.append(cifra_horas(constitucional["faltan"]) + " de estudios constitucionales")
                if len(faltantes) > 0:
                    alertas.append({"estudiante": fila["estudiante"], "grupo": item["grupo"]["nombre"],
                                    "texto": "Le faltan " + " y ".join(faltantes) + "."})
    return alertas


@app.route("/horas", methods=["GET", "POST"])
def horas_panel():
    if not tiene_alguno(g.yo, ROLES_HORAS):
        return redirect("/inicio")

    gestiona = tiene_alguno(g.yo, GESTIONAN_PROYECTOS)
    errores = []
    mensaje = ""
    valores = valores_proyecto({})
    if request.method == "POST":
        accion = request.form.get("accion", "")
        if accion == "crear_proyecto":
            if not gestiona:
                return redirect("/inicio")
            revision = revisar_proyecto(request.form, None)
            errores = revision["errores"]
            datos = revision["datos"]
            if len(errores) == 0:
                base_datos.ejecutar(
                    "INSERT INTO proyectos_sociales (colegio_id, anio, nombre, descripcion, entidad_aliada, lugar, responsable_id, cupos, activo) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)",
                    [g.colegio["id"], g.colegio["anio"], datos["nombre"], datos["descripcion"], datos["entidad_aliada"],
                     datos["lugar"], datos["responsable_id"], datos["cupos"]],
                )
                registrar("Creó proyecto de servicio social", datos["nombre"])
                mensaje = "Proyecto «" + datos["nombre"] + "» creado. Los estudiantes de 10° y 11° ya pueden inscribirse."
            else:
                valores = valores_proyecto(request.form)
        elif accion == "revisar":
            registro = buscar_registro(entero(request.form.get("registro_id", ""), 1, 1000000000))
            if not puede_revisar(g.yo, registro):
                return redirect("/inicio")
            decision = request.form.get("decision", "")
            observacion = request.form.get("observacion", "").strip()
            if registro["estado"] != "pendiente":
                errores.append("Ese registro ya fue revisado.")
            elif decision not in ["aprobada", "rechazada"]:
                errores.append("Elige si apruebas o rechazas las horas.")
            elif decision == "rechazada" and observacion == "":
                errores.append("Escribe una observación para explicarle al estudiante por qué se rechazan las horas.")
            elif len(observacion) > 300:
                errores.append("La observación puede tener máximo 300 caracteres.")
            else:
                base_datos.ejecutar(
                    "UPDATE horas_registradas SET estado = ?, revisado_por = ?, revisado_en = ?, observacion = ? "
                    "WHERE id = ? AND colegio_id = ?",
                    [decision, g.yo["id"], ahora(), observacion, registro["id"], g.colegio["id"]],
                )
                detalle = registro["estudiante"] + ": " + cifra_horas(registro["horas"]) + " h de " + TIPOS_HORAS[registro["tipo"]].lower()
                if decision == "aprobada":
                    registrar("Aprobó horas sociales", detalle)
                    mensaje = "Horas aprobadas. " + detalle + "."
                else:
                    registrar("Rechazó horas sociales", detalle)
                    mensaje = "Horas rechazadas. " + detalle + "."

    ve_todos_los_proyectos = tiene_alguno(g.yo, DIRECTIVOS)
    proyectos = []
    for proyecto in proyectos_del_anio():
        if ve_todos_los_proyectos or proyecto["responsable_id"] == g.yo["id"]:
            proyectos.append(proyecto)
    revisa = tiene_rol(g.yo, "coordinador") or (tiene_rol(g.yo, "docente") and responsable_de_alguno(g.yo))
    pendientes = []
    if revisa:
        pendientes = pendientes_para(g.yo)
    grupos = avance_de_grupos()
    alertas = alertas_de(grupos)
    cifras = {"estudiantes": 0, "sociales": 0, "constitucionales": 0}
    for item in grupos:
        cifras["estudiantes"] = cifras["estudiantes"] + len(item["filas"])
        cifras["sociales"] = cifras["sociales"] + item["sociales"]
        cifras["constitucionales"] = cifras["constitucionales"] + item["constitucionales"]
    docentes = []
    if gestiona:
        docentes = base_datos.usuarios_con_rol(g.colegio["id"], "docente")

    return render_template("horas.html", activo="horas", gestiona=gestiona, revisa=revisa, proyectos=proyectos,
                           pendientes=pendientes, grupos=grupos, alertas=alertas, cifras=cifras, docentes=docentes,
                           valores=valores, errores=errores, mensaje=mensaje, tipos=TIPOS_HORAS,
                           horas_sociales=HORAS_SOCIALES, horas_constitucionales=HORAS_CONSTITUCIONALES)


@app.route("/horas/proyecto/<int:proyecto_id>", methods=["GET", "POST"])
def horas_proyecto(proyecto_id):
    if g.yo is None:
        return redirect("/")
    proyecto = buscar_proyecto(proyecto_id)
    if proyecto is None:
        return redirect("/inicio")
    gestiona = tiene_alguno(g.yo, GESTIONAN_PROYECTOS)
    if not tiene_alguno(g.yo, DIRECTIVOS) and proyecto["responsable_id"] != g.yo["id"]:
        return redirect("/inicio")

    errores = []
    mensaje = ""
    valores = valores_proyecto(proyecto)
    if request.method == "POST":
        if not gestiona:
            return redirect("/inicio")
        revision = revisar_proyecto(request.form, proyecto)
        errores = revision["errores"]
        datos = revision["datos"]
        if len(errores) == 0:
            base_datos.ejecutar(
                "UPDATE proyectos_sociales SET nombre = ?, descripcion = ?, entidad_aliada = ?, lugar = ?, responsable_id = ?, "
                "cupos = ?, activo = ? WHERE id = ? AND colegio_id = ?",
                [datos["nombre"], datos["descripcion"], datos["entidad_aliada"], datos["lugar"], datos["responsable_id"],
                 datos["cupos"], datos["activo"], proyecto["id"], g.colegio["id"]],
            )
            registrar("Editó proyecto de servicio social", datos["nombre"])
            mensaje = "Cambios guardados."
            proyecto = buscar_proyecto(proyecto_id)
            valores = valores_proyecto(proyecto)
        else:
            valores = valores_proyecto(request.form)

    inscritos = inscritos_del_proyecto(proyecto_id)
    total_aprobadas = 0
    for persona in inscritos:
        if persona["aprobadas"] is not None:
            total_aprobadas = total_aprobadas + persona["aprobadas"]
    docentes = []
    if gestiona:
        docentes = base_datos.usuarios_con_rol(g.colegio["id"], "docente")

    return render_template("horas_proyecto.html", activo="horas", proyecto=proyecto, inscritos=inscritos,
                           total_aprobadas=round(total_aprobadas, 1), gestiona=gestiona, docentes=docentes,
                           valores=valores, errores=errores, mensaje=mensaje)


@app.route("/mis-horas", methods=["GET", "POST"])
def horas_mias():
    if not tiene_rol(g.yo, "estudiante"):
        return redirect("/inicio")

    errores = []
    mensaje = ""
    formulario = {"tipo": "social", "proyecto_id": "", "fecha": hoy(), "horas": "", "actividad": "", "evidencia": ""}
    grupo = grupo_del_estudiante(g.yo["id"])
    if es_de_media(grupo) and request.method == "POST":
        accion = request.form.get("accion", "")
        if accion == "inscribir":
            proyecto = buscar_proyecto(entero(request.form.get("proyecto_id", ""), 1, 1000000000))
            if proyecto is None or proyecto["anio"] != g.colegio["anio"] or proyecto["activo"] == 0:
                errores.append("Ese proyecto no está disponible para inscripciones.")
            elif esta_inscrito(g.yo["id"], proyecto["id"]):
                errores.append("Ya estás inscrito en «" + proyecto["nombre"] + "».")
            elif proyecto["inscritos"] >= proyecto["cupos"]:
                errores.append("El proyecto «" + proyecto["nombre"] + "» ya no tiene cupos.")
            else:
                base_datos.ejecutar(
                    "INSERT INTO inscripciones_sociales (colegio_id, proyecto_id, estudiante_id, inscrito_en) VALUES (?, ?, ?, ?)",
                    [g.colegio["id"], proyecto["id"], g.yo["id"], ahora()],
                )
                registrar("Se inscribió en proyecto de servicio social", proyecto["nombre"])
                mensaje = "Quedaste inscrito en «" + proyecto["nombre"] + "». Ya puedes registrar tus horas en ese proyecto."
        elif accion == "registrar":
            revision = revisar_registro(request.form, g.yo["id"])
            errores = revision["errores"]
            datos = revision["datos"]
            if len(errores) == 0:
                base_datos.ejecutar(
                    "INSERT INTO horas_registradas (colegio_id, estudiante_id, tipo, proyecto_id, fecha, horas, actividad, evidencia, "
                    "estado, registrado_por, registrado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?, ?)",
                    [g.colegio["id"], g.yo["id"], datos["tipo"], datos["proyecto_id"], datos["fecha"], datos["horas"],
                     datos["actividad"], datos["evidencia"], g.yo["id"], ahora()],
                )
                registrar("Registró horas sociales", cifra_horas(datos["horas"]) + " h de " + TIPOS_HORAS[datos["tipo"]].lower())
                mensaje = "Registraste " + cifra_horas(datos["horas"]) + " horas. Quedan pendientes hasta que las aprueben."
            else:
                for campo in formulario:
                    formulario[campo] = request.form.get(campo, "")

    ficha = ficha_de(g.yo)
    disponibles = []
    if ficha["de_media"]:
        for proyecto in proyectos_del_anio():
            if proyecto["activo"] == 1 and proyecto["libres"] > 0 and not esta_inscrito(g.yo["id"], proyecto["id"]):
                disponibles.append(proyecto)

    return render_template("horas_mias.html", activo="mis_horas", ficha=ficha, disponibles=disponibles,
                           formulario=formulario, errores=errores, mensaje=mensaje, hoy=hoy(), tipos=TIPOS_HORAS,
                           estados=ESTADOS_HORAS, clases_estados=CLASES_ESTADOS, puede_emitir=False,
                           maximo_dia=MAXIMO_HORAS_DIA)


@app.route("/horas/estudiante/<int:estudiante_id>")
def horas_estudiante(estudiante_id):
    estudiante = estudiante_del_colegio(estudiante_id)
    if not puede_ver_estudiante(g.yo, estudiante):
        return redirect("/inicio")

    activo = "horas"
    volver = ""
    if g.yo["id"] == estudiante["id"]:
        activo = "mis_horas"
    elif tiene_alguno(g.yo, ROLES_HORAS):
        volver = "/horas"
    elif tiene_rol(g.yo, "acudiente"):
        activo = "familia"

    return render_template("horas_estudiante.html", activo=activo, volver=volver, ficha=ficha_de(estudiante),
                           tipos=TIPOS_HORAS, estados=ESTADOS_HORAS, clases_estados=CLASES_ESTADOS,
                           puede_emitir=tiene_alguno(g.yo, EMITEN_CERTIFICADOS))


def fechas_semanales(inicio, cantidad):
    fechas = []
    dia = date.fromisoformat(inicio)
    for semana in range(cantidad):
        fechas.append((dia + timedelta(days=7 * semana)).isoformat())
    return fechas


def dias_despues(fecha, dias):
    return (date.fromisoformat(fecha) + timedelta(days=dias)).isoformat()


def sembrar_horas():
    if not base_datos.tabla_vacia("proyectos_sociales"):
        return
    colegio = base_datos.buscar_colegio(1)
    if colegio is None:
        return
    nombres = ["coordinadora"]
    for proyecto in PROYECTOS_EJEMPLO:
        nombres.append(proyecto["responsable"])
    for inscripcion in INSCRIPCIONES_EJEMPLO:
        nombres.append(inscripcion["estudiante"])
    personas = {}
    for nombre in nombres:
        persona = base_datos.buscar_usuario(nombre)
        if persona is None or persona["colegio_id"] != colegio["id"]:
            return
        personas[nombre] = persona["id"]

    proyectos = {}
    responsables = {}
    for proyecto in PROYECTOS_EJEMPLO:
        proyectos[proyecto["clave"]] = base_datos.ejecutar(
            "INSERT INTO proyectos_sociales (colegio_id, anio, nombre, descripcion, entidad_aliada, lugar, responsable_id, cupos, activo) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)",
            [colegio["id"], colegio["anio"], proyecto["nombre"], proyecto["descripcion"], proyecto["entidad"],
             proyecto["lugar"], personas[proyecto["responsable"]], proyecto["cupos"]],
        )
        responsables[proyecto["clave"]] = personas[proyecto["responsable"]]

    conexion = base_datos.conectar()
    for inscripcion in INSCRIPCIONES_EJEMPLO:
        conexion.execute(
            "INSERT INTO inscripciones_sociales (colegio_id, proyecto_id, estudiante_id, inscrito_en) VALUES (?, ?, ?, ?)",
            [colegio["id"], proyectos[inscripcion["proyecto"]], personas[inscripcion["estudiante"]], inscripcion["fecha"] + " 10:00"],
        )

    for bloque in HORAS_EJEMPLO:
        estudiante_id = personas[bloque["estudiante"]]
        clave = "constitucional"
        proyecto_id = None
        revisor_id = personas["coordinadora"]
        if bloque["proyecto"] != "":
            clave = bloque["proyecto"]
            proyecto_id = proyectos[clave]
            revisor_id = responsables[clave]
        cantidades = []
        for sesion in range(bloque["sesiones"]):
            cantidades.append(bloque["horas"])
        if bloque["extra"] > 0:
            cantidades.append(bloque["extra"])
        fechas = fechas_semanales(bloque["inicio"], len(cantidades))
        actividades = ACTIVIDADES_EJEMPLO[clave]
        for i in range(len(fechas)):
            conexion.execute(
                "INSERT INTO horas_registradas (colegio_id, estudiante_id, tipo, proyecto_id, fecha, horas, actividad, evidencia, "
                "estado, registrado_por, registrado_en, revisado_por, revisado_en, observacion) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'aprobada', ?, ?, ?, ?, '')",
                [colegio["id"], estudiante_id, bloque["tipo"], proyecto_id, fechas[i], cantidades[i],
                 actividades[i % len(actividades)], EVIDENCIAS_EJEMPLO[clave], estudiante_id, fechas[i] + " 19:00",
                 revisor_id, dias_despues(fechas[i], 2) + " 16:00"],
            )

    for pendiente in PENDIENTES_EJEMPLO:
        proyecto_id = None
        if pendiente["proyecto"] != "":
            proyecto_id = proyectos[pendiente["proyecto"]]
        conexion.execute(
            "INSERT INTO horas_registradas (colegio_id, estudiante_id, tipo, proyecto_id, fecha, horas, actividad, evidencia, "
            "estado, registrado_por, registrado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?, ?)",
            [colegio["id"], personas[pendiente["estudiante"]], pendiente["tipo"], proyecto_id, pendiente["fecha"],
             pendiente["horas"], pendiente["actividad"], pendiente["evidencia"], personas[pendiente["estudiante"]],
             pendiente["fecha"] + " 20:10"],
        )

    conexion.execute(
        "INSERT INTO horas_registradas (colegio_id, estudiante_id, tipo, proyecto_id, fecha, horas, actividad, evidencia, "
        "estado, registrado_por, registrado_en, revisado_por, revisado_en, observacion) "
        "VALUES (?, ?, 'social', ?, '2026-10-24', 6, 'Jornada de limpieza de la huerta', 'Ninguna', 'rechazada', ?, "
        "'2026-10-24 21:00', ?, '2026-10-27 15:30', ?)",
        [colegio["id"], personas["kevin.largo"], proyectos["huerta"], personas["kevin.largo"], responsables["huerta"],
         "No apareces en la planilla de asistencia de ese día. Habla con la profesora Sandra."],
    )
    conexion.commit()
    conexion.close()


sembrar_horas()
