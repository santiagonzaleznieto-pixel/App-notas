import secrets
from flask import g, render_template, request, redirect
from nucleo import (app, agregar_menu, tiene_rol, tiene_alguno, estudiante_del_colegio, registrar, ahora,
                    DIRECTIVOS, CON_DATOS_DE_EJEMPLO)
import base_datos

TABLAS_GOBIERNO = """
CREATE TABLE IF NOT EXISTS elecciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    anio INTEGER NOT NULL,
    cargo TEXT NOT NULL,
    titulo TEXT NOT NULL,
    grupo_id INTEGER REFERENCES grupos(id),
    apertura TEXT NOT NULL,
    cierre TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'preparacion',
    creada_por INTEGER REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS candidatos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    eleccion_id INTEGER NOT NULL REFERENCES elecciones(id),
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    numero INTEGER NOT NULL,
    propuesta TEXT NOT NULL,
    UNIQUE (eleccion_id, estudiante_id),
    UNIQUE (eleccion_id, numero)
);

CREATE TABLE IF NOT EXISTS votantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    eleccion_id INTEGER NOT NULL REFERENCES elecciones(id),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    votado_en TEXT NOT NULL,
    UNIQUE (eleccion_id, usuario_id)
);

CREATE TABLE IF NOT EXISTS votos (
    id INTEGER PRIMARY KEY,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    eleccion_id INTEGER NOT NULL REFERENCES elecciones(id),
    candidato_id INTEGER REFERENCES candidatos(id)
);
"""

base_datos.crear_tablas(TABLAS_GOBIERNO)

agregar_menu("elecciones", "Elecciones", "/elecciones", ["estudiante", "administrador", "rector", "coordinador", "orientador"],
             "Elección de personero, contralor y representantes con voto secreto.")

CARGOS = [
    {"clave": "personero", "nombre": "Personero estudiantil"},
    {"clave": "contralor", "nombre": "Contralor estudiantil"},
    {"clave": "representante", "nombre": "Representante de grupo"},
]

ESTADOS = {
    "preparacion": {"texto": "En preparación", "clase": "neutro"},
    "abierta": {"texto": "Votación abierta", "clase": "bien"},
    "cerrada": {"texto": "Cerrada", "clase": "atencion"},
}

ORGANIZAN = DIRECTIVOS + ["orientador"]


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


def fecha_hora_valida(texto):
    if len(texto) != 16 or texto[10] != " " or texto[13] != ":":
        return False
    if not fecha_valida(texto[0:10]):
        return False
    for posicion in [11, 12, 14, 15]:
        if texto[posicion] not in "0123456789":
            return False
    if int(texto[11:13]) > 23 or int(texto[14:16]) > 59:
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


def porcentaje(parte, total):
    if total == 0:
        return 0
    return round(parte * 100 / total)


def contar(sql, valores):
    return base_datos.consultar_uno(sql, valores)["cantidad"]


def buscar_eleccion(eleccion_id):
    return base_datos.consultar_uno(
        "SELECT elecciones.*, grupos.nombre AS grupo FROM elecciones LEFT JOIN grupos ON grupos.id = elecciones.grupo_id "
        "WHERE elecciones.id = ? AND elecciones.colegio_id = ?",
        [eleccion_id, g.colegio["id"]],
    )


def elecciones_del_colegio():
    return base_datos.consultar(
        "SELECT elecciones.*, grupos.nombre AS grupo FROM elecciones LEFT JOIN grupos ON grupos.id = elecciones.grupo_id "
        "WHERE elecciones.colegio_id = ? ORDER BY elecciones.anio DESC, elecciones.id DESC",
        [g.colegio["id"]],
    )


def matricula_en(eleccion, estudiante_id):
    matricula = base_datos.matricula_activa(estudiante_id, eleccion["anio"])
    if matricula is None or matricula["colegio_id"] != eleccion["colegio_id"]:
        return None
    return matricula


def grado_del_grupo(grupo_id):
    return base_datos.consultar_uno(
        "SELECT grados.orden AS orden, grados.nombre AS nombre FROM grupos JOIN grados ON grados.id = grupos.grado_id "
        "WHERE grupos.id = ?",
        [grupo_id],
    )


def grado_mayor(colegio_id, anio):
    mayor = None
    for grupo in base_datos.grupos_del_colegio(colegio_id, anio):
        if mayor is None or grupo["orden_grado"] > mayor["orden"]:
            mayor = {"orden": grupo["orden_grado"], "nombre": grupo["grado"]}
    return mayor


def puede_postularse(eleccion, estudiante_id):
    matricula = matricula_en(eleccion, estudiante_id)
    if matricula is None:
        return False
    if eleccion["cargo"] == "representante":
        return matricula["grupo_id"] == eleccion["grupo_id"]
    mayor = grado_mayor(eleccion["colegio_id"], eleccion["anio"])
    grado = grado_del_grupo(matricula["grupo_id"])
    return mayor is not None and grado is not None and grado["orden"] == mayor["orden"]


def puede_votar(yo, eleccion):
    if not tiene_rol(yo, "estudiante") or eleccion["colegio_id"] != yo["colegio_id"]:
        return False
    matricula = matricula_en(eleccion, yo["id"])
    if matricula is None:
        return False
    if eleccion["cargo"] == "representante":
        return matricula["grupo_id"] == eleccion["grupo_id"]
    return True


def ya_voto(eleccion_id, usuario_id):
    fila = base_datos.consultar_uno(
        "SELECT id FROM votantes WHERE eleccion_id = ? AND usuario_id = ?", [eleccion_id, usuario_id]
    )
    return fila is not None


def candidatos_de(eleccion):
    candidatos = base_datos.consultar(
        "SELECT candidatos.*, usuarios.nombre AS nombre FROM candidatos JOIN usuarios ON usuarios.id = candidatos.estudiante_id "
        "WHERE candidatos.eleccion_id = ? AND candidatos.colegio_id = ? ORDER BY candidatos.numero",
        [eleccion["id"], eleccion["colegio_id"]],
    )
    for candidato in candidatos:
        candidato["grupo"] = ""
        matricula = matricula_en(eleccion, candidato["estudiante_id"])
        if matricula is not None:
            candidato["grupo"] = base_datos.buscar_grupo(matricula["grupo_id"])["nombre"]
    return candidatos


def habilitados(eleccion):
    sql = ("SELECT COUNT(*) AS cantidad FROM matriculas JOIN usuarios ON usuarios.id = matriculas.estudiante_id "
           "JOIN roles_usuario ON roles_usuario.usuario_id = usuarios.id AND roles_usuario.rol = 'estudiante' "
           "WHERE matriculas.colegio_id = ? AND matriculas.anio = ? AND matriculas.estado = 'activa' AND usuarios.activo = 1")
    valores = [eleccion["colegio_id"], eleccion["anio"]]
    if eleccion["cargo"] == "representante":
        sql = sql + " AND matriculas.grupo_id = ?"
        valores.append(eleccion["grupo_id"])
    return contar(sql, valores)


def participacion(eleccion):
    votantes = contar("SELECT COUNT(*) AS cantidad FROM votantes WHERE eleccion_id = ?", [eleccion["id"]])
    total = habilitados(eleccion)
    return {"votantes": votantes, "habilitados": total, "porcentaje": porcentaje(votantes, total)}


def ordenar_por_votos(filas):
    pendientes = []
    for fila in filas:
        pendientes.append(fila)
    ordenadas = []
    while len(pendientes) > 0:
        mejor = pendientes[0]
        for fila in pendientes:
            if fila["votos"] > mejor["votos"]:
                mejor = fila
        ordenadas.append(mejor)
        pendientes.remove(mejor)
    return ordenadas


def resultados(eleccion):
    conteo = {}
    blanco = 0
    total = 0
    for fila in base_datos.consultar(
        "SELECT candidato_id, COUNT(*) AS cantidad FROM votos WHERE eleccion_id = ? AND colegio_id = ? GROUP BY candidato_id",
        [eleccion["id"], eleccion["colegio_id"]],
    ):
        total = total + fila["cantidad"]
        if fila["candidato_id"] is None:
            blanco = fila["cantidad"]
        else:
            conteo[fila["candidato_id"]] = fila["cantidad"]
    filas = []
    for candidato in candidatos_de(eleccion):
        votos = 0
        if candidato["id"] in conteo:
            votos = conteo[candidato["id"]]
        candidato["votos"] = votos
        candidato["porcentaje"] = porcentaje(votos, total)
        filas.append(candidato)
    ordenadas = ordenar_por_votos(filas)
    ganador = None
    empate = False
    if len(ordenadas) > 0 and ordenadas[0]["votos"] > 0:
        if len(ordenadas) > 1 and ordenadas[1]["votos"] == ordenadas[0]["votos"]:
            empate = True
        else:
            ganador = ordenadas[0]
    blanco_gana = ganador is not None and blanco > ganador["votos"]
    return {"filas": ordenadas, "blanco": blanco, "porcentaje_blanco": porcentaje(blanco, total), "total": total,
            "ganador": ganador, "empate": empate, "blanco_gana": blanco_gana}


def id_secreto(conexion):
    nuevo = secrets.randbelow(900000000000) + 100000000000
    while base_datos.en(conexion, "SELECT id FROM votos WHERE id = ?", [nuevo]).fetchone() is not None:
        nuevo = secrets.randbelow(900000000000) + 100000000000
    return nuevo


def emitir_voto(eleccion, usuario_id, candidato_id):
    conexion = base_datos.conectar()
    cursor = base_datos.en(conexion, 
        "INSERT OR IGNORE INTO votantes (colegio_id, eleccion_id, usuario_id, votado_en) VALUES (?, ?, ?, ?)",
        [eleccion["colegio_id"], eleccion["id"], usuario_id, ahora()],
    )
    if cursor.rowcount != 1:
        conexion.close()
        return False
    base_datos.en(conexion, 
        "INSERT INTO votos (id, colegio_id, eleccion_id, candidato_id) VALUES (?, ?, ?, ?)",
        [id_secreto(conexion), eleccion["colegio_id"], eleccion["id"], candidato_id],
    )
    conexion.commit()
    conexion.close()
    return True


def opciones_de_candidatos(eleccion, candidatos):
    inscritos = []
    for candidato in candidatos:
        inscritos.append(candidato["estudiante_id"])
    mayor = grado_mayor(eleccion["colegio_id"], eleccion["anio"])
    opciones = []
    for grupo in base_datos.grupos_del_colegio(eleccion["colegio_id"], eleccion["anio"]):
        sirve = False
        if eleccion["cargo"] == "representante":
            sirve = grupo["id"] == eleccion["grupo_id"]
        elif mayor is not None:
            sirve = grupo["orden_grado"] == mayor["orden"]
        if sirve:
            for estudiante in base_datos.estudiantes_del_grupo(grupo["id"]):
                if estudiante["id"] not in inscritos:
                    opciones.append({"id": estudiante["id"], "nombre": estudiante["nombre"], "grupo": grupo["nombre"]})
    return opciones


def regla_de(eleccion):
    if eleccion["cargo"] == "representante":
        return "Solo se postulan y votan los estudiantes del grupo " + str(eleccion["grupo"]) + "."
    mayor = grado_mayor(eleccion["colegio_id"], eleccion["anio"])
    grado = "el último grado"
    if mayor is not None:
        grado = mayor["nombre"]
    return "Se postulan estudiantes de " + grado + " y votan todos los estudiantes matriculados."


def siguiente_numero(candidatos):
    mayor = 0
    for candidato in candidatos:
        if candidato["numero"] > mayor:
            mayor = candidato["numero"]
    return mayor + 1


def formulario_eleccion():
    return {"cargo": "personero", "titulo": "", "grupo_id": "", "apertura": "", "cierre": ""}


def crear_eleccion(formulario):
    errores = []
    apertura = formulario["apertura"].replace("T", " ")
    cierre = formulario["cierre"].replace("T", " ")
    grupo_id = None
    if formulario["cargo"] not in claves(CARGOS):
        errores.append("Elige el cargo de la elección.")
    if formulario["titulo"] == "":
        errores.append("Escribe el título de la elección.")
    elif len(formulario["titulo"]) > 120:
        errores.append("El título no puede pasar de 120 caracteres.")
    if formulario["cargo"] == "representante":
        grupo = None
        numero_grupo = entero(formulario["grupo_id"])
        if numero_grupo is not None:
            grupo = base_datos.buscar_grupo(numero_grupo)
        if grupo is None or grupo["colegio_id"] != g.colegio["id"] or grupo["anio"] != g.colegio["anio"]:
            errores.append("Elige el grupo del representante.")
        else:
            grupo_id = grupo["id"]
    if not fecha_hora_valida(apertura):
        errores.append("La apertura debe tener el formato AAAA-MM-DD HH:MM.")
    if not fecha_hora_valida(cierre):
        errores.append("El cierre debe tener el formato AAAA-MM-DD HH:MM.")
    elif fecha_hora_valida(apertura) and cierre <= apertura:
        errores.append("El cierre debe ser después de la apertura.")
    if len(errores) == 0:
        base_datos.ejecutar(
            "INSERT INTO elecciones (colegio_id, anio, cargo, titulo, grupo_id, apertura, cierre, estado, creada_por) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'preparacion', ?)",
            [g.colegio["id"], g.colegio["anio"], formulario["cargo"], formulario["titulo"], grupo_id, apertura, cierre,
             g.yo["id"]],
        )
        registrar("Creó una elección", formulario["titulo"])
    return errores


def agregar_candidato():
    errores = []
    eleccion = None
    eleccion_id = entero(request.form.get("eleccion_id", ""))
    if eleccion_id is not None:
        eleccion = buscar_eleccion(eleccion_id)
    if eleccion is None:
        return ["No se encontró la elección."]
    if eleccion["estado"] != "preparacion":
        return ["Solo se agregan candidatos mientras la elección está en preparación."]
    estudiante = None
    estudiante_id = entero(request.form.get("estudiante_id", ""))
    if estudiante_id is not None:
        estudiante = estudiante_del_colegio(estudiante_id)
    numero = entero(request.form.get("numero", ""))
    propuesta = request.form.get("propuesta", "").strip()
    if estudiante is None:
        errores.append("Elige al estudiante candidato.")
    elif not puede_postularse(eleccion, estudiante["id"]):
        errores.append(estudiante["nombre"] + " no puede postularse: " + regla_de(eleccion))
    elif base_datos.consultar_uno("SELECT id FROM candidatos WHERE eleccion_id = ? AND estudiante_id = ?",
                                  [eleccion["id"], estudiante["id"]]) is not None:
        errores.append(estudiante["nombre"] + " ya es candidato en esta elección.")
    if numero is None or numero < 1 or numero > 99:
        errores.append("El número del tarjetón debe estar entre 1 y 99.")
    elif base_datos.consultar_uno("SELECT id FROM candidatos WHERE eleccion_id = ? AND numero = ?",
                                  [eleccion["id"], numero]) is not None:
        errores.append("El número " + str(numero) + " ya lo tiene otro candidato.")
    if propuesta == "":
        errores.append("Escribe la propuesta del candidato.")
    elif len(propuesta) > 600:
        errores.append("La propuesta no puede pasar de 600 caracteres.")
    if len(errores) == 0:
        base_datos.ejecutar(
            "INSERT INTO candidatos (colegio_id, eleccion_id, estudiante_id, numero, propuesta) VALUES (?, ?, ?, ?, ?)",
            [g.colegio["id"], eleccion["id"], estudiante["id"], numero, propuesta],
        )
        registrar("Agregó un candidato", eleccion["titulo"] + ": " + estudiante["nombre"])
    return errores


def quitar_candidato():
    candidato = None
    candidato_id = entero(request.form.get("candidato_id", ""))
    if candidato_id is not None:
        candidato = base_datos.consultar_uno(
            "SELECT * FROM candidatos WHERE id = ? AND colegio_id = ?", [candidato_id, g.colegio["id"]]
        )
    if candidato is None:
        return ["No se encontró el candidato."]
    eleccion = buscar_eleccion(candidato["eleccion_id"])
    if eleccion is None or eleccion["estado"] != "preparacion":
        return ["Solo se quitan candidatos mientras la elección está en preparación."]
    base_datos.ejecutar("DELETE FROM candidatos WHERE id = ?", [candidato["id"]])
    registrar("Quitó un candidato", eleccion["titulo"] + ": candidato " + str(candidato["numero"]))
    return []


def cambiar_estado(accion):
    eleccion = None
    eleccion_id = entero(request.form.get("eleccion_id", ""))
    if eleccion_id is not None:
        eleccion = buscar_eleccion(eleccion_id)
    if eleccion is None:
        return ["No se encontró la elección."]
    if accion == "abrir":
        if eleccion["estado"] != "preparacion":
            return ["Solo se abre una elección que está en preparación."]
        if len(candidatos_de(eleccion)) == 0:
            return ["Agrega al menos un candidato antes de abrir la votación."]
        base_datos.ejecutar("UPDATE elecciones SET estado = 'abierta' WHERE id = ?", [eleccion["id"]])
        registrar("Abrió una elección", eleccion["titulo"])
    else:
        if eleccion["estado"] != "abierta":
            return ["Solo se cierra una elección que está abierta."]
        base_datos.ejecutar("UPDATE elecciones SET estado = 'cerrada' WHERE id = ?", [eleccion["id"]])
        registrar("Cerró una elección", eleccion["titulo"])
    return []


def mensaje_de(accion):
    mensajes = {
        "crear": "Elección creada. Ahora agrega los candidatos.",
        "agregar_candidato": "Candidato agregado.",
        "quitar_candidato": "Candidato retirado.",
        "abrir": "La votación quedó abierta.",
        "cerrar": "La votación quedó cerrada. Los resultados ya son públicos.",
    }
    return mensajes[accion]


@app.route("/elecciones", methods=["GET", "POST"])
def elecciones():
    organiza = tiene_alguno(g.yo, ORGANIZAN)
    es_estudiante = tiene_rol(g.yo, "estudiante")
    if not organiza and not es_estudiante:
        return redirect("/inicio")

    errores = []
    mensaje = ""
    formulario = formulario_eleccion()
    if request.method == "POST":
        if not organiza:
            return redirect("/inicio")
        accion = request.form.get("accion", "")
        if accion == "crear":
            for campo in formulario:
                formulario[campo] = request.form.get(campo, "").strip()
            errores = crear_eleccion(formulario)
            if len(errores) == 0:
                formulario = formulario_eleccion()
        elif accion == "agregar_candidato":
            errores = agregar_candidato()
        elif accion == "quitar_candidato":
            errores = quitar_candidato()
        elif accion == "abrir" or accion == "cerrar":
            errores = cambiar_estado(accion)
        else:
            errores = ["Acción no válida."]
        if len(errores) == 0:
            mensaje = mensaje_de(accion)

    todas = elecciones_del_colegio()
    mis_elecciones = None
    if es_estudiante:
        mis_elecciones = []
        for eleccion in todas:
            if eleccion["anio"] == g.colegio["anio"] and puede_votar(g.yo, eleccion):
                voto = ya_voto(eleccion["id"], g.yo["id"])
                item = {"eleccion": eleccion, "votaste": voto, "puede_votar": False, "resultado": None}
                if eleccion["estado"] == "cerrada":
                    item["texto"] = "Cerrada"
                    item["clase"] = "neutro"
                    item["resultado"] = resultados(eleccion)
                elif voto:
                    item["texto"] = "Votaste"
                    item["clase"] = "bien"
                elif eleccion["estado"] == "abierta":
                    item["texto"] = "Puedes votar"
                    item["clase"] = "atencion"
                    item["puede_votar"] = True
                else:
                    item["texto"] = "Próximamente"
                    item["clase"] = "neutro"
                mis_elecciones.append(item)

    gestion = []
    grupos = []
    if organiza:
        grupos = base_datos.grupos_del_colegio(g.colegio["id"], g.colegio["anio"])
        momento = ahora()
        for eleccion in todas:
            candidatos = candidatos_de(eleccion)
            item = {"eleccion": eleccion, "candidatos": candidatos, "participacion": participacion(eleccion),
                    "regla": regla_de(eleccion), "opciones": [], "siguiente": siguiente_numero(candidatos),
                    "vencida": eleccion["estado"] == "abierta" and momento > eleccion["cierre"]}
            if eleccion["estado"] == "preparacion":
                item["opciones"] = opciones_de_candidatos(eleccion, candidatos)
            gestion.append(item)

    return render_template("gobierno_elecciones.html", activo="elecciones", organiza=organiza,
                           mis_elecciones=mis_elecciones, gestion=gestion, grupos=grupos, formulario=formulario,
                           errores=errores, mensaje=mensaje, cargos=CARGOS, nombres_cargos=nombres(CARGOS),
                           estados=ESTADOS)


def buscar_opcion(opcion, candidatos):
    if opcion == "blanco":
        return {"opcion": "blanco", "candidato_id": None, "blanco": True, "nombre": "Voto en blanco", "numero": "",
                "grupo": ""}
    for candidato in candidatos:
        if str(candidato["id"]) == opcion:
            return {"opcion": str(candidato["id"]), "candidato_id": candidato["id"], "blanco": False,
                    "nombre": candidato["nombre"], "numero": candidato["numero"], "grupo": candidato["grupo"]}
    return None


@app.route("/elecciones/<int:eleccion_id>/votar", methods=["GET", "POST"])
def votar(eleccion_id):
    if g.yo is None:
        return redirect("/inicio")
    eleccion = buscar_eleccion(eleccion_id)
    if eleccion is None or not puede_votar(g.yo, eleccion):
        return redirect("/inicio")

    candidatos = candidatos_de(eleccion)
    paso = "tarjeton"
    errores = []
    elegido = None
    if ya_voto(eleccion["id"], g.yo["id"]):
        paso = "ya_voto"
    elif eleccion["estado"] != "abierta":
        paso = "no_abierta"
    elif request.method == "POST":
        elegido = buscar_opcion(request.form.get("opcion", ""), candidatos)
        if elegido is None:
            errores.append("Marca un candidato o el voto en blanco.")
        elif request.form.get("paso", "") == "votar":
            if emitir_voto(eleccion, g.yo["id"], elegido["candidato_id"]):
                registrar("Votó en una elección", eleccion["titulo"])
                paso = "listo"
            else:
                paso = "ya_voto"
            elegido = None
        else:
            paso = "confirmar"

    return render_template("gobierno_votar.html", activo="elecciones", eleccion=eleccion, candidatos=candidatos,
                           paso=paso, errores=errores, elegido=elegido, nombres_cargos=nombres(CARGOS))


@app.route("/elecciones/<int:eleccion_id>")
def resultados_eleccion(eleccion_id):
    if g.yo is None:
        return redirect("/inicio")
    eleccion = buscar_eleccion(eleccion_id)
    if eleccion is None:
        return redirect("/inicio")
    organiza = tiene_alguno(g.yo, ORGANIZAN)
    if not organiza and eleccion["estado"] != "cerrada":
        return redirect("/inicio")
    datos = participacion(eleccion)
    resultado = resultados(eleccion)
    descuadre = resultado["total"] != datos["votantes"]
    return render_template("gobierno_resultados.html", activo="elecciones", eleccion=eleccion, resultado=resultado,
                           participacion=datos, organiza=organiza, descuadre=descuadre,
                           nombres_cargos=nombres(CARGOS), estados=ESTADOS)


def sembrar_votos(conexion, colegio_id, eleccion_id, candidato_id, cantidad):
    for vez in range(cantidad):
        base_datos.en(conexion, 
            "INSERT INTO votos (id, colegio_id, eleccion_id, candidato_id) VALUES (?, ?, ?, ?)",
            [id_secreto(conexion), colegio_id, eleccion_id, candidato_id],
        )


def sembrar_gobierno():
    colegio = base_datos.buscar_colegio(1)
    if colegio is None or not base_datos.tabla_vacia("elecciones"):
        return
    rectora = base_datos.buscar_usuario("rectora")
    coordinadora = base_datos.buscar_usuario("coordinadora")
    luisa = base_datos.buscar_usuario("luisa.montoya")
    esteban = base_datos.buscar_usuario("esteban.ramirez")
    daniela = base_datos.buscar_usuario("daniela.cardona")
    laura = base_datos.buscar_usuario("laura.patino")
    david = base_datos.buscar_usuario("david.giraldo")
    personas = [rectora, coordinadora, luisa, esteban, daniela, laura, david]
    for persona in personas:
        if persona is None:
            return
    anio = colegio["anio"]
    grupo = base_datos.consultar_uno(
        "SELECT id FROM grupos WHERE colegio_id = ? AND anio = ? AND nombre = '10-A'", [colegio["id"], anio]
    )
    if grupo is None:
        return

    personero = base_datos.ejecutar(
        "INSERT INTO elecciones (colegio_id, anio, cargo, titulo, grupo_id, apertura, cierre, estado, creada_por) "
        "VALUES (?, ?, 'personero', ?, NULL, ?, ?, 'cerrada', ?)",
        [colegio["id"], anio, "Personero estudiantil " + str(anio), str(anio) + "-02-20 07:00",
         str(anio) + "-02-20 12:00", rectora["id"]],
    )
    propuestas = [
        {"persona": esteban, "numero": 1,
         "propuesta": "Torneo intercursos de fútbol y microfútbol, buzón de sugerencias en cada salón y jornadas de "
                      "reciclaje con el comité ambiental."},
        {"persona": luisa, "numero": 2,
         "propuesta": "Mesas de escucha cada mes, monitorías entre estudiantes para reforzar materias y una semana "
                      "cultural con la música y la historia de Pijao."},
        {"persona": daniela, "numero": 3,
         "propuesta": "Opciones saludables en la tienda escolar, arreglo de los baños con la asociación de padres y un "
                      "club de lectura."},
    ]
    ids = {}
    for item in propuestas:
        ids[item["numero"]] = base_datos.ejecutar(
            "INSERT INTO candidatos (colegio_id, eleccion_id, estudiante_id, numero, propuesta) VALUES (?, ?, ?, ?, ?)",
            [colegio["id"], personero, item["persona"]["id"], item["numero"], item["propuesta"]],
        )

    votaron = ["melany.osorio", "juan.restrepo", "sharon.loaiza", "valentina.arias", "david.giraldo", "mariana.henao",
               "samuel.ocampo", "laura.patino", "esteban.ramirez", "daniela.cardona", "luisa.montoya", "kevin.largo",
               "maria.valencia"]
    conexion = base_datos.conectar()
    minuto = 5
    for usuario in votaron:
        persona = base_datos.buscar_usuario(usuario)
        if persona is not None:
            texto_minuto = str(minuto)
            if minuto < 10:
                texto_minuto = "0" + texto_minuto
            base_datos.en(conexion, 
                "INSERT INTO votantes (colegio_id, eleccion_id, usuario_id, votado_en) VALUES (?, ?, ?, ?)",
                [colegio["id"], personero, persona["id"], str(anio) + "-02-20 07:" + texto_minuto],
            )
            minuto = minuto + 3
    sembrar_votos(conexion, colegio["id"], personero, ids[2], 6)
    sembrar_votos(conexion, colegio["id"], personero, ids[1], 4)
    sembrar_votos(conexion, colegio["id"], personero, ids[3], 2)
    sembrar_votos(conexion, colegio["id"], personero, None, 1)
    conexion.commit()
    conexion.close()

    representante = base_datos.ejecutar(
        "INSERT INTO elecciones (colegio_id, anio, cargo, titulo, grupo_id, apertura, cierre, estado, creada_por) "
        "VALUES (?, ?, 'representante', ?, ?, ?, ?, 'preparacion', ?)",
        [colegio["id"], anio, "Representante de grupo 10-A", grupo["id"], str(anio) + "-11-27 07:00",
         str(anio) + "-11-27 09:00", coordinadora["id"]],
    )
    base_datos.ejecutar(
        "INSERT INTO candidatos (colegio_id, eleccion_id, estudiante_id, numero, propuesta) VALUES (?, ?, ?, ?, ?)",
        [colegio["id"], representante, laura["id"], 1,
         "Grupos de estudio antes de cada evaluación y llevar las inquietudes del curso al consejo de estudiantes."],
    )
    base_datos.ejecutar(
        "INSERT INTO candidatos (colegio_id, eleccion_id, estudiante_id, numero, propuesta) VALUES (?, ?, ?, ?, ?)",
        [colegio["id"], representante, david["id"], 2,
         "Una salida pedagógica al Paisaje Cultural Cafetero y un fondo común de fotocopias para el curso."],
    )


if CON_DATOS_DE_EJEMPLO:
    sembrar_gobierno()
