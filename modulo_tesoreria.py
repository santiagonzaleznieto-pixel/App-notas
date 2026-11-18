from datetime import date
from flask import g, render_template, request, redirect
import nucleo
from nucleo import (app, agregar_menu, tiene_rol, tiene_alguno, estudiante_del_colegio, grupo_del_estudiante,
                    registrar, numero, CON_DATOS_DE_EJEMPLO)
import base_datos

TABLAS_TESORERIA = """
CREATE TABLE IF NOT EXISTS conceptos_cobro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    anio INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    tipo TEXT NOT NULL,
    valor INTEGER NOT NULL,
    valor_anio_anterior INTEGER NOT NULL DEFAULT 0,
    activo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS cobros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    anio INTEGER NOT NULL,
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    concepto_id INTEGER NOT NULL REFERENCES conceptos_cobro(id),
    descripcion TEXT NOT NULL,
    valor INTEGER NOT NULL,
    fecha_limite TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendiente',
    motivo_anulacion TEXT NOT NULL DEFAULT '',
    creado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pagos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    cobro_id INTEGER NOT NULL REFERENCES cobros(id),
    valor INTEGER NOT NULL,
    fecha TEXT NOT NULL,
    medio TEXT NOT NULL,
    referencia TEXT NOT NULL DEFAULT '',
    recibido_por INTEGER NOT NULL REFERENCES usuarios(id),
    registrado_en TEXT NOT NULL,
    numero_recibo TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS descuentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    cobro_id INTEGER NOT NULL REFERENCES cobros(id),
    valor INTEGER NOT NULL,
    motivo TEXT NOT NULL,
    autorizado_por INTEGER NOT NULL REFERENCES usuarios(id),
    fecha TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS parametros_tesoreria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    anio INTEGER NOT NULL,
    tope_aumento REAL NOT NULL,
    UNIQUE (colegio_id, anio)
);
"""

base_datos.crear_tablas(TABLAS_TESORERIA)

VEN_TESORERIA = ["tesoreria", "administrador", "rector"]
CONFIGURAN = ["tesoreria", "administrador"]
AUTORIZAN_DESCUENTOS = ["administrador", "rector"]

TIPOS = {"matricula": "Matrícula", "pension": "Pensión", "otro": "Otro cobro"}
MEDIOS = {"efectivo": "Efectivo", "transferencia": "Transferencia", "consignacion": "Consignación", "pse": "PSE", "otro": "Otro"}
PIDEN_REFERENCIA = ["transferencia", "consignacion", "pse"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]

CONSULTA_COBROS = (
    "SELECT cobros.*, conceptos_cobro.nombre AS concepto, conceptos_cobro.tipo AS tipo, "
    "(SELECT COALESCE(SUM(pagos.valor), 0) FROM pagos WHERE pagos.cobro_id = cobros.id) AS pagado, "
    "(SELECT COALESCE(SUM(descuentos.valor), 0) FROM descuentos WHERE descuentos.cobro_id = cobros.id) AS descontado "
    "FROM cobros JOIN conceptos_cobro ON conceptos_cobro.id = cobros.concepto_id "
)

agregar_menu("tesoreria", "Tesorería", "/tesoreria", VEN_TESORERIA, "Cobros, pagos, cartera y paz y salvo.")
agregar_menu("pagos", "Pagos", "/mis-pagos", ["acudiente"], "Estado de cuenta de tus hijos.")


def formato_pesos(valor):
    if valor is None:
        valor = 0
    cantidad = int(valor)
    signo = ""
    if cantidad < 0:
        signo = "-"
        cantidad = -cantidad
    texto = str(cantidad)
    resultado = ""
    contador = 0
    posicion = len(texto) - 1
    while posicion >= 0:
        if contador == 3:
            resultado = "." + resultado
            contador = 0
        resultado = texto[posicion] + resultado
        contador = contador + 1
        posicion = posicion - 1
    return signo + "$" + resultado


def sin_signo(valor):
    return formato_pesos(valor).replace("$", "")


def formato_porcentaje(valor):
    if valor is None:
        return "—"
    texto = str(round(valor, 2))
    if texto.endswith(".0"):
        texto = texto[0:len(texto) - 2]
    return texto.replace(".", ",")


def leer_pesos(texto, minimo, maximo):
    limpio = texto.strip().replace("$", "").replace(" ", "").replace(".", "")
    if limpio == "" or "," in limpio:
        return None
    valor = numero(limpio, minimo, maximo)
    if valor is None:
        return None
    return int(valor)


def entero(texto):
    limpio = texto.strip()
    if limpio == "" or len(limpio) > 9:
        return None
    for letra in limpio:
        if letra not in "0123456789":
            return None
    return int(limpio)


def dias_del_mes(anio, mes):
    dias = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if mes == 2 and anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0):
        return 29
    return dias[mes - 1]


def fecha_valida(texto):
    if len(texto) != 10 or texto[4] != "-" or texto[7] != "-":
        return False
    for posicion in range(10):
        if posicion != 4 and posicion != 7 and texto[posicion] not in "0123456789":
            return False
    anio = int(texto[0:4])
    mes = int(texto[5:7])
    dia = int(texto[8:10])
    if anio < 2000 or anio > 2100 or mes < 1 or mes > 12 or dia < 1:
        return False
    return dia <= dias_del_mes(anio, mes)


def fecha_larga(texto):
    if texto is None or not fecha_valida(texto[0:10]):
        return texto
    return str(int(texto[8:10])) + " de " + MESES[int(texto[5:7]) - 1] + " de " + texto[0:4]


def dias_entre(desde, hasta):
    inicio = date(int(desde[0:4]), int(desde[5:7]), int(desde[8:10]))
    fin = date(int(hasta[0:4]), int(hasta[5:7]), int(hasta[8:10]))
    return (fin - inicio).days


def dos_digitos(valor):
    texto = str(valor)
    if len(texto) < 2:
        texto = "0" + texto
    return texto


def es_acudiente_de(yo, estudiante_id):
    if not tiene_rol(yo, "acudiente"):
        return False
    for hijo in base_datos.estudiantes_a_cargo(yo["id"]):
        if hijo["id"] == estudiante_id:
            return True
    return False


def puede_ver_cuenta(yo, estudiante):
    if yo is None or estudiante is None or estudiante["colegio_id"] != yo["colegio_id"]:
        return False
    if tiene_alguno(yo, VEN_TESORERIA):
        return True
    return es_acudiente_de(yo, estudiante["id"])


def pestana_de(yo):
    if tiene_alguno(yo, VEN_TESORERIA):
        return "tesoreria"
    return "pagos"


def completar_cobro(cobro, fecha_hoy):
    saldo = cobro["valor"] - cobro["pagado"] - cobro["descontado"]
    if cobro["estado"] == "anulado" or saldo < 0:
        saldo = 0
    cobro["saldo"] = saldo
    cobro["vencido"] = saldo > 0 and cobro["fecha_limite"] < fecha_hoy
    cobro["dias_mora"] = 0
    if cobro["vencido"]:
        cobro["dias_mora"] = dias_entre(cobro["fecha_limite"], fecha_hoy)
    if cobro["estado"] == "anulado":
        cobro["situacion"] = "Anulado"
        cobro["clase"] = "neutro"
    elif saldo == 0:
        cobro["situacion"] = "Pagado"
        cobro["clase"] = "bien"
    elif cobro["vencido"]:
        cobro["situacion"] = "Vencido"
        cobro["clase"] = "mal"
    elif cobro["pagado"] + cobro["descontado"] > 0:
        cobro["situacion"] = "Abonado"
        cobro["clase"] = "atencion"
    else:
        cobro["situacion"] = "Por pagar"
        cobro["clase"] = "atencion"
    return cobro


def cobros_completos(condicion, valores, fecha_hoy):
    cobros = base_datos.consultar(CONSULTA_COBROS + condicion + " ORDER BY cobros.fecha_limite, cobros.id", valores)
    for cobro in cobros:
        completar_cobro(cobro, fecha_hoy)
    return cobros


def cobros_del_estudiante(estudiante_id):
    return cobros_completos("WHERE cobros.colegio_id = ? AND cobros.estudiante_id = ?", [g.colegio["id"], estudiante_id],
                            nucleo.hoy())


def buscar_cobro(texto, estudiante_id):
    cobro_id = entero(texto)
    if cobro_id is None:
        return None
    cobro = base_datos.consultar_uno(
        CONSULTA_COBROS + "WHERE cobros.id = ? AND cobros.colegio_id = ? AND cobros.estudiante_id = ?",
        [cobro_id, g.colegio["id"], estudiante_id],
    )
    if cobro is None:
        return None
    return completar_cobro(cobro, nucleo.hoy())


def movimientos(cobro):
    cobro["pagos"] = base_datos.consultar(
        "SELECT pagos.*, usuarios.nombre AS recibio FROM pagos JOIN usuarios ON usuarios.id = pagos.recibido_por "
        "WHERE pagos.cobro_id = ? AND pagos.colegio_id = ? ORDER BY pagos.fecha, pagos.id",
        [cobro["id"], cobro["colegio_id"]],
    )
    cobro["descuentos"] = base_datos.consultar(
        "SELECT descuentos.*, usuarios.nombre AS autorizo FROM descuentos JOIN usuarios ON usuarios.id = descuentos.autorizado_por "
        "WHERE descuentos.cobro_id = ? AND descuentos.colegio_id = ? ORDER BY descuentos.fecha, descuentos.id",
        [cobro["id"], cobro["colegio_id"]],
    )
    return cobro


def resumen_cuenta(cobros, anio):
    cuenta = {"cobrado": 0, "pagado": 0, "descontado": 0, "saldo": 0, "vencido": 0, "dias_mora": 0,
              "cobrado_anio": 0, "pagado_anio": 0, "pendientes": [], "vencidos": []}
    for cobro in cobros:
        if cobro["estado"] != "anulado":
            cuenta["cobrado"] = cuenta["cobrado"] + cobro["valor"]
            cuenta["pagado"] = cuenta["pagado"] + cobro["pagado"]
            cuenta["descontado"] = cuenta["descontado"] + cobro["descontado"]
            if cobro["anio"] == anio:
                cuenta["cobrado_anio"] = cuenta["cobrado_anio"] + cobro["valor"]
                cuenta["pagado_anio"] = cuenta["pagado_anio"] + cobro["pagado"]
        cuenta["saldo"] = cuenta["saldo"] + cobro["saldo"]
        if cobro["saldo"] > 0:
            cuenta["pendientes"].append(cobro)
        if cobro["vencido"]:
            cuenta["vencido"] = cuenta["vencido"] + cobro["saldo"]
            cuenta["vencidos"].append(cobro)
            if cobro["dias_mora"] > cuenta["dias_mora"]:
                cuenta["dias_mora"] = cobro["dias_mora"]
    return cuenta


def actualizar_estado(cobro_id):
    cobro = base_datos.consultar_uno(CONSULTA_COBROS + "WHERE cobros.id = ?", [cobro_id])
    if cobro is not None and cobro["estado"] == "pendiente" and cobro["pagado"] + cobro["descontado"] >= cobro["valor"]:
        base_datos.ejecutar("UPDATE cobros SET estado = 'pagado' WHERE id = ?", [cobro_id])


def armar_recibo(anio, consecutivo):
    texto = str(consecutivo)
    while len(texto) < 6:
        texto = "0" + texto
    return "R-" + str(anio) + "-" + texto


def siguiente_recibo(colegio_id, anio):
    fila = base_datos.consultar_uno(
        "SELECT COUNT(*) AS total FROM pagos WHERE colegio_id = ? AND numero_recibo LIKE ?",
        [colegio_id, "R-" + str(anio) + "-%"],
    )
    consecutivo = fila["total"] + 1
    numero_recibo = armar_recibo(anio, consecutivo)
    while base_datos.consultar_uno("SELECT id FROM pagos WHERE numero_recibo = ?", [numero_recibo]) is not None:
        consecutivo = consecutivo + 1
        numero_recibo = armar_recibo(anio, consecutivo)
    return numero_recibo


def tope_del_anio(colegio_id, anio):
    fila = base_datos.consultar_uno("SELECT tope_aumento FROM parametros_tesoreria WHERE colegio_id = ? AND anio = ?",
                                    [colegio_id, anio])
    if fila is None:
        return None
    return fila["tope_aumento"]


def guardar_tope(colegio_id, anio, tope):
    if tope_del_anio(colegio_id, anio) is None:
        base_datos.ejecutar("INSERT INTO parametros_tesoreria (colegio_id, anio, tope_aumento) VALUES (?, ?, ?)",
                            [colegio_id, anio, tope])
    else:
        base_datos.ejecutar("UPDATE parametros_tesoreria SET tope_aumento = ? WHERE colegio_id = ? AND anio = ?",
                            [tope, colegio_id, anio])


def buscar_concepto(concepto_id):
    if concepto_id is None:
        return None
    return base_datos.consultar_uno("SELECT * FROM conceptos_cobro WHERE id = ? AND colegio_id = ?", [concepto_id, g.colegio["id"]])


def revisar_aumento(concepto):
    concepto["aumento"] = None
    concepto["tope"] = tope_del_anio(concepto["colegio_id"], concepto["anio"])
    concepto["supera"] = False
    if concepto["tipo"] != "otro" and concepto["valor_anio_anterior"] > 0:
        aumento = (concepto["valor"] - concepto["valor_anio_anterior"]) * 100 / concepto["valor_anio_anterior"]
        concepto["aumento"] = round(aumento, 2)
        if concepto["tope"] is not None and concepto["aumento"] > concepto["tope"]:
            concepto["supera"] = True
    return concepto


def texto_advertencia(concepto):
    return ("Advertencia: el aumento de «" + concepto["nombre"] + "» frente al año anterior es de "
            + formato_porcentaje(concepto["aumento"]) + " % y supera el tope de " + formato_porcentaje(concepto["tope"])
            + " % que escribiste para " + str(concepto["anio"]) + ". Revisa el valor antes de generar los cobros.")


def clave_familia(estudiante_id):
    acudientes = base_datos.acudientes_de(estudiante_id)
    if len(acudientes) == 0:
        return "estudiante-" + str(estudiante_id)
    return "acudiente-" + str(acudientes[0]["id"])


def ordenar_por_mora(lista):
    copia = []
    for elemento in lista:
        copia.append(elemento)
    ordenada = []
    while len(copia) > 0:
        mayor = 0
        for posicion in range(len(copia)):
            if copia[posicion]["cuenta"]["dias_mora"] > copia[mayor]["cuenta"]["dias_mora"]:
                mayor = posicion
        ordenada.append(copia.pop(mayor))
    return ordenada


def estudiantes_con_grupo(grupos):
    estudiantes = []
    for grupo in grupos:
        for estudiante in base_datos.estudiantes_del_grupo(grupo["id"]):
            estudiante["grupo"] = grupo
            estudiantes.append(estudiante)
    return estudiantes


def cobros_por_estudiante(colegio_id):
    por_estudiante = {}
    for cobro in cobros_completos("WHERE cobros.colegio_id = ?", [colegio_id], nucleo.hoy()):
        if cobro["estudiante_id"] not in por_estudiante:
            por_estudiante[cobro["estudiante_id"]] = []
        por_estudiante[cobro["estudiante_id"]].append(cobro)
    return por_estudiante


def grupo_elegido(texto, grupos):
    grupo_id = entero(texto)
    for grupo in grupos:
        if grupo["id"] == grupo_id:
            return grupo
    return None


def mensaje_recordatorio(estudiante, acudientes, cuenta):
    saludo = "Cordial saludo, familia de " + estudiante["nombre"] + "."
    if len(acudientes) > 0:
        saludo = "Cordial saludo, " + acudientes[0]["nombre"] + "."
    detalle = ""
    for cobro in cuenta["vencidos"]:
        if detalle != "":
            detalle = detalle + "; "
        detalle = (detalle + cobro["descripcion"] + " (" + formato_pesos(cobro["saldo"]) + ", fecha límite "
                   + fecha_larga(cobro["fecha_limite"]) + ")")
    return (saludo + " Le escribimos de la tesorería de " + g.colegio["nombre"] + ". De manera respetuosa le recordamos que, "
            + "a la fecha, la cuenta de " + estudiante["nombre"] + " registra un saldo vencido de " + formato_pesos(cuenta["vencido"])
            + " por: " + detalle + ". Si ya realizó el pago, le agradecemos enviarnos el comprobante para actualizar el registro "
            + "y le ofrecemos excusas por la molestia. Si necesita un acuerdo de pago, con gusto le atendemos en la tesorería "
            + "del colegio. Muchas gracias por su atención.")


def guardar_pago(estudiante):
    cobro = buscar_cobro(request.form.get("cobro_id", ""), estudiante["id"])
    valor = leer_pesos(request.form.get("valor", ""), 1, 100000000)
    fecha = request.form.get("fecha", "").strip()
    medio = request.form.get("medio", "")
    referencia = request.form.get("referencia", "").strip()
    errores = []
    if cobro is None or cobro["estado"] != "pendiente" or cobro["saldo"] <= 0:
        errores.append("Elige un cobro pendiente de este estudiante.")
    elif valor is None:
        errores.append("Escribe el valor del pago en pesos, sin decimales (por ejemplo 320.000).")
    elif valor > cobro["saldo"]:
        errores.append("El pago no puede ser mayor que el saldo del cobro (" + formato_pesos(cobro["saldo"]) + ").")
    if not fecha_valida(fecha):
        errores.append("La fecha del pago no es válida. Usa el formato AAAA-MM-DD.")
    elif fecha > nucleo.hoy():
        errores.append("La fecha del pago no puede ser posterior a hoy.")
    if medio not in MEDIOS:
        errores.append("Elige el medio de pago.")
    elif medio in PIDEN_REFERENCIA and referencia == "":
        errores.append("Escribe la referencia o el número del comprobante de la " + MEDIOS[medio].lower() + ".")
    if len(referencia) > 60:
        errores.append("La referencia no puede tener más de 60 caracteres.")
    if len(errores) > 0:
        return {"errores": errores, "mensaje": "", "recibo": ""}

    numero_recibo = siguiente_recibo(g.colegio["id"], g.colegio["anio"])
    base_datos.ejecutar(
        "INSERT INTO pagos (colegio_id, cobro_id, valor, fecha, medio, referencia, recibido_por, registrado_en, numero_recibo) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [g.colegio["id"], cobro["id"], valor, fecha, medio, referencia, g.yo["id"], nucleo.ahora(), numero_recibo],
    )
    actualizar_estado(cobro["id"])
    registrar("Registró un pago", numero_recibo + ": " + formato_pesos(valor) + " de " + estudiante["nombre"]
              + " por " + cobro["descripcion"])
    return {"errores": [], "mensaje": "Pago registrado con el recibo " + numero_recibo + ".", "recibo": numero_recibo}


def guardar_descuento(estudiante):
    cobro = buscar_cobro(request.form.get("cobro_id", ""), estudiante["id"])
    valor = leer_pesos(request.form.get("valor", ""), 1, 100000000)
    motivo = request.form.get("motivo", "").strip()
    errores = []
    if cobro is None or cobro["estado"] != "pendiente" or cobro["saldo"] <= 0:
        errores.append("Elige un cobro pendiente de este estudiante.")
    elif valor is None:
        errores.append("Escribe el valor del descuento en pesos, sin decimales.")
    elif valor > cobro["saldo"]:
        errores.append("El descuento no puede ser mayor que el saldo del cobro (" + formato_pesos(cobro["saldo"]) + ").")
    if len(motivo) < 5 or len(motivo) > 200:
        errores.append("Escribe el motivo del descuento (entre 5 y 200 caracteres), por ejemplo el acta que lo aprobó.")
    if len(errores) > 0:
        return {"errores": errores, "mensaje": "", "recibo": ""}

    base_datos.ejecutar(
        "INSERT INTO descuentos (colegio_id, cobro_id, valor, motivo, autorizado_por, fecha) VALUES (?, ?, ?, ?, ?, ?)",
        [g.colegio["id"], cobro["id"], valor, motivo, g.yo["id"], nucleo.hoy()],
    )
    actualizar_estado(cobro["id"])
    registrar("Autorizó un descuento", formato_pesos(valor) + " a " + estudiante["nombre"] + " en " + cobro["descripcion"]
              + ": " + motivo)
    return {"errores": [], "mensaje": "Descuento de " + formato_pesos(valor) + " registrado.", "recibo": ""}


def anular_cobro(estudiante):
    cobro = buscar_cobro(request.form.get("cobro_id", ""), estudiante["id"])
    motivo = request.form.get("motivo", "").strip()
    errores = []
    if cobro is None or cobro["estado"] != "pendiente":
        errores.append("Elige un cobro pendiente de este estudiante.")
    elif cobro["pagado"] > 0:
        errores.append("No se puede anular un cobro que ya tiene pagos registrados.")
    if len(motivo) < 5 or len(motivo) > 200:
        errores.append("Escribe el motivo de la anulación (entre 5 y 200 caracteres).")
    if len(errores) > 0:
        return {"errores": errores, "mensaje": "", "recibo": ""}

    base_datos.ejecutar("UPDATE cobros SET estado = 'anulado', motivo_anulacion = ? WHERE id = ? AND colegio_id = ?",
                        [motivo, cobro["id"], g.colegio["id"]])
    registrar("Anuló un cobro", cobro["descripcion"] + " de " + estudiante["nombre"] + ": " + motivo)
    return {"errores": [], "mensaje": "Cobro anulado: " + cobro["descripcion"] + ".", "recibo": ""}


def guardar_concepto(anios):
    concepto_id = entero(request.form.get("concepto_id", ""))
    nombre = request.form.get("nombre", "").strip()
    tipo = request.form.get("tipo", "")
    anio = entero(request.form.get("anio", ""))
    valor = leer_pesos(request.form.get("valor", ""), 1, 100000000)
    texto_anterior = request.form.get("valor_anterior", "").strip()
    activo = 0
    if request.form.get("activo", "") == "1":
        activo = 1
    anterior = 0
    errores = []
    concepto = None
    if concepto_id is not None:
        concepto = buscar_concepto(concepto_id)
        if concepto is None:
            errores.append("El concepto que intentas editar no existe en tu colegio.")
    if len(nombre) < 3 or len(nombre) > 80:
        errores.append("El nombre debe tener entre 3 y 80 caracteres.")
    if tipo not in TIPOS:
        errores.append("Elige el tipo de cobro.")
    if anio not in anios:
        errores.append("Elige el año del concepto.")
    if valor is None:
        errores.append("Escribe el valor en pesos, sin decimales (por ejemplo 320.000).")
    if tipo != "otro" and texto_anterior != "" and texto_anterior != "0":
        anterior = leer_pesos(texto_anterior, 1, 100000000)
        if anterior is None:
            errores.append("El valor del año anterior debe estar en pesos, sin decimales. Déjalo vacío si no aplica.")
    if len(errores) == 0:
        excluir = 0
        if concepto_id is not None:
            excluir = concepto_id
        repetido = base_datos.consultar_uno(
            "SELECT id FROM conceptos_cobro WHERE colegio_id = ? AND anio = ? AND nombre = ? AND id != ?",
            [g.colegio["id"], anio, nombre, excluir],
        )
        if repetido is not None:
            errores.append("Ya existe un concepto con ese nombre en " + str(anio) + ".")
    if len(errores) > 0:
        return {"errores": errores, "mensaje": "", "concepto": None}

    if concepto is None:
        concepto_id = base_datos.ejecutar(
            "INSERT INTO conceptos_cobro (colegio_id, anio, nombre, tipo, valor, valor_anio_anterior, activo) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [g.colegio["id"], anio, nombre, tipo, valor, anterior, activo],
        )
        registrar("Creó un concepto de cobro", nombre + " " + str(anio) + ": " + formato_pesos(valor))
        mensaje = "Concepto creado: " + nombre + "."
    else:
        base_datos.ejecutar(
            "UPDATE conceptos_cobro SET anio = ?, nombre = ?, tipo = ?, valor = ?, valor_anio_anterior = ?, activo = ? "
            "WHERE id = ? AND colegio_id = ?",
            [anio, nombre, tipo, valor, anterior, activo, concepto_id, g.colegio["id"]],
        )
        registrar("Editó un concepto de cobro", nombre + " " + str(anio) + ": " + formato_pesos(valor))
        mensaje = "Concepto actualizado: " + nombre + "."
    return {"errores": [], "mensaje": mensaje, "concepto": revisar_aumento(buscar_concepto(concepto_id))}


def valores_vacios_concepto(anio):
    return {"concepto_id": "", "nombre": "", "tipo": "pension", "anio": anio, "valor": "", "valor_anterior": "", "activo": True}


@app.route("/tesoreria")
def tesoreria():
    if not tiene_alguno(g.yo, VEN_TESORERIA):
        return redirect("/inicio")

    colegio_id = g.colegio["id"]
    anio = g.colegio["anio"]
    por_estudiante = cobros_por_estudiante(colegio_id)

    total = {"cobrado": 0, "pagado": 0, "vencido": 0, "estudiantes_en_mora": 0}
    familias = []
    for estudiante_id in por_estudiante:
        cuenta = resumen_cuenta(por_estudiante[estudiante_id], anio)
        total["cobrado"] = total["cobrado"] + cuenta["cobrado_anio"]
        total["pagado"] = total["pagado"] + cuenta["pagado_anio"]
        total["vencido"] = total["vencido"] + cuenta["vencido"]
        if cuenta["vencido"] > 0:
            total["estudiantes_en_mora"] = total["estudiantes_en_mora"] + 1
            clave = clave_familia(estudiante_id)
            if clave not in familias:
                familias.append(clave)
    porcentaje = None
    if total["cobrado"] > 0:
        porcentaje = round(total["pagado"] * 100 / total["cobrado"])

    grupos = base_datos.grupos_del_colegio(colegio_id, anio)
    cartera_grupos = []
    for grupo in grupos:
        fila = {"grupo": grupo, "estudiantes": 0, "cobrado": 0, "pagado": 0, "saldo": 0, "vencido": 0, "en_mora": 0}
        for estudiante in base_datos.estudiantes_del_grupo(grupo["id"]):
            fila["estudiantes"] = fila["estudiantes"] + 1
            if estudiante["id"] in por_estudiante:
                cuenta = resumen_cuenta(por_estudiante[estudiante["id"]], anio)
                fila["cobrado"] = fila["cobrado"] + cuenta["cobrado_anio"]
                fila["pagado"] = fila["pagado"] + cuenta["pagado_anio"]
                fila["saldo"] = fila["saldo"] + cuenta["saldo"]
                fila["vencido"] = fila["vencido"] + cuenta["vencido"]
                if cuenta["vencido"] > 0:
                    fila["en_mora"] = fila["en_mora"] + 1
        cartera_grupos.append(fila)

    grupo = None
    buscar = request.args.get("buscar", "").strip()
    if buscar == "":
        grupo = grupo_elegido(request.args.get("grupo", ""), grupos)
        if grupo is None and len(grupos) > 0:
            grupo = grupos[0]
    estudiantes = []
    for estudiante in estudiantes_con_grupo(grupos):
        del_grupo = grupo is not None and estudiante["grupo"]["id"] == grupo["id"]
        coincide = buscar != "" and buscar.lower() in estudiante["nombre"].lower()
        if del_grupo or coincide:
            cobros = []
            if estudiante["id"] in por_estudiante:
                cobros = por_estudiante[estudiante["id"]]
            estudiante["cuenta"] = resumen_cuenta(cobros, anio)
            estudiantes.append(estudiante)

    ultimos = base_datos.consultar(
        "SELECT pagos.*, cobros.descripcion, usuarios.nombre AS estudiante FROM pagos "
        "JOIN cobros ON cobros.id = pagos.cobro_id JOIN usuarios ON usuarios.id = cobros.estudiante_id "
        "WHERE pagos.colegio_id = ? ORDER BY pagos.registrado_en DESC, pagos.id DESC LIMIT 6",
        [colegio_id],
    )

    return render_template("tesoreria_tablero.html", activo="tesoreria", total=total, familias=len(familias),
                           porcentaje=porcentaje, cartera=cartera_grupos, grupos=grupos, grupo=grupo, buscar=buscar,
                           estudiantes=estudiantes, ultimos=ultimos, medios=MEDIOS,
                           puede_configurar=tiene_alguno(g.yo, CONFIGURAN), puede_generar=tiene_rol(g.yo, "tesoreria"),
                           pesos=formato_pesos, fecha_larga=fecha_larga)


@app.route("/tesoreria/conceptos", methods=["GET", "POST"])
def conceptos_de_cobro():
    if not tiene_alguno(g.yo, CONFIGURAN):
        return redirect("/inicio")

    colegio_id = g.colegio["id"]
    anios = [g.colegio["anio"], g.colegio["anio"] + 1]
    errores = []
    mensaje = ""
    advertencia = ""
    valores = valores_vacios_concepto(anios[0])

    editando = buscar_concepto(entero(request.args.get("editar", "")))
    if editando is not None:
        valores = {"concepto_id": editando["id"], "nombre": editando["nombre"], "tipo": editando["tipo"], "anio": editando["anio"],
                   "valor": sin_signo(editando["valor"]), "valor_anterior": "", "activo": editando["activo"] == 1}
        if editando["valor_anio_anterior"] > 0:
            valores["valor_anterior"] = sin_signo(editando["valor_anio_anterior"])

    if request.method == "POST":
        accion = request.form.get("accion", "")
        if accion == "tope":
            anio = entero(request.form.get("anio", ""))
            tope = numero(request.form.get("tope", ""), 0, 100)
            if anio not in anios:
                errores.append("Elige el año del tope.")
            elif tope is None:
                errores.append("El tope debe ser un porcentaje entre 0 y 100, por ejemplo 9,1.")
            else:
                guardar_tope(colegio_id, anio, round(tope, 2))
                registrar("Guardó el tope de aumento", str(anio) + ": " + formato_porcentaje(tope) + " %")
                mensaje = "Tope de aumento para " + str(anio) + " guardado: " + formato_porcentaje(tope) + " %."
        elif accion == "concepto":
            resultado = guardar_concepto(anios)
            errores = resultado["errores"]
            mensaje = resultado["mensaje"]
            if len(errores) > 0:
                valores = {"concepto_id": request.form.get("concepto_id", ""), "nombre": request.form.get("nombre", ""),
                           "tipo": request.form.get("tipo", ""), "anio": entero(request.form.get("anio", "")),
                           "valor": request.form.get("valor", ""), "valor_anterior": request.form.get("valor_anterior", ""),
                           "activo": request.form.get("activo", "") == "1"}
            else:
                editando = None
                valores = valores_vacios_concepto(anios[0])
                if resultado["concepto"]["supera"]:
                    advertencia = texto_advertencia(resultado["concepto"])
        else:
            return redirect("/tesoreria/conceptos")

    lista = base_datos.consultar("SELECT * FROM conceptos_cobro WHERE colegio_id = ? ORDER BY anio DESC, activo DESC, nombre", [colegio_id])
    advertencias = []
    for concepto in lista:
        revisar_aumento(concepto)
        if concepto["supera"] and texto_advertencia(concepto) != advertencia:
            advertencias.append(texto_advertencia(concepto))
    topes = []
    for anio in anios:
        topes.append({"anio": anio, "tope": tope_del_anio(colegio_id, anio)})

    return render_template("tesoreria_conceptos.html", activo="tesoreria", conceptos=lista, valores=valores, editando=editando,
                           tipos=TIPOS, anios=anios, topes=topes, errores=errores, mensaje=mensaje, advertencia=advertencia,
                           advertencias=advertencias, porcentaje=formato_porcentaje, pesos=formato_pesos, fecha_larga=fecha_larga)


@app.route("/tesoreria/generar", methods=["GET", "POST"])
def generar_cobros():
    if not tiene_rol(g.yo, "tesoreria"):
        return redirect("/inicio")

    colegio_id = g.colegio["id"]
    grupos = base_datos.grupos_del_colegio(colegio_id, g.colegio["anio"])
    activos = base_datos.consultar("SELECT * FROM conceptos_cobro WHERE colegio_id = ? AND activo = 1 ORDER BY anio DESC, nombre", [colegio_id])
    errores = []
    mensaje = ""
    valores = {"concepto_id": "", "grupo": "", "descripcion": "", "fecha_limite": ""}

    if request.method == "POST":
        valores = {"concepto_id": request.form.get("concepto_id", ""), "grupo": request.form.get("grupo", ""),
                   "descripcion": request.form.get("descripcion", "").strip(), "fecha_limite": request.form.get("fecha_limite", "").strip()}
        concepto = buscar_concepto(entero(valores["concepto_id"]))
        grupo = None
        if concepto is None or concepto["activo"] != 1:
            errores.append("Elige un concepto de cobro activo de tu colegio.")
        if valores["grupo"] != "todos":
            grupo = grupo_elegido(valores["grupo"], grupos)
            if grupo is None:
                errores.append("Elige un grupo de tu colegio o todo el colegio.")
        if not fecha_valida(valores["fecha_limite"]):
            errores.append("La fecha límite no es válida. Usa el formato AAAA-MM-DD.")
        elif valores["fecha_limite"] < nucleo.hoy():
            errores.append("La fecha límite no puede ser anterior a hoy: el cobro quedaría vencido desde el primer día.")
        if len(valores["descripcion"]) > 120:
            errores.append("La descripción no puede tener más de 120 caracteres.")

        if len(errores) == 0:
            descripcion = valores["descripcion"]
            if descripcion == "":
                descripcion = concepto["nombre"]
            destinos = grupos
            nombre_destino = "todo el colegio"
            if grupo is not None:
                destinos = [grupo]
                nombre_destino = "el grupo " + grupo["nombre"]
            creados = 0
            repetidos = 0
            conexion = base_datos.conectar()
            for destino in destinos:
                for estudiante in base_datos.estudiantes_del_grupo(destino["id"]):
                    existe = conexion.execute(
                        "SELECT id FROM cobros WHERE colegio_id = ? AND concepto_id = ? AND estudiante_id = ? AND fecha_limite = ?",
                        [colegio_id, concepto["id"], estudiante["id"], valores["fecha_limite"]],
                    ).fetchone()
                    if existe is None:
                        conexion.execute(
                            "INSERT INTO cobros (colegio_id, anio, estudiante_id, concepto_id, descripcion, valor, fecha_limite, creado_en) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            [colegio_id, concepto["anio"], estudiante["id"], concepto["id"], descripcion, concepto["valor"],
                             valores["fecha_limite"], nucleo.ahora()],
                        )
                        creados = creados + 1
                    else:
                        repetidos = repetidos + 1
            conexion.commit()
            conexion.close()
            registrar("Generó cobros", descripcion + " para " + nombre_destino + ": " + str(creados) + " nuevos, "
                      + str(repetidos) + " ya existían")
            mensaje = ("Se crearon " + str(creados) + " cobros de «" + descripcion + "» para " + nombre_destino
                       + " por " + formato_pesos(concepto["valor"]) + " cada uno.")
            if repetidos > 0:
                mensaje = mensaje + " " + str(repetidos) + " estudiantes ya tenían ese cobro con la misma fecha límite y no se repitió."
            valores = {"concepto_id": "", "grupo": "", "descripcion": "", "fecha_limite": ""}

    lotes = base_datos.consultar(
        "SELECT cobros.descripcion, cobros.fecha_limite, cobros.valor, conceptos_cobro.nombre AS concepto, COUNT(*) AS cantidad, "
        "MAX(cobros.creado_en) AS creado FROM cobros JOIN conceptos_cobro ON conceptos_cobro.id = cobros.concepto_id "
        "WHERE cobros.colegio_id = ? AND cobros.estado != 'anulado' "
        "GROUP BY cobros.concepto_id, cobros.descripcion, cobros.fecha_limite, cobros.valor ORDER BY creado DESC LIMIT 8",
        [colegio_id],
    )

    return render_template("tesoreria_generar.html", activo="tesoreria", conceptos=activos, grupos=grupos, valores=valores,
                           errores=errores, mensaje=mensaje, lotes=lotes, tipos=TIPOS, hoy=nucleo.hoy(),
                           pesos=formato_pesos, fecha_larga=fecha_larga)


@app.route("/tesoreria/estudiante/<int:estudiante_id>", methods=["GET", "POST"])
def estado_de_cuenta(estudiante_id):
    estudiante = estudiante_del_colegio(estudiante_id)
    if not puede_ver_cuenta(g.yo, estudiante):
        return redirect("/inicio")

    errores = []
    mensaje = ""
    recibo_nuevo = ""
    if request.method == "POST":
        accion = request.form.get("accion", "")
        if accion == "pago" and tiene_rol(g.yo, "tesoreria"):
            resultado = guardar_pago(estudiante)
        elif accion == "descuento" and tiene_alguno(g.yo, AUTORIZAN_DESCUENTOS):
            resultado = guardar_descuento(estudiante)
        elif accion == "anular" and tiene_rol(g.yo, "tesoreria"):
            resultado = anular_cobro(estudiante)
        else:
            return redirect("/inicio")
        errores = resultado["errores"]
        mensaje = resultado["mensaje"]
        recibo_nuevo = resultado["recibo"]

    cobros = cobros_del_estudiante(estudiante_id)
    for cobro in cobros:
        movimientos(cobro)
    cuenta = resumen_cuenta(cobros, g.colegio["anio"])
    anulables = []
    for cobro in cuenta["pendientes"]:
        if cobro["pagado"] == 0:
            anulables.append(cobro)

    return render_template("tesoreria_estudiante.html", activo=pestana_de(g.yo), estudiante=estudiante,
                           grupo=grupo_del_estudiante(estudiante_id), cobros=cobros, cuenta=cuenta, anulables=anulables,
                           acudientes=base_datos.acudientes_de(estudiante_id), errores=errores, mensaje=mensaje,
                           recibo_nuevo=recibo_nuevo, medios=MEDIOS, puede_cobrar=tiene_rol(g.yo, "tesoreria"),
                           puede_descontar=tiene_alguno(g.yo, AUTORIZAN_DESCUENTOS), ve_tesoreria=tiene_alguno(g.yo, VEN_TESORERIA),
                           hoy=nucleo.hoy(), pesos=formato_pesos, fecha_larga=fecha_larga)


@app.route("/tesoreria/recibo/<numero_recibo>")
def recibo_de_pago(numero_recibo):
    if g.yo is None:
        return redirect("/")
    pago = base_datos.consultar_uno(
        "SELECT pagos.*, cobros.estudiante_id, cobros.descripcion, conceptos_cobro.nombre AS concepto, usuarios.nombre AS recibio "
        "FROM pagos JOIN cobros ON cobros.id = pagos.cobro_id JOIN conceptos_cobro ON conceptos_cobro.id = cobros.concepto_id "
        "JOIN usuarios ON usuarios.id = pagos.recibido_por "
        "WHERE pagos.numero_recibo = ? AND pagos.colegio_id = ? AND cobros.colegio_id = ?",
        [numero_recibo, g.colegio["id"], g.colegio["id"]],
    )
    if pago is None:
        return redirect("/inicio")
    estudiante = estudiante_del_colegio(pago["estudiante_id"])
    if not puede_ver_cuenta(g.yo, estudiante):
        return redirect("/inicio")
    return render_template("tesoreria_recibo.html", activo=pestana_de(g.yo), pago=pago, estudiante=estudiante,
                           cobro=buscar_cobro(str(pago["cobro_id"]), estudiante["id"]), grupo=grupo_del_estudiante(estudiante["id"]),
                           medios=MEDIOS, pesos=formato_pesos, fecha_larga=fecha_larga)


def tesorero_del_colegio():
    tesoreros = base_datos.usuarios_con_rol(g.colegio["id"], "tesoreria")
    if len(tesoreros) == 0:
        return None
    return tesoreros[0]


def esta_a_paz_y_salvo(colegio_id, estudiante_id):
    cobros = cobros_completos("WHERE cobros.colegio_id = ? AND cobros.estudiante_id = ?", [colegio_id, estudiante_id], nucleo.hoy())
    for cobro in cobros:
        if cobro["saldo"] > 0:
            return False
    return True


@app.route("/tesoreria/paz-y-salvo/<int:estudiante_id>")
def paz_y_salvo_del_estudiante(estudiante_id):
    estudiante = estudiante_del_colegio(estudiante_id)
    if not puede_ver_cuenta(g.yo, estudiante):
        return redirect("/inicio")
    cuenta = resumen_cuenta(cobros_del_estudiante(estudiante_id), g.colegio["anio"])
    return render_template("tesoreria_paz_y_salvo.html", activo=pestana_de(g.yo), estudiante=estudiante,
                           grupo=grupo_del_estudiante(estudiante_id), cuenta=cuenta, tesorero=tesorero_del_colegio(),
                           hoy=nucleo.hoy(), ve_tesoreria=tiene_alguno(g.yo, VEN_TESORERIA), pesos=formato_pesos, fecha_larga=fecha_larga)


@app.route("/tesoreria/cartera")
def cartera_vencida():
    if not tiene_alguno(g.yo, VEN_TESORERIA):
        return redirect("/inicio")

    grupos = base_datos.grupos_del_colegio(g.colegio["id"], g.colegio["anio"])
    grupo = grupo_elegido(request.args.get("grupo", ""), grupos)
    por_estudiante = cobros_por_estudiante(g.colegio["id"])

    filas = []
    total = 0
    for estudiante in estudiantes_con_grupo(grupos):
        if estudiante["id"] in por_estudiante and (grupo is None or estudiante["grupo"]["id"] == grupo["id"]):
            cuenta = resumen_cuenta(por_estudiante[estudiante["id"]], g.colegio["anio"])
            if cuenta["vencido"] > 0:
                acudientes = base_datos.acudientes_de(estudiante["id"])
                total = total + cuenta["vencido"]
                filas.append({"estudiante": estudiante, "cuenta": cuenta, "acudientes": acudientes,
                              "mensaje": mensaje_recordatorio(estudiante, acudientes, cuenta)})

    return render_template("tesoreria_cartera.html", activo="tesoreria", filas=ordenar_por_mora(filas), grupos=grupos,
                           grupo=grupo, total=total, pesos=formato_pesos, fecha_larga=fecha_larga)


@app.route("/mis-pagos")
def mis_pagos():
    if not tiene_rol(g.yo, "acudiente"):
        return redirect("/inicio")
    hijos = []
    for hijo in base_datos.estudiantes_a_cargo(g.yo["id"]):
        if hijo["colegio_id"] == g.colegio["id"]:
            cobros = cobros_del_estudiante(hijo["id"])
            for cobro in cobros:
                movimientos(cobro)
            hijos.append({"estudiante": hijo, "grupo": grupo_del_estudiante(hijo["id"]), "cobros": cobros,
                          "cuenta": resumen_cuenta(cobros, g.colegio["anio"])})
    return render_template("tesoreria_mis_pagos.html", activo="pagos", hijos=hijos, medios=MEDIOS,
                           pesos=formato_pesos, fecha_larga=fecha_larga)


def crear_cobro_semilla(colegio_id, anio, estudiante_id, concepto_id, descripcion, valor, fecha_limite, creado_en):
    return base_datos.ejecutar(
        "INSERT INTO cobros (colegio_id, anio, estudiante_id, concepto_id, descripcion, valor, fecha_limite, creado_en) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [colegio_id, anio, estudiante_id, concepto_id, descripcion, valor, fecha_limite, creado_en],
    )


def pagar_semilla(colegio_id, anio, cobro_id, valor, fecha, medio, recibido_por, hora):
    referencia = ""
    if medio in PIDEN_REFERENCIA:
        referencia = "Comprobante " + str(cobro_id * 7919 % 900000 + 100000)
    base_datos.ejecutar(
        "INSERT INTO pagos (colegio_id, cobro_id, valor, fecha, medio, referencia, recibido_por, registrado_en, numero_recibo) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [colegio_id, cobro_id, valor, fecha, medio, referencia, recibido_por, fecha + " " + hora, siguiente_recibo(colegio_id, anio)],
    )
    actualizar_estado(cobro_id)


def sembrar_tesoreria():
    colegio = base_datos.buscar_colegio(1)
    if colegio is None or not base_datos.tabla_vacia("conceptos_cobro"):
        return
    melany = base_datos.buscar_usuario("melany.osorio")
    tesorero = base_datos.buscar_usuario("tesoreria")
    rectora = base_datos.buscar_usuario("rectora")
    if melany is None or tesorero is None or rectora is None:
        return
    matricula = base_datos.matricula_activa(melany["id"], colegio["anio"])
    if matricula is None:
        return

    colegio_id = colegio["id"]
    anio = colegio["anio"]
    texto_anio = str(anio)
    base_datos.ejecutar(
        "INSERT INTO conceptos_cobro (colegio_id, anio, nombre, tipo, valor, valor_anio_anterior) VALUES (?, ?, ?, ?, ?, ?)",
        [colegio_id, anio, "Matrícula " + texto_anio, "matricula", 380000, 350000],
    )
    pension_id = base_datos.ejecutar(
        "INSERT INTO conceptos_cobro (colegio_id, anio, nombre, tipo, valor, valor_anio_anterior) VALUES (?, ?, ?, ?, ?, ?)",
        [colegio_id, anio, "Pensión mensual", "pension", 320000, 300000],
    )
    salida_id = base_datos.ejecutar(
        "INSERT INTO conceptos_cobro (colegio_id, anio, nombre, tipo, valor, valor_anio_anterior) VALUES (?, ?, ?, ?, ?, ?)",
        [colegio_id, anio, "Salida pedagógica al Jardín Botánico", "otro", 45000, 0],
    )
    base_datos.ejecutar("INSERT INTO parametros_tesoreria (colegio_id, anio, tope_aumento) VALUES (?, ?, ?)", [colegio_id, anio, 9.1])

    estudiantes = base_datos.estudiantes_del_grupo(matricula["grupo_id"])
    medios = ["transferencia", "efectivo", "pse", "consignacion"]
    sin_pagar_octubre = ["juan.restrepo"]
    sin_pagar_noviembre = ["juan.restrepo", "samuel.ocampo", "jhon.castano"]
    sin_pagar_salida = ["juan.restrepo", "jhon.castano", "laura.patino"]
    abonos_salida = {"sharon.loaiza": 20000}

    for posicion in range(len(estudiantes)):
        estudiante = estudiantes[posicion]
        cobro_id = crear_cobro_semilla(colegio_id, anio, estudiante["id"], pension_id, "Pensión de octubre " + texto_anio, 320000,
                                       texto_anio + "-10-20", texto_anio + "-10-01 07:30")
        if estudiante["usuario"] not in sin_pagar_octubre:
            pagar_semilla(colegio_id, anio, cobro_id, 320000, texto_anio + "-10-" + dos_digitos(5 + posicion),
                          medios[posicion % 4], tesorero["id"], "09:" + dos_digitos(10 + posicion))

    for posicion in range(len(estudiantes)):
        estudiante = estudiantes[posicion]
        cobro_id = crear_cobro_semilla(colegio_id, anio, estudiante["id"], pension_id, "Pensión de noviembre " + texto_anio, 320000,
                                       texto_anio + "-11-20", texto_anio + "-11-01 07:30")
        valor = 320000
        if estudiante["usuario"] == "melany.osorio":
            base_datos.ejecutar(
                "INSERT INTO descuentos (colegio_id, cobro_id, valor, motivo, autorizado_por, fecha) VALUES (?, ?, ?, ?, ?, ?)",
                [colegio_id, cobro_id, 96000, "Beca parcial del 30 % por excelencia académica, aprobada por el Consejo Directivo (Acta 09)",
                 rectora["id"], texto_anio + "-11-02"],
            )
            valor = 224000
        if estudiante["usuario"] not in sin_pagar_noviembre:
            pagar_semilla(colegio_id, anio, cobro_id, valor, texto_anio + "-11-" + dos_digitos(3 + posicion),
                          medios[(posicion + 1) % 4], tesorero["id"], "10:" + dos_digitos(5 + posicion))

    for posicion in range(len(estudiantes)):
        estudiante = estudiantes[posicion]
        cobro_id = crear_cobro_semilla(colegio_id, anio, estudiante["id"], salida_id, "Salida pedagógica al Jardín Botánico", 45000,
                                       texto_anio + "-11-25", texto_anio + "-11-05 08:00")
        if estudiante["usuario"] in abonos_salida:
            pagar_semilla(colegio_id, anio, cobro_id, abonos_salida[estudiante["usuario"]], texto_anio + "-11-12", "efectivo",
                          tesorero["id"], "11:" + dos_digitos(10 + posicion))
        elif estudiante["usuario"] not in sin_pagar_salida:
            pagar_semilla(colegio_id, anio, cobro_id, 45000, texto_anio + "-11-" + dos_digitos(6 + posicion), "efectivo",
                          tesorero["id"], "11:" + dos_digitos(10 + posicion))


if CON_DATOS_DE_EJEMPLO:
    sembrar_tesoreria()
