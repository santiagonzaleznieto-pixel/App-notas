from flask import Flask, render_template, request, redirect, session
from datos import COLEGIO, GRADO, ANIO, PERIODOS, USUARIOS, MATERIAS, NOTAS

app = Flask(__name__)
app.secret_key = "instituto-pijao-decimo"

ESTUDIANTES = []
for persona in USUARIOS:
    if persona["rol"] == "estudiante":
        ESTUDIANTES.append(persona)


def buscar_usuario(usuario):
    i = 0
    while i < len(USUARIOS):
        if USUARIOS[i]["usuario"] == usuario:
            return USUARIOS[i]
        i = i + 1
    return None


def usuario_actual():
    return buscar_usuario(session.get("usuario", ""))


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


def nota_materia(usuario, id_materia, periodo):
    lista = NOTAS[usuario][id_materia]
    if periodo == 0:
        return promedio(lista)
    return lista[periodo - 1]


def tabla_grupo(periodo):
    filas = []
    for estudiante in ESTUDIANTES:
        notas = []
        for materia in MATERIAS:
            notas.append(nota_materia(estudiante["usuario"], materia["id"], periodo))
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
app.jinja_env.globals["colegio"] = COLEGIO
app.jinja_env.globals["grado"] = GRADO
app.jinja_env.globals["anio"] = ANIO


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
        elif persona["clave"] != clave:
            error = "La contraseña no es correcta."
        else:
            session["usuario"] = persona["usuario"]
            return redirect("/inicio")

    accesos = []
    roles_vistos = []
    for persona in USUARIOS:
        if persona["rol"] not in roles_vistos:
            accesos.append(persona)
            roles_vistos.append(persona["rol"])

    return render_template("login.html", error=error, accesos=accesos)


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

    mis_materias = []
    for materia in MATERIAS:
        if materia["profesor"] == yo["usuario"]:
            finales = []
            en_bajo = 0
            calificados = 0
            for estudiante in ESTUDIANTES:
                lista = NOTAS[estudiante["usuario"]][materia["id"]]
                final = promedio(lista)
                finales.append(final)
                if final is not None and final < 3.0:
                    en_bajo = en_bajo + 1
                if lista[PERIODOS - 1] is not None:
                    calificados = calificados + 1
            mis_materias.append({
                "materia": materia,
                "promedio": promedio(finales),
                "en_bajo": en_bajo,
                "calificados": calificados,
            })

    return render_template("materias.html", yo=yo, activo="materias", mis_materias=mis_materias,
                           total=len(ESTUDIANTES), periodos=PERIODOS)


@app.route("/calificar/<id_materia>", methods=["GET", "POST"])
def calificar(id_materia):
    yo = usuario_actual()
    if yo is None:
        return redirect("/")

    materia = None
    for m in MATERIAS:
        if m["id"] == id_materia:
            materia = m
    if materia is None or materia["profesor"] != yo["usuario"]:
        return redirect("/inicio")

    mensaje = ""
    errores = []
    if request.method == "POST":
        for estudiante in ESTUDIANTES:
            for p in range(PERIODOS):
                texto = request.form.get(estudiante["usuario"] + "-" + str(p + 1), "").strip()
                if texto == "":
                    NOTAS[estudiante["usuario"]][id_materia][p] = None
                else:
                    valor = round(float(texto.replace(",", ".")), 1)
                    if valor >= 1.0 and valor <= 5.0:
                        NOTAS[estudiante["usuario"]][id_materia][p] = valor
                    else:
                        errores.append(estudiante["nombre"] + ", período " + str(p + 1) + ": la nota debe estar entre 1.0 y 5.0")
        if len(errores) == 0:
            mensaje = "Notas guardadas correctamente."

    filas = []
    for estudiante in ESTUDIANTES:
        lista = NOTAS[estudiante["usuario"]][id_materia]
        filas.append({"estudiante": estudiante, "notas": lista, "final": promedio(lista)})

    return render_template("calificar.html", yo=yo, activo="materias", materia=materia, filas=filas,
                           mensaje=mensaje, errores=errores, periodos=PERIODOS)


@app.route("/consolidado")
def consolidado():
    yo = usuario_actual()
    if yo is None or yo["rol"] not in ["director", "coordinadora", "rectora"]:
        return redirect("/")

    periodo = request.args.get("periodo", "0")
    if periodo not in ["0", "1", "2", "3", "4"]:
        periodo = "0"
    periodo = int(periodo)

    filas = tabla_grupo(periodo)

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
        for i in range(len(MATERIAS)):
            if fila["notas"][i] is not None and fila["notas"][i] < 3.0:
                perdidas.append(MATERIAS[i]["nombre"])
        if len(perdidas) > 0:
            alertas.append({"estudiante": fila["estudiante"], "materias": perdidas})

    resumen = []
    for i in range(len(MATERIAS)):
        columna = []
        en_bajo = 0
        for fila in filas:
            columna.append(fila["notas"][i])
            if fila["notas"][i] is not None and fila["notas"][i] < 3.0:
                en_bajo = en_bajo + 1
        resumen.append({
            "materia": MATERIAS[i],
            "profesor": buscar_usuario(MATERIAS[i]["profesor"]),
            "promedio": promedio(columna),
            "en_bajo": en_bajo,
        })

    mejor = None
    if len(ordenadas) > 0 and ordenadas[0]["puesto"] == 1:
        mejor = ordenadas[0]

    return render_template("consolidado.html", yo=yo, activo="consolidado", filas=ordenadas, materias=MATERIAS,
                           periodo=periodo, periodos=PERIODOS, promedio_grupo=promedio(promedios),
                           conteo=conteo, alertas=alertas, resumen=resumen, mejor=mejor)


@app.route("/boletin/<usuario>")
def boletin(usuario):
    yo = usuario_actual()
    if yo is None:
        return redirect("/")

    estudiante = buscar_usuario(usuario)
    if estudiante is None or estudiante["rol"] != "estudiante":
        return redirect("/inicio")
    if yo["rol"] == "estudiante" and yo["usuario"] != usuario:
        return redirect("/inicio")
    if yo["rol"] == "profesor":
        return redirect("/inicio")

    filas = []
    for materia in MATERIAS:
        lista = NOTAS[usuario][materia["id"]]
        filas.append({
            "materia": materia,
            "profesor": buscar_usuario(materia["profesor"]),
            "notas": lista,
            "final": promedio(lista),
        })

    puesto = None
    general = None
    for fila in tabla_grupo(0):
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
    for persona in USUARIOS:
        if persona["rol"] == "director":
            director = persona

    activo = "consolidado"
    if yo["rol"] == "estudiante":
        activo = "boletin"

    return render_template("boletin.html", yo=yo, activo=activo, estudiante=estudiante, filas=filas,
                           puesto=puesto, general=general, mensaje=mensaje, director=director,
                           total=len(ESTUDIANTES), periodos=PERIODOS)


@app.route("/salir")
def salir():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
