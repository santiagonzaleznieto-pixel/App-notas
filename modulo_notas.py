from datetime import date
from flask import g, render_template, request, redirect
from nucleo import (app, agregar_menu, tiene_rol, tiene_alguno, promedio, nota_final, desempeno, numero,
                    puede_ver_grupo, puede_ver_estudiante, estudiante_del_colegio, grupo_del_estudiante,
                    registrar, hoy, ahora, fecha_valida, desempeno_definitivo, NIVELES_DESEMPENO,
                    VEN_TODOS_LOS_ESTUDIANTES, CON_DATOS_DE_EJEMPLO)
import base_datos

agregar_menu("clases", "Mis clases", "/mis-clases", ["docente"],
             "Crea actividades, califica y registra las definitivas de cada período.")
agregar_menu("grupos", "Grupos", "/grupos", VEN_TODOS_LOS_ESTUDIANTES + ["director"],
             "Consolidado de notas de cada grupo, puestos y alertas.")
agregar_menu("boletin", "Mis notas", "/mis-notas", ["estudiante"],
             "Tu boletín del año, período por período.")

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def periodos_actuales():
    return base_datos.periodos_del_anio(g.colegio["id"], g.colegio["anio"])


def fecha_larga(texto):
    if not fecha_valida(texto):
        return texto
    return str(int(texto[8:10])) + " de " + MESES[int(texto[5:7]) - 1] + " de " + texto[0:4]


def dias_entre(desde, hasta):
    return (date.fromisoformat(hasta) - date.fromisoformat(desde)).days


def celda(valor, manual):
    return {"valor": valor, "manual": manual, "desempeno": desempeno_definitivo(valor, manual)}


def vacias(periodos):
    lista = []
    for p in range(len(periodos)):
        lista.append(None)
    return lista


def definitivas_de(estudiante_id, periodos):
    notas = base_datos.notas_del_estudiante(estudiante_id, g.colegio["anio"], len(periodos))
    manuales = base_datos.desempenos_manuales_de(estudiante_id, g.colegio["anio"])
    materias = []
    for materia_id in notas:
        materias.append(materia_id)
    for materia_id in manuales:
        if materia_id not in materias:
            materias.append(materia_id)
    resultado = {}
    for materia_id in materias:
        lista = vacias(periodos)
        if materia_id in notas:
            lista = notas[materia_id]
        propios = {}
        if materia_id in manuales:
            propios = manuales[materia_id]
        celdas = []
        for i in range(len(periodos)):
            celdas.append(celda(lista[i], propios.get(i + 1)))
        resultado[materia_id] = {
            "valores": lista,
            "periodos": celdas,
            "final": celda(nota_final(lista, periodos), propios.get(0)),
        }
    return resultado


def definitiva_vacia(periodos):
    celdas = []
    for p in range(len(periodos)):
        celdas.append(celda(None, None))
    return {"valores": vacias(periodos), "periodos": celdas, "final": celda(None, None)}


def tabla_grupo(grupo_id, periodo):
    periodos = periodos_actuales()
    asignaciones = base_datos.asignaciones_del_grupo(grupo_id)
    filas = []
    for estudiante in base_datos.estudiantes_del_grupo(grupo_id):
        definitivas = definitivas_de(estudiante["id"], periodos)
        notas = []
        niveles = []
        for asignacion in asignaciones:
            datos = definitiva_vacia(periodos)
            if asignacion["materia_id"] in definitivas:
                datos = definitivas[asignacion["materia_id"]]
            if periodo == 0:
                valor = datos["final"]
            else:
                valor = datos["periodos"][periodo - 1]
            notas.append(valor["valor"])
            niveles.append(valor["desempeno"])
        filas.append({"estudiante": estudiante, "notas": notas, "niveles": niveles,
                      "promedio": promedio(notas), "puesto": None})

    for fila in filas:
        if fila["promedio"] is not None:
            puesto = 1
            for otra in filas:
                if otra["promedio"] is not None and otra["promedio"] > fila["promedio"]:
                    puesto = puesto + 1
            fila["puesto"] = puesto
    return filas


def ordenar_por_puesto(filas):
    ordenadas = []
    for posicion in range(1, len(filas) + 1):
        for fila in filas:
            if fila["puesto"] == posicion:
                ordenadas.append(fila)
    for fila in filas:
        if fila["puesto"] is None:
            ordenadas.append(fila)
    return ordenadas


def periodo_abierto(periodos):
    for periodo in periodos:
        if periodo["abierto"] == 1:
            return periodo
    return None


def asignacion_propia(asignacion_id):
    asignacion = base_datos.buscar_asignacion(asignacion_id)
    if g.yo is None or asignacion is None:
        return None
    if asignacion["colegio_id"] != g.colegio["id"] or asignacion["docente_id"] != g.yo["id"]:
        return None
    return asignacion


def resumen_periodo(asignacion, estudiantes, periodo):
    anio = g.colegio["anio"]
    actividades = base_datos.actividades_del_periodo(asignacion["id"], anio, periodo["numero"])
    calificaciones = base_datos.calificaciones_del_periodo(asignacion["id"], anio, periodo["numero"])
    periodos = periodos_actuales()
    filas = []
    guardadas = 0
    calculados = []
    for estudiante in estudiantes:
        propias = {}
        if estudiante["id"] in calificaciones:
            propias = calificaciones[estudiante["id"]]
        notas = []
        valores = []
        for actividad in actividades:
            valor = None
            observacion = ""
            if actividad["id"] in propias:
                valor = propias[actividad["id"]]["valor"]
                observacion = propias[actividad["id"]]["observacion"]
            notas.append({"valor": valor, "observacion": observacion})
            if valor is not None:
                valores.append(valor)
        calculado = promedio(valores)
        calculados.append(calculado)
        definitivas = definitivas_de(estudiante["id"], periodos)
        datos = definitiva_vacia(periodos)
        if asignacion["materia_id"] in definitivas:
            datos = definitivas[asignacion["materia_id"]]
        guardada = datos["periodos"][periodo["numero"] - 1]
        if guardada["manual"] is not None:
            estado = {"texto": "Manual", "clase": "bien"}
        elif guardada["valor"] is None and calculado is None:
            estado = {"texto": "Sin notas", "clase": "neutro"}
        elif guardada["valor"] is None:
            estado = {"texto": "Sin guardar", "clase": "atencion"}
        elif calculado is not None and guardada["valor"] != calculado:
            estado = {"texto": "Desactualizada", "clase": "atencion"}
        else:
            estado = {"texto": "Guardada", "clase": "bien"}
        if guardada["manual"] is not None or guardada["valor"] is not None:
            guardadas = guardadas + 1
        filas.append({"estudiante": estudiante, "notas": notas, "calculado": calculado,
                      "nivel_calculado": desempeno(calculado), "guardada": guardada, "estado": estado})
    return {"actividades": actividades, "filas": filas, "guardadas": guardadas, "promedio": promedio(calculados)}


def promedio_actividad(actividad, filas, posicion):
    valores = []
    for fila in filas:
        valores.append(fila["notas"][posicion]["valor"])
    return promedio(valores)


@app.route("/mis-clases")
def mis_clases():
    if not tiene_rol(g.yo, "docente"):
        return redirect("/inicio")

    periodos = periodos_actuales()
    abierto = periodo_abierto(periodos)
    faltan = None
    if abierto is not None:
        faltan = dias_entre(hoy(), abierto["fecha_fin"])

    clases = []
    for asignacion in base_datos.asignaciones_del_docente(g.yo["id"], g.colegio["anio"]):
        estudiantes = base_datos.estudiantes_del_grupo(asignacion["grupo_id"])
        actividades = 0
        guardadas = 0
        promedio_clase = None
        if abierto is not None:
            resumen = resumen_periodo(asignacion, estudiantes, abierto)
            actividades = len(resumen["actividades"])
            guardadas = resumen["guardadas"]
            promedio_clase = resumen["promedio"]
        clases.append({
            "asignacion": asignacion,
            "total": len(estudiantes),
            "actividades": actividades,
            "guardadas": guardadas,
            "promedio": promedio_clase,
        })

    return render_template("mis_clases.html", activo="clases", clases=clases, abierto=abierto, faltan=faltan,
                           fecha_larga=fecha_larga)


@app.route("/calificar/<int:asignacion_id>", methods=["GET", "POST"])
def calificar(asignacion_id):
    asignacion = asignacion_propia(asignacion_id)
    if asignacion is None:
        return redirect("/inicio")

    periodos = periodos_actuales()
    if len(periodos) == 0:
        return redirect("/mis-clases")
    estudiantes = base_datos.estudiantes_del_grupo(asignacion["grupo_id"])
    anio = g.colegio["anio"]
    abierto = periodo_abierto(periodos)

    vista = request.args.get("periodo", "")
    if vista == "final":
        return calificar_final(asignacion, estudiantes, periodos)
    periodo = None
    for p in periodos:
        if str(p["numero"]) == vista:
            periodo = p
    if periodo is None:
        periodo = abierto
    if periodo is None:
        periodo = periodos[len(periodos) - 1]

    mensaje = ""
    errores = []
    nueva = {"nombre": "", "fecha": hoy(), "descripcion": ""}
    editable = periodo["abierto"] == 1
    if request.method == "POST":
        if not editable:
            return redirect("/calificar/" + str(asignacion_id) + "?periodo=" + str(periodo["numero"]))
        accion = request.form.get("accion", "")
        if accion == "nueva_actividad":
            nueva = {
                "nombre": request.form.get("nombre", "").strip(),
                "fecha": request.form.get("fecha", "").strip(),
                "descripcion": request.form.get("descripcion", "").strip(),
            }
            errores = errores_de_actividad(nueva, periodo)
            if len(errores) == 0:
                actividad_id = base_datos.ejecutar(
                    "INSERT INTO actividades (colegio_id, anio, asignacion_id, periodo, nombre, fecha, descripcion, creado_por, creado_en) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [g.colegio["id"], anio, asignacion_id, periodo["numero"], nueva["nombre"], nueva["fecha"],
                     nueva["descripcion"], g.yo["id"], ahora()],
                )
                registrar("Creó una actividad", asignacion["materia"] + " " + asignacion["grupo"] + ": " + nueva["nombre"])
                return redirect("/calificar/" + str(asignacion_id) + "/actividad/" + str(actividad_id) + "?nueva=1")
        elif accion == "definitivas":
            resumen = resumen_periodo(asignacion, estudiantes, periodo)
            for fila in resumen["filas"]:
                eleccion = request.form.get("definitiva-" + str(fila["estudiante"]["id"]), "auto")
                manual = None
                if eleccion in NIVELES_DESEMPENO:
                    manual = eleccion
                base_datos.guardar_nota(g.colegio["id"], anio, fila["estudiante"]["id"], asignacion["materia_id"],
                                        periodo["numero"], fila["calculado"])
                base_datos.guardar_desempeno_manual(g.colegio["id"], anio, fila["estudiante"]["id"], asignacion["materia_id"],
                                                    periodo["numero"], manual, g.yo["id"], ahora())
            registrar("Guardó definitivas", asignacion["materia"] + " " + asignacion["grupo"] + ", " + periodo["nombre"].lower())
            mensaje = "Definitivas del " + periodo["nombre"].lower() + " guardadas. Ya se ven en el boletín."

    resumen = resumen_periodo(asignacion, estudiantes, periodo)
    actividades = []
    for posicion in range(len(resumen["actividades"])):
        actividad = resumen["actividades"][posicion]
        actividades.append({"actividad": actividad, "promedio": promedio_actividad(actividad, resumen["filas"], posicion)})
    faltan = None
    if editable:
        faltan = dias_entre(hoy(), periodo["fecha_fin"])

    return render_template("calificar.html", activo="clases", asignacion=asignacion, periodos=periodos, periodo=periodo,
                           resumen=resumen, actividades=actividades, editable=editable, faltan=faltan, nueva=nueva,
                           mensaje=mensaje, errores=errores, niveles=NIVELES_DESEMPENO, fecha_larga=fecha_larga)


def errores_de_actividad(datos, periodo):
    errores = []
    if len(datos["nombre"]) < 3 or len(datos["nombre"]) > 80:
        errores.append("Escribe el nombre de la actividad (entre 3 y 80 letras).")
    if not fecha_valida(datos["fecha"]):
        errores.append("La fecha no es válida.")
    elif datos["fecha"] < periodo["fecha_inicio"] or datos["fecha"] > periodo["fecha_fin"]:
        errores.append("La fecha debe estar dentro del " + periodo["nombre"].lower() + " (del "
                       + fecha_larga(periodo["fecha_inicio"]) + " al " + fecha_larga(periodo["fecha_fin"]) + ").")
    if len(datos["descripcion"]) > 300:
        errores.append("La descripción puede tener máximo 300 letras.")
    return errores


def calificar_final(asignacion, estudiantes, periodos):
    anio = g.colegio["anio"]
    ultimo = periodos[len(periodos) - 1]
    editable = ultimo["abierto"] == 1
    mensaje = ""
    if request.method == "POST":
        if not editable:
            return redirect("/calificar/" + str(asignacion["id"]) + "?periodo=final")
        for estudiante in estudiantes:
            eleccion = request.form.get("final-" + str(estudiante["id"]), "auto")
            manual = None
            if eleccion in NIVELES_DESEMPENO:
                manual = eleccion
            base_datos.guardar_desempeno_manual(g.colegio["id"], anio, estudiante["id"], asignacion["materia_id"], 0,
                                                manual, g.yo["id"], ahora())
        registrar("Guardó definitivas del año", asignacion["materia"] + " " + asignacion["grupo"])
        mensaje = "Definitivas del año guardadas. Ya se ven en el boletín."

    filas = []
    for estudiante in estudiantes:
        definitivas = definitivas_de(estudiante["id"], periodos)
        datos = definitiva_vacia(periodos)
        if asignacion["materia_id"] in definitivas:
            datos = definitivas[asignacion["materia_id"]]
        filas.append({"estudiante": estudiante, "periodos": datos["periodos"], "final": datos["final"],
                      "calculado": nota_final(datos["valores"], periodos)})
    return render_template("calificar_final.html", activo="clases", asignacion=asignacion, periodos=periodos,
                           filas=filas, editable=editable, mensaje=mensaje, niveles=NIVELES_DESEMPENO, ultimo=ultimo,
                           fecha_larga=fecha_larga)


@app.route("/calificar/<int:asignacion_id>/actividad/<int:actividad_id>", methods=["GET", "POST"])
def calificar_actividad(asignacion_id, actividad_id):
    asignacion = asignacion_propia(asignacion_id)
    actividad = base_datos.buscar_actividad(actividad_id)
    if asignacion is None or actividad is None or actividad["asignacion_id"] != asignacion_id:
        return redirect("/inicio")
    if actividad["colegio_id"] != g.colegio["id"]:
        return redirect("/inicio")

    periodo = None
    for p in periodos_actuales():
        if p["numero"] == actividad["periodo"]:
            periodo = p
    if periodo is None:
        return redirect("/calificar/" + str(asignacion_id))
    editable = periodo["abierto"] == 1
    volver = "/calificar/" + str(asignacion_id) + "?periodo=" + str(periodo["numero"])
    estudiantes = base_datos.estudiantes_del_grupo(asignacion["grupo_id"])
    minima = g.colegio["nota_minima"]
    maxima = g.colegio["nota_maxima"]
    mensaje = ""
    if request.args.get("nueva", "") == "1":
        mensaje = "Actividad creada. Ahora escribe la nota de cada estudiante."
    errores = []
    datos = {"nombre": actividad["nombre"], "fecha": actividad["fecha"], "descripcion": actividad["descripcion"]}

    if request.method == "POST":
        if not editable:
            return redirect(volver)
        accion = request.form.get("accion", "")
        if accion == "borrar":
            base_datos.borrar_actividad(actividad_id)
            registrar("Borró una actividad", asignacion["materia"] + " " + asignacion["grupo"] + ": " + actividad["nombre"])
            return redirect(volver)
        datos = {
            "nombre": request.form.get("nombre", "").strip(),
            "fecha": request.form.get("fecha", "").strip(),
            "descripcion": request.form.get("descripcion", "").strip(),
        }
        errores = errores_de_actividad(datos, periodo)
        if len(errores) == 0:
            base_datos.ejecutar("UPDATE actividades SET nombre = ?, fecha = ?, descripcion = ? WHERE id = ?",
                                [datos["nombre"], datos["fecha"], datos["descripcion"], actividad_id])
        cambios = 0
        for estudiante in estudiantes:
            campo = "nota-" + str(estudiante["id"])
            if campo in request.form:
                texto = request.form.get(campo, "").strip()
                observacion = request.form.get("obs-" + str(estudiante["id"]), "").strip()
                valor = None
                valido = True
                if texto != "":
                    valor = numero(texto, minima, maxima)
                    if valor is None:
                        valido = False
                        errores.append(estudiante["nombre"] + ": la nota debe estar entre " + str(minima) + " y " + str(maxima) + ".")
                    else:
                        valor = round(valor, 1)
                if len(observacion) > 200:
                    valido = False
                    errores.append(estudiante["nombre"] + ": la observación puede tener máximo 200 letras.")
                if valido:
                    base_datos.guardar_calificacion(g.colegio["id"], actividad_id, estudiante["id"], valor, observacion, ahora())
                    cambios = cambios + 1
        if cambios > 0:
            registrar("Calificó una actividad", asignacion["materia"] + " " + asignacion["grupo"] + ": " + datos["nombre"])
        if len(errores) == 0:
            mensaje = "Notas de la actividad guardadas."
        actividad = base_datos.buscar_actividad(actividad_id)

    calificaciones = base_datos.calificaciones_del_periodo(asignacion_id, g.colegio["anio"], periodo["numero"])
    filas = []
    valores = []
    for estudiante in estudiantes:
        valor = None
        observacion = ""
        if estudiante["id"] in calificaciones and actividad_id in calificaciones[estudiante["id"]]:
            valor = calificaciones[estudiante["id"]][actividad_id]["valor"]
            observacion = calificaciones[estudiante["id"]][actividad_id]["observacion"]
        valores.append(valor)
        filas.append({"estudiante": estudiante, "valor": valor, "observacion": observacion})

    return render_template("calificar_actividad.html", activo="clases", asignacion=asignacion, actividad=actividad,
                           periodo=periodo, filas=filas, datos=datos, editable=editable, volver=volver,
                           mensaje=mensaje, errores=errores, promedio_actividad=promedio(valores), fecha_larga=fecha_larga)


@app.route("/grupos")
def grupos():
    if g.yo is None:
        return redirect("/")
    visibles = []
    for grupo in base_datos.grupos_del_colegio(g.colegio["id"], g.colegio["anio"]):
        if puede_ver_grupo(g.yo, grupo):
            filas = tabla_grupo(grupo["id"], 0)
            promedios = []
            en_bajo = 0
            for fila in filas:
                promedios.append(fila["promedio"])
                if desempeno(fila["promedio"]) == "Bajo":
                    en_bajo = en_bajo + 1
            visibles.append({"grupo": grupo, "total": len(filas), "promedio": promedio(promedios), "en_bajo": en_bajo})
    if len(visibles) == 0:
        return redirect("/inicio")
    if len(visibles) == 1 and not tiene_alguno(g.yo, VEN_TODOS_LOS_ESTUDIANTES):
        return redirect("/grupos/" + str(visibles[0]["grupo"]["id"]))
    return render_template("grupos.html", activo="grupos", grupos=visibles)


@app.route("/grupos/<int:grupo_id>")
def consolidado(grupo_id):
    grupo = base_datos.buscar_grupo(grupo_id)
    if not puede_ver_grupo(g.yo, grupo):
        return redirect("/inicio")

    periodos = periodos_actuales()
    asignaciones = base_datos.asignaciones_del_grupo(grupo_id)
    periodo = request.args.get("periodo", "0")
    opciones = ["0"]
    for p in periodos:
        opciones.append(str(p["numero"]))
    if periodo not in opciones:
        periodo = "0"
    periodo = int(periodo)

    filas = tabla_grupo(grupo_id, periodo)
    ordenadas = ordenar_por_puesto(filas)

    promedios = []
    conteo = {"Superior": 0, "Alto": 0, "Básico": 0, "Bajo": 0, "Pendiente": 0}
    alertas = []
    for fila in filas:
        promedios.append(fila["promedio"])
        conteo[desempeno(fila["promedio"])] = conteo[desempeno(fila["promedio"])] + 1
        perdidas = []
        for i in range(len(asignaciones)):
            if fila["niveles"][i] == "Bajo":
                perdidas.append(asignaciones[i]["materia"])
        if len(perdidas) > 0:
            alertas.append({"estudiante": fila["estudiante"], "materias": perdidas})

    resumen = []
    for i in range(len(asignaciones)):
        columna = []
        en_bajo = 0
        for fila in filas:
            columna.append(fila["notas"][i])
            if fila["niveles"][i] == "Bajo":
                en_bajo = en_bajo + 1
        resumen.append({"asignacion": asignaciones[i], "promedio": promedio(columna), "en_bajo": en_bajo})

    mejor = None
    if len(ordenadas) > 0 and ordenadas[0]["puesto"] == 1:
        mejor = ordenadas[0]

    return render_template("consolidado.html", activo="grupos", grupo=grupo, filas=ordenadas, asignaciones=asignaciones,
                           periodo=periodo, periodos=periodos, promedio_grupo=promedio(promedios),
                           conteo=conteo, alertas=alertas, resumen=resumen, mejor=mejor)


@app.route("/mis-notas")
def mis_notas():
    if not tiene_rol(g.yo, "estudiante"):
        return redirect("/inicio")
    return redirect("/boletin/" + str(g.yo["id"]))


@app.route("/boletin/<int:estudiante_id>")
def boletin(estudiante_id):
    estudiante = estudiante_del_colegio(estudiante_id)
    if not puede_ver_estudiante(g.yo, estudiante):
        return redirect("/inicio")

    grupo = grupo_del_estudiante(estudiante_id)
    periodos = periodos_actuales()
    filas = []
    puesto = None
    general = None
    total = 0
    if grupo is not None:
        definitivas = definitivas_de(estudiante_id, periodos)
        for asignacion in base_datos.asignaciones_del_grupo(grupo["id"]):
            datos = definitiva_vacia(periodos)
            if asignacion["materia_id"] in definitivas:
                datos = definitivas[asignacion["materia_id"]]
            filas.append({"asignacion": asignacion, "periodos": datos["periodos"], "final": datos["final"]})
        tabla = tabla_grupo(grupo["id"], 0)
        total = len(tabla)
        for fila in tabla:
            if fila["estudiante"]["id"] == estudiante_id:
                puesto = fila["puesto"]
                general = fila["promedio"]

    nivel = desempeno(general)
    if general is None:
        mensaje = "Aún no hay notas definitivas registradas."
    elif nivel == "Superior":
        mensaje = "¡Excelente trabajo! Sigue así, eres ejemplo para el grupo."
    elif nivel == "Alto":
        mensaje = "Muy buen desempeño. Vas por excelente camino."
    elif nivel == "Básico":
        mensaje = "Vas aprobando. Con un poco más de esfuerzo puedes llegar a Alto."
    else:
        mensaje = "Necesitas reforzar. Habla con tus profesores y con tu director de grupo."

    activo = "grupos"
    if g.yo["id"] == estudiante_id:
        activo = "boletin"
    elif tiene_rol(g.yo, "acudiente"):
        activo = "familia"

    return render_template("boletin.html", activo=activo,
                           estudiante=estudiante, grupo=grupo, filas=filas, periodos=periodos, puesto=puesto,
                           general=general, mensaje=mensaje, total=total)


ACTIVIDADES_DE_EJEMPLO = {
    "Matemáticas": [["Taller de funciones cuadráticas", "2026-09-22", "Ejercicios del libro, páginas 84 a 90."],
                    ["Quiz de trigonometría", "2026-10-14", "Razones trigonométricas y triángulos rectángulos."],
                    ["Proyecto de estadística", "2026-11-05", "Encuesta en el barrio y gráficas de los resultados."]],
    "Ciencias Sociales": [["Línea de tiempo del Frente Nacional", "2026-09-24", "Trabajo en parejas."],
                          ["Exposición sobre la Constitución de 1991", "2026-10-15", "Exposición de 10 minutos por grupo."],
                          ["Evaluación del período", "2026-11-06", ""]],
    "Filosofía": [["Ensayo sobre la ética de Aristóteles", "2026-09-25", "Máximo dos páginas."],
                  ["Debate socrático", "2026-10-16", "Participación y argumentos."]],
}
OBSERVACIONES_DE_EJEMPLO = ["Entregó un día tarde.", "Excelente sustentación.", "", "", "Le faltó el punto 4.", "", ""]


def sembrar_actividades():
    colegio = base_datos.buscar_colegio(1)
    if colegio is None or not base_datos.tabla_vacia("actividades"):
        return
    grupo = base_datos.consultar_uno("SELECT id FROM grupos WHERE colegio_id = 1 AND nombre = '10-A' AND anio = ?", [colegio["anio"]])
    if grupo is None:
        return
    periodos = base_datos.periodos_del_anio(1, colegio["anio"])
    abierto = None
    for periodo in periodos:
        if periodo["abierto"] == 1:
            abierto = periodo
    if abierto is None or abierto["numero"] < 2:
        return
    estudiantes = base_datos.estudiantes_del_grupo(grupo["id"])
    ajustes = [-0.3, 0.2, 0.0, 0.4, -0.1]
    for asignacion in base_datos.asignaciones_del_grupo(grupo["id"]):
        if asignacion["materia"] in ACTIVIDADES_DE_EJEMPLO:
            lista = ACTIVIDADES_DE_EJEMPLO[asignacion["materia"]]
            for posicion in range(len(lista)):
                actividad_id = base_datos.ejecutar(
                    "INSERT INTO actividades (colegio_id, anio, asignacion_id, periodo, nombre, fecha, descripcion, creado_por, creado_en) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [1, colegio["anio"], asignacion["id"], abierto["numero"], lista[posicion][0], lista[posicion][1],
                     lista[posicion][2], asignacion["docente_id"], lista[posicion][1] + " 18:00"],
                )
                conexion = base_datos.conectar()
                for indice in range(len(estudiantes)):
                    estudiante = estudiantes[indice]
                    anteriores = base_datos.notas_del_estudiante(estudiante["id"], colegio["anio"], len(periodos))
                    base = 3.5
                    if asignacion["materia_id"] in anteriores and anteriores[asignacion["materia_id"]][abierto["numero"] - 2] is not None:
                        base = anteriores[asignacion["materia_id"]][abierto["numero"] - 2]
                    valor = round(base + ajustes[(indice + posicion) % len(ajustes)], 1)
                    if valor > 5.0:
                        valor = 5.0
                    if valor < 1.0:
                        valor = 1.0
                    observacion = OBSERVACIONES_DE_EJEMPLO[(indice + posicion * 3) % len(OBSERVACIONES_DE_EJEMPLO)]
                    base_datos.en(conexion,
                        "INSERT INTO calificaciones (colegio_id, actividad_id, estudiante_id, valor, observacion, actualizado_en) VALUES (?, ?, ?, ?, ?, ?)",
                        [1, actividad_id, estudiante["id"], valor, observacion, lista[posicion][1] + " 18:00"],
                    )
                conexion.commit()
                conexion.close()


if CON_DATOS_DE_EJEMPLO and base_datos.reclamar_siembra(2):
    sembrar_actividades()
