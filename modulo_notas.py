from flask import g, render_template, request, redirect
from nucleo import (app, agregar_menu, tiene_rol, tiene_alguno, promedio, nota_final, desempeno, numero,
                    puede_ver_grupo, puede_ver_estudiante, estudiante_del_colegio, grupo_del_estudiante,
                    registrar, VEN_TODOS_LOS_ESTUDIANTES)
import base_datos

agregar_menu("clases", "Mis clases", "/mis-clases", ["docente"],
             "Califica a tus grupos en los períodos abiertos.")
agregar_menu("grupos", "Grupos", "/grupos", VEN_TODOS_LOS_ESTUDIANTES + ["director"],
             "Consolidado de notas de cada grupo, puestos y alertas.")
agregar_menu("boletin", "Mis notas", "/mis-notas", ["estudiante"],
             "Tu boletín del año, período por período.")


def periodos_actuales():
    return base_datos.periodos_del_anio(g.colegio["id"], g.colegio["anio"])


def notas_por_materia(estudiante_id, materia_id, periodos):
    notas = base_datos.notas_del_estudiante(estudiante_id, g.colegio["anio"], len(periodos))
    if materia_id in notas:
        return notas[materia_id]
    lista = []
    for p in range(len(periodos)):
        lista.append(None)
    return lista


def tabla_grupo(grupo_id, periodo):
    periodos = periodos_actuales()
    asignaciones = base_datos.asignaciones_del_grupo(grupo_id)
    filas = []
    for estudiante in base_datos.estudiantes_del_grupo(grupo_id):
        todas = base_datos.notas_del_estudiante(estudiante["id"], g.colegio["anio"], len(periodos))
        notas = []
        for asignacion in asignaciones:
            lista = None
            if asignacion["materia_id"] in todas:
                lista = todas[asignacion["materia_id"]]
            if lista is None:
                notas.append(None)
            elif periodo == 0:
                notas.append(nota_final(lista, periodos))
            else:
                notas.append(lista[periodo - 1])
        filas.append({"estudiante": estudiante, "notas": notas, "promedio": promedio(notas), "puesto": None})

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


@app.route("/mis-clases")
def mis_clases():
    if not tiene_rol(g.yo, "docente"):
        return redirect("/inicio")

    periodos = periodos_actuales()
    abierto = None
    for periodo in periodos:
        if periodo["abierto"] == 1:
            abierto = periodo

    clases = []
    for asignacion in base_datos.asignaciones_del_docente(g.yo["id"], g.colegio["anio"]):
        estudiantes = base_datos.estudiantes_del_grupo(asignacion["grupo_id"])
        finales = []
        en_bajo = 0
        calificados = 0
        for estudiante in estudiantes:
            lista = notas_por_materia(estudiante["id"], asignacion["materia_id"], periodos)
            final = nota_final(lista, periodos)
            finales.append(final)
            if desempeno(final) == "Bajo":
                en_bajo = en_bajo + 1
            if abierto is not None and lista[abierto["numero"] - 1] is not None:
                calificados = calificados + 1
        clases.append({
            "asignacion": asignacion,
            "total": len(estudiantes),
            "promedio": promedio(finales),
            "en_bajo": en_bajo,
            "calificados": calificados,
        })

    return render_template("mis_clases.html", activo="clases", clases=clases, abierto=abierto)


@app.route("/calificar/<int:asignacion_id>", methods=["GET", "POST"])
def calificar(asignacion_id):
    if g.yo is None:
        return redirect("/")
    asignacion = base_datos.buscar_asignacion(asignacion_id)
    if asignacion is None or asignacion["colegio_id"] != g.colegio["id"] or asignacion["docente_id"] != g.yo["id"]:
        return redirect("/inicio")

    periodos = periodos_actuales()
    estudiantes = base_datos.estudiantes_del_grupo(asignacion["grupo_id"])
    minima = g.colegio["nota_minima"]
    maxima = g.colegio["nota_maxima"]
    mensaje = ""
    errores = []
    if request.method == "POST":
        cambios = 0
        for estudiante in estudiantes:
            anteriores = notas_por_materia(estudiante["id"], asignacion["materia_id"], periodos)
            for periodo in periodos:
                campo = "nota-" + str(estudiante["id"]) + "-" + str(periodo["numero"])
                if periodo["abierto"] == 1 and campo in request.form:
                    texto = request.form.get(campo, "").strip()
                    anterior = anteriores[periodo["numero"] - 1]
                    if texto == "":
                        if anterior is not None:
                            base_datos.guardar_nota(g.colegio["id"], g.colegio["anio"], estudiante["id"],
                                                    asignacion["materia_id"], periodo["numero"], None)
                            cambios = cambios + 1
                    else:
                        valor = numero(texto, minima, maxima)
                        if valor is None:
                            errores.append(estudiante["nombre"] + ", " + periodo["nombre"].lower() + ": la nota debe estar entre "
                                           + str(minima) + " y " + str(maxima) + ".")
                        elif round(valor, 1) != anterior:
                            base_datos.guardar_nota(g.colegio["id"], g.colegio["anio"], estudiante["id"],
                                                    asignacion["materia_id"], periodo["numero"], round(valor, 1))
                            cambios = cambios + 1
        if cambios > 0:
            registrar("Guardó notas", asignacion["materia"] + " " + asignacion["grupo"] + ": " + str(cambios) + " cambios")
        if len(errores) == 0:
            mensaje = "Notas guardadas correctamente."

    filas = []
    for estudiante in estudiantes:
        lista = notas_por_materia(estudiante["id"], asignacion["materia_id"], periodos)
        filas.append({"estudiante": estudiante, "notas": lista, "final": nota_final(lista, periodos)})

    return render_template("calificar.html", activo="clases", asignacion=asignacion, filas=filas,
                           periodos=periodos, mensaje=mensaje, errores=errores)


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
            if desempeno(fila["notas"][i]) == "Bajo":
                perdidas.append(asignaciones[i]["materia"])
        if len(perdidas) > 0:
            alertas.append({"estudiante": fila["estudiante"], "materias": perdidas})

    resumen = []
    for i in range(len(asignaciones)):
        columna = []
        en_bajo = 0
        for fila in filas:
            columna.append(fila["notas"][i])
            if desempeno(fila["notas"][i]) == "Bajo":
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
        todas = base_datos.notas_del_estudiante(estudiante_id, g.colegio["anio"], len(periodos))
        for asignacion in base_datos.asignaciones_del_grupo(grupo["id"]):
            lista = []
            for p in range(len(periodos)):
                lista.append(None)
            if asignacion["materia_id"] in todas:
                lista = todas[asignacion["materia_id"]]
            filas.append({"asignacion": asignacion, "notas": lista, "final": nota_final(lista, periodos)})
        tabla = tabla_grupo(grupo["id"], 0)
        total = len(tabla)
        for fila in tabla:
            if fila["estudiante"]["id"] == estudiante_id:
                puesto = fila["puesto"]
                general = fila["promedio"]

    nivel = desempeno(general)
    if general is None:
        mensaje = "Aún no hay notas registradas."
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
