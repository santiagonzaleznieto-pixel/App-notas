from flask import g, render_template, request, redirect
from nucleo import app, agregar_menu, tiene_rol, tiene_alguno, dicta_en_grupo, registrar, hoy, ahora, DIRECTIVOS
from modulo_familias import fecha_valida, hora_valida, fecha_larga, hora_texto, entero, porcentaje, MESES_CORTOS
import base_datos

TABLAS_CIRCULARES = """
CREATE TABLE IF NOT EXISTS circulares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    titulo TEXT NOT NULL,
    cuerpo TEXT NOT NULL,
    autor_id INTEGER NOT NULL REFERENCES usuarios(id),
    publicada_en TEXT NOT NULL,
    destinatarios TEXT NOT NULL,
    grupo_id INTEGER REFERENCES grupos(id),
    requiere_confirmacion INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS lecturas_circular (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    circular_id INTEGER NOT NULL REFERENCES circulares(id),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    leida_en TEXT NOT NULL,
    confirmada_en TEXT NOT NULL DEFAULT '',
    UNIQUE (circular_id, usuario_id)
);

CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    titulo TEXT NOT NULL,
    fecha TEXT NOT NULL,
    hora TEXT NOT NULL DEFAULT '',
    lugar TEXT NOT NULL DEFAULT '',
    descripcion TEXT NOT NULL DEFAULT '',
    para TEXT NOT NULL DEFAULT 'todos',
    creado_por INTEGER REFERENCES usuarios(id)
);
"""

base_datos.crear_tablas(TABLAS_CIRCULARES)

TODOS_LOS_ROLES = ["administrador", "rector", "coordinador", "docente", "secretaria", "orientador", "estudiante", "acudiente"]

agregar_menu("circulares", "Circulares", "/circulares", TODOS_LOS_ROLES,
             "Comunicados del colegio y confirmación de lectura.")
agregar_menu("agenda", "Agenda", "/agenda", TODOS_LOS_ROLES,
             "Fechas importantes del año escolar.")

PUBLICAN_CIRCULARES = ["rector", "coordinador", "administrador", "secretaria", "orientador"]
GESTIONAN_AGENDA = DIRECTIVOS + ["secretaria", "orientador"]

DESTINATARIOS = {
    "todos": "Toda la comunidad",
    "docentes": "Docentes y directivos",
    "familias": "Familias",
    "estudiantes": "Estudiantes",
    "grupo": "Un grupo",
}

PARA_EVENTOS = {
    "todos": "Toda la comunidad",
    "docentes": "Docentes",
    "familias": "Familias",
    "estudiantes": "Estudiantes",
}


def en_el_grupo(estudiante_id, grupo):
    matricula = base_datos.matricula_activa(estudiante_id, grupo["anio"])
    return matricula is not None and matricula["grupo_id"] == grupo["id"]


def pertenece_al_grupo(persona, grupo_id):
    grupo = base_datos.buscar_grupo(grupo_id)
    if grupo is None or grupo["colegio_id"] != persona["colegio_id"]:
        return False
    if grupo["director_id"] == persona["id"]:
        return True
    if dicta_en_grupo(persona, grupo["id"]):
        return True
    if tiene_rol(persona, "estudiante") and en_el_grupo(persona["id"], grupo):
        return True
    if tiene_rol(persona, "acudiente"):
        for hijo in base_datos.estudiantes_a_cargo(persona["id"]):
            if en_el_grupo(hijo["id"], grupo):
                return True
    return False


def es_destinatario(persona, circular):
    if persona is None or persona["colegio_id"] != circular["colegio_id"]:
        return False
    tipo = circular["destinatarios"]
    if tipo == "todos":
        return True
    elif tipo == "docentes":
        return tiene_alguno(persona, ["docente"] + DIRECTIVOS)
    elif tipo == "familias":
        return tiene_rol(persona, "acudiente")
    elif tipo == "estudiantes":
        return tiene_rol(persona, "estudiante")
    elif tipo == "grupo":
        return pertenece_al_grupo(persona, circular["grupo_id"])
    return False


def ids_del_grupo(grupo_id):
    ids = []
    grupo = base_datos.buscar_grupo(grupo_id)
    if grupo is None:
        return ids
    if grupo["director_id"] is not None:
        ids.append(grupo["director_id"])
    for asignacion in base_datos.asignaciones_del_grupo(grupo["id"]):
        if "docente" in base_datos.roles_de(asignacion["docente_id"]):
            ids.append(asignacion["docente_id"])
    for estudiante in base_datos.estudiantes_del_grupo(grupo["id"]):
        ids.append(estudiante["id"])
        for acudiente in base_datos.acudientes_de(estudiante["id"]):
            ids.append(acudiente["id"])
    return ids


def destinatarios_de(circular):
    ids_grupo = []
    if circular["destinatarios"] == "grupo":
        ids_grupo = ids_del_grupo(circular["grupo_id"])
    personas = []
    for persona in base_datos.usuarios_del_colegio(circular["colegio_id"]):
        if persona["activo"] == 1:
            if circular["destinatarios"] == "grupo":
                if persona["id"] in ids_grupo:
                    personas.append(persona)
            elif es_destinatario(persona, circular):
                personas.append(persona)
    return personas


def puede_publicar(yo):
    return tiene_alguno(yo, PUBLICAN_CIRCULARES) or tiene_rol(yo, "director")


def destinatarios_permitidos(yo):
    if tiene_alguno(yo, PUBLICAN_CIRCULARES):
        return ["todos", "docentes", "familias", "estudiantes", "grupo"]
    if tiene_rol(yo, "director"):
        return ["grupo"]
    return []


def grupos_permitidos(yo):
    if tiene_alguno(yo, PUBLICAN_CIRCULARES):
        return base_datos.grupos_del_colegio(g.colegio["id"], g.colegio["anio"])
    grupos = []
    if tiene_rol(yo, "director"):
        for fila in base_datos.grupos_dirigidos(yo["id"], g.colegio["anio"]):
            grupo = base_datos.buscar_grupo(fila["id"])
            if grupo is not None and grupo["colegio_id"] == g.colegio["id"]:
                grupos.append(grupo)
    return grupos


def circulares_del_colegio():
    return base_datos.consultar(
        "SELECT circulares.*, usuarios.nombre AS autor, grupos.nombre AS grupo FROM circulares "
        "JOIN usuarios ON usuarios.id = circulares.autor_id LEFT JOIN grupos ON grupos.id = circulares.grupo_id "
        "WHERE circulares.colegio_id = ? ORDER BY circulares.publicada_en DESC, circulares.id DESC",
        [g.colegio["id"]],
    )


def buscar_circular(circular_id):
    circular = base_datos.consultar_uno(
        "SELECT circulares.*, usuarios.nombre AS autor, grupos.nombre AS grupo FROM circulares "
        "JOIN usuarios ON usuarios.id = circulares.autor_id LEFT JOIN grupos ON grupos.id = circulares.grupo_id "
        "WHERE circulares.id = ?",
        [circular_id],
    )
    if circular is None or circular["colegio_id"] != g.colegio["id"]:
        return None
    return circular


def lecturas_de(usuario_id):
    lecturas = {}
    filas = base_datos.consultar(
        "SELECT * FROM lecturas_circular WHERE usuario_id = ? AND colegio_id = ?",
        [usuario_id, g.colegio["id"]],
    )
    for fila in filas:
        lecturas[fila["circular_id"]] = fila
    return lecturas


def buscar_lectura(circular_id, usuario_id):
    return base_datos.consultar_uno(
        "SELECT * FROM lecturas_circular WHERE circular_id = ? AND usuario_id = ?",
        [circular_id, usuario_id],
    )


def reporte_de(circular):
    lecturas = {}
    filas = base_datos.consultar(
        "SELECT * FROM lecturas_circular WHERE circular_id = ? AND colegio_id = ?",
        [circular["id"], g.colegio["id"]],
    )
    for fila in filas:
        lecturas[fila["usuario_id"]] = fila
    personas = destinatarios_de(circular)
    leidas = 0
    confirmadas = 0
    faltan = []
    for persona in personas:
        lectura = None
        if persona["id"] in lecturas:
            lectura = lecturas[persona["id"]]
        if lectura is None:
            faltan.append({"persona": persona, "estado": "Sin leer", "clase": "mal"})
        else:
            leidas = leidas + 1
            if lectura["confirmada_en"] != "":
                confirmadas = confirmadas + 1
            elif circular["requiere_confirmacion"] == 1:
                faltan.append({"persona": persona, "estado": "Leída, sin confirmar", "clase": "atencion"})
    total = len(personas)
    return {
        "total": total,
        "leidas": leidas,
        "confirmadas": confirmadas,
        "faltan": faltan,
        "porcentaje_leidas": porcentaje(leidas, total),
        "porcentaje_confirmadas": porcentaje(confirmadas, total),
    }


@app.route("/circulares")
def circulares():
    if not tiene_alguno(g.yo, TODOS_LOS_ROLES):
        return redirect("/inicio")

    directivo = tiene_alguno(g.yo, DIRECTIVOS)
    lecturas = lecturas_de(g.yo["id"])
    lista = []
    sin_leer = 0
    por_confirmar = 0
    for circular in circulares_del_colegio():
        mia = es_destinatario(g.yo, circular)
        if mia or circular["autor_id"] == g.yo["id"] or directivo:
            lectura = None
            if circular["id"] in lecturas:
                lectura = lecturas[circular["id"]]
            nueva = mia and lectura is None
            falta_confirmar = False
            if mia and circular["requiere_confirmacion"] == 1:
                if lectura is None or lectura["confirmada_en"] == "":
                    falta_confirmar = True
            if nueva:
                sin_leer = sin_leer + 1
            if falta_confirmar:
                por_confirmar = por_confirmar + 1
            lista.append({"circular": circular, "mia": mia, "nueva": nueva, "falta_confirmar": falta_confirmar})

    return render_template("circulares_lista.html", activo="circulares", lista=lista, sin_leer=sin_leer,
                           por_confirmar=por_confirmar, puede_publicar=puede_publicar(g.yo),
                           destinatarios=DESTINATARIOS, fecha_larga=fecha_larga)


@app.route("/circulares/nueva", methods=["GET", "POST"])
def nueva_circular():
    opciones = destinatarios_permitidos(g.yo)
    if len(opciones) == 0:
        return redirect("/inicio")

    grupos = grupos_permitidos(g.yo)
    errores = []
    formulario = {"titulo": "", "cuerpo": "", "destinatarios": opciones[0], "grupo_id": "", "requiere_confirmacion": False}
    if request.method == "POST":
        formulario["titulo"] = request.form.get("titulo", "").strip()
        formulario["cuerpo"] = request.form.get("cuerpo", "").strip()
        formulario["destinatarios"] = request.form.get("destinatarios", "")
        formulario["grupo_id"] = request.form.get("grupo_id", "")
        formulario["requiere_confirmacion"] = "requiere_confirmacion" in request.form
        if formulario["titulo"] == "" or len(formulario["titulo"]) > 150:
            errores.append("Escribe el título de la circular (máximo 150 caracteres).")
        if formulario["cuerpo"] == "" or len(formulario["cuerpo"]) > 6000:
            errores.append("Escribe el texto de la circular (máximo 6000 caracteres).")
        grupo_id = None
        if formulario["destinatarios"] not in opciones:
            errores.append("Elige a quién va dirigida la circular.")
        elif formulario["destinatarios"] == "grupo":
            elegido = entero(formulario["grupo_id"])
            for grupo in grupos:
                if grupo["id"] == elegido:
                    grupo_id = grupo["id"]
            if grupo_id is None:
                errores.append("Elige uno de tus grupos para enviar la circular.")
        if len(errores) == 0:
            confirmacion = 0
            if formulario["requiere_confirmacion"]:
                confirmacion = 1
            nuevo_id = base_datos.ejecutar(
                "INSERT INTO circulares (colegio_id, titulo, cuerpo, autor_id, publicada_en, destinatarios, grupo_id, "
                "requiere_confirmacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [g.colegio["id"], formulario["titulo"], formulario["cuerpo"], g.yo["id"], ahora(),
                 formulario["destinatarios"], grupo_id, confirmacion],
            )
            registrar("Publicó una circular", formulario["titulo"] + " · " + DESTINATARIOS[formulario["destinatarios"]])
            return redirect("/circulares/" + str(nuevo_id) + "?publicada=1")

    return render_template("circulares_nueva.html", activo="circulares", opciones=opciones, grupos=grupos,
                           formulario=formulario, errores=errores, destinatarios=DESTINATARIOS)


@app.route("/circulares/<int:circular_id>", methods=["GET", "POST"])
def ver_circular(circular_id):
    if not tiene_alguno(g.yo, TODOS_LOS_ROLES):
        return redirect("/inicio")
    circular = buscar_circular(circular_id)
    if circular is None:
        return redirect("/inicio")

    mia = es_destinatario(g.yo, circular)
    es_autor = circular["autor_id"] == g.yo["id"]
    directivo = tiene_alguno(g.yo, DIRECTIVOS)
    if not mia and not es_autor and not directivo:
        return redirect("/inicio")

    errores = []
    mensaje = ""
    if request.args.get("publicada", "") == "1" and es_autor:
        mensaje = "Circular publicada."
    if mia:
        base_datos.ejecutar(
            "INSERT OR IGNORE INTO lecturas_circular (colegio_id, circular_id, usuario_id, leida_en) VALUES (?, ?, ?, ?)",
            [g.colegio["id"], circular["id"], g.yo["id"], ahora()],
        )
    if request.method == "POST":
        if not mia or circular["requiere_confirmacion"] != 1:
            errores.append("Esta circular no te pide confirmar la lectura.")
        else:
            lectura = buscar_lectura(circular["id"], g.yo["id"])
            if lectura is not None and lectura["confirmada_en"] == "":
                base_datos.ejecutar(
                    "UPDATE lecturas_circular SET confirmada_en = ? WHERE id = ?",
                    [ahora(), lectura["id"]],
                )
                registrar("Confirmó la lectura de una circular", circular["titulo"])
            mensaje = "Gracias. Quedó registrado que leíste esta circular."

    lectura = None
    if mia:
        lectura = buscar_lectura(circular["id"], g.yo["id"])
    reporte = None
    if es_autor or directivo:
        reporte = reporte_de(circular)

    return render_template("circulares_detalle.html", activo="circulares", circular=circular, mia=mia,
                           lectura=lectura, reporte=reporte, errores=errores, mensaje=mensaje,
                           destinatarios=DESTINATARIOS, fecha_larga=fecha_larga, hora_texto=hora_texto)


def para_visibles(yo):
    if tiene_alguno(yo, GESTIONAN_AGENDA):
        return ["todos", "docentes", "familias", "estudiantes"]
    visibles = ["todos"]
    if tiene_rol(yo, "docente"):
        visibles.append("docentes")
    if tiene_rol(yo, "acudiente"):
        visibles.append("familias")
    if tiene_rol(yo, "estudiante"):
        visibles.append("estudiantes")
    return visibles


@app.route("/agenda", methods=["GET", "POST"])
def agenda():
    if not tiene_alguno(g.yo, TODOS_LOS_ROLES):
        return redirect("/inicio")

    gestiona = tiene_alguno(g.yo, GESTIONAN_AGENDA)
    errores = []
    mensaje = ""
    if request.args.get("borrado", "") == "1":
        mensaje = "Evento borrado de la agenda."
    formulario = {"titulo": "", "fecha": "", "hora": "", "lugar": "", "descripcion": "", "para": "todos"}
    if request.method == "POST":
        if not gestiona:
            return redirect("/inicio")
        for campo in formulario:
            formulario[campo] = request.form.get(campo, "").strip()
        if formulario["titulo"] == "" or len(formulario["titulo"]) > 150:
            errores.append("Escribe el nombre del evento (máximo 150 caracteres).")
        if not fecha_valida(formulario["fecha"]):
            errores.append("Escribe la fecha como año-mes-día, por ejemplo " + str(g.colegio["anio"]) + "-12-04.")
        if formulario["hora"] != "" and not hora_valida(formulario["hora"]):
            errores.append("Escribe la hora en formato de 24 horas, por ejemplo 07:00 o 14:30, o déjala vacía.")
        if len(formulario["lugar"]) > 150:
            errores.append("El lugar debe tener máximo 150 caracteres.")
        if len(formulario["descripcion"]) > 2000:
            errores.append("La descripción debe tener máximo 2000 caracteres.")
        if formulario["para"] not in PARA_EVENTOS:
            errores.append("Elige para quién es el evento.")
        if len(errores) == 0:
            base_datos.ejecutar(
                "INSERT INTO eventos (colegio_id, titulo, fecha, hora, lugar, descripcion, para, creado_por) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [g.colegio["id"], formulario["titulo"], formulario["fecha"], formulario["hora"], formulario["lugar"],
                 formulario["descripcion"], formulario["para"], g.yo["id"]],
            )
            registrar("Creó un evento en la agenda", formulario["titulo"] + " · " + formulario["fecha"])
            mensaje = "Evento agregado a la agenda: " + formulario["titulo"] + "."
            formulario = {"titulo": "", "fecha": "", "hora": "", "lugar": "", "descripcion": "", "para": "todos"}

    visibles = para_visibles(g.yo)
    inicio_anio = str(g.colegio["anio"]) + "-01-01"
    proximos = []
    pasados = []
    eventos = base_datos.consultar(
        "SELECT * FROM eventos WHERE colegio_id = ? ORDER BY fecha, hora, id",
        [g.colegio["id"]],
    )
    for evento in eventos:
        if evento["para"] in visibles:
            if evento["fecha"] >= hoy():
                proximos.append(evento)
            elif evento["fecha"] >= inicio_anio:
                pasados.insert(0, evento)

    return render_template("agenda_eventos.html", activo="agenda", proximos=proximos, pasados=pasados,
                           gestiona=gestiona, formulario=formulario, errores=errores, mensaje=mensaje,
                           para_eventos=PARA_EVENTOS, fecha_larga=fecha_larga, hora_texto=hora_texto,
                           meses_cortos=MESES_CORTOS, hoy=hoy())


@app.route("/agenda/<int:evento_id>/borrar", methods=["POST"])
def borrar_evento(evento_id):
    if not tiene_alguno(g.yo, GESTIONAN_AGENDA):
        return redirect("/inicio")
    evento = base_datos.consultar_uno("SELECT * FROM eventos WHERE id = ?", [evento_id])
    if evento is None or evento["colegio_id"] != g.colegio["id"]:
        return redirect("/inicio")
    base_datos.ejecutar("DELETE FROM eventos WHERE id = ? AND colegio_id = ?", [evento["id"], g.colegio["id"]])
    registrar("Borró un evento de la agenda", evento["titulo"] + " · " + evento["fecha"])
    return redirect("/agenda?borrado=1")


def sembrar_circulares():
    colegio = base_datos.buscar_colegio(1)
    if colegio is None or not base_datos.tabla_vacia("circulares"):
        return
    rectora = base_datos.buscar_usuario("rectora")
    coordinadora = base_datos.buscar_usuario("coordinadora")
    gloria = base_datos.buscar_usuario("gloria.cardenas")
    grupo = base_datos.consultar_uno(
        "SELECT * FROM grupos WHERE colegio_id = ? AND anio = ? AND nombre = ?",
        [1, colegio["anio"], "10-A"],
    )
    if rectora is None or coordinadora is None or gloria is None or grupo is None:
        return

    base_datos.ejecutar(
        "INSERT INTO circulares (colegio_id, titulo, cuerpo, autor_id, publicada_en, destinatarios, grupo_id, "
        "requiere_confirmacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [1, "Entrega de boletines del cuarto período",
         "Apreciada comunidad educativa:\n\n"
         "La Rectoría informa que la entrega de boletines del cuarto período y del informe final del año escolar "
         "2026 será el viernes 4 de diciembre de 2026, de 7:00 a. m. a 12:00 m., en el aula de cada grupo de la "
         "sede principal.\n\n"
         "• Cada acudiente debe asistir para recibir el boletín y firmar la planilla de entrega.\n"
         "• Los estudiantes con desempeño bajo en alguna materia recibirán ese día su plan de mejoramiento y las "
         "fechas de las actividades de recuperación.\n"
         "• Ese día no hay clases.\n\n"
         "Recuerden que el cuarto período termina el viernes 27 de noviembre.\n\n"
         "Cordialmente,\n" + rectora["nombre"] + "\nRectora",
         rectora["id"], "2026-11-10 08:00", "todos", None, 0],
    )
    salida = base_datos.ejecutar(
        "INSERT INTO circulares (colegio_id, titulo, cuerpo, autor_id, publicada_en, destinatarios, grupo_id, "
        "requiere_confirmacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [1, "Salida pedagógica al Jardín Botánico del Quindío",
         "Señores acudientes y estudiantes del grupo " + grupo["nombre"] + ":\n\n"
         "El martes 24 de noviembre de 2026 haremos la salida pedagógica al Jardín Botánico del Quindío, en "
         "Calarcá, como cierre del proyecto de Ciencias Naturales sobre la biodiversidad del Paisaje Cultural "
         "Cafetero.\n\n"
         "• Salida: 7:00 a. m. desde la sede principal. Regreso: 1:00 p. m., aproximadamente.\n"
         "• Acompañan: la docente de Ciencias Naturales y el director de grupo.\n"
         "• Deben llevar: uniforme de educación física, gorra, bloqueador, agua y refrigerio.\n"
         "• Cada estudiante debe entregar la autorización firmada por su acudiente a más tardar el viernes 20 de "
         "noviembre.\n\n"
         "Los estudiantes que no asistan tendrán jornada normal de clases.\n\n"
         "Por favor confirmen en la plataforma que leyeron esta circular.\n\n" + coordinadora["nombre"] +
         "\nCoordinación",
         coordinadora["id"], "2026-11-13 10:30", "grupo", grupo["id"], 1],
    )
    base_datos.ejecutar(
        "INSERT INTO lecturas_circular (colegio_id, circular_id, usuario_id, leida_en, confirmada_en) VALUES (?, ?, ?, ?, ?)",
        [1, salida, gloria["id"], "2026-11-13 19:45", ""],
    )


def sembrar_agenda():
    colegio = base_datos.buscar_colegio(1)
    if colegio is None or not base_datos.tabla_vacia("eventos"):
        return
    secretaria = base_datos.buscar_usuario("secretaria")
    if secretaria is None:
        return
    eventos = [
        ["Comisión de evaluación y promoción del tercer período", "2026-09-18", "13:00", "Sala de profesores",
         "Revisión de los estudiantes con desempeño bajo y de los planes de mejoramiento.", "docentes"],
        ["Cierre del cuarto período", "2026-11-27", "", "",
         "Último día de clases del cuarto período. Los docentes deben dejar las notas registradas en la plataforma.",
         "todos"],
        ["Escuela para familias: prevención del consumo de sustancias psicoactivas", "2026-11-28", "08:00",
         "Auditorio de la sede principal", "Encuentro de la escuela para padres, madres y cuidadores.", "familias"],
        ["Entrega de boletines del cuarto período", "2026-12-04", "07:00", "Aula de cada grupo, sede principal",
         "Entrega del boletín del cuarto período y del informe final del año. Ese día no hay clases.", "todos"],
        ["Ceremonia de grado de 11°", "2026-12-05", "09:00", "Auditorio de la sede principal",
         "Ceremonia de graduación de los bachilleres " + str(colegio["anio"]) + ". Los graduandos llegan a las 8:00 a. m.",
         "todos"],
    ]
    for evento in eventos:
        base_datos.ejecutar(
            "INSERT INTO eventos (colegio_id, titulo, fecha, hora, lugar, descripcion, para, creado_por) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [1, evento[0], evento[1], evento[2], evento[3], evento[4], evento[5], secretaria["id"]],
        )


sembrar_circulares()
sembrar_agenda()
