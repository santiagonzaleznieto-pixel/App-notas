from datetime import date
from flask import g, render_template, request, redirect
from nucleo import (app, agregar_menu, tiene_rol, tiene_alguno, promedio, nota_final, grupo_del_estudiante,
                    registrar, hoy, ahora)
import base_datos

TABLAS_FAMILIAS = """
CREATE TABLE IF NOT EXISTS compromisos_familia (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    anio INTEGER NOT NULL,
    acudiente_id INTEGER NOT NULL REFERENCES usuarios(id),
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    aceptado_en TEXT NOT NULL,
    UNIQUE (anio, acudiente_id, estudiante_id)
);

CREATE TABLE IF NOT EXISTS encuentros_familias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    anio INTEGER NOT NULL,
    titulo TEXT NOT NULL,
    tema TEXT NOT NULL,
    fecha TEXT NOT NULL,
    hora TEXT NOT NULL,
    lugar TEXT NOT NULL,
    descripcion TEXT NOT NULL DEFAULT '',
    creado_por INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS asistencia_encuentros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    encuentro_id INTEGER NOT NULL REFERENCES encuentros_familias(id),
    acudiente_id INTEGER NOT NULL REFERENCES usuarios(id),
    asistio INTEGER NOT NULL DEFAULT 0,
    UNIQUE (encuentro_id, acudiente_id)
);

CREATE TABLE IF NOT EXISTS caracterizacion_familias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    anio INTEGER NOT NULL,
    acudiente_id INTEGER NOT NULL REFERENCES usuarios(id),
    personas_hogar INTEGER NOT NULL,
    tiene_internet INTEGER NOT NULL DEFAULT 0,
    medio_preferido TEXT NOT NULL DEFAULT 'whatsapp',
    necesidades TEXT NOT NULL DEFAULT '',
    actualizado_en TEXT NOT NULL,
    UNIQUE (anio, acudiente_id)
);
"""

base_datos.crear_tablas(TABLAS_FAMILIAS)

agregar_menu("familia", "Mi familia", "/familia", ["acudiente"],
             "Notas, asistencia, observador y horas sociales de tus hijos.")
agregar_menu("escuela_familias", "Escuela para familias", "/escuela-familias",
             ["coordinador", "rector", "orientador", "administrador"],
             "Encuentros con las familias, asistencia y caracterización.")

GESTIONAN_ESCUELA = ["coordinador", "rector", "orientador", "administrador"]

MEDIOS = {"whatsapp": "WhatsApp", "correo": "Correo electrónico", "llamada": "Llamada"}

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


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


def hora_valida(texto):
    if len(texto) != 5 or texto[2] != ":":
        return False
    for posicion in [0, 1, 3, 4]:
        if texto[posicion] not in "0123456789":
            return False
    return int(texto[0:2]) <= 23 and int(texto[3:5]) <= 59


def fecha_larga(texto):
    if not fecha_valida(texto):
        return texto
    anio = int(texto[0:4])
    mes = int(texto[5:7])
    dia = int(texto[8:10])
    dia_semana = DIAS[date(anio, mes, dia).weekday()]
    return dia_semana + " " + str(dia) + " de " + MESES[mes - 1] + " de " + str(anio)


def hora_texto(texto):
    if not hora_valida(texto):
        return texto
    horas = int(texto[0:2])
    sufijo = "a. m."
    if horas >= 12:
        sufijo = "p. m."
    if horas > 12:
        horas = horas - 12
    if horas == 0:
        horas = 12
    return str(horas) + ":" + texto[3:5] + " " + sufijo


def entero(texto):
    limpio = texto.strip()
    if limpio == "" or len(limpio) > 9:
        return None
    for letra in limpio:
        if letra not in "0123456789":
            return None
    return int(limpio)


def porcentaje(parte, total):
    if total == 0:
        return 0
    return round(parte * 100 / total)


def hijos_de(acudiente_id):
    hijos = []
    for hijo in base_datos.estudiantes_a_cargo(acudiente_id):
        if hijo["colegio_id"] == g.colegio["id"]:
            hijos.append(hijo)
    return hijos


def nombres_hijos(acudiente_id):
    nombres = []
    for hijo in hijos_de(acudiente_id):
        grupo = grupo_del_estudiante(hijo["id"])
        if grupo is None:
            nombres.append(hijo["nombre"])
        else:
            nombres.append(hijo["nombre"] + " (" + grupo["nombre"] + ")")
    return nombres


def compromisos_de(acudiente_id):
    return base_datos.consultar(
        "SELECT * FROM compromisos_familia WHERE colegio_id = ? AND anio = ? AND acudiente_id = ? ORDER BY aceptado_en",
        [g.colegio["id"], g.colegio["anio"], acudiente_id],
    )


def compromiso_aceptado(acudiente_id):
    hijos = hijos_de(acudiente_id)
    if len(hijos) == 0:
        return False
    firmados = []
    for compromiso in compromisos_de(acudiente_id):
        firmados.append(compromiso["estudiante_id"])
    for hijo in hijos:
        if hijo["id"] not in firmados:
            return False
    return True


def acudientes_del_colegio():
    return base_datos.usuarios_con_rol(g.colegio["id"], "acudiente")


def encuentros_del_anio():
    return base_datos.consultar(
        "SELECT * FROM encuentros_familias WHERE colegio_id = ? AND anio = ? ORDER BY fecha, hora",
        [g.colegio["id"], g.colegio["anio"]],
    )


def buscar_encuentro(encuentro_id):
    encuentro = base_datos.consultar_uno("SELECT * FROM encuentros_familias WHERE id = ?", [encuentro_id])
    if encuentro is None or encuentro["colegio_id"] != g.colegio["id"]:
        return None
    return encuentro


def marcas_del_encuentro(encuentro_id):
    marcas = {}
    filas = base_datos.consultar(
        "SELECT acudiente_id, asistio FROM asistencia_encuentros WHERE encuentro_id = ? AND colegio_id = ?",
        [encuentro_id, g.colegio["id"]],
    )
    for fila in filas:
        marcas[fila["acudiente_id"]] = fila["asistio"]
    return marcas


def contar_asistentes(marcas, acudientes):
    asistentes = 0
    for acudiente in acudientes:
        if acudiente["id"] in marcas and marcas[acudiente["id"]] == 1:
            asistentes = asistentes + 1
    return asistentes


def caracterizacion_de(acudiente_id):
    return base_datos.consultar_uno(
        "SELECT * FROM caracterizacion_familias WHERE colegio_id = ? AND anio = ? AND acudiente_id = ?",
        [g.colegio["id"], g.colegio["anio"], acudiente_id],
    )


def promedio_general(estudiante_id, grupo_id, periodos):
    todas = base_datos.notas_del_estudiante(estudiante_id, g.colegio["anio"], len(periodos))
    finales = []
    for asignacion in base_datos.asignaciones_del_grupo(grupo_id):
        if asignacion["materia_id"] in todas:
            finales.append(nota_final(todas[asignacion["materia_id"]], periodos))
        else:
            finales.append(None)
    return promedio(finales)


def guardar_caracterizacion(personas, internet, medio, necesidades):
    anterior = caracterizacion_de(g.yo["id"])
    if anterior is None:
        base_datos.ejecutar(
            "INSERT INTO caracterizacion_familias (colegio_id, anio, acudiente_id, personas_hogar, tiene_internet, "
            "medio_preferido, necesidades, actualizado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [g.colegio["id"], g.colegio["anio"], g.yo["id"], personas, internet, medio, necesidades, ahora()],
        )
    else:
        base_datos.ejecutar(
            "UPDATE caracterizacion_familias SET personas_hogar = ?, tiene_internet = ?, medio_preferido = ?, "
            "necesidades = ?, actualizado_en = ? WHERE id = ?",
            [personas, internet, medio, necesidades, ahora(), anterior["id"]],
        )


@app.route("/familia", methods=["GET", "POST"])
def familia():
    if not tiene_rol(g.yo, "acudiente"):
        return redirect("/inicio")

    hijos = hijos_de(g.yo["id"])
    errores = []
    mensaje = ""
    formulario = None
    if request.method == "POST":
        accion = request.form.get("accion", "")
        if accion == "compromiso":
            if len(hijos) == 0:
                errores.append("No tienes estudiantes a cargo para firmar el compromiso.")
            else:
                for hijo in hijos:
                    base_datos.ejecutar(
                        "INSERT OR IGNORE INTO compromisos_familia (colegio_id, anio, acudiente_id, estudiante_id, aceptado_en) "
                        "VALUES (?, ?, ?, ?, ?)",
                        [g.colegio["id"], g.colegio["anio"], g.yo["id"], hijo["id"], ahora()],
                    )
                registrar("Aceptó el compromiso de la escuela para familias", "Año " + str(g.colegio["anio"]))
                mensaje = "Gracias. Tu compromiso con la escuela para familias quedó registrado."
        elif accion == "caracterizacion":
            formulario = {
                "personas_hogar": request.form.get("personas_hogar", "").strip(),
                "tiene_internet": request.form.get("tiene_internet", ""),
                "medio_preferido": request.form.get("medio_preferido", ""),
                "necesidades": request.form.get("necesidades", "").strip(),
            }
            personas = entero(formulario["personas_hogar"])
            if personas is None or personas < 1 or personas > 30:
                errores.append("Escribe cuántas personas viven en tu hogar, de 1 a 30.")
            if formulario["tiene_internet"] not in ["si", "no"]:
                errores.append("Cuéntanos si tienes internet en casa.")
            if formulario["medio_preferido"] not in MEDIOS:
                errores.append("Elige cómo prefieres que el colegio se comunique contigo.")
            if len(formulario["necesidades"]) > 1000:
                errores.append("Las necesidades deben tener máximo 1000 caracteres.")
            if len(errores) == 0:
                internet = 0
                if formulario["tiene_internet"] == "si":
                    internet = 1
                guardar_caracterizacion(personas, internet, formulario["medio_preferido"], formulario["necesidades"])
                registrar("Actualizó la caracterización de su familia", "Año " + str(g.colegio["anio"]))
                mensaje = "Los datos de tu familia quedaron guardados. ¡Gracias!"
                formulario = None

    ficha = caracterizacion_de(g.yo["id"])
    if formulario is None:
        formulario = {"personas_hogar": "", "tiene_internet": "", "medio_preferido": "whatsapp", "necesidades": ""}
        if ficha is not None:
            formulario["personas_hogar"] = str(ficha["personas_hogar"])
            formulario["tiene_internet"] = "no"
            if ficha["tiene_internet"] == 1:
                formulario["tiene_internet"] = "si"
            formulario["medio_preferido"] = ficha["medio_preferido"]
            formulario["necesidades"] = ficha["necesidades"]

    periodos = base_datos.periodos_del_anio(g.colegio["id"], g.colegio["anio"])
    tarjetas = []
    nombres = []
    for hijo in hijos:
        grupo = grupo_del_estudiante(hijo["id"])
        general = None
        if grupo is not None:
            general = promedio_general(hijo["id"], grupo["id"], periodos)
        tarjetas.append({"hijo": hijo, "grupo": grupo, "general": general})
        nombres.append(hijo["nombre"])

    aceptado = compromiso_aceptado(g.yo["id"])
    aceptado_en = ""
    if aceptado:
        firmados = compromisos_de(g.yo["id"])
        aceptado_en = firmados[len(firmados) - 1]["aceptado_en"]

    marcas = {}
    filas = base_datos.consultar(
        "SELECT encuentro_id, asistio FROM asistencia_encuentros WHERE acudiente_id = ? AND colegio_id = ?",
        [g.yo["id"], g.colegio["id"]],
    )
    for fila in filas:
        marcas[fila["encuentro_id"]] = fila["asistio"]
    proximos = []
    pasados = []
    for encuentro in encuentros_del_anio():
        if encuentro["fecha"] >= hoy():
            proximos.append(encuentro)
        else:
            encuentro["asistio"] = None
            if encuentro["id"] in marcas:
                encuentro["asistio"] = marcas[encuentro["id"]]
            pasados.insert(0, encuentro)

    return render_template("familias_mi_familia.html", activo="familia", tarjetas=tarjetas, nombres=nombres,
                           aceptado=aceptado, aceptado_en=aceptado_en, proximos=proximos, pasados=pasados,
                           formulario=formulario, ficha=ficha, medios=MEDIOS, errores=errores, mensaje=mensaje,
                           fecha_larga=fecha_larga, hora_texto=hora_texto, meses_cortos=MESES_CORTOS)


@app.route("/escuela-familias", methods=["GET", "POST"])
def escuela_familias():
    if not tiene_alguno(g.yo, GESTIONAN_ESCUELA):
        return redirect("/inicio")

    anio = g.colegio["anio"]
    errores = []
    mensaje = ""
    formulario = {"titulo": "", "tema": "", "fecha": "", "hora": "", "lugar": "", "descripcion": ""}
    if request.method == "POST":
        for campo in formulario:
            formulario[campo] = request.form.get(campo, "").strip()
        if formulario["titulo"] == "" or len(formulario["titulo"]) > 150:
            errores.append("Escribe el título del encuentro (máximo 150 caracteres).")
        if formulario["tema"] == "" or len(formulario["tema"]) > 150:
            errores.append("Escribe el tema del encuentro (máximo 150 caracteres).")
        if not fecha_valida(formulario["fecha"]):
            errores.append("Escribe la fecha como año-mes-día, por ejemplo " + str(anio) + "-11-28.")
        elif formulario["fecha"][0:4] != str(anio):
            errores.append("La fecha debe estar dentro del año escolar " + str(anio) + ".")
        if not hora_valida(formulario["hora"]):
            errores.append("Escribe la hora en formato de 24 horas, por ejemplo 08:00 o 14:30.")
        if formulario["lugar"] == "" or len(formulario["lugar"]) > 150:
            errores.append("Escribe el lugar del encuentro (máximo 150 caracteres).")
        if len(formulario["descripcion"]) > 2000:
            errores.append("La descripción debe tener máximo 2000 caracteres.")
        if len(errores) == 0:
            base_datos.ejecutar(
                "INSERT INTO encuentros_familias (colegio_id, anio, titulo, tema, fecha, hora, lugar, descripcion, creado_por) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [g.colegio["id"], anio, formulario["titulo"], formulario["tema"], formulario["fecha"], formulario["hora"],
                 formulario["lugar"], formulario["descripcion"], g.yo["id"]],
            )
            registrar("Creó un encuentro de la escuela para familias", formulario["titulo"] + " · " + formulario["fecha"])
            mensaje = "Encuentro creado: " + formulario["titulo"] + "."
            for campo in formulario:
                formulario[campo] = ""

    acudientes = acudientes_del_colegio()
    total = len(acudientes)
    con_compromiso = 0
    caracterizadas = 0
    for acudiente in acudientes:
        if compromiso_aceptado(acudiente["id"]):
            con_compromiso = con_compromiso + 1
        if caracterizacion_de(acudiente["id"]) is not None:
            caracterizadas = caracterizadas + 1

    filas = []
    suma = 0
    tomados = 0
    for encuentro in encuentros_del_anio():
        marcas = marcas_del_encuentro(encuentro["id"])
        asistentes = contar_asistentes(marcas, acudientes)
        tomada = len(marcas) > 0
        if tomada and total > 0:
            suma = suma + asistentes * 100 / total
            tomados = tomados + 1
        filas.append({"encuentro": encuentro, "futuro": encuentro["fecha"] > hoy(), "tomada": tomada,
                      "asistentes": asistentes, "porcentaje": porcentaje(asistentes, total)})
    asistencia_promedio = None
    if tomados > 0:
        asistencia_promedio = round(suma / tomados)

    return render_template("familias_escuela.html", activo="escuela_familias", filas=filas, total=total,
                           con_compromiso=con_compromiso, caracterizadas=caracterizadas,
                           asistencia_promedio=asistencia_promedio, tomados=tomados, porcentaje=porcentaje,
                           formulario=formulario, errores=errores, mensaje=mensaje,
                           fecha_larga=fecha_larga, hora_texto=hora_texto, meses_cortos=MESES_CORTOS)


@app.route("/escuela-familias/<int:encuentro_id>", methods=["GET", "POST"])
def encuentro_familias(encuentro_id):
    if not tiene_alguno(g.yo, GESTIONAN_ESCUELA):
        return redirect("/inicio")
    encuentro = buscar_encuentro(encuentro_id)
    if encuentro is None:
        return redirect("/inicio")

    futuro = encuentro["fecha"] > hoy()
    acudientes = acudientes_del_colegio()
    errores = []
    mensaje = ""
    if request.method == "POST":
        if futuro:
            errores.append("Este encuentro todavía no se ha realizado. La asistencia se toma el día del encuentro.")
        else:
            asistentes = 0
            for acudiente in acudientes:
                asistio = 0
                if "asistio-" + str(acudiente["id"]) in request.form:
                    asistio = 1
                    asistentes = asistentes + 1
                base_datos.ejecutar(
                    "INSERT OR REPLACE INTO asistencia_encuentros (colegio_id, encuentro_id, acudiente_id, asistio) "
                    "VALUES (?, ?, ?, ?)",
                    [g.colegio["id"], encuentro["id"], acudiente["id"], asistio],
                )
            registrar("Tomó asistencia de la escuela para familias",
                      encuentro["titulo"] + ": " + str(asistentes) + " de " + str(len(acudientes)))
            mensaje = "Asistencia guardada: " + str(asistentes) + " de " + str(len(acudientes)) + " familias asistieron."

    marcas = marcas_del_encuentro(encuentro["id"])
    filas = []
    for acudiente in acudientes:
        asistio = None
        if acudiente["id"] in marcas:
            asistio = marcas[acudiente["id"]]
        filas.append({"acudiente": acudiente, "hijos": nombres_hijos(acudiente["id"]), "asistio": asistio,
                      "compromiso": compromiso_aceptado(acudiente["id"])})
    asistentes = contar_asistentes(marcas, acudientes)

    return render_template("familias_encuentro.html", activo="escuela_familias", encuentro=encuentro, filas=filas,
                           futuro=futuro, tomada=len(marcas) > 0, asistentes=asistentes, total=len(acudientes),
                           porcentaje=porcentaje(asistentes, len(acudientes)), errores=errores, mensaje=mensaje,
                           fecha_larga=fecha_larga, hora_texto=hora_texto)


@app.route("/escuela-familias/caracterizacion")
def caracterizacion_familias():
    if not tiene_alguno(g.yo, GESTIONAN_ESCUELA):
        return redirect("/inicio")

    internet = request.args.get("internet", "")
    medio = request.args.get("medio", "")
    if internet not in ["si", "no"]:
        internet = ""
    if medio not in MEDIOS:
        medio = ""

    fichas = {}
    filas_fichas = base_datos.consultar(
        "SELECT * FROM caracterizacion_familias WHERE colegio_id = ? AND anio = ?",
        [g.colegio["id"], g.colegio["anio"]],
    )
    for fila in filas_fichas:
        fichas[fila["acudiente_id"]] = fila

    acudientes = acudientes_del_colegio()
    conteo = {"caracterizadas": 0, "sin_internet": 0, "whatsapp": 0, "correo": 0, "llamada": 0}
    filas = []
    for acudiente in acudientes:
        ficha = None
        if acudiente["id"] in fichas:
            ficha = fichas[acudiente["id"]]
            conteo["caracterizadas"] = conteo["caracterizadas"] + 1
            if ficha["tiene_internet"] == 0:
                conteo["sin_internet"] = conteo["sin_internet"] + 1
            if ficha["medio_preferido"] in conteo:
                conteo[ficha["medio_preferido"]] = conteo[ficha["medio_preferido"]] + 1
        incluir = True
        if internet != "" or medio != "":
            if ficha is None:
                incluir = False
            elif internet == "si" and ficha["tiene_internet"] != 1:
                incluir = False
            elif internet == "no" and ficha["tiene_internet"] != 0:
                incluir = False
            elif medio != "" and ficha["medio_preferido"] != medio:
                incluir = False
        if incluir:
            filas.append({"acudiente": acudiente, "hijos": nombres_hijos(acudiente["id"]), "ficha": ficha})

    return render_template("familias_caracterizacion.html", activo="escuela_familias", filas=filas, conteo=conteo,
                           total=len(acudientes), internet=internet, medio=medio, medios=MEDIOS)


def sembrar_familias():
    colegio = base_datos.buscar_colegio(1)
    if colegio is None or not base_datos.tabla_vacia("encuentros_familias"):
        return
    gloria = base_datos.buscar_usuario("gloria.cardenas")
    jorge = base_datos.buscar_usuario("jorge.restrepo")
    olga = base_datos.buscar_usuario("olga.gomez")
    melany = base_datos.buscar_usuario("melany.osorio")
    orientadora = base_datos.buscar_usuario("orientadora")
    if gloria is None or jorge is None or olga is None or melany is None or orientadora is None:
        return
    anio = colegio["anio"]

    base_datos.ejecutar(
        "INSERT INTO compromisos_familia (colegio_id, anio, acudiente_id, estudiante_id, aceptado_en) VALUES (?, ?, ?, ?, ?)",
        [1, anio, gloria["id"], melany["id"], "2026-01-20 10:12"],
    )

    pasado = base_datos.ejecutar(
        "INSERT INTO encuentros_familias (colegio_id, anio, titulo, tema, fecha, hora, lugar, descripcion, creado_por) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [1, anio, "Cómo acompañar las tareas en casa", "Acompañamiento académico en el hogar", "2026-08-22", "08:00",
         "Auditorio de la sede principal",
         "Taller práctico para organizar un horario de estudio en casa, crear un rincón de tareas sin distracciones "
         "y acompañar a los hijos sin hacerles el trabajo.\nDirige: Orientación escolar.",
         orientadora["id"]],
    )
    base_datos.ejecutar(
        "INSERT INTO encuentros_familias (colegio_id, anio, titulo, tema, fecha, hora, lugar, descripcion, creado_por) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [1, anio, "Prevención del consumo de sustancias psicoactivas", "Prevención y cuidado de la salud mental",
         "2026-11-28", "08:00", "Auditorio de la sede principal",
         "Hablaremos de las señales de alerta, de cómo conversar del tema en familia y de a quién acudir en el "
         "municipio si necesitan apoyo.\nDirige: Orientación escolar.",
         orientadora["id"]],
    )

    asistencias = [[gloria["id"], 1], [jorge["id"], 1], [olga["id"], 0]]
    for asistencia in asistencias:
        base_datos.ejecutar(
            "INSERT INTO asistencia_encuentros (colegio_id, encuentro_id, acudiente_id, asistio) VALUES (?, ?, ?, ?)",
            [1, pasado, asistencia[0], asistencia[1]],
        )

    base_datos.ejecutar(
        "INSERT INTO caracterizacion_familias (colegio_id, anio, acudiente_id, personas_hogar, tiene_internet, "
        "medio_preferido, necesidades, actualizado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [1, anio, gloria["id"], 4, 1, "whatsapp",
         "En temporada de cosecha de café trabajo los sábados en la mañana; me sirven más los encuentros en la tarde.",
         "2026-02-03 18:40"],
    )


sembrar_familias()
