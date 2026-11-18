import secrets
from flask import g, render_template, request, redirect
from nucleo import (app, agregar_menu, tiene_rol, tiene_alguno, numero, ahora, registrar, promedio, nota_final,
                    desempeno, estudiante_del_colegio, grupo_del_estudiante, DIRECTIVOS, CON_DATOS_DE_EJEMPLO)
import base_datos

LETRAS_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
LARGO_CODIGO = 10
EMITEN = ["secretaria", "administrador", "rector", "coordinador"]
ANULAN = ["secretaria", "rector"]
ROLES_CERTIFICADOS = ["secretaria", "administrador", "rector", "coordinador", "estudiante", "acudiente"]
TIPOS = {
    "constancia_estudio": "Constancia de estudio",
    "notas": "Certificado de notas",
    "servicio_social": "Certificado de servicio social estudiantil",
    "estudios_constitucionales": "Certificado de estudios constitucionales",
}
ORDEN_TIPOS = ["constancia_estudio", "notas", "servicio_social", "estudios_constitucionales"]
HORAS_REQUERIDAS = {"servicio_social": 80, "estudios_constitucionales": 50}
TIPO_DE_HORAS = {"servicio_social": "social", "estudios_constitucionales": "constitucional"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]

TABLAS_CERTIFICADOS = """
CREATE TABLE IF NOT EXISTS certificados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id),
    codigo TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL CHECK (tipo IN ('constancia_estudio', 'servicio_social', 'estudios_constitucionales', 'notas')),
    estudiante_id INTEGER NOT NULL REFERENCES usuarios(id),
    emitido_por INTEGER NOT NULL REFERENCES usuarios(id),
    emitido_en TEXT NOT NULL,
    contenido TEXT NOT NULL,
    anulado INTEGER NOT NULL DEFAULT 0,
    anulado_por INTEGER REFERENCES usuarios(id),
    anulado_en TEXT NOT NULL DEFAULT ''
);
"""

CONSULTA_CERTIFICADOS = (
    "SELECT certificados.*, estudiantes.nombre AS estudiante, emisores.nombre AS emisor, anuladores.nombre AS anulador "
    "FROM certificados JOIN usuarios AS estudiantes ON estudiantes.id = certificados.estudiante_id "
    "JOIN usuarios AS emisores ON emisores.id = certificados.emitido_por "
    "LEFT JOIN usuarios AS anuladores ON anuladores.id = certificados.anulado_por "
)

base_datos.crear_tablas(TABLAS_CERTIFICADOS)

agregar_menu("certificados", "Certificados", "/certificados", ROLES_CERTIFICADOS,
             "Constancias y certificados con código de verificación.")


def entero(texto, minimo, maximo):
    valor = numero(texto, minimo, maximo)
    if valor is None or valor != int(valor):
        return None
    return int(valor)


def tabla_existe(nombre):
    fila = base_datos.consultar_uno("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", [nombre])
    return fila is not None


def nuevo_codigo():
    codigo = ""
    for posicion in range(LARGO_CODIGO):
        codigo = codigo + secrets.choice(LETRAS_CODIGO)
    return codigo


def generar_codigo():
    codigo = nuevo_codigo()
    while base_datos.consultar_uno("SELECT id FROM certificados WHERE codigo = ?", [codigo]) is not None:
        codigo = nuevo_codigo()
    return codigo


def limpiar_codigo(texto):
    limpio = texto.strip().upper().replace(" ", "").replace("-", "")
    return limpio[:40]


def fecha_en_letras(texto):
    if len(texto) < 10:
        return texto
    mes = int(texto[5:7])
    if mes < 1 or mes > 12:
        return texto
    return str(int(texto[8:10])) + " de " + MESES[mes - 1] + " de " + texto[0:4]


def texto_horas(valor):
    if valor == int(valor):
        return str(int(valor))
    return str(round(valor, 1)).replace(".", ",")


def texto_nota(valor):
    if valor is None:
        return "—"
    return str(valor)


def grupo_actual(colegio, estudiante_id):
    matricula = base_datos.matricula_activa(estudiante_id, colegio["anio"])
    if matricula is None:
        return None
    grupo = base_datos.buscar_grupo(matricula["grupo_id"])
    if grupo is None or grupo["colegio_id"] != colegio["id"]:
        return None
    return grupo


def horas_aprobadas(colegio_id, estudiante_id, tipo):
    if not tabla_existe("horas_registradas"):
        return None
    fila = base_datos.consultar_uno(
        "SELECT SUM(horas) AS total FROM horas_registradas WHERE colegio_id = ? AND estudiante_id = ? AND tipo = ? AND estado = 'aprobada'",
        [colegio_id, estudiante_id, TIPO_DE_HORAS[tipo]],
    )
    if fila is None or fila["total"] is None:
        return 0
    return round(fila["total"], 1)


def proyectos_aprobados(colegio_id, estudiante_id):
    if not tabla_existe("proyectos_sociales"):
        return []
    return base_datos.consultar(
        "SELECT DISTINCT proyectos_sociales.nombre, proyectos_sociales.entidad_aliada FROM horas_registradas "
        "JOIN proyectos_sociales ON proyectos_sociales.id = horas_registradas.proyecto_id "
        "WHERE horas_registradas.colegio_id = ? AND horas_registradas.estudiante_id = ? AND horas_registradas.tipo = 'social' "
        "AND horas_registradas.estado = 'aprobada' ORDER BY proyectos_sociales.nombre",
        [colegio_id, estudiante_id],
    )


def identificacion(estudiante):
    if estudiante["documento"].strip() == "":
        return ""
    return ", identificado(a) con documento número " + estudiante["documento"].strip()


def descripcion_grupo(grupo):
    return "el grado " + grupo["grado"] + ", grupo " + grupo["nombre"]


def escala_del_colegio(colegio):
    return ("Escala de valoración (Decreto 1290 de 2009): Superior desde " + str(colegio["limite_superior"])
            + ", Alto desde " + str(colegio["limite_alto"]) + ", Básico desde " + str(colegio["limite_basico"])
            + " y Bajo por debajo de " + str(colegio["limite_basico"]) + ", sobre " + str(colegio["nota_maxima"]) + ".")


def armar_contenido(colegio, estudiante, tipo, fecha):
    grupo = grupo_actual(colegio, estudiante["id"])
    anio = str(colegio["anio"])
    quien = "Que " + estudiante["nombre"] + identificacion(estudiante)
    if tipo not in TIPOS:
        return {"error": "Ese tipo de certificado no existe.", "texto": ""}

    if tipo == "constancia_estudio" or tipo == "notas":
        if grupo is None:
            return {"error": estudiante["nombre"] + " no tiene matrícula activa en " + anio + ".", "texto": ""}

    if tipo == "constancia_estudio":
        lineas = [
            quien + ", se encuentra matriculado(a) en esta institución educativa en " + descripcion_grupo(grupo)
            + ", sede " + grupo["sede"] + ", jornada " + grupo["jornada"].lower() + ", para el año lectivo " + anio + ".",
            "La presente constancia se expide a solicitud del interesado.",
        ]
        return {"error": "", "texto": "\n".join(lineas)}

    if tipo == "notas":
        periodos = base_datos.periodos_del_anio(colegio["id"], colegio["anio"])
        todas = base_datos.notas_del_estudiante(estudiante["id"], colegio["anio"], len(periodos))
        lineas = [quien + ", cursa en esta institución educativa " + descripcion_grupo(grupo) + " en el año lectivo " + anio
                  + " y, con corte al " + fecha_en_letras(fecha) + ", obtuvo las siguientes valoraciones finales:"]
        finales = []
        for asignacion in base_datos.asignaciones_del_grupo(grupo["id"]):
            final = None
            if asignacion["materia_id"] in todas:
                final = nota_final(todas[asignacion["materia_id"]], periodos)
            finales.append(final)
            lineas.append(asignacion["materia"] + " | " + texto_nota(final) + " | " + desempeno(final))
        general = promedio(finales)
        lineas.append("Promedio general | " + texto_nota(general) + " | " + desempeno(general))
        lineas.append(escala_del_colegio(colegio))
        return {"error": "", "texto": "\n".join(lineas)}

    total = horas_aprobadas(colegio["id"], estudiante["id"], tipo)
    requeridas = HORAS_REQUERIDAS[tipo]
    if total is None:
        return {"error": "El módulo de horas sociales todavía no está disponible.", "texto": ""}
    if total < requeridas:
        return {"error": estudiante["nombre"] + " lleva " + texto_horas(total) + " de " + str(requeridas)
                + " horas aprobadas: todavía no cumple el requisito.", "texto": ""}
    donde = ""
    if grupo is not None:
        donde = ", estudiante del grado " + grupo["grado"] + ", grupo " + grupo["nombre"] + ", en " + anio

    if tipo == "servicio_social":
        nombres = []
        for proyecto in proyectos_aprobados(colegio["id"], estudiante["id"]):
            if proyecto["entidad_aliada"] != "":
                nombres.append("\"" + proyecto["nombre"] + "\" con " + proyecto["entidad_aliada"])
            else:
                nombres.append("\"" + proyecto["nombre"] + "\"")
        primera = (quien + donde + ", prestó " + texto_horas(total)
                   + " horas de servicio social estudiantil obligatorio, aprobadas por la institución")
        if len(nombres) == 1:
            primera = primera + ", en el proyecto pedagógico " + nombres[0]
        elif len(nombres) > 1:
            primera = primera + ", en los proyectos pedagógicos " + "; ".join(nombres)
        lineas = [
            primera + ".",
            "Con ello cumple la intensidad mínima de " + str(requeridas) + " horas exigida por la Resolución 4210 de 1996 "
            "del Ministerio de Educación Nacional, requisito para obtener el título de bachiller.",
        ]
        return {"error": "", "texto": "\n".join(lineas)}

    lineas = [
        quien + donde + ", cursó y aprobó " + texto_horas(total) + " horas de estudios constitucionales en esta institución educativa.",
        "Con ello cumple las " + str(requeridas) + " horas de estudios constitucionales que exige la Ley 107 de 1994 "
        "para obtener el título de bachiller.",
    ]
    return {"error": "", "texto": "\n".join(lineas)}


def guardar_certificado(colegio_id, tipo, estudiante_id, emisor_id, fecha, contenido):
    codigo = generar_codigo()
    base_datos.ejecutar(
        "INSERT INTO certificados (colegio_id, codigo, tipo, estudiante_id, emitido_por, emitido_en, contenido) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [colegio_id, codigo, tipo, estudiante_id, emisor_id, fecha, contenido],
    )
    return codigo


def es_acudiente_de(yo, estudiante_id):
    if not tiene_rol(yo, "acudiente"):
        return False
    for hijo in base_datos.estudiantes_a_cargo(yo["id"]):
        if hijo["id"] == estudiante_id:
            return True
    return False


def puede_emitir(yo, estudiante, tipo):
    if yo is None or estudiante is None or estudiante["colegio_id"] != yo["colegio_id"]:
        return False
    if tiene_alguno(yo, EMITEN):
        return True
    if tipo != "constancia_estudio":
        return False
    if tiene_rol(yo, "estudiante") and yo["id"] == estudiante["id"]:
        return True
    return es_acudiente_de(yo, estudiante["id"])


def puede_ver_certificado(yo, certificado):
    if yo is None or certificado is None or certificado["colegio_id"] != yo["colegio_id"]:
        return False
    if tiene_alguno(yo, DIRECTIVOS + ["secretaria"]):
        return True
    if certificado["emitido_por"] == yo["id"] or certificado["estudiante_id"] == yo["id"]:
        return True
    return es_acudiente_de(yo, certificado["estudiante_id"])


def completar(certificado):
    certificado["titulo"] = TIPOS[certificado["tipo"]]
    certificado["fecha"] = fecha_en_letras(certificado["emitido_en"])
    return certificado


def buscar_certificado(codigo):
    certificado = base_datos.consultar_uno(CONSULTA_CERTIFICADOS + "WHERE certificados.codigo = ?", [codigo])
    if certificado is None:
        return None
    return completar(certificado)


def buscar_certificado_por_id(certificado_id):
    if certificado_id is None:
        return None
    return base_datos.consultar_uno(
        CONSULTA_CERTIFICADOS + "WHERE certificados.id = ? AND certificados.colegio_id = ?",
        [certificado_id, g.colegio["id"]],
    )


def certificados_de(estudiante_id):
    lista = []
    filas = base_datos.consultar(
        CONSULTA_CERTIFICADOS + "WHERE certificados.colegio_id = ? AND certificados.estudiante_id = ? ORDER BY certificados.id DESC",
        [g.colegio["id"], estudiante_id],
    )
    for certificado in filas:
        lista.append(completar(certificado))
    return lista


def ultimos_certificados():
    lista = []
    filas = base_datos.consultar(
        CONSULTA_CERTIFICADOS + "WHERE certificados.colegio_id = ? ORDER BY certificados.id DESC LIMIT 20",
        [g.colegio["id"]],
    )
    for certificado in filas:
        lista.append(completar(certificado))
    return lista


def buscar_estudiantes(texto):
    patron = "%" + texto[:60] + "%"
    personas = base_datos.consultar(
        "SELECT usuarios.id, usuarios.nombre, usuarios.usuario, usuarios.documento FROM usuarios "
        "JOIN roles_usuario ON roles_usuario.usuario_id = usuarios.id "
        "WHERE usuarios.colegio_id = ? AND roles_usuario.rol = 'estudiante' "
        "AND (usuarios.nombre LIKE ? OR usuarios.documento LIKE ? OR usuarios.usuario LIKE ?) "
        "ORDER BY usuarios.nombre LIMIT 30",
        [g.colegio["id"], patron, patron, patron],
    )
    for persona in personas:
        persona["grupo"] = grupo_del_estudiante(persona["id"])
    return personas


def opciones_para(estudiante):
    grupo = grupo_actual(g.colegio, estudiante["id"])
    anio = str(g.colegio["anio"])
    opciones = []
    for tipo in ORDEN_TIPOS:
        opcion = {"tipo": tipo, "titulo": TIPOS[tipo], "disponible": True, "detalle": ""}
        if tipo in HORAS_REQUERIDAS:
            total = horas_aprobadas(g.colegio["id"], estudiante["id"], tipo)
            if total is None:
                opcion = None
            elif total < HORAS_REQUERIDAS[tipo]:
                opcion["disponible"] = False
                opcion["detalle"] = "Lleva " + texto_horas(total) + " de " + str(HORAS_REQUERIDAS[tipo]) + " horas aprobadas."
            else:
                opcion["detalle"] = texto_horas(total) + " horas aprobadas. Requisito cumplido."
        elif grupo is None:
            opcion["disponible"] = False
            opcion["detalle"] = "Sin matrícula activa en " + anio + "."
        else:
            opcion["detalle"] = "Grupo " + grupo["nombre"] + " · año " + anio
        if opcion is not None:
            opciones.append(opcion)
    return opciones


def ficha_familiar(estudiante):
    return {"estudiante": estudiante, "grupo": grupo_del_estudiante(estudiante["id"]), "certificados": certificados_de(estudiante["id"])}


def firma_rector(colegio_id):
    fila = base_datos.consultar_uno(
        "SELECT usuarios.nombre FROM usuarios JOIN roles_usuario ON roles_usuario.usuario_id = usuarios.id "
        "WHERE usuarios.colegio_id = ? AND roles_usuario.rol = 'rector' AND usuarios.activo = 1 ORDER BY usuarios.id LIMIT 1",
        [colegio_id],
    )
    if fila is None:
        return ""
    return fila["nombre"]


def dividir_contenido(texto):
    partes = {"antes": [], "filas": [], "despues": []}
    for linea in texto.split("\n"):
        linea = linea.strip()
        if linea != "":
            if " | " in linea:
                partes["filas"].append(linea.split(" | "))
            elif len(partes["filas"]) == 0:
                partes["antes"].append(linea)
            else:
                partes["despues"].append(linea)
    return partes


@app.route("/certificados", methods=["GET", "POST"])
def certificados_panel():
    if not tiene_alguno(g.yo, ROLES_CERTIFICADOS):
        return redirect("/inicio")

    emite = tiene_alguno(g.yo, EMITEN)
    anula = tiene_alguno(g.yo, ANULAN)
    errores = []
    mensaje = ""
    elegido_id = entero(request.args.get("estudiante", ""), 1, 1000000000)
    if request.method == "POST":
        accion = request.form.get("accion", "")
        if accion == "emitir":
            tipo = request.form.get("tipo", "")
            estudiante = estudiante_del_colegio(entero(request.form.get("estudiante_id", ""), 1, 1000000000))
            if tipo not in TIPOS or estudiante is None:
                errores.append("Elige un estudiante de este colegio y un tipo de certificado válido.")
            elif not puede_emitir(g.yo, estudiante, tipo):
                return redirect("/inicio")
            else:
                elegido_id = estudiante["id"]
                fecha = ahora()
                armado = armar_contenido(g.colegio, estudiante, tipo, fecha)
                if armado["error"] != "":
                    errores.append(armado["error"])
                else:
                    codigo = guardar_certificado(g.colegio["id"], tipo, estudiante["id"], g.yo["id"], fecha, armado["texto"])
                    registrar("Emitió certificado", TIPOS[tipo] + " de " + estudiante["nombre"] + " · código " + codigo)
                    return redirect("/certificados/" + codigo)
        elif accion == "anular":
            if not anula:
                return redirect("/inicio")
            certificado = buscar_certificado_por_id(entero(request.form.get("certificado_id", ""), 1, 1000000000))
            if certificado is None:
                return redirect("/inicio")
            if certificado["anulado"] == 1:
                errores.append("El certificado " + certificado["codigo"] + " ya estaba anulado.")
            else:
                base_datos.ejecutar(
                    "UPDATE certificados SET anulado = 1, anulado_por = ?, anulado_en = ? WHERE id = ? AND colegio_id = ?",
                    [g.yo["id"], ahora(), certificado["id"], g.colegio["id"]],
                )
                registrar("Anuló certificado", TIPOS[certificado["tipo"]] + " de " + certificado["estudiante"] + " · código " + certificado["codigo"])
                mensaje = "Certificado " + certificado["codigo"] + " anulado. Desde ahora aparece como anulado al verificarlo."

    buscar = request.args.get("buscar", "").strip()
    resultados = []
    seleccionado = None
    ultimos = []
    if emite:
        if buscar != "":
            resultados = buscar_estudiantes(buscar)
        elegido = estudiante_del_colegio(elegido_id)
        if elegido is not None:
            seleccionado = {"estudiante": elegido, "grupo": grupo_del_estudiante(elegido["id"]),
                            "opciones": opciones_para(elegido), "certificados": certificados_de(elegido["id"])}
        ultimos = ultimos_certificados()
    propios = None
    if tiene_rol(g.yo, "estudiante"):
        propios = ficha_familiar(g.yo)
    hijos = []
    if tiene_rol(g.yo, "acudiente"):
        for hijo in base_datos.estudiantes_a_cargo(g.yo["id"]):
            if hijo["colegio_id"] == g.colegio["id"]:
                hijos.append(ficha_familiar(hijo))

    return render_template("certificados.html", activo="certificados", emite=emite, anula=anula, buscar=buscar,
                           resultados=resultados, seleccionado=seleccionado, ultimos=ultimos, propios=propios,
                           hijos=hijos, errores=errores, mensaje=mensaje)


@app.route("/certificados/<codigo>")
def certificados_ver(codigo):
    if g.yo is None:
        return redirect("/")
    certificado = buscar_certificado(limpiar_codigo(codigo))
    if not puede_ver_certificado(g.yo, certificado):
        return redirect("/inicio")

    verbo = "certifica"
    if certificado["tipo"] == "constancia_estudio":
        verbo = "hace constar"
    anulado_en = ""
    if certificado["anulado"] == 1:
        anulado_en = fecha_en_letras(certificado["anulado_en"])

    return render_template("certificados_ver.html", activo="certificados", certificado=certificado,
                           partes=dividir_contenido(certificado["contenido"]), verbo=verbo,
                           rector=firma_rector(g.colegio["id"]), anulado_en=anulado_en,
                           enlace_verificar=request.url_root + "verificar")


@app.route("/verificar", methods=["GET", "POST"])
def certificados_verificar():
    codigo = request.args.get("codigo", "")
    if request.method == "POST":
        codigo = request.form.get("codigo", "")
    codigo = limpiar_codigo(codigo)
    estado = ""
    datos = {}
    if codigo != "":
        certificado = buscar_certificado(codigo)
        if certificado is None:
            estado = "inexistente"
        elif certificado["anulado"] == 1:
            estado = "anulado"
            datos = {"anulado_en": fecha_en_letras(certificado["anulado_en"])}
        else:
            estado = "valido"
            colegio = base_datos.buscar_colegio(certificado["colegio_id"])
            datos = {"tipo": certificado["titulo"], "estudiante": certificado["estudiante"], "colegio": colegio["nombre"],
                     "lugar": colegio["municipio"] + ", " + colegio["departamento"], "fecha": certificado["fecha"]}

    return render_template("certificados_verificar.html", activo="", codigo=codigo, estado=estado, datos=datos,
                           largo=LARGO_CODIGO)


def sembrar_certificados():
    if not base_datos.tabla_vacia("certificados"):
        return
    colegio = base_datos.buscar_colegio(1)
    if colegio is None:
        return
    secretaria = base_datos.buscar_usuario("secretaria")
    melany = base_datos.buscar_usuario("melany.osorio")
    luisa = base_datos.buscar_usuario("luisa.montoya")
    if secretaria is None or melany is None or luisa is None:
        return
    armado = armar_contenido(colegio, melany, "constancia_estudio", "2026-11-10 08:40")
    if armado["error"] == "":
        guardar_certificado(colegio["id"], "constancia_estudio", melany["id"], secretaria["id"], "2026-11-10 08:40", armado["texto"])
    armado = armar_contenido(colegio, luisa, "servicio_social", "2026-11-12 10:15")
    if armado["error"] == "":
        guardar_certificado(colegio["id"], "servicio_social", luisa["id"], secretaria["id"], "2026-11-12 10:15", armado["texto"])


if CON_DATOS_DE_EJEMPLO:
    sembrar_certificados()
