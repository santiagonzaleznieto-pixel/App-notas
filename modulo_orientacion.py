from flask import g, render_template, request, redirect
from nucleo import (app, agregar_menu, tiene_rol, tiene_alguno, dicta_en_grupo, grupo_del_estudiante,
                    estudiante_del_colegio, registrar, hoy, ahora, SEMBRAR)
import base_datos

TABLAS_ORIENTACION = """
CREATE TABLE IF NOT EXISTS atenciones_orientacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    orientador_id INTEGER NOT NULL REFERENCES usuarios(id),
    fecha TEXT NOT NULL,
    motivo TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    acciones TEXT NOT NULL DEFAULT '',
    remision TEXT NOT NULL DEFAULT 'ninguna',
    proxima_cita TEXT NOT NULL DEFAULT '',
    estado TEXT NOT NULL DEFAULT 'abierta',
    creado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS remisiones_docentes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    docente_id INTEGER NOT NULL REFERENCES usuarios(id),
    fecha TEXT NOT NULL,
    motivo TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendiente',
    atendida_en TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS piar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    anio INTEGER NOT NULL,
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    descripcion_estudiante TEXT NOT NULL DEFAULT '',
    barreras TEXT NOT NULL DEFAULT '',
    apoyos_familia TEXT NOT NULL DEFAULT '',
    elaborado_por INTEGER NOT NULL REFERENCES usuarios(id),
    elaborado_en TEXT NOT NULL,
    revisado_acudiente_en TEXT NOT NULL DEFAULT '',
    UNIQUE (anio, estudiante_id)
);

CREATE TABLE IF NOT EXISTS piar_ajustes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    piar_id INTEGER NOT NULL REFERENCES piar(id),
    materia_id INTEGER NOT NULL REFERENCES materias(id),
    objetivo TEXT NOT NULL DEFAULT '',
    ajustes TEXT NOT NULL DEFAULT '',
    evaluacion TEXT NOT NULL DEFAULT '',
    seguimiento TEXT NOT NULL DEFAULT '',
    actualizado_por INTEGER REFERENCES usuarios(id),
    actualizado_en TEXT NOT NULL DEFAULT '',
    UNIQUE (piar_id, materia_id)
);
"""

base_datos.crear_tablas(TABLAS_ORIENTACION)

agregar_menu("orientacion", "Orientación", "/orientacion", ["orientador", "rector", "coordinador"],
             "Atenciones confidenciales, remisiones y PIAR.")
agregar_menu("piar", "PIAR", "/piar", ["docente", "acudiente", "estudiante", "orientador", "coordinador"],
             "Planes individuales de ajustes razonables (Decreto 1421 de 2017).")

MOTIVOS = [
    {"clave": "académico", "nombre": "Académico"},
    {"clave": "emocional", "nombre": "Emocional"},
    {"clave": "familiar", "nombre": "Familiar"},
    {"clave": "convivencia", "nombre": "Convivencia"},
    {"clave": "salud", "nombre": "Salud"},
    {"clave": "otro", "nombre": "Otro"},
]

REMISIONES = [
    {"clave": "ninguna", "nombre": "Sin remisión externa"},
    {"clave": "salud", "nombre": "EPS o servicio de salud"},
    {"clave": "icbf", "nombre": "ICBF"},
    {"clave": "comisaria", "nombre": "Comisaría de Familia"},
    {"clave": "policia", "nombre": "Policía de Infancia y Adolescencia"},
    {"clave": "otra", "nombre": "Otra entidad"},
]

EDITAN_PIAR = ["orientador", "coordinador"]
VEN_PIAR = ["docente", "acudiente", "estudiante", "orientador", "coordinador"]
CAMPOS_GENERALES = ["descripcion_estudiante", "barreras", "apoyos_familia"]
CAMPOS_AJUSTE = ["objetivo", "ajustes", "evaluacion", "seguimiento"]


def claves(opciones):
    lista = []
    for opcion in opciones:
        lista.append(opcion["clave"])
    return lista


def nombres(opciones):
    diccionario = {}
    for opcion in opciones:
        diccionario[opcion["clave"]] = opcion["nombre"]
    return diccionario


def fecha_valida(texto):
    if len(texto) != 10:
        return False
    if texto[4] != "-" or texto[7] != "-":
        return False
    for posicion in range(10):
        if posicion != 4 and posicion != 7 and texto[posicion] not in "0123456789":
            return False
    mes = int(texto[5:7])
    dia = int(texto[8:10])
    if mes < 1 or mes > 12 or dia < 1 or dia > 31:
        return False
    return True


def entero(texto):
    limpio = texto.strip()
    if limpio == "" or len(limpio) > 9:
        return None
    for letra in limpio:
        if letra not in "0123456789":
            return None
    return int(limpio)


def sin_tildes(texto):
    cambios = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
    limpio = texto.lower()
    for letra in cambios:
        limpio = limpio.replace(letra, cambios[letra])
    return limpio


def porcentaje(parte, total):
    if total == 0:
        return 0
    return round(parte * 100 / total)


def contar(sql, valores):
    return base_datos.consultar_uno(sql, valores)["cantidad"]


def nombre_grupo(estudiante_id):
    grupo = grupo_del_estudiante(estudiante_id)
    if grupo is None:
        return "Sin grupo"
    return grupo["nombre"]


def estado_cita(fecha):
    if fecha == "":
        return {"clase": "neutro", "texto": "Sin cita"}
    if fecha < hoy():
        return {"clase": "mal", "texto": "Cita vencida: " + fecha}
    if fecha == hoy():
        return {"clase": "atencion", "texto": "Cita hoy"}
    return {"clase": "bien", "texto": "Cita: " + fecha}


def remisiones_pendientes():
    return base_datos.consultar(
        "SELECT remisiones_docentes.*, estudiantes.nombre AS estudiante, docentes.nombre AS docente "
        "FROM remisiones_docentes JOIN usuarios AS estudiantes ON estudiantes.id = remisiones_docentes.estudiante_id "
        "JOIN usuarios AS docentes ON docentes.id = remisiones_docentes.docente_id "
        "WHERE remisiones_docentes.colegio_id = ? AND remisiones_docentes.estado = 'pendiente' "
        "ORDER BY remisiones_docentes.fecha, remisiones_docentes.id",
        [g.colegio["id"]],
    )


def atenciones_abiertas():
    return base_datos.consultar(
        "SELECT atenciones_orientacion.id, atenciones_orientacion.estudiante_id, atenciones_orientacion.fecha, "
        "atenciones_orientacion.motivo, atenciones_orientacion.proxima_cita, usuarios.nombre AS estudiante "
        "FROM atenciones_orientacion JOIN usuarios ON usuarios.id = atenciones_orientacion.estudiante_id "
        "WHERE atenciones_orientacion.colegio_id = ? AND atenciones_orientacion.estado = 'abierta' "
        "ORDER BY atenciones_orientacion.proxima_cita = '', atenciones_orientacion.proxima_cita, atenciones_orientacion.fecha",
        [g.colegio["id"]],
    )


def atenciones_del_estudiante(estudiante_id):
    return base_datos.consultar(
        "SELECT atenciones_orientacion.*, usuarios.nombre AS orientador FROM atenciones_orientacion "
        "JOIN usuarios ON usuarios.id = atenciones_orientacion.orientador_id "
        "WHERE atenciones_orientacion.colegio_id = ? AND atenciones_orientacion.estudiante_id = ? "
        "ORDER BY atenciones_orientacion.fecha DESC, atenciones_orientacion.id DESC",
        [g.colegio["id"], estudiante_id],
    )


def remisiones_del_estudiante(estudiante_id):
    return base_datos.consultar(
        "SELECT remisiones_docentes.*, usuarios.nombre AS docente FROM remisiones_docentes "
        "JOIN usuarios ON usuarios.id = remisiones_docentes.docente_id "
        "WHERE remisiones_docentes.colegio_id = ? AND remisiones_docentes.estudiante_id = ? "
        "ORDER BY remisiones_docentes.estado = 'atendida', remisiones_docentes.fecha DESC, remisiones_docentes.id DESC",
        [g.colegio["id"], estudiante_id],
    )


def buscar_atencion(atencion_id):
    return base_datos.consultar_uno(
        "SELECT * FROM atenciones_orientacion WHERE id = ? AND colegio_id = ?", [atencion_id, g.colegio["id"]]
    )


def buscar_remision(remision_id):
    return base_datos.consultar_uno(
        "SELECT * FROM remisiones_docentes WHERE id = ? AND colegio_id = ?", [remision_id, g.colegio["id"]]
    )


def conteo_por_motivo(anio):
    filas = []
    total = 0
    for motivo in MOTIVOS:
        cantidad = contar(
            "SELECT COUNT(*) AS cantidad FROM atenciones_orientacion WHERE colegio_id = ? AND motivo = ? AND fecha LIKE ?",
            [g.colegio["id"], motivo["clave"], str(anio) + "-%"],
        )
        filas.append({"nombre": motivo["nombre"], "cantidad": cantidad, "porcentaje": 0})
        total = total + cantidad
    for fila in filas:
        fila["porcentaje"] = porcentaje(fila["cantidad"], total)
    return {"filas": filas, "total": total}


def formulario_atencion():
    return {"fecha": hoy(), "motivo": "", "descripcion": "", "acciones": "", "remision": "ninguna", "proxima_cita": ""}


def validar_atencion(datos):
    errores = []
    if not fecha_valida(datos["fecha"]):
        errores.append("La fecha de la atención no es válida. Usa el formato AAAA-MM-DD.")
    elif datos["fecha"] > hoy():
        errores.append("La fecha de la atención no puede ser futura.")
    if datos["motivo"] not in claves(MOTIVOS):
        errores.append("Elige el motivo de la atención.")
    if datos["descripcion"] == "":
        errores.append("Escribe la descripción de la atención.")
    elif len(datos["descripcion"]) > 4000:
        errores.append("La descripción no puede pasar de 4000 caracteres.")
    if len(datos["acciones"]) > 2000:
        errores.append("Las acciones no pueden pasar de 2000 caracteres.")
    if datos["remision"] not in claves(REMISIONES):
        errores.append("Elige una remisión externa válida.")
    if datos["proxima_cita"] != "":
        if not fecha_valida(datos["proxima_cita"]):
            errores.append("La próxima cita no es una fecha válida. Usa el formato AAAA-MM-DD.")
        elif fecha_valida(datos["fecha"]) and datos["proxima_cita"] <= datos["fecha"]:
            errores.append("La próxima cita debe ser después de la fecha de la atención.")
    return errores


def buscar_estudiantes(buscar):
    resultados = []
    texto = sin_tildes(buscar)
    for estudiante in base_datos.usuarios_con_rol(g.colegio["id"], "estudiante"):
        nombre = sin_tildes(estudiante["nombre"])
        coincide = texto in nombre or texto in estudiante["documento"].lower() or texto in estudiante["usuario"].lower()
        if coincide and len(resultados) < 30:
            atenciones = contar(
                "SELECT COUNT(*) AS cantidad FROM atenciones_orientacion WHERE colegio_id = ? AND estudiante_id = ?",
                [g.colegio["id"], estudiante["id"]],
            )
            abiertas = contar(
                "SELECT COUNT(*) AS cantidad FROM atenciones_orientacion WHERE colegio_id = ? AND estudiante_id = ? "
                "AND estado = 'abierta'",
                [g.colegio["id"], estudiante["id"]],
            )
            resultados.append({"estudiante": estudiante, "grupo": nombre_grupo(estudiante["id"]),
                               "atenciones": atenciones, "abiertas": abiertas})
    return resultados


def panel_orientador():
    remisiones = remisiones_pendientes()
    for remision in remisiones:
        remision["grupo"] = nombre_grupo(remision["estudiante_id"])
    abiertas = atenciones_abiertas()
    for atencion in abiertas:
        atencion["grupo"] = nombre_grupo(atencion["estudiante_id"])
        atencion["cita"] = estado_cita(atencion["proxima_cita"])
    buscar = request.args.get("buscar", "").strip()[0:60]
    resultados = []
    if buscar != "":
        resultados = buscar_estudiantes(buscar)
    total_anio = conteo_por_motivo(g.colegio["anio"])["total"]
    return render_template("orientacion_panel.html", activo="orientacion", remisiones=remisiones, abiertas=abiertas,
                           buscar=buscar, resultados=resultados, total_anio=total_anio,
                           nombres_motivos=nombres(MOTIVOS))


@app.route("/orientacion")
def orientacion():
    if tiene_rol(g.yo, "orientador"):
        return panel_orientador()
    if not tiene_alguno(g.yo, ["rector", "coordinador"]):
        return redirect("/inicio")
    conteo = conteo_por_motivo(g.colegio["anio"])
    pendientes = contar(
        "SELECT COUNT(*) AS cantidad FROM remisiones_docentes WHERE colegio_id = ? AND estado = 'pendiente'",
        [g.colegio["id"]],
    )
    abiertas = contar(
        "SELECT COUNT(*) AS cantidad FROM atenciones_orientacion WHERE colegio_id = ? AND estado = 'abierta'",
        [g.colegio["id"]],
    )
    return render_template("orientacion_cifras.html", activo="orientacion", conteo=conteo["filas"],
                           total=conteo["total"], pendientes=pendientes, abiertas=abiertas)


@app.route("/orientacion/estudiante/<int:estudiante_id>", methods=["GET", "POST"])
def orientacion_estudiante(estudiante_id):
    if not tiene_rol(g.yo, "orientador"):
        return redirect("/inicio")
    estudiante = estudiante_del_colegio(estudiante_id)
    if estudiante is None:
        return redirect("/inicio")

    errores = []
    mensaje = ""
    formulario = formulario_atencion()
    if request.method == "POST":
        accion = request.form.get("accion", "")
        if accion == "nueva":
            for campo in formulario:
                formulario[campo] = request.form.get(campo, "").strip()
            errores = validar_atencion(formulario)
            if len(errores) == 0:
                nuevo_id = base_datos.ejecutar(
                    "INSERT INTO atenciones_orientacion (colegio_id, estudiante_id, orientador_id, fecha, motivo, descripcion, "
                    "acciones, remision, proxima_cita, estado, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'abierta', ?)",
                    [g.colegio["id"], estudiante["id"], g.yo["id"], formulario["fecha"], formulario["motivo"],
                     formulario["descripcion"], formulario["acciones"], formulario["remision"], formulario["proxima_cita"],
                     ahora()],
                )
                registrar("Registró una atención de orientación", "Atención " + str(nuevo_id))
                mensaje = "Atención registrada."
                formulario = formulario_atencion()
        elif accion == "cerrar":
            atencion = None
            atencion_id = entero(request.form.get("atencion_id", ""))
            if atencion_id is not None:
                atencion = buscar_atencion(atencion_id)
            if atencion is None or atencion["estudiante_id"] != estudiante["id"]:
                errores.append("No se encontró la atención.")
            elif atencion["estado"] == "cerrada":
                errores.append("La atención ya estaba cerrada.")
            else:
                base_datos.ejecutar("UPDATE atenciones_orientacion SET estado = 'cerrada' WHERE id = ?", [atencion["id"]])
                registrar("Cerró una atención de orientación", "Atención " + str(atencion["id"]))
                mensaje = "Atención cerrada."
        elif accion == "remision_atendida":
            remision = None
            remision_id = entero(request.form.get("remision_id", ""))
            if remision_id is not None:
                remision = buscar_remision(remision_id)
            if remision is None or remision["estudiante_id"] != estudiante["id"]:
                errores.append("No se encontró la remisión.")
            elif remision["estado"] == "atendida":
                errores.append("La remisión ya estaba atendida.")
            else:
                base_datos.ejecutar(
                    "UPDATE remisiones_docentes SET estado = 'atendida', atendida_en = ? WHERE id = ?",
                    [ahora(), remision["id"]],
                )
                registrar("Atendió una remisión docente", "Remisión " + str(remision["id"]))
                mensaje = "Remisión marcada como atendida."
        else:
            errores.append("Acción no válida.")

    atenciones = atenciones_del_estudiante(estudiante["id"])
    for atencion in atenciones:
        atencion["cita"] = estado_cita(atencion["proxima_cita"])
    plan = base_datos.consultar_uno(
        "SELECT id FROM piar WHERE colegio_id = ? AND anio = ? AND estudiante_id = ?",
        [g.colegio["id"], g.colegio["anio"], estudiante["id"]],
    )
    return render_template("orientacion_estudiante.html", activo="orientacion", estudiante=estudiante,
                           grupo=grupo_del_estudiante(estudiante["id"]), atenciones=atenciones,
                           remisiones=remisiones_del_estudiante(estudiante["id"]),
                           acudientes=base_datos.acudientes_de(estudiante["id"]), plan=plan,
                           formulario=formulario, errores=errores, mensaje=mensaje, hoy=hoy(),
                           motivos=MOTIVOS, remisiones_externas=REMISIONES,
                           nombres_motivos=nombres(MOTIVOS), nombres_remisiones=nombres(REMISIONES))


def puede_remitir(yo, estudiante):
    if yo is None or estudiante is None:
        return False
    grupo = grupo_del_estudiante(estudiante["id"])
    if grupo is None:
        return False
    return dicta_en_grupo(yo, grupo["id"]) or grupo["director_id"] == yo["id"]


@app.route("/orientacion/remitir")
def remitir_lista():
    if g.yo is None:
        return redirect("/inicio")
    ids = []
    if tiene_rol(g.yo, "docente"):
        for asignacion in base_datos.asignaciones_del_docente(g.yo["id"], g.colegio["anio"]):
            if asignacion["grupo_id"] not in ids:
                ids.append(asignacion["grupo_id"])
    for dirigido in base_datos.grupos_dirigidos(g.yo["id"], g.colegio["anio"]):
        if dirigido["id"] not in ids:
            ids.append(dirigido["id"])
    grupos = []
    for grupo_id in ids:
        grupo = base_datos.buscar_grupo(grupo_id)
        if grupo is not None and grupo["colegio_id"] == g.colegio["id"]:
            grupos.append({"grupo": grupo, "estudiantes": base_datos.estudiantes_del_grupo(grupo_id)})
    if len(grupos) == 0:
        return redirect("/inicio")
    return render_template("orientacion_remitir.html", activo="", grupos=grupos, estudiante=None)


@app.route("/orientacion/remitir/<int:estudiante_id>", methods=["GET", "POST"])
def remitir(estudiante_id):
    estudiante = estudiante_del_colegio(estudiante_id)
    if not puede_remitir(g.yo, estudiante):
        return redirect("/inicio")

    errores = []
    enviado = False
    motivo = ""
    if request.method == "POST":
        motivo = request.form.get("motivo", "").strip()
        if motivo == "":
            errores.append("Escribe por qué pides la atención de orientación.")
        elif len(motivo) > 600:
            errores.append("El motivo no puede pasar de 600 caracteres.")
        else:
            nuevo_id = base_datos.ejecutar(
                "INSERT INTO remisiones_docentes (colegio_id, estudiante_id, docente_id, fecha, motivo, estado) "
                "VALUES (?, ?, ?, ?, ?, 'pendiente')",
                [g.colegio["id"], estudiante["id"], g.yo["id"], hoy(), motivo],
            )
            registrar("Remitió un estudiante a orientación", "Remisión " + str(nuevo_id))
            enviado = True
            motivo = ""

    return render_template("orientacion_remitir.html", activo="", estudiante=estudiante,
                           grupo=grupo_del_estudiante(estudiante["id"]), errores=errores, enviado=enviado, motivo=motivo)


def grupo_en_anio(estudiante_id, anio):
    matricula = base_datos.matricula_activa(estudiante_id, anio)
    if matricula is None:
        return None
    return base_datos.buscar_grupo(matricula["grupo_id"])


def es_acudiente_de(yo, estudiante_id):
    if not tiene_rol(yo, "acudiente"):
        return False
    for hijo in base_datos.estudiantes_a_cargo(yo["id"]):
        if hijo["id"] == estudiante_id:
            return True
    return False


def permisos_piar(yo, plan, grupo):
    permisos = {"ver": False, "editar_todo": False, "materias": [], "revisar": False}
    if yo is None or plan is None or plan["colegio_id"] != yo["colegio_id"]:
        return permisos
    if tiene_alguno(yo, EDITAN_PIAR):
        permisos["ver"] = True
        permisos["editar_todo"] = True
    if grupo is not None and dicta_en_grupo(yo, grupo["id"]):
        permisos["ver"] = True
        for asignacion in base_datos.asignaciones_del_grupo(grupo["id"]):
            if asignacion["docente_id"] == yo["id"]:
                permisos["materias"].append(asignacion["materia_id"])
    if grupo is not None and grupo["director_id"] == yo["id"]:
        permisos["ver"] = True
    if tiene_rol(yo, "estudiante") and yo["id"] == plan["estudiante_id"]:
        permisos["ver"] = True
    if es_acudiente_de(yo, plan["estudiante_id"]):
        permisos["ver"] = True
        permisos["revisar"] = True
    return permisos


def buscar_piar(piar_id):
    return base_datos.consultar_uno(
        "SELECT piar.*, estudiantes.nombre AS estudiante, autores.nombre AS autor FROM piar "
        "JOIN usuarios AS estudiantes ON estudiantes.id = piar.estudiante_id "
        "LEFT JOIN usuarios AS autores ON autores.id = piar.elaborado_por "
        "WHERE piar.id = ? AND piar.colegio_id = ?",
        [piar_id, g.colegio["id"]],
    )


def piar_del_anio(anio, estudiante_id):
    return base_datos.consultar_uno("SELECT id FROM piar WHERE anio = ? AND estudiante_id = ?", [anio, estudiante_id])


def ajustes_del_piar(piar_id):
    ajustes = {}
    filas = base_datos.consultar(
        "SELECT piar_ajustes.*, usuarios.nombre AS autor FROM piar_ajustes "
        "LEFT JOIN usuarios ON usuarios.id = piar_ajustes.actualizado_por "
        "WHERE piar_ajustes.piar_id = ? AND piar_ajustes.colegio_id = ?",
        [piar_id, g.colegio["id"]],
    )
    for fila in filas:
        ajustes[fila["materia_id"]] = fila
    return ajustes


def validar_general(datos):
    errores = []
    if datos["descripcion_estudiante"] == "":
        errores.append("Escribe la descripción del estudiante.")
    largos = 0
    for campo in CAMPOS_GENERALES:
        if len(datos[campo]) > 3000:
            largos = largos + 1
    if largos > 0:
        errores.append("Cada campo del PIAR puede tener máximo 3000 caracteres.")
    return errores


def opciones_para_crear():
    opciones = []
    for grupo in base_datos.grupos_del_colegio(g.colegio["id"], g.colegio["anio"]):
        estudiantes = []
        for estudiante in base_datos.estudiantes_del_grupo(grupo["id"]):
            if piar_del_anio(g.colegio["anio"], estudiante["id"]) is None:
                estudiantes.append(estudiante)
        if len(estudiantes) > 0:
            opciones.append({"nombre": grupo["nombre"], "estudiantes": estudiantes})
    return opciones


@app.route("/piar", methods=["GET", "POST"])
def piar_lista():
    if not tiene_alguno(g.yo, VEN_PIAR):
        return redirect("/inicio")
    puede_crear = tiene_alguno(g.yo, EDITAN_PIAR)
    anio = g.colegio["anio"]
    errores = []
    formulario = {"estudiante_id": "", "descripcion_estudiante": "", "barreras": "", "apoyos_familia": ""}
    if request.method == "POST":
        if not puede_crear:
            return redirect("/inicio")
        for campo in formulario:
            formulario[campo] = request.form.get(campo, "").strip()
        estudiante = None
        estudiante_id = entero(formulario["estudiante_id"])
        if estudiante_id is not None:
            estudiante = estudiante_del_colegio(estudiante_id)
        if estudiante is None:
            errores.append("Elige un estudiante del colegio.")
        elif base_datos.matricula_activa(estudiante["id"], anio) is None:
            errores.append(estudiante["nombre"] + " no tiene matrícula activa en " + str(anio) + ".")
        elif piar_del_anio(anio, estudiante["id"]) is not None:
            errores.append(estudiante["nombre"] + " ya tiene PIAR en " + str(anio) + ".")
        errores = errores + validar_general(formulario)
        if len(errores) == 0:
            nuevo_id = base_datos.ejecutar(
                "INSERT INTO piar (colegio_id, anio, estudiante_id, descripcion_estudiante, barreras, apoyos_familia, "
                "elaborado_por, elaborado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [g.colegio["id"], anio, estudiante["id"], formulario["descripcion_estudiante"], formulario["barreras"],
                 formulario["apoyos_familia"], g.yo["id"], ahora()],
            )
            registrar("Creó un PIAR", "PIAR " + str(nuevo_id))
            return redirect("/piar/" + str(nuevo_id) + "?creado=1")

    planes = []
    filas = base_datos.consultar(
        "SELECT piar.*, usuarios.nombre AS estudiante FROM piar JOIN usuarios ON usuarios.id = piar.estudiante_id "
        "WHERE piar.colegio_id = ? ORDER BY piar.anio DESC, usuarios.nombre",
        [g.colegio["id"]],
    )
    for plan in filas:
        grupo = grupo_en_anio(plan["estudiante_id"], plan["anio"])
        if permisos_piar(g.yo, plan, grupo)["ver"]:
            plan["grupo"] = "Sin grupo"
            plan["materias"] = 0
            if grupo is not None:
                plan["grupo"] = grupo["nombre"]
                plan["materias"] = len(base_datos.asignaciones_del_grupo(grupo["id"]))
            plan["con_ajustes"] = contar(
                "SELECT COUNT(*) AS cantidad FROM piar_ajustes WHERE piar_id = ? AND ajustes != ''", [plan["id"]]
            )
            planes.append(plan)

    opciones = []
    if puede_crear:
        opciones = opciones_para_crear()
    return render_template("orientacion_piar_lista.html", activo="piar", planes=planes, puede_crear=puede_crear,
                           opciones=opciones, formulario=formulario, errores=errores,
                           es_docente=tiene_rol(g.yo, "docente"))


def guardar_ajuste(plan, asignacion, datos):
    existente = base_datos.consultar_uno(
        "SELECT id FROM piar_ajustes WHERE piar_id = ? AND materia_id = ?", [plan["id"], asignacion["materia_id"]]
    )
    if existente is None:
        base_datos.ejecutar(
            "INSERT INTO piar_ajustes (colegio_id, piar_id, materia_id, objetivo, ajustes, evaluacion, seguimiento, "
            "actualizado_por, actualizado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [g.colegio["id"], plan["id"], asignacion["materia_id"], datos["objetivo"], datos["ajustes"],
             datos["evaluacion"], datos["seguimiento"], g.yo["id"], ahora()],
        )
    else:
        base_datos.ejecutar(
            "UPDATE piar_ajustes SET objetivo = ?, ajustes = ?, evaluacion = ?, seguimiento = ?, actualizado_por = ?, "
            "actualizado_en = ? WHERE id = ?",
            [datos["objetivo"], datos["ajustes"], datos["evaluacion"], datos["seguimiento"], g.yo["id"], ahora(),
             existente["id"]],
        )


@app.route("/piar/<int:piar_id>", methods=["GET", "POST"])
def piar_detalle(piar_id):
    if g.yo is None:
        return redirect("/inicio")
    plan = buscar_piar(piar_id)
    if plan is None:
        return redirect("/inicio")
    grupo = grupo_en_anio(plan["estudiante_id"], plan["anio"])
    permisos = permisos_piar(g.yo, plan, grupo)
    if not permisos["ver"]:
        return redirect("/inicio")
    asignaciones = []
    if grupo is not None:
        asignaciones = base_datos.asignaciones_del_grupo(grupo["id"])

    errores = []
    mensaje = ""
    if request.args.get("creado", "") == "1":
        mensaje = "PIAR creado. Ahora cada docente del grupo puede registrar los ajustes de su materia."
    if request.method == "POST":
        accion = request.form.get("accion", "")
        if accion == "general":
            if not permisos["editar_todo"]:
                return redirect("/inicio")
            datos = {}
            for campo in CAMPOS_GENERALES:
                datos[campo] = request.form.get(campo, "").strip()
            errores = validar_general(datos)
            if len(errores) == 0:
                base_datos.ejecutar(
                    "UPDATE piar SET descripcion_estudiante = ?, barreras = ?, apoyos_familia = ? WHERE id = ?",
                    [datos["descripcion_estudiante"], datos["barreras"], datos["apoyos_familia"], plan["id"]],
                )
                registrar("Actualizó un PIAR", "PIAR " + str(plan["id"]))
                mensaje = "Información del estudiante guardada."
        elif accion == "ajuste":
            materia_id = entero(request.form.get("materia_id", ""))
            asignacion = None
            for opcion in asignaciones:
                if opcion["materia_id"] == materia_id:
                    asignacion = opcion
            if asignacion is None:
                errores.append("Esa materia no es del grupo del estudiante.")
            elif not permisos["editar_todo"] and materia_id not in permisos["materias"]:
                return redirect("/inicio")
            else:
                datos = {}
                largos = 0
                for campo in CAMPOS_AJUSTE:
                    datos[campo] = request.form.get(campo, "").strip()
                    if len(datos[campo]) > 2000:
                        largos = largos + 1
                if datos["objetivo"] == "" or datos["ajustes"] == "":
                    errores.append(asignacion["materia"] + ": escribe al menos el objetivo y los ajustes.")
                if largos > 0:
                    errores.append("Cada campo del ajuste puede tener máximo 2000 caracteres.")
                if len(errores) == 0:
                    guardar_ajuste(plan, asignacion, datos)
                    registrar("Actualizó ajustes del PIAR", "PIAR " + str(plan["id"]) + ", " + asignacion["materia"])
                    mensaje = "Ajustes de " + asignacion["materia"] + " guardados."
        elif accion == "revisado":
            if not permisos["revisar"]:
                return redirect("/inicio")
            base_datos.ejecutar("UPDATE piar SET revisado_acudiente_en = ? WHERE id = ?", [ahora(), plan["id"]])
            registrar("Revisó el PIAR como acudiente", "PIAR " + str(plan["id"]))
            mensaje = "Gracias. Quedó registrado que revisaste el PIAR."
        else:
            errores.append("Acción no válida.")
        plan = buscar_piar(piar_id)

    ajustes = ajustes_del_piar(plan["id"])
    filas = []
    for asignacion in asignaciones:
        ajuste = None
        if asignacion["materia_id"] in ajustes:
            ajuste = ajustes[asignacion["materia_id"]]
        editable = permisos["editar_todo"] or asignacion["materia_id"] in permisos["materias"]
        filas.append({"asignacion": asignacion, "ajuste": ajuste, "editable": editable})

    return render_template("orientacion_piar.html", activo="piar", plan=plan, grupo=grupo, filas=filas,
                           permisos=permisos, errores=errores, mensaje=mensaje)


def buscar_materia(colegio_id, nombre):
    return base_datos.consultar_uno("SELECT * FROM materias WHERE colegio_id = ? AND nombre = ?", [colegio_id, nombre])


def sembrar_orientacion():
    colegio = base_datos.buscar_colegio(1)
    if colegio is None or not base_datos.tabla_vacia("atenciones_orientacion"):
        return
    andres = base_datos.buscar_usuario("andres.quintero")
    kevin = base_datos.buscar_usuario("kevin.largo")
    munoz = base_datos.buscar_usuario("c.munoz")
    trejos = base_datos.buscar_usuario("a.trejos")
    orientadora = base_datos.buscar_usuario("orientadora")
    matematicas = buscar_materia(colegio["id"], "Matemáticas")
    castellano = buscar_materia(colegio["id"], "Lengua Castellana")
    if andres is None or kevin is None or munoz is None or trejos is None or orientadora is None:
        return
    if matematicas is None or castellano is None:
        return
    anio = str(colegio["anio"])

    base_datos.ejecutar(
        "INSERT INTO atenciones_orientacion (colegio_id, estudiante_id, orientador_id, fecha, motivo, descripcion, acciones, "
        "remision, proxima_cita, estado, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [colegio["id"], andres["id"], orientadora["id"], anio + "-11-10", "académico",
         "Andrés llega remitido por la directora de grupo. Reconoce que en el tercer período bajó en casi todas las "
         "materias; dice que se siente cansado y que no le encuentra sentido a estudiar porque ayuda en la finca en "
         "época de cosecha de café.",
         "Se acuerda un horario de estudio en casa, monitoría de Matemáticas con un compañero y llamada a la madre para "
         "citarla a la próxima sesión.",
         "ninguna", anio + "-11-24", "abierta", anio + "-11-10 10:20"],
    )
    base_datos.ejecutar(
        "INSERT INTO remisiones_docentes (colegio_id, estudiante_id, docente_id, fecha, motivo, estado) "
        "VALUES (?, ?, ?, ?, ?, 'pendiente')",
        [colegio["id"], andres["id"], munoz["id"], anio + "-11-13",
         "Bajo rendimiento en Matemáticas (2.3 en el tercer período) y desmotivación: no entrega los talleres, se queda "
         "dormido en clase y dice que ya no le importa perder el año."],
    )

    piar_id = base_datos.ejecutar(
        "INSERT INTO piar (colegio_id, anio, estudiante_id, descripcion_estudiante, barreras, apoyos_familia, "
        "elaborado_por, elaborado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [colegio["id"], colegio["anio"], kevin["id"],
         "Kevin es respetuoso, colaborador y muy hábil para el dibujo y el fútbol. Aprende mejor con ejemplos concretos, "
         "apoyos visuales y trabajo en parejas.",
         "Dificultad para comprender textos largos y para el cálculo de varios pasos. Se distrae con el ruido y necesita "
         "más tiempo para terminar las evaluaciones escritas.",
         "La familia revisa la agenda todos los días, acompaña media hora de tareas en casa y asiste a las citas de "
         "seguimiento con orientación.",
         orientadora["id"], anio + "-02-20 09:00"],
    )
    base_datos.ejecutar(
        "INSERT INTO piar_ajustes (colegio_id, piar_id, materia_id, objetivo, ajustes, evaluacion, seguimiento, "
        "actualizado_por, actualizado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [colegio["id"], piar_id, matematicas["id"],
         "Resolver problemas de funciones y proporcionalidad con apoyo de material concreto.",
         "Ubicarlo cerca del tablero, entregar guías con pasos numerados, permitir tabla de multiplicar y calculadora en "
         "problemas de varios pasos y dividir los talleres largos en partes cortas.",
         "Evaluaciones más cortas con 30 % más de tiempo, preguntas leídas en voz alta y valoración del procedimiento.",
         "Tercer período: mejoró al plantear ecuaciones; aún necesita apoyo en problemas de varios pasos.",
         munoz["id"], anio + "-09-18 15:40"],
    )
    base_datos.ejecutar(
        "INSERT INTO piar_ajustes (colegio_id, piar_id, materia_id, objetivo, ajustes, evaluacion, seguimiento, "
        "actualizado_por, actualizado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [colegio["id"], piar_id, castellano["id"],
         "Identificar la idea principal y las ideas secundarias en textos argumentativos cortos.",
         "Textos de máximo una página con el vocabulario clave resaltado, organizadores gráficos y lectura en pareja con "
         "un compañero tutor.",
         "Opción de responder de forma oral, preguntas de selección y rúbrica conocida antes de la evaluación.",
         "Participa más en la lectura en voz alta y avanza en los resúmenes con organizadores gráficos.",
         trejos["id"], anio + "-09-20 11:05"],
    )


if SEMBRAR:
    sembrar_orientacion()
