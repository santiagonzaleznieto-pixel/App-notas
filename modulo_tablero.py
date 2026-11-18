from datetime import date, timedelta
from flask import g, render_template, redirect
from nucleo import app, agregar_menu, tiene_alguno, promedio, nota_final, desempeno, hoy
from modulo_notas import tabla_grupo, periodos_actuales
import base_datos

QUIENES = ["rector", "coordinador", "administrador"]
NIVELES = ["Superior", "Alto", "Básico", "Bajo", "Pendiente"]

agregar_menu("indicadores", "Indicadores", "/indicadores", QUIENES,
             "Desempeño de cada grupo, promedio por materia y alertas del colegio.")


def existe_tabla(nombre):
    fila = base_datos.consultar_uno("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", [nombre])
    return fila is not None


def contar(sql, valores):
    fila = base_datos.consultar_uno(sql, valores)
    if fila is None or fila["total"] is None:
        return 0
    return fila["total"]


def ordenar_de_mayor_a_menor(lista, campo):
    copia = []
    for elemento in lista:
        copia.append(elemento)
    ordenada = []
    while len(copia) > 0:
        mayor = 0
        for i in range(len(copia)):
            if copia[i][campo] is not None and (copia[mayor][campo] is None or copia[i][campo] > copia[mayor][campo]):
                mayor = i
        ordenada.append(copia.pop(mayor))
    return ordenada


def alertas_del_colegio(colegio_id):
    alertas = []
    if existe_tabla("asistencia"):
        desde = (date.fromisoformat(hoy()) - timedelta(days=30)).isoformat()
        fallas = contar("SELECT COUNT(*) AS total FROM asistencia WHERE colegio_id = ? AND estado = 'falla' AND fecha >= ?", [colegio_id, desde])
        alertas.append({"titulo": "Fallas sin excusa en los últimos 30 días", "valor": fallas, "ruta": "/asistencia"})
    if existe_tabla("excusas"):
        pendientes = contar("SELECT COUNT(*) AS total FROM excusas WHERE colegio_id = ? AND estado = 'pendiente'", [colegio_id])
        alertas.append({"titulo": "Excusas por revisar", "valor": pendientes, "ruta": "/asistencia/excusas"})
    if existe_tabla("observaciones"):
        casos = contar("SELECT COUNT(*) AS total FROM observaciones WHERE colegio_id = ? AND tipo = 'situacion' AND situacion_tipo >= 2 AND estado = 'abierta'", [colegio_id])
        alertas.append({"titulo": "Casos de convivencia tipo II y III abiertos", "valor": casos, "ruta": "/convivencia"})
    if existe_tabla("horas_registradas"):
        sin_completar = 0
        for grupo in base_datos.grupos_del_colegio(colegio_id, g.colegio["anio"]):
            if grupo["orden_grado"] == ultimo_grado(colegio_id):
                for estudiante in base_datos.estudiantes_del_grupo(grupo["id"]):
                    horas = contar("SELECT SUM(horas) AS total FROM horas_registradas WHERE estudiante_id = ? AND tipo = 'social' AND estado = 'aprobada'", [estudiante["id"]])
                    if horas < 80:
                        sin_completar = sin_completar + 1
        alertas.append({"titulo": "Estudiantes del último grado sin las 80 horas sociales", "valor": sin_completar, "ruta": "/horas"})
    return alertas


def ultimo_grado(colegio_id):
    mayor = -1
    for grupo in base_datos.grupos_del_colegio(colegio_id, g.colegio["anio"]):
        if grupo["orden_grado"] > mayor:
            mayor = grupo["orden_grado"]
    return mayor


@app.route("/indicadores")
def indicadores():
    if not tiene_alguno(g.yo, QUIENES):
        return redirect("/inicio")

    colegio_id = g.colegio["id"]
    periodos = periodos_actuales()
    grupos = base_datos.grupos_del_colegio(colegio_id, g.colegio["anio"])

    distribucion = []
    todos_los_promedios = []
    total_estudiantes = 0
    total_bajo = 0
    for grupo in grupos:
        conteo = {"Superior": 0, "Alto": 0, "Básico": 0, "Bajo": 0, "Pendiente": 0}
        filas = tabla_grupo(grupo["id"], 0)
        for fila in filas:
            nivel = desempeno(fila["promedio"])
            conteo[nivel] = conteo[nivel] + 1
            todos_los_promedios.append(fila["promedio"])
        total_estudiantes = total_estudiantes + len(filas)
        total_bajo = total_bajo + conteo["Bajo"]
        segmentos = []
        for nivel in NIVELES:
            if conteo[nivel] > 0:
                segmentos.append({"nivel": nivel, "cantidad": conteo[nivel],
                                  "porcentaje": round(conteo[nivel] * 100 / len(filas))})
        distribucion.append({"grupo": grupo, "total": len(filas), "conteo": conteo, "segmentos": segmentos})

    materias = []
    for materia in base_datos.materias_del_colegio(colegio_id):
        finales = []
        en_bajo = 0
        for grupo in grupos:
            for estudiante in base_datos.estudiantes_del_grupo(grupo["id"]):
                notas = base_datos.notas_del_estudiante(estudiante["id"], g.colegio["anio"], len(periodos))
                if materia["id"] in notas:
                    final = nota_final(notas[materia["id"]], periodos)
                    finales.append(final)
                    if desempeno(final) == "Bajo":
                        en_bajo = en_bajo + 1
        valor = promedio(finales)
        if valor is not None:
            materias.append({"nombre": materia["nombre"], "promedio": valor, "en_bajo": en_bajo,
                             "ancho": round(valor * 100 / g.colegio["nota_maxima"], 1)})
    materias = ordenar_de_mayor_a_menor(materias, "promedio")

    evolucion = []
    for periodo in periodos:
        valores = []
        for grupo in grupos:
            for fila in tabla_grupo(grupo["id"], periodo["numero"]):
                valores.append(fila["promedio"])
        valor = promedio(valores)
        alto = 0
        if valor is not None:
            alto = round(valor * 100 / g.colegio["nota_maxima"], 1)
        evolucion.append({"periodo": periodo, "promedio": valor, "alto": alto})

    marcas = []
    paso = 0
    while paso <= g.colegio["nota_maxima"]:
        marcas.append({"valor": paso, "posicion": round(paso * 100 / g.colegio["nota_maxima"], 1)})
        paso = paso + 1

    porcentaje_bajo = None
    if total_estudiantes > 0:
        porcentaje_bajo = round(total_bajo * 100 / total_estudiantes)

    return render_template("tablero.html", activo="indicadores", distribucion=distribucion, materias=materias,
                           evolucion=evolucion, marcas=marcas, niveles=NIVELES, total_estudiantes=total_estudiantes,
                           promedio_colegio=promedio(todos_los_promedios), porcentaje_bajo=porcentaje_bajo,
                           total_bajo=total_bajo, alertas=alertas_del_colegio(colegio_id),
                           linea_aprobacion=round(g.colegio["limite_basico"] * 100 / g.colegio["nota_maxima"], 1),
                           docentes=len(base_datos.usuarios_con_rol(colegio_id, "docente")))
