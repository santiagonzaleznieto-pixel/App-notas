from flask import g, render_template, request, redirect
import nucleo
from nucleo import (app, agregar_menu, tiene_rol, tiene_alguno, puede_ver_grupo, puede_ver_estudiante,
                    puede_anotar_estudiante, dicta_en_grupo, estudiante_del_colegio, grupo_del_estudiante,
                    registrar, VEN_TODOS_LOS_ESTUDIANTES, CON_DATOS_DE_EJEMPLO)
import base_datos

TABLAS_OBSERVADOR = """
CREATE TABLE IF NOT EXISTS observaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    autor_id INTEGER NOT NULL REFERENCES usuarios(id),
    fecha TEXT NOT NULL,
    tipo TEXT NOT NULL,
    situacion_tipo INTEGER NOT NULL DEFAULT 0,
    descripcion TEXT NOT NULL,
    compromiso TEXT NOT NULL DEFAULT '',
    estado TEXT NOT NULL DEFAULT 'abierta',
    confidencial INTEGER NOT NULL DEFAULT 0,
    reportado_siuce INTEGER NOT NULL DEFAULT 0,
    creado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS seguimientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    observacion_id INTEGER NOT NULL REFERENCES observaciones(id),
    autor_id INTEGER NOT NULL REFERENCES usuarios(id),
    fecha TEXT NOT NULL,
    texto TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pasos_protocolo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    observacion_id INTEGER NOT NULL REFERENCES observaciones(id),
    paso TEXT NOT NULL,
    hecho INTEGER NOT NULL DEFAULT 0,
    hecho_por INTEGER REFERENCES usuarios(id),
    hecho_en TEXT NOT NULL DEFAULT ''
);
"""

base_datos.crear_tablas(TABLAS_OBSERVADOR)

agregar_menu("observador", "Observador", "/observador",
             ["docente", "director", "coordinador", "rector", "orientador", "administrador"],
             "Anotaciones de los estudiantes y casos de convivencia.")
agregar_menu("convivencia", "Convivencia", "/convivencia", ["coordinador", "rector", "orientador"],
             "Casos tipo I, II y III, protocolos y reporte al SIUCE.")

VEN_OBSERVADOR = ["docente", "director", "coordinador", "rector", "orientador", "administrador"]
GESTORES = ["coordinador", "rector", "orientador"]
TIPOS = {"positiva": "Positiva", "por_mejorar": "Por mejorar", "situacion": "Situación de convivencia"}
ROMANOS = {1: "I", 2: "II", 3: "III"}

PROTOCOLOS = {
    1: [
        "Reunir a las partes y mediar",
        "Acordar una solución y la reparación",
        "Dejar constancia",
        "Hacer seguimiento",
    ],
    2: [
        "Brindar atención en salud si hubo daño",
        "Adoptar medidas de protección",
        "Informar de inmediato a los acudientes",
        "Generar espacios para exponer lo sucedido",
        "Determinar acciones restaurativas",
        "Informar al comité escolar de convivencia",
        "Reportar en el SIUCE",
    ],
    3: [
        "Brindar atención inmediata en salud",
        "Informar a los acudientes",
        "Informar a la Policía de Infancia y Adolescencia",
        "Citar al comité escolar de convivencia",
        "Adoptar medidas de protección",
        "Reportar en el SIUCE",
    ],
}

CONSULTA_OBSERVACIONES = (
    "SELECT observaciones.*, alumno.nombre AS estudiante_nombre, autor.nombre AS autor_nombre FROM observaciones "
    "JOIN usuarios AS alumno ON alumno.id = observaciones.estudiante_id "
    "JOIN usuarios AS autor ON autor.id = observaciones.autor_id "
)


def es_gestor(yo):
    return tiene_alguno(yo, GESTORES)


def sin_tildes(texto):
    cambios = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
    limpio = ""
    for letra in texto.lower():
        if letra in cambios:
            limpio = limpio + cambios[letra]
        else:
            limpio = limpio + letra
    return limpio


def ve_como_personal(yo, estudiante):
    if yo is None or estudiante is None or estudiante["colegio_id"] != yo["colegio_id"]:
        return False
    if tiene_alguno(yo, VEN_TODOS_LOS_ESTUDIANTES):
        return True
    grupo = grupo_del_estudiante(estudiante["id"])
    return grupo is not None and grupo["director_id"] == yo["id"]


def puede_ver_observacion(yo, observacion, estudiante):
    if yo is None or observacion is None or estudiante is None:
        return False
    if observacion["colegio_id"] != yo["colegio_id"] or observacion["estudiante_id"] != estudiante["id"]:
        return False
    if es_gestor(yo):
        return True
    if observacion["autor_id"] == yo["id"]:
        return True
    if observacion["confidencial"] == 1:
        return False
    if ve_como_personal(yo, estudiante):
        return True
    if puede_ver_estudiante(yo, estudiante):
        return observacion["tipo"] != "situacion" or observacion["situacion_tipo"] == 1
    return False


def puede_abrir_caso(yo, observacion, estudiante):
    if not puede_ver_observacion(yo, observacion, estudiante):
        return False
    return es_gestor(yo) or observacion["autor_id"] == yo["id"] or ve_como_personal(yo, estudiante)


def preparar(observacion):
    if observacion["tipo"] == "situacion":
        observacion["nombre_tipo"] = "Situación tipo " + ROMANOS[observacion["situacion_tipo"]]
        observacion["clase"] = "situacion-" + str(observacion["situacion_tipo"])
    elif observacion["tipo"] == "positiva":
        observacion["nombre_tipo"] = "Positiva"
        observacion["clase"] = "positiva"
    else:
        observacion["nombre_tipo"] = "Por mejorar"
        observacion["clase"] = "por-mejorar"
    return observacion


def buscar_observacion(observacion_id):
    observacion = base_datos.consultar_uno(
        CONSULTA_OBSERVACIONES + "WHERE observaciones.id = ? AND observaciones.colegio_id = ?",
        [observacion_id, g.colegio["id"]],
    )
    if observacion is None:
        return None
    return preparar(observacion)


def observaciones_del_estudiante(estudiante_id):
    lista = base_datos.consultar(
        CONSULTA_OBSERVACIONES + "WHERE observaciones.colegio_id = ? AND observaciones.estudiante_id = ? "
        "ORDER BY observaciones.fecha DESC, observaciones.id DESC",
        [g.colegio["id"], estudiante_id],
    )
    for observacion in lista:
        preparar(observacion)
    return lista


def pasos_de(observacion_id):
    return base_datos.consultar(
        "SELECT pasos_protocolo.*, usuarios.nombre AS hecho_por_nombre FROM pasos_protocolo "
        "LEFT JOIN usuarios ON usuarios.id = pasos_protocolo.hecho_por "
        "WHERE pasos_protocolo.observacion_id = ? AND pasos_protocolo.colegio_id = ? ORDER BY pasos_protocolo.id",
        [observacion_id, g.colegio["id"]],
    )


def seguimientos_de(observacion_id):
    return base_datos.consultar(
        "SELECT seguimientos.*, usuarios.nombre AS autor_nombre FROM seguimientos "
        "JOIN usuarios ON usuarios.id = seguimientos.autor_id "
        "WHERE seguimientos.observacion_id = ? AND seguimientos.colegio_id = ? ORDER BY seguimientos.id",
        [observacion_id, g.colegio["id"]],
    )


def avance_de(observacion_id):
    fila = base_datos.consultar_uno(
        "SELECT COUNT(*) AS total, COALESCE(SUM(hecho), 0) AS hechos FROM pasos_protocolo WHERE observacion_id = ? AND colegio_id = ?",
        [observacion_id, g.colegio["id"]],
    )
    return fila


def crear_observacion(datos):
    estado = "cerrada"
    if datos["tipo"] == "situacion":
        estado = "abierta"
    nuevo_id = base_datos.ejecutar(
        "INSERT INTO observaciones (colegio_id, estudiante_id, autor_id, fecha, tipo, situacion_tipo, descripcion, compromiso, "
        "estado, confidencial, reportado_siuce, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
        [datos["colegio_id"], datos["estudiante_id"], datos["autor_id"], datos["fecha"], datos["tipo"], datos["situacion_tipo"],
         datos["descripcion"], datos["compromiso"], estado, datos["confidencial"], datos["creado_en"]],
    )
    if datos["tipo"] == "situacion":
        for paso in PROTOCOLOS[datos["situacion_tipo"]]:
            base_datos.ejecutar("INSERT INTO pasos_protocolo (colegio_id, observacion_id, paso) VALUES (?, ?, ?)",
                                [datos["colegio_id"], nuevo_id, paso])
    return nuevo_id


def agregar_seguimiento(observacion_id, texto):
    base_datos.ejecutar(
        "INSERT INTO seguimientos (colegio_id, observacion_id, autor_id, fecha, texto) VALUES (?, ?, ?, ?, ?)",
        [g.colegio["id"], observacion_id, g.yo["id"], nucleo.ahora(), texto],
    )


def errores_de_anotacion(valores, gestor):
    errores = []
    if valores["tipo"] not in TIPOS:
        errores.append("Elige el tipo de anotación.")
    elif valores["tipo"] == "situacion":
        if valores["situacion_tipo"] not in ["1", "2", "3"]:
            errores.append("Elige si la situación es tipo I, II o III.")
        elif valores["situacion_tipo"] != "1" and not gestor:
            errores.append("Las situaciones tipo II y III las registra coordinación, rectoría u orientación. Infórmala a coordinación de inmediato.")
    if valores["confidencial"] == "1" and not gestor:
        errores.append("Solo coordinación, rectoría y orientación pueden marcar una anotación como confidencial.")
    if len(valores["descripcion"]) < 10:
        errores.append("Describe lo sucedido: mínimo 10 caracteres.")
    elif len(valores["descripcion"]) > 3000:
        errores.append("La descripción es muy larga: máximo 3000 caracteres.")
    if len(valores["compromiso"]) > 1000:
        errores.append("El compromiso es muy largo: máximo 1000 caracteres.")
    return errores


def nombre_del_grupo(estudiante_id):
    grupo = grupo_del_estudiante(estudiante_id)
    if grupo is None:
        return ""
    return grupo["nombre"]


@app.route("/observador")
def observador():
    if not tiene_alguno(g.yo, VEN_OBSERVADOR):
        return redirect("/inicio")

    texto = request.args.get("q", "").strip()
    grupo_elegido = request.args.get("grupo", "").strip()
    grupos = []
    estudiantes = []
    for grupo in base_datos.grupos_del_colegio(g.colegio["id"], g.colegio["anio"]):
        if puede_ver_grupo(g.yo, grupo) or dicta_en_grupo(g.yo, grupo["id"]):
            grupos.append(grupo)
            if grupo_elegido == "" or grupo_elegido == str(grupo["id"]):
                for estudiante in base_datos.estudiantes_del_grupo(grupo["id"]):
                    if texto == "" or sin_tildes(texto) in sin_tildes(estudiante["nombre"]):
                        estudiante["grupo"] = grupo["nombre"]
                        estudiantes.append(estudiante)
    mostrar = texto != "" or grupo_elegido != "" or len(estudiantes) <= 60

    recientes = []
    filas = base_datos.consultar(
        CONSULTA_OBSERVACIONES + "WHERE observaciones.colegio_id = ? ORDER BY observaciones.fecha DESC, observaciones.id DESC LIMIT 300",
        [g.colegio["id"]],
    )
    posicion = 0
    while posicion < len(filas) and len(recientes) < 12:
        observacion = filas[posicion]
        estudiante = estudiante_del_colegio(observacion["estudiante_id"])
        if puede_ver_observacion(g.yo, observacion, estudiante):
            preparar(observacion)
            observacion["abrir"] = puede_abrir_caso(g.yo, observacion, estudiante)
            recientes.append(observacion)
        posicion = posicion + 1

    return render_template("observador_inicio.html", activo="observador", grupos=grupos, estudiantes=estudiantes[0:100],
                           total=len(estudiantes), mostrar=mostrar, texto=texto, grupo_elegido=grupo_elegido,
                           recientes=recientes)


@app.route("/observador/estudiante/<int:estudiante_id>", methods=["GET", "POST"])
def observador_estudiante(estudiante_id):
    estudiante = estudiante_del_colegio(estudiante_id)
    if g.yo is None or estudiante is None:
        return redirect("/inicio")
    puede_ver = puede_ver_estudiante(g.yo, estudiante)
    puede_anotar = puede_anotar_estudiante(g.yo, estudiante)
    if not puede_ver and not puede_anotar:
        return redirect("/inicio")

    gestor = es_gestor(g.yo)
    errores = []
    mensaje = ""
    if request.args.get("guardada", "") == "1":
        mensaje = "Anotación guardada en el observador."
    valores = {"tipo": "positiva", "situacion_tipo": "1", "descripcion": "", "compromiso": "", "confidencial": ""}
    if request.method == "POST":
        if not puede_anotar:
            return redirect("/inicio")
        valores = {
            "tipo": request.form.get("tipo", ""),
            "situacion_tipo": request.form.get("situacion_tipo", ""),
            "descripcion": request.form.get("descripcion", "").strip(),
            "compromiso": request.form.get("compromiso", "").strip(),
            "confidencial": request.form.get("confidencial", ""),
        }
        errores = errores_de_anotacion(valores, gestor)
        if len(errores) == 0:
            situacion_tipo = 0
            if valores["tipo"] == "situacion":
                situacion_tipo = int(valores["situacion_tipo"])
            confidencial = 0
            if valores["confidencial"] == "1":
                confidencial = 1
            nuevo_id = crear_observacion({
                "colegio_id": g.colegio["id"],
                "estudiante_id": estudiante_id,
                "autor_id": g.yo["id"],
                "fecha": nucleo.hoy(),
                "tipo": valores["tipo"],
                "situacion_tipo": situacion_tipo,
                "descripcion": valores["descripcion"],
                "compromiso": valores["compromiso"],
                "confidencial": confidencial,
                "creado_en": nucleo.ahora(),
            })
            nombre = TIPOS[valores["tipo"]]
            if situacion_tipo > 0:
                nombre = "Situación tipo " + ROMANOS[situacion_tipo]
            registrar("Escribió en el observador", nombre + " para " + estudiante["nombre"] + " (anotación " + str(nuevo_id) + ")")
            if situacion_tipo > 0:
                return redirect("/observador/caso/" + str(nuevo_id) + "?creado=1")
            return redirect("/observador/estudiante/" + str(estudiante_id) + "?guardada=1")

    anotaciones = []
    reservados = 0
    conteo = {"positiva": 0, "por_mejorar": 0, "situacion": 0}
    for observacion in observaciones_del_estudiante(estudiante_id):
        if puede_ver_observacion(g.yo, observacion, estudiante):
            observacion["abrir"] = puede_abrir_caso(g.yo, observacion, estudiante)
            anotaciones.append(observacion)
            conteo[observacion["tipo"]] = conteo[observacion["tipo"]] + 1
        elif observacion["tipo"] == "situacion" and observacion["situacion_tipo"] >= 2 and observacion["estado"] == "abierta":
            reservados = reservados + 1

    grupo = grupo_del_estudiante(estudiante_id)
    activo = "observador"
    volver = None
    if tiene_alguno(g.yo, VEN_OBSERVADOR):
        volver = {"ruta": "/observador", "texto": "← Observador"}
    elif tiene_rol(g.yo, "acudiente") and g.yo["id"] != estudiante_id:
        activo = "familia"
        volver = {"ruta": "/familia", "texto": "← Mi familia"}
    else:
        activo = ""

    return render_template("observador_estudiante.html", activo=activo, estudiante=estudiante, grupo=grupo,
                           anotaciones=anotaciones, reservados=reservados, conteo=conteo, puede_ver=puede_ver,
                           puede_anotar=puede_anotar, gestor=gestor, valores=valores, errores=errores, mensaje=mensaje,
                           volver=volver, tipos=TIPOS)


@app.route("/observador/caso/<int:observacion_id>", methods=["GET", "POST"])
def caso(observacion_id):
    if g.yo is None:
        return redirect("/")
    observacion = buscar_observacion(observacion_id)
    estudiante = None
    if observacion is not None:
        estudiante = estudiante_del_colegio(observacion["estudiante_id"])
    if not puede_abrir_caso(g.yo, observacion, estudiante):
        return redirect("/inicio")

    gestor = es_gestor(g.yo)
    puede_seguir = gestor or observacion["autor_id"] == g.yo["id"]
    es_situacion = observacion["tipo"] == "situacion"
    errores = []
    mensaje = ""
    if request.args.get("creado", "") == "1":
        mensaje = "Caso registrado. Sigue los pasos del protocolo."
    elif request.args.get("seguimiento", "") == "1":
        mensaje = "Seguimiento agregado."

    if request.method == "POST":
        accion = request.form.get("accion", "")
        if accion == "seguimiento":
            texto = request.form.get("texto", "").strip()
            if not puede_seguir:
                errores.append("Solo coordinación, rectoría, orientación o quien escribió la anotación pueden agregar seguimientos.")
            elif len(texto) < 5:
                errores.append("Escribe el seguimiento: mínimo 5 caracteres.")
            elif len(texto) > 2000:
                errores.append("El seguimiento es muy largo: máximo 2000 caracteres.")
            else:
                agregar_seguimiento(observacion_id, texto)
                registrar("Agregó seguimiento", "Anotación " + str(observacion_id) + " de " + estudiante["nombre"])
                return redirect("/observador/caso/" + str(observacion_id) + "?seguimiento=1")
        elif not gestor:
            errores.append("Solo coordinación, rectoría y orientación pueden gestionar el caso.")
        elif not es_situacion:
            errores.append("Esta anotación no es un caso de convivencia.")
        elif accion == "paso":
            paso_id = request.form.get("paso_id", "").strip()
            hecho = request.form.get("hecho", "")
            paso = None
            if paso_id.isdigit():
                paso = base_datos.consultar_uno(
                    "SELECT * FROM pasos_protocolo WHERE id = ? AND observacion_id = ? AND colegio_id = ?",
                    [int(paso_id), observacion_id, g.colegio["id"]],
                )
            if paso is None or hecho not in ["0", "1"]:
                errores.append("Ese paso no pertenece a este caso.")
            elif observacion["estado"] != "abierta":
                errores.append("El caso está cerrado. Reábrelo para cambiar los pasos.")
            elif hecho == "1":
                base_datos.ejecutar(
                    "UPDATE pasos_protocolo SET hecho = 1, hecho_por = ?, hecho_en = ? WHERE id = ? AND colegio_id = ?",
                    [g.yo["id"], nucleo.ahora(), paso["id"], g.colegio["id"]],
                )
                registrar("Marcó un paso del protocolo", "Caso " + str(observacion_id) + ": " + paso["paso"])
                mensaje = "Paso marcado como hecho: " + paso["paso"] + "."
            else:
                base_datos.ejecutar(
                    "UPDATE pasos_protocolo SET hecho = 0, hecho_por = NULL, hecho_en = '' WHERE id = ? AND colegio_id = ?",
                    [paso["id"], g.colegio["id"]],
                )
                registrar("Desmarcó un paso del protocolo", "Caso " + str(observacion_id) + ": " + paso["paso"])
                mensaje = "Paso desmarcado: " + paso["paso"] + "."
        elif accion == "cerrar" or accion == "reabrir":
            nota = request.form.get("nota", "").strip()
            if len(nota) > 1000:
                errores.append("La nota es muy larga: máximo 1000 caracteres.")
            elif accion == "cerrar" and observacion["estado"] != "abierta":
                errores.append("El caso ya está cerrado.")
            elif accion == "reabrir" and observacion["estado"] != "cerrada":
                errores.append("El caso ya está abierto.")
            else:
                estado = "cerrada"
                texto = "Cerró el caso."
                if accion == "reabrir":
                    estado = "abierta"
                    texto = "Reabrió el caso."
                if nota != "":
                    texto = texto + " " + nota
                base_datos.ejecutar("UPDATE observaciones SET estado = ? WHERE id = ? AND colegio_id = ?",
                                    [estado, observacion_id, g.colegio["id"]])
                agregar_seguimiento(observacion_id, texto)
                registrar(texto.split(".")[0], "Caso " + str(observacion_id) + " de " + estudiante["nombre"])
                if estado == "cerrada":
                    mensaje = "Caso cerrado."
                else:
                    mensaje = "Caso reabierto."
        elif accion == "siuce":
            valor = request.form.get("valor", "")
            if observacion["situacion_tipo"] < 2:
                errores.append("Solo las situaciones tipo II y III se reportan en el SIUCE.")
            elif valor not in ["0", "1"]:
                errores.append("Indica si el caso quedó reportado en el SIUCE.")
            else:
                base_datos.ejecutar("UPDATE observaciones SET reportado_siuce = ? WHERE id = ? AND colegio_id = ?",
                                    [int(valor), observacion_id, g.colegio["id"]])
                if valor == "1":
                    agregar_seguimiento(observacion_id, "Registró el reporte del caso en el SIUCE.")
                    registrar("Marcó caso reportado en el SIUCE", "Caso " + str(observacion_id))
                    mensaje = "El caso quedó marcado como reportado en el SIUCE."
                else:
                    agregar_seguimiento(observacion_id, "Corrigió: el caso aún no está reportado en el SIUCE.")
                    registrar("Quitó la marca de reporte en el SIUCE", "Caso " + str(observacion_id))
                    mensaje = "Se quitó la marca de reporte en el SIUCE."
        else:
            errores.append("Acción no válida.")
        observacion = buscar_observacion(observacion_id)

    pasos = pasos_de(observacion_id)
    hechos = 0
    for paso in pasos:
        hechos = hechos + paso["hecho"]
    volver = {"ruta": "/observador/estudiante/" + str(estudiante["id"]), "texto": "← Observador de " + estudiante["nombre"]}

    return render_template("observador_caso.html", activo="observador", observacion=observacion, estudiante=estudiante,
                           grupo=grupo_del_estudiante(estudiante["id"]), pasos=pasos, hechos=hechos,
                           seguimientos=seguimientos_de(observacion_id), gestor=gestor, puede_seguir=puede_seguir,
                           es_situacion=es_situacion, errores=errores, mensaje=mensaje, volver=volver)


@app.route("/convivencia")
def convivencia():
    if not es_gestor(g.yo):
        return redirect("/inicio")

    casos = base_datos.consultar(
        CONSULTA_OBSERVACIONES + "WHERE observaciones.colegio_id = ? AND observaciones.tipo = 'situacion' "
        "ORDER BY observaciones.fecha DESC, observaciones.id DESC",
        [g.colegio["id"]],
    )
    abiertos = []
    por_reportar = []
    cerrados = []
    abiertos_por_tipo = {1: 0, 2: 0, 3: 0}
    for caso_actual in casos:
        preparar(caso_actual)
        caso_actual["grupo"] = nombre_del_grupo(caso_actual["estudiante_id"])
        caso_actual["avance"] = avance_de(caso_actual["id"])
        if caso_actual["estado"] == "abierta":
            abiertos.append(caso_actual)
            if caso_actual["situacion_tipo"] in abiertos_por_tipo:
                abiertos_por_tipo[caso_actual["situacion_tipo"]] = abiertos_por_tipo[caso_actual["situacion_tipo"]] + 1
        elif len(cerrados) < 10:
            cerrados.append(caso_actual)
        if caso_actual["situacion_tipo"] >= 2 and caso_actual["reportado_siuce"] == 0:
            por_reportar.append(caso_actual)

    anio = str(g.colegio["anio"])
    conteo = {"positiva": 0, "por_mejorar": 0, "tipo_1": 0, "tipo_2": 0, "tipo_3": 0}
    filas = base_datos.consultar(
        "SELECT tipo, situacion_tipo, COUNT(*) AS total FROM observaciones WHERE colegio_id = ? AND fecha >= ? AND fecha <= ? "
        "GROUP BY tipo, situacion_tipo",
        [g.colegio["id"], anio + "-01-01", anio + "-12-31"],
    )
    for fila in filas:
        if fila["tipo"] == "situacion":
            conteo["tipo_" + str(fila["situacion_tipo"])] = fila["total"]
        else:
            conteo[fila["tipo"]] = fila["total"]

    return render_template("observador_convivencia.html", activo="convivencia", abiertos=abiertos, por_reportar=por_reportar,
                           cerrados=cerrados, abiertos_por_tipo=abiertos_por_tipo, conteo=conteo)


def sembrar_observador():
    if base_datos.buscar_colegio(1) is None or not base_datos.tabla_vacia("observaciones"):
        return
    melany = base_datos.buscar_usuario("melany.osorio")
    andres = base_datos.buscar_usuario("andres.quintero")
    juan = base_datos.buscar_usuario("juan.restrepo")
    esteban = base_datos.buscar_usuario("esteban.ramirez")
    aguirre = base_datos.buscar_usuario("h.aguirre")
    munoz = base_datos.buscar_usuario("c.munoz")
    tapasco = base_datos.buscar_usuario("w.tapasco")
    coordinadora = base_datos.buscar_usuario("coordinadora")
    orientadora = base_datos.buscar_usuario("orientadora")
    personas = [melany, andres, juan, esteban, aguirre, munoz, tapasco, coordinadora, orientadora]
    for persona in personas:
        if persona is None:
            return

    crear_observacion({
        "colegio_id": 1, "estudiante_id": melany["id"], "autor_id": aguirre["id"], "fecha": "2026-10-23",
        "tipo": "positiva", "situacion_tipo": 0,
        "descripcion": "Lideró con su equipo la jornada de limpieza del río Lejos y presentó al grupo un informe "
                       "muy completo sobre el cuidado del agua en el Paisaje Cultural Cafetero.",
        "compromiso": "", "confidencial": 0, "creado_en": "2026-10-23 11:05",
    })
    crear_observacion({
        "colegio_id": 1, "estudiante_id": andres["id"], "autor_id": munoz["id"], "fecha": "2026-11-06",
        "tipo": "por_mejorar", "situacion_tipo": 0,
        "descripcion": "No ha entregado los tres últimos talleres de Matemáticas y se distrae con el celular durante las explicaciones.",
        "compromiso": "Ponerse al día con los talleres antes del 20 de noviembre y asistir a la tutoría del jueves.",
        "confidencial": 0, "creado_en": "2026-11-06 09:30",
    })
    tipo_uno = crear_observacion({
        "colegio_id": 1, "estudiante_id": juan["id"], "autor_id": tapasco["id"], "fecha": "2026-11-10",
        "tipo": "situacion", "situacion_tipo": 1,
        "descripcion": "Durante el partido de microfútbol en Educación Física, Juan Pablo y un compañero discutieron por una falta "
                       "y se empujaron. Nadie resultó lastimado.",
        "compromiso": "Resolver los desacuerdos hablando y respetar las decisiones del árbitro.",
        "confidencial": 0, "creado_en": "2026-11-10 10:15",
    })
    tipo_dos = crear_observacion({
        "colegio_id": 1, "estudiante_id": esteban["id"], "autor_id": orientadora["id"], "fecha": "2026-11-12",
        "tipo": "situacion", "situacion_tipo": 2,
        "descripcion": "Esteban cuenta que desde hace tres semanas recibe mensajes y memes burlones de forma repetida en un grupo "
                       "de WhatsApp de compañeros. Trae capturas de pantalla.",
        "compromiso": "", "confidencial": 1, "creado_en": "2026-11-12 08:40",
    })

    pasos_uno = base_datos.consultar("SELECT id FROM pasos_protocolo WHERE observacion_id = ? ORDER BY id", [tipo_uno])
    for posicion in range(2):
        base_datos.ejecutar("UPDATE pasos_protocolo SET hecho = 1, hecho_por = ?, hecho_en = ? WHERE id = ?",
                            [coordinadora["id"], "2026-11-11 07:30", pasos_uno[posicion]["id"]])
    pasos_dos = base_datos.consultar("SELECT id FROM pasos_protocolo WHERE observacion_id = ? ORDER BY id", [tipo_dos])
    for posicion in [1, 2]:
        base_datos.ejecutar("UPDATE pasos_protocolo SET hecho = 1, hecho_por = ?, hecho_en = ? WHERE id = ?",
                            [orientadora["id"], "2026-11-12 11:00", pasos_dos[posicion]["id"]])

    base_datos.ejecutar(
        "INSERT INTO seguimientos (colegio_id, observacion_id, autor_id, fecha, texto) VALUES (?, ?, ?, ?, ?)",
        [1, tipo_uno, tapasco["id"], "2026-11-11 10:20",
         "Los dos estudiantes se disculparon frente al equipo y acordaron jugar en el mismo equipo la próxima clase."],
    )
    base_datos.ejecutar(
        "INSERT INTO seguimientos (colegio_id, observacion_id, autor_id, fecha, texto) VALUES (?, ?, ?, ?, ?)",
        [1, tipo_dos, orientadora["id"], "2026-11-12 11:00",
         "Entrevista con Esteban y con su madre. Se acordó acompañamiento semanal de orientación."],
    )


if CON_DATOS_DE_EJEMPLO:
    sembrar_observador()
