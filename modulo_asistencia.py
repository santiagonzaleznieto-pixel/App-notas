from datetime import date, timedelta
from flask import g, render_template, request, redirect
import nucleo
from nucleo import (app, agregar_menu, tiene_rol, tiene_alguno, puede_ver_grupo, puede_ver_estudiante,
                    estudiante_del_colegio, grupo_del_estudiante, registrar, CON_DATOS_DE_EJEMPLO)
import base_datos

TABLAS_ASISTENCIA = """
CREATE TABLE IF NOT EXISTS asistencia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    fecha TEXT NOT NULL,
    asignacion_id INTEGER NOT NULL REFERENCES asignaciones(id),
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    estado TEXT NOT NULL,
    registrado_por INTEGER NOT NULL REFERENCES usuarios(id),
    registrado_en TEXT NOT NULL,
    UNIQUE (asignacion_id, estudiante_id, fecha)
);

CREATE INDEX IF NOT EXISTS asistencia_por_estudiante ON asistencia (estudiante_id, fecha);

CREATE TABLE IF NOT EXISTS excusas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT NOT NULL,
    motivo TEXT NOT NULL,
    enviada_por INTEGER NOT NULL REFERENCES usuarios(id),
    enviada_en TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendiente',
    revisada_por INTEGER REFERENCES usuarios(id),
    revisada_en TEXT NOT NULL DEFAULT '',
    respuesta TEXT NOT NULL DEFAULT ''
);
"""

base_datos.crear_tablas(TABLAS_ASISTENCIA)

agregar_menu("asistencia", "Asistencia", "/asistencia",
             ["docente", "director", "coordinador", "rector", "administrador", "orientador"],
             "Toma lista, revisa fallas y aprueba excusas.")
agregar_menu("mi_asistencia", "Mi asistencia", "/mi-asistencia", ["estudiante"],
             "Tus fallas, retardos y excusas.")

VEN_ASISTENCIA = ["docente", "director", "coordinador", "rector", "administrador", "orientador"]
REVISAN_TODAS = ["coordinador", "rector", "administrador"]
OPCIONES_LISTA = ["presente", "falla", "retardo"]
NOMBRES_ESTADOS = {"presente": "Presente", "falla": "Falla", "retardo": "Retardo", "excusa": "Falla con excusa"}
COLORES_ESTADOS = {"presente": "bien", "falla": "mal", "retardo": "atencion", "excusa": "neutro"}
NOMBRES_EXCUSAS = {"pendiente": "Pendiente", "aprobada": "Aprobada", "rechazada": "Rechazada"}
COLORES_EXCUSAS = {"pendiente": "atencion", "aprobada": "bien", "rechazada": "mal"}

CONSULTA_EXCUSAS = (
    "SELECT excusas.*, alumno.nombre AS estudiante_nombre, quien_envia.nombre AS enviada_por_nombre, "
    "quien_revisa.nombre AS revisada_por_nombre FROM excusas "
    "JOIN usuarios AS alumno ON alumno.id = excusas.estudiante_id "
    "JOIN usuarios AS quien_envia ON quien_envia.id = excusas.enviada_por "
    "LEFT JOIN usuarios AS quien_revisa ON quien_revisa.id = excusas.revisada_por "
)


def fecha_valida(texto):
    if len(texto) != 10 or texto[4] != "-" or texto[7] != "-":
        return False
    for posicion in range(10):
        if posicion != 4 and posicion != 7 and texto[posicion] not in "0123456789":
            return False
    anio = int(texto[0:4])
    mes = int(texto[5:7])
    dia = int(texto[8:10])
    if anio < 1 or mes < 1 or mes > 12 or dia < 1:
        return False
    dias_del_mes = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0):
        dias_del_mes[1] = 29
    return dia <= dias_del_mes[mes - 1]


def dias_antes(fecha, dias):
    return (date.fromisoformat(fecha) - timedelta(days=dias)).isoformat()


def lunes_de_la_semana(fecha):
    dia = date.fromisoformat(fecha)
    return (dia - timedelta(days=dia.weekday())).isoformat()


def limites_del_anio():
    anio = str(g.colegio["anio"])
    limites = {"inicio": anio + "-01-01", "fin": anio + "-12-31"}
    periodos = base_datos.periodos_del_anio(g.colegio["id"], g.colegio["anio"])
    if len(periodos) > 0:
        limites["inicio"] = periodos[0]["fecha_inicio"]
        limites["fin"] = periodos[len(periodos) - 1]["fecha_fin"]
    return limites


def problema_con_fecha(fecha):
    limites = limites_del_anio()
    if not fecha_valida(fecha):
        return "Escribe la fecha con la forma AAAA-MM-DD."
    if fecha > nucleo.hoy():
        return "No se puede tomar lista de un día que todavía no llega."
    if fecha < limites["inicio"] or fecha > limites["fin"]:
        return "La fecha debe estar dentro del año escolar: del " + limites["inicio"] + " al " + limites["fin"] + "."
    return ""


def fecha_por_defecto():
    limites = limites_del_anio()
    fecha = nucleo.hoy()
    if fecha > limites["fin"]:
        fecha = limites["fin"]
    return fecha


def es_acudiente_de(yo, estudiante_id):
    if not tiene_rol(yo, "acudiente"):
        return False
    for hijo in base_datos.estudiantes_a_cargo(yo["id"]):
        if hijo["id"] == estudiante_id:
            return True
    return False


def puede_revisar_excusas(yo):
    return tiene_alguno(yo, REVISAN_TODAS + ["director"])


def puede_revisar_excusa(yo, estudiante_id):
    estudiante = estudiante_del_colegio(estudiante_id)
    if yo is None or estudiante is None:
        return False
    if tiene_alguno(yo, REVISAN_TODAS):
        return True
    if tiene_rol(yo, "director"):
        grupo = grupo_del_estudiante(estudiante_id)
        return grupo is not None and grupo["director_id"] == yo["id"]
    return False


def guardar_asistencia(fecha, asignacion_id, estudiante_id, estado):
    base_datos.ejecutar(
        "INSERT OR REPLACE INTO asistencia (colegio_id, fecha, asignacion_id, estudiante_id, estado, registrado_por, registrado_en) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [g.colegio["id"], fecha, asignacion_id, estudiante_id, estado, g.yo["id"], nucleo.ahora()],
    )


def lista_del_dia(asignacion_id, fecha):
    estados = {}
    filas = base_datos.consultar(
        "SELECT estudiante_id, estado FROM asistencia WHERE colegio_id = ? AND asignacion_id = ? AND fecha = ?",
        [g.colegio["id"], asignacion_id, fecha],
    )
    for fila in filas:
        estados[fila["estudiante_id"]] = fila["estado"]
    return estados


def listas_recientes(asignacion_id):
    return base_datos.consultar(
        "SELECT fecha, COUNT(*) AS total, SUM(CASE WHEN estado = 'falla' THEN 1 ELSE 0 END) AS fallas "
        "FROM asistencia WHERE colegio_id = ? AND asignacion_id = ? GROUP BY fecha ORDER BY fecha DESC LIMIT 8",
        [g.colegio["id"], asignacion_id],
    )


def excusa_aprobada(estudiante_id, fecha):
    excusa = base_datos.consultar_uno(
        "SELECT id FROM excusas WHERE colegio_id = ? AND estudiante_id = ? AND estado = 'aprobada' "
        "AND fecha_inicio <= ? AND fecha_fin >= ?",
        [g.colegio["id"], estudiante_id, fecha, fecha],
    )
    return excusa is not None


def registros_del_estudiante(estudiante_id):
    limites = limites_del_anio()
    return base_datos.consultar(
        "SELECT asistencia.*, materias.nombre AS materia FROM asistencia "
        "JOIN asignaciones ON asignaciones.id = asistencia.asignacion_id "
        "JOIN materias ON materias.id = asignaciones.materia_id "
        "WHERE asistencia.colegio_id = ? AND asistencia.estudiante_id = ? AND asistencia.fecha >= ? AND asistencia.fecha <= ? "
        "ORDER BY asistencia.fecha DESC, materias.id",
        [g.colegio["id"], estudiante_id, limites["inicio"], limites["fin"]],
    )


def inasistencia_continua(registros):
    dias = []
    completos = {}
    for registro in registros:
        if registro["fecha"] not in completos:
            dias.append(registro["fecha"])
            completos[registro["fecha"]] = True
        if registro["estado"] != "falla":
            completos[registro["fecha"]] = False

    continua = {"dias": 0, "desde": "", "hasta": "", "vigente": False, "marca": 0}
    posicion = 0
    while posicion < len(dias) and not completos[dias[posicion]]:
        posicion = posicion + 1
    if posicion == len(dias):
        return continua

    hasta = dias[posicion]
    desde = hasta
    while posicion < len(dias) and completos[dias[posicion]]:
        desde = dias[posicion]
        posicion = posicion + 1

    total = (date.fromisoformat(hasta) - date.fromisoformat(desde)).days + 1
    continua["dias"] = total
    continua["desde"] = desde
    continua["hasta"] = hasta
    continua["vigente"] = hasta == dias[0]
    if total >= 30:
        continua["marca"] = 30
    elif total >= 20:
        continua["marca"] = 20
    elif total >= 10:
        continua["marca"] = 10
    return continua


def alertas_de(resumen):
    alertas = []
    if resumen["fallas_recientes"] >= 3:
        alertas.append({"nivel": "atencion",
                        "texto": str(resumen["fallas_recientes"]) + " fallas sin excusa en los últimos 30 días."})
    continua = resumen["continua"]
    if continua["marca"] > 0:
        texto = (str(continua["dias"]) + " días calendario de inasistencia continua sin justificar (del "
                 + continua["desde"] + " al " + continua["hasta"] + ").")
        nivel = "mal"
        if continua["dias"] > 30:
            texto = texto + " Supera los 30 días: la Resolución 5862 de 2024 ordena retirarlo del SIMAT."
        elif continua["marca"] == 30:
            texto = texto + " Llegó a 30 días: si los supera, la Resolución 5862 de 2024 ordena retirarlo del SIMAT."
        elif continua["marca"] == 20:
            texto = texto + " Pasó los 20 días: cite al acudiente y avise a coordinación y orientación."
        else:
            texto = texto + " Pasó los 10 días: comuníquese con la familia."
            nivel = "atencion"
        if not continua["vigente"]:
            texto = texto + " Ya volvió a clase."
        alertas.append({"nivel": nivel, "texto": texto})
    return alertas


def resumen_asistencia(estudiante_id):
    registros = registros_del_estudiante(estudiante_id)
    hoy = nucleo.hoy()
    desde = dias_antes(hoy, 30)
    resumen = {"registros": registros, "presente": 0, "falla": 0, "retardo": 0, "excusa": 0, "fallas_recientes": 0}
    for registro in registros:
        resumen[registro["estado"]] = resumen[registro["estado"]] + 1
        if registro["estado"] == "falla" and registro["fecha"] >= desde and registro["fecha"] <= hoy:
            resumen["fallas_recientes"] = resumen["fallas_recientes"] + 1
    resumen["continua"] = inasistencia_continua(registros)
    resumen["alertas"] = alertas_de(resumen)
    return resumen


def fallas_entre(estudiante_id, inicio, fin):
    fila = base_datos.consultar_uno(
        "SELECT COUNT(*) AS total FROM asistencia WHERE colegio_id = ? AND estudiante_id = ? AND estado = 'falla' "
        "AND fecha >= ? AND fecha <= ?",
        [g.colegio["id"], estudiante_id, inicio, fin],
    )
    return fila["total"]


def justificar_fallas(excusa):
    cantidad = fallas_entre(excusa["estudiante_id"], excusa["fecha_inicio"], excusa["fecha_fin"])
    base_datos.ejecutar(
        "UPDATE asistencia SET estado = 'excusa' WHERE colegio_id = ? AND estudiante_id = ? AND estado = 'falla' "
        "AND fecha >= ? AND fecha <= ?",
        [g.colegio["id"], excusa["estudiante_id"], excusa["fecha_inicio"], excusa["fecha_fin"]],
    )
    return cantidad


def excusas_del_estudiante(estudiante_id):
    return base_datos.consultar(
        CONSULTA_EXCUSAS + "WHERE excusas.colegio_id = ? AND excusas.estudiante_id = ? "
        "ORDER BY excusas.fecha_inicio DESC, excusas.id DESC",
        [g.colegio["id"], estudiante_id],
    )


def excusas_visibles(estado, limite):
    visibles = []
    if estado == "pendiente":
        filas = base_datos.consultar(
            CONSULTA_EXCUSAS + "WHERE excusas.colegio_id = ? AND excusas.estado = 'pendiente' ORDER BY excusas.enviada_en, excusas.id",
            [g.colegio["id"]],
        )
    else:
        filas = base_datos.consultar(
            CONSULTA_EXCUSAS + "WHERE excusas.colegio_id = ? AND excusas.estado != 'pendiente' "
            "ORDER BY excusas.revisada_en DESC, excusas.id DESC LIMIT 200",
            [g.colegio["id"]],
        )
    posicion = 0
    while posicion < len(filas) and len(visibles) < limite:
        excusa = filas[posicion]
        if puede_revisar_excusa(g.yo, excusa["estudiante_id"]):
            grupo = grupo_del_estudiante(excusa["estudiante_id"])
            excusa["grupo"] = ""
            if grupo is not None:
                excusa["grupo"] = grupo["nombre"]
            excusa["fallas"] = fallas_entre(excusa["estudiante_id"], excusa["fecha_inicio"], excusa["fecha_fin"])
            visibles.append(excusa)
        posicion = posicion + 1
    return visibles


def errores_de_excusa(valores):
    errores = []
    limites = limites_del_anio()
    hace_un_mes = dias_antes(nucleo.hoy(), 30)
    if not fecha_valida(valores["fecha_inicio"]) or not fecha_valida(valores["fecha_fin"]):
        errores.append("Escribe las dos fechas con la forma AAAA-MM-DD.")
    elif valores["fecha_fin"] < valores["fecha_inicio"]:
        errores.append("La fecha final no puede ser anterior a la fecha inicial.")
    elif valores["fecha_inicio"] < hace_un_mes:
        errores.append("Solo se reciben excusas de los últimos 30 días (desde el " + hace_un_mes + ").")
    elif valores["fecha_inicio"] < limites["inicio"] or valores["fecha_fin"] > limites["fin"]:
        errores.append("La excusa debe quedar dentro del año escolar: del " + limites["inicio"] + " al " + limites["fin"] + ".")
    if valores["motivo"] == "":
        errores.append("Escribe el motivo de la inasistencia.")
    elif len(valores["motivo"]) > 1000:
        errores.append("El motivo es muy largo: máximo 1000 caracteres.")
    return errores


@app.route("/asistencia")
def asistencia():
    if not tiene_alguno(g.yo, VEN_ASISTENCIA):
        return redirect("/inicio")

    hoy = nucleo.hoy()
    lunes = lunes_de_la_semana(hoy)
    clases = []
    if tiene_rol(g.yo, "docente"):
        for asignacion in base_datos.asignaciones_del_docente(g.yo["id"], g.colegio["anio"]):
            semana = base_datos.consultar_uno(
                "SELECT COUNT(DISTINCT fecha) AS listas, MAX(fecha) AS ultima FROM asistencia "
                "WHERE colegio_id = ? AND asignacion_id = ? AND fecha >= ? AND fecha <= ?",
                [g.colegio["id"], asignacion["id"], lunes, hoy],
            )
            ultima = base_datos.consultar_uno(
                "SELECT MAX(fecha) AS fecha FROM asistencia WHERE colegio_id = ? AND asignacion_id = ?",
                [g.colegio["id"], asignacion["id"]],
            )
            clases.append({
                "asignacion": asignacion,
                "semana": semana["listas"],
                "hoy": semana["ultima"] == hoy,
                "ultima": ultima["fecha"],
                "total": len(base_datos.estudiantes_del_grupo(asignacion["grupo_id"])),
            })

    grupos = []
    for grupo in base_datos.grupos_del_colegio(g.colegio["id"], g.colegio["anio"]):
        if puede_ver_grupo(g.yo, grupo):
            estudiantes = base_datos.estudiantes_del_grupo(grupo["id"])
            fallas = 0
            con_alerta = 0
            for estudiante in estudiantes:
                resumen = resumen_asistencia(estudiante["id"])
                fallas = fallas + resumen["fallas_recientes"]
                if len(resumen["alertas"]) > 0:
                    con_alerta = con_alerta + 1
            grupos.append({"grupo": grupo, "total": len(estudiantes), "fallas": fallas, "con_alerta": con_alerta})

    pendientes = None
    if puede_revisar_excusas(g.yo):
        pendientes = len(excusas_visibles("pendiente", 1000))

    return render_template("asistencia_inicio.html", activo="asistencia", clases=clases, grupos=grupos,
                           pendientes=pendientes, lunes=lunes, hoy=hoy)


@app.route("/asistencia/tomar/<int:asignacion_id>", methods=["GET", "POST"])
def tomar_lista(asignacion_id):
    if g.yo is None:
        return redirect("/")
    asignacion = base_datos.buscar_asignacion(asignacion_id)
    if asignacion is None or asignacion["colegio_id"] != g.colegio["id"] or asignacion["docente_id"] != g.yo["id"]:
        return redirect("/inicio")
    grupo = base_datos.buscar_grupo(asignacion["grupo_id"])
    if grupo is None or grupo["anio"] != g.colegio["anio"]:
        return redirect("/inicio")

    estudiantes = base_datos.estudiantes_del_grupo(asignacion["grupo_id"])
    errores = []
    mensaje = ""
    elegidos = {}
    if request.method == "POST":
        fecha = request.form.get("fecha", "").strip()
    else:
        fecha = request.args.get("fecha", "").strip()
    if fecha == "":
        fecha = fecha_por_defecto()
    problema = problema_con_fecha(fecha)

    if problema != "":
        errores.append(problema)
    elif request.method == "POST":
        accion = request.form.get("accion", "guardar")
        for estudiante in estudiantes:
            estado = "presente"
            if accion != "todos":
                estado = request.form.get("estado-" + str(estudiante["id"]), "")
            if estado not in OPCIONES_LISTA:
                errores.append(estudiante["nombre"] + ": elige Presente, Falla o Retardo.")
            elegidos[estudiante["id"]] = estado
        if len(errores) == 0:
            conteo = {"presente": 0, "falla": 0, "retardo": 0, "excusa": 0}
            for estudiante in estudiantes:
                estado = elegidos[estudiante["id"]]
                if estado == "falla" and excusa_aprobada(estudiante["id"], fecha):
                    estado = "excusa"
                guardar_asistencia(fecha, asignacion_id, estudiante["id"], estado)
                conteo[estado] = conteo[estado] + 1
            registrar("Tomó lista", asignacion["materia"] + " " + asignacion["grupo"] + " del " + fecha + ": "
                      + str(conteo["falla"]) + " fallas, " + str(conteo["retardo"]) + " retardos")
            mensaje = ("Lista del " + fecha + " guardada: " + str(conteo["presente"]) + " presentes, "
                       + str(conteo["falla"]) + " fallas, " + str(conteo["retardo"]) + " retardos")
            if conteo["excusa"] > 0:
                mensaje = mensaje + " y " + str(conteo["excusa"]) + " fallas con excusa aprobada"
            mensaje = mensaje + "."
            elegidos = {}

    guardados = {}
    if problema == "":
        guardados = lista_del_dia(asignacion_id, fecha)
    filas = []
    for estudiante in estudiantes:
        guardado = None
        if estudiante["id"] in guardados:
            guardado = guardados[estudiante["id"]]
        estado = "presente"
        if estudiante["id"] in elegidos and elegidos[estudiante["id"]] in OPCIONES_LISTA:
            estado = elegidos[estudiante["id"]]
        elif guardado == "excusa":
            estado = "falla"
        elif guardado is not None:
            estado = guardado
        excusa = False
        if problema == "":
            excusa = excusa_aprobada(estudiante["id"], fecha)
        filas.append({"estudiante": estudiante, "estado": estado, "guardado": guardado, "excusa": excusa})

    limites = limites_del_anio()
    maxima = nucleo.hoy()
    if maxima > limites["fin"]:
        maxima = limites["fin"]
    return render_template("asistencia_tomar.html", activo="asistencia", asignacion=asignacion, filas=filas,
                           fecha=fecha, fecha_ok=problema == "", tomada=len(guardados) > 0,
                           recientes=listas_recientes(asignacion_id), minima=limites["inicio"], maxima=maxima,
                           errores=errores, mensaje=mensaje, nombres_estados=NOMBRES_ESTADOS)


@app.route("/asistencia/grupo/<int:grupo_id>")
def asistencia_grupo(grupo_id):
    grupo = base_datos.buscar_grupo(grupo_id)
    if not puede_ver_grupo(g.yo, grupo):
        return redirect("/inicio")

    limites = limites_del_anio()
    filas = []
    alertas = []
    totales = {"falla": 0, "retardo": 0, "excusa": 0}
    for estudiante in base_datos.estudiantes_del_grupo(grupo_id):
        resumen = resumen_asistencia(estudiante["id"])
        filas.append({"estudiante": estudiante, "resumen": resumen})
        totales["falla"] = totales["falla"] + resumen["falla"]
        totales["retardo"] = totales["retardo"] + resumen["retardo"]
        totales["excusa"] = totales["excusa"] + resumen["excusa"]
        if len(resumen["alertas"]) > 0:
            alertas.append({"estudiante": estudiante, "alertas": resumen["alertas"]})

    materias = []
    for asignacion in base_datos.asignaciones_del_grupo(grupo_id):
        datos = base_datos.consultar_uno(
            "SELECT COUNT(DISTINCT fecha) AS listas, MAX(fecha) AS ultima FROM asistencia "
            "WHERE colegio_id = ? AND asignacion_id = ? AND fecha >= ? AND fecha <= ?",
            [g.colegio["id"], asignacion["id"], limites["inicio"], limites["fin"]],
        )
        materias.append({"asignacion": asignacion, "listas": datos["listas"], "ultima": datos["ultima"]})

    return render_template("asistencia_grupo.html", activo="asistencia", grupo=grupo, filas=filas, alertas=alertas,
                           totales=totales, materias=materias, limites=limites)


@app.route("/asistencia/estudiante/<int:estudiante_id>", methods=["GET", "POST"])
def asistencia_estudiante(estudiante_id):
    estudiante = estudiante_del_colegio(estudiante_id)
    if not puede_ver_estudiante(g.yo, estudiante):
        return redirect("/inicio")

    acudiente = es_acudiente_de(g.yo, estudiante_id)
    errores = []
    mensaje = ""
    if request.args.get("enviada", "") == "1":
        mensaje = "Excusa enviada. La coordinación o el director de grupo la revisará."
    valores = {"fecha_inicio": nucleo.hoy(), "fecha_fin": nucleo.hoy(), "motivo": ""}
    if request.method == "POST":
        if not acudiente:
            return redirect("/inicio")
        valores = {
            "fecha_inicio": request.form.get("fecha_inicio", "").strip(),
            "fecha_fin": request.form.get("fecha_fin", "").strip(),
            "motivo": request.form.get("motivo", "").strip(),
        }
        errores = errores_de_excusa(valores)
        if len(errores) == 0:
            base_datos.ejecutar(
                "INSERT INTO excusas (colegio_id, estudiante_id, fecha_inicio, fecha_fin, motivo, enviada_por, enviada_en) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [g.colegio["id"], estudiante_id, valores["fecha_inicio"], valores["fecha_fin"], valores["motivo"],
                 g.yo["id"], nucleo.ahora()],
            )
            registrar("Envió una excusa", estudiante["nombre"] + ": del " + valores["fecha_inicio"] + " al " + valores["fecha_fin"])
            return redirect("/asistencia/estudiante/" + str(estudiante_id) + "?enviada=1")

    resumen = resumen_asistencia(estudiante_id)
    novedades = []
    for registro in resumen["registros"]:
        if registro["estado"] != "presente":
            novedades.append(registro)

    grupo = grupo_del_estudiante(estudiante_id)
    activo = "asistencia"
    volver = None
    if g.yo["id"] == estudiante_id:
        activo = "mi_asistencia"
    elif acudiente:
        activo = "familia"
        volver = {"ruta": "/familia", "texto": "← Mi familia"}
    elif grupo is not None and puede_ver_grupo(g.yo, grupo):
        volver = {"ruta": "/asistencia/grupo/" + str(grupo["id"]), "texto": "← Asistencia de " + grupo["nombre"]}
    elif tiene_alguno(g.yo, VEN_ASISTENCIA):
        volver = {"ruta": "/asistencia", "texto": "← Asistencia"}

    return render_template("asistencia_estudiante.html", activo=activo, estudiante=estudiante, grupo=grupo,
                           resumen=resumen, novedades=novedades, excusas=excusas_del_estudiante(estudiante_id),
                           acudiente=acudiente, valores=valores, errores=errores, mensaje=mensaje, volver=volver,
                           minima=dias_antes(nucleo.hoy(), 30), limites=limites_del_anio(),
                           nombres_estados=NOMBRES_ESTADOS, colores_estados=COLORES_ESTADOS,
                           nombres_excusas=NOMBRES_EXCUSAS, colores_excusas=COLORES_EXCUSAS)


@app.route("/mi-asistencia")
def mi_asistencia():
    if not tiene_rol(g.yo, "estudiante"):
        return redirect("/inicio")
    return redirect("/asistencia/estudiante/" + str(g.yo["id"]))


@app.route("/asistencia/excusas", methods=["GET", "POST"])
def excusas():
    if not puede_revisar_excusas(g.yo):
        return redirect("/inicio")

    errores = []
    mensaje = ""
    if request.method == "POST":
        excusa_id = request.form.get("excusa_id", "").strip()
        accion = request.form.get("accion", "")
        respuesta = request.form.get("respuesta", "").strip()
        excusa = None
        if excusa_id.isdigit():
            excusa = base_datos.consultar_uno("SELECT * FROM excusas WHERE id = ? AND colegio_id = ?",
                                              [int(excusa_id), g.colegio["id"]])
        if excusa is None or not puede_revisar_excusa(g.yo, excusa["estudiante_id"]):
            errores.append("Esa excusa no existe o no te corresponde revisarla.")
        elif excusa["estado"] != "pendiente":
            errores.append("Esa excusa ya fue revisada.")
        elif accion not in ["aprobar", "rechazar"]:
            errores.append("Elige si apruebas o rechazas la excusa.")
        elif accion == "rechazar" and respuesta == "":
            errores.append("Escribe el motivo del rechazo para que la familia lo conozca.")
        elif len(respuesta) > 500:
            errores.append("La respuesta es muy larga: máximo 500 caracteres.")
        else:
            estado = "aprobada"
            if accion == "rechazar":
                estado = "rechazada"
            base_datos.ejecutar(
                "UPDATE excusas SET estado = ?, revisada_por = ?, revisada_en = ?, respuesta = ? WHERE id = ? AND colegio_id = ?",
                [estado, g.yo["id"], nucleo.ahora(), respuesta, excusa["id"], g.colegio["id"]],
            )
            nombre = base_datos.buscar_usuario_por_id(excusa["estudiante_id"])["nombre"]
            if estado == "aprobada":
                cambiadas = justificar_fallas(excusa)
                registrar("Aprobó una excusa", nombre + ": del " + excusa["fecha_inicio"] + " al " + excusa["fecha_fin"]
                          + ", " + str(cambiadas) + " fallas justificadas")
                mensaje = "Excusa de " + nombre + " aprobada. Fallas justificadas: " + str(cambiadas) + "."
            else:
                registrar("Rechazó una excusa", nombre + ": del " + excusa["fecha_inicio"] + " al " + excusa["fecha_fin"])
                mensaje = "Excusa de " + nombre + " rechazada."

    return render_template("asistencia_excusas.html", activo="asistencia", pendientes=excusas_visibles("pendiente", 1000),
                           revisadas=excusas_visibles("revisadas", 10), errores=errores, mensaje=mensaje,
                           nombres_excusas=NOMBRES_EXCUSAS, colores_excusas=COLORES_EXCUSAS)


NOVEDADES_SEMILLA = [
    {"usuario": "juan.restrepo", "materia": "Matemáticas", "fecha": "2026-11-05", "estado": "falla"},
    {"usuario": "juan.restrepo", "materia": "Ciencias Sociales", "fecha": "2026-11-05", "estado": "falla"},
    {"usuario": "juan.restrepo", "materia": "Matemáticas", "fecha": "2026-11-12", "estado": "falla"},
    {"usuario": "juan.restrepo", "materia": "Ciencias Sociales", "fecha": "2026-11-09", "estado": "retardo"},
    {"usuario": "melany.osorio", "materia": "Matemáticas", "fecha": "2026-11-10", "estado": "falla"},
    {"usuario": "samuel.ocampo", "materia": "Matemáticas", "fecha": "2026-11-04", "estado": "retardo"},
    {"usuario": "samuel.ocampo", "materia": "Matemáticas", "fecha": "2026-11-09", "estado": "retardo"},
    {"usuario": "samuel.ocampo", "materia": "Ciencias Sociales", "fecha": "2026-11-11", "estado": "falla"},
    {"usuario": "david.giraldo", "materia": "Ciencias Sociales", "fecha": "2026-11-06", "estado": "retardo"},
    {"usuario": "isabella.mejia", "materia": "Matemáticas", "fecha": "2026-11-13", "estado": "retardo"},
    {"usuario": "sharon.loaiza", "materia": "Ciencias Sociales", "fecha": "2026-11-03", "estado": "retardo"},
]


def sembrar_asistencia():
    colegio = base_datos.buscar_colegio(1)
    if colegio is None or not base_datos.tabla_vacia("asistencia"):
        return
    grupo = base_datos.consultar_uno("SELECT id FROM grupos WHERE colegio_id = ? AND anio = ? AND nombre = ?",
                                     [1, colegio["anio"], "10-A"])
    melany = base_datos.buscar_usuario("melany.osorio")
    gloria = base_datos.buscar_usuario("gloria.cardenas")
    if grupo is None or melany is None or gloria is None:
        return
    asignaciones = {}
    for asignacion in base_datos.asignaciones_del_grupo(grupo["id"]):
        asignaciones[asignacion["materia"]] = asignacion
    if "Matemáticas" not in asignaciones or "Ciencias Sociales" not in asignaciones:
        return

    novedades = {}
    for novedad in NOVEDADES_SEMILLA:
        persona = base_datos.buscar_usuario(novedad["usuario"])
        if persona is not None:
            novedades[str(persona["id"]) + "|" + novedad["materia"] + "|" + novedad["fecha"]] = novedad["estado"]

    dias = []
    dia = date(2026, 11, 3)
    while dia <= date(2026, 11, 13):
        if dia.weekday() < 5:
            dias.append(dia.isoformat())
        dia = dia + timedelta(days=1)

    horas = {"Matemáticas": " 07:10", "Ciencias Sociales": " 09:40"}
    estudiantes = base_datos.estudiantes_del_grupo(grupo["id"])
    conexion = base_datos.conectar()
    for fecha in dias:
        for materia in ["Matemáticas", "Ciencias Sociales"]:
            asignacion = asignaciones[materia]
            for estudiante in estudiantes:
                clave = str(estudiante["id"]) + "|" + materia + "|" + fecha
                estado = "presente"
                if clave in novedades:
                    estado = novedades[clave]
                conexion.execute(
                    "INSERT INTO asistencia (colegio_id, fecha, asignacion_id, estudiante_id, estado, registrado_por, registrado_en) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [1, fecha, asignacion["id"], estudiante["id"], estado, asignacion["docente_id"], fecha + horas[materia]],
                )
    conexion.execute(
        "INSERT INTO excusas (colegio_id, estudiante_id, fecha_inicio, fecha_fin, motivo, enviada_por, enviada_en) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [1, melany["id"], "2026-11-10", "2026-11-10",
         "Melany tuvo cita con el odontólogo en el hospital de Pijao a las 7 de la mañana. "
         "La constancia de la cita se la entrego al director de grupo.",
         gloria["id"], "2026-11-10 18:25"],
    )
    conexion.commit()
    conexion.close()


if CON_DATOS_DE_EJEMPLO:
    sembrar_asistencia()
