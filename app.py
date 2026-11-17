import os
from flask import Flask, render_template, request, redirect, session
from werkzeug.security import check_password_hash
from datos import GRADO, CLAVE_PRUEBA
import base_datos

app = Flask(__name__)
app.secret_key = os.environ.get("CLAVE_SECRETA", "solo-para-pruebas-en-mi-computador")

base_datos.preparar_base()
PILOTO = base_datos.buscar_colegio(1)


def buscar_usuario(usuario):
    usuarios = base_datos.todos_los_usuarios()
    i = 0
    while i < len(usuarios):
        if usuarios[i]["usuario"] == usuario:
            return usuarios[i]
        i = i + 1
    return None


def usuario_actual():
    return buscar_usuario(session.get("usuario", ""))


def datos_del_colegio(colegio_id):
    colegio = base_datos.buscar_colegio(colegio_id)
    usuarios = base_datos.usuarios_del_colegio(colegio_id)
    estudiantes = []
    for persona in usuarios:
        if persona["rol"] == "estudiante":
            estudiantes.append(persona)
    return {
        "colegio": colegio,
        "usuarios": usuarios,
        "estudiantes": estudiantes,
        "materias": base_datos.materias_del_colegio(colegio_id),
        "notas": base_datos.notas_del_colegio(colegio_id, colegio["periodos"]),
        "periodos": colegio["periodos"],
    }


def desempeno(nota):
    if nota is None:
        return "Pendiente"
    elif nota >= 4.6:
        return "Superior"
    elif nota >= 4.0:
        return "Alto"
    elif nota >= 3.0:
        return "Básico"
    else:
        return "Bajo"


def promedio(lista):
    suma = 0
    cantidad = 0
    for nota in lista:
        if nota is not None:
            suma = suma + nota
            cantidad = cantidad + 1
    if cantidad == 0:
        return None
    return round(suma / cantidad, 1)


def nota_materia(datos, usuario, id_materia, periodo):
    lista = datos["notas"][usuario][id_materia]
    if periodo == 0:
        return promedio(lista)
    return lista[periodo - 1]


def tabla_grupo(datos, periodo):
    filas = []
    for estudiante in datos["estudiantes"]:
        notas = []
        for materia in datos["materias"]:
            notas.append(nota_materia(datos, estudiante["usuario"], materia["id"], periodo))
        filas.append({"estudiante": estudiante, "notas": notas, "promedio": promedio(notas), "puesto": None})

    for fila in filas:
        if fila["promedio"] is not None:
            puesto = 1
            for otra in filas:
                if otra["promedio"] is not None and otra["promedio"] > fila["promedio"]:
                    puesto = puesto + 1
            fila["puesto"] = puesto
    return filas


app.jinja_env.globals["desempeno"] = desempeno
app.jinja_env.globals["colegio"] = PILOTO["nombre"]
app.jinja_env.globals["grado"] = GRADO
app.jinja_env.globals["anio"] = PILOTO["anio"]


@app.route("/", methods=["GET", "POST"])
def login():
    if usuario_actual() is not None:
        return redirect("/inicio")

    error = ""
    if request.method == "POST":
        usuario = request.form["usuario"].strip().lower()
        clave = request.form["clave"]
        persona = buscar_usuario(usuario)
        if usuario == "" or clave == "":
            error = "Escribe tu usuario y tu contraseña."
        elif persona is None:
            error = "Ese usuario no existe en el grado " + GRADO + "."
        elif not check_password_hash(persona["clave"], clave):
            error = "La contraseña no es correcta."
        else:
            session["usuario"] = persona["usuario"]
            return redirect("/inicio")

    accesos = []
    roles_vistos = []
    for persona in base_datos.usuarios_del_colegio(PILOTO["id"]):
        if persona["rol"] not in roles_vistos:
            accesos.append(persona)
            roles_vistos.append(persona["rol"])

    return render_template("login.html", error=error, accesos=accesos, clave_prueba=CLAVE_PRUEBA)


@app.route("/inicio")
def inicio():
    yo = usuario_actual()
    if yo is None:
        return redirect("/")
    if yo["rol"] == "estudiante":
        return redirect("/boletin/" + yo["usuario"])
    elif yo["rol"] == "profesor" or yo["rol"] == "director":
        return redirect("/materias")
    else:
        return redirect("/consolidado")


@app.route("/materias")
def materias():
    yo = usuario_actual()
    if yo is None or yo["rol"] not in ["profesor", "director"]:
        return redirect("/")

    datos = datos_del_colegio(yo["colegio_id"])
    periodos = datos["periodos"]
    mis_materias = []
    for materia in datos["materias"]:
        if materia["profesor"] == yo["usuario"]:
            finales = []
            en_bajo = 0
            calificados = 0
            for estudiante in datos["estudiantes"]:
                lista = datos["notas"][estudiante["usuario"]][materia["id"]]
                final = promedio(lista)
                finales.append(final)
                if final is not None and final < 3.0:
                    en_bajo = en_bajo + 1
                if lista[periodos - 1] is not None:
                    calificados = calificados + 1
            mis_materias.append({
                "materia": materia,
                "promedio": promedio(finales),
                "en_bajo": en_bajo,
                "calificados": calificados,
            })

    return render_template("materias.html", yo=yo, activo="materias", mis_materias=mis_materias,
                           total=len(datos["estudiantes"]), periodos=periodos)


@app.route("/calificar/<int:id_materia>", methods=["GET", "POST"])
def calificar(id_materia):
    yo = usuario_actual()
    if yo is None:
        return redirect("/")

    datos = datos_del_colegio(yo["colegio_id"])
    materia = None
    for m in datos["materias"]:
        if m["id"] == id_materia:
            materia = m
    if materia is None or materia["profesor"] != yo["usuario"]:
        return redirect("/inicio")

    mensaje = ""
    errores = []
    if request.method == "POST":
        for estudiante in datos["estudiantes"]:
            for p in range(datos["periodos"]):
                texto = request.form.get(estudiante["usuario"] + "-" + str(p + 1), "").strip()
                if texto == "":
                    base_datos.guardar_nota(yo["colegio_id"], estudiante["usuario"], id_materia, p + 1, None)
                else:
                    valor = round(float(texto.replace(",", ".")), 1)
                    if valor >= 1.0 and valor <= 5.0:
                        base_datos.guardar_nota(yo["colegio_id"], estudiante["usuario"], id_materia, p + 1, valor)
                    else:
                        errores.append(estudiante["nombre"] + ", período " + str(p + 1) + ": la nota debe estar entre 1.0 y 5.0")
        if len(errores) == 0:
            mensaje = "Notas guardadas correctamente."
        datos = datos_del_colegio(yo["colegio_id"])

    filas = []
    for estudiante in datos["estudiantes"]:
        lista = datos["notas"][estudiante["usuario"]][id_materia]
        filas.append({"estudiante": estudiante, "notas": lista, "final": promedio(lista)})

    return render_template("calificar.html", yo=yo, activo="materias", materia=materia, filas=filas,
                           mensaje=mensaje, errores=errores, periodos=datos["periodos"])


@app.route("/consolidado")
def consolidado():
    yo = usuario_actual()
    if yo is None or yo["rol"] not in ["director", "coordinadora", "rectora"]:
        return redirect("/")

    datos = datos_del_colegio(yo["colegio_id"])
    materias_colegio = datos["materias"]

    periodo = request.args.get("periodo", "0")
    opciones = ["0"]
    for p in range(1, datos["periodos"] + 1):
        opciones.append(str(p))
    if periodo not in opciones:
        periodo = "0"
    periodo = int(periodo)

    filas = tabla_grupo(datos, periodo)

    ordenadas = []
    for posicion in range(1, len(filas) + 1):
        for fila in filas:
            if fila["puesto"] == posicion:
                ordenadas.append(fila)
    for fila in filas:
        if fila["puesto"] is None:
            ordenadas.append(fila)

    promedios = []
    conteo = {"Superior": 0, "Alto": 0, "Básico": 0, "Bajo": 0, "Pendiente": 0}
    alertas = []
    for fila in filas:
        promedios.append(fila["promedio"])
        conteo[desempeno(fila["promedio"])] = conteo[desempeno(fila["promedio"])] + 1
        perdidas = []
        for i in range(len(materias_colegio)):
            if fila["notas"][i] is not None and fila["notas"][i] < 3.0:
                perdidas.append(materias_colegio[i]["nombre"])
        if len(perdidas) > 0:
            alertas.append({"estudiante": fila["estudiante"], "materias": perdidas})

    resumen = []
    for i in range(len(materias_colegio)):
        columna = []
        en_bajo = 0
        for fila in filas:
            columna.append(fila["notas"][i])
            if fila["notas"][i] is not None and fila["notas"][i] < 3.0:
                en_bajo = en_bajo + 1
        resumen.append({
            "materia": materias_colegio[i],
            "profesor": buscar_usuario(materias_colegio[i]["profesor"]),
            "promedio": promedio(columna),
            "en_bajo": en_bajo,
        })

    mejor = None
    if len(ordenadas) > 0 and ordenadas[0]["puesto"] == 1:
        mejor = ordenadas[0]

    return render_template("consolidado.html", yo=yo, activo="consolidado", filas=ordenadas, materias=materias_colegio,
                           periodo=periodo, periodos=datos["periodos"], promedio_grupo=promedio(promedios),
                           conteo=conteo, alertas=alertas, resumen=resumen, mejor=mejor)


@app.route("/boletin/<usuario>")
def boletin(usuario):
    yo = usuario_actual()
    if yo is None:
        return redirect("/")

    estudiante = buscar_usuario(usuario)
    if estudiante is None or estudiante["rol"] != "estudiante" or estudiante["colegio_id"] != yo["colegio_id"]:
        return redirect("/inicio")
    if yo["rol"] == "estudiante" and yo["usuario"] != usuario:
        return redirect("/inicio")
    if yo["rol"] == "profesor":
        return redirect("/inicio")

    datos = datos_del_colegio(yo["colegio_id"])
    filas = []
    for materia in datos["materias"]:
        lista = datos["notas"][usuario][materia["id"]]
        filas.append({
            "materia": materia,
            "profesor": buscar_usuario(materia["profesor"]),
            "notas": lista,
            "final": promedio(lista),
        })

    puesto = None
    general = None
    for fila in tabla_grupo(datos, 0):
        if fila["estudiante"]["usuario"] == usuario:
            puesto = fila["puesto"]
            general = fila["promedio"]

    if general is None:
        mensaje = "Aún no hay notas registradas."
    elif general >= 4.6:
        mensaje = "¡Excelente trabajo! Sigue así, eres ejemplo para el grupo."
    elif general >= 4.0:
        mensaje = "Muy buen desempeño. Vas por excelente camino."
    elif general >= 3.0:
        mensaje = "Vas aprobando. Con un poco más de esfuerzo puedes llegar a Alto."
    else:
        mensaje = "Necesitas reforzar. Habla con tus profesores y con tu director de grupo."

    director = None
    for persona in datos["usuarios"]:
        if persona["rol"] == "director":
            director = persona

    activo = "consolidado"
    if yo["rol"] == "estudiante":
        activo = "boletin"

    return render_template("boletin.html", yo=yo, activo=activo, estudiante=estudiante, filas=filas,
                           puesto=puesto, general=general, mensaje=mensaje, director=director,
                           total=len(datos["estudiantes"]), periodos=datos["periodos"])


@app.route("/salir")
def salir():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
