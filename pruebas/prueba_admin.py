import ayuda
from ayuda import entrar, revisar, destino
import modulo_inicio
import modulo_notas
import modulo_admin
import base_datos
from werkzeug.security import generate_password_hash, check_password_hash
from nucleo import hoy

PAGINAS = ["/admin", "/admin/colegio", "/admin/sedes", "/admin/periodos", "/admin/materias", "/admin/grupos",
           "/admin/grupos/1", "/admin/usuarios", "/admin/usuarios/nuevo", "/admin/usuarios/13", "/admin/cargue",
           "/admin/registro"]


def revisar_acceso(nombre, cliente, permitidas):
    bien = True
    for pagina in PAGINAS:
        respuesta = cliente.get(pagina)
        if pagina in permitidas:
            if respuesta.status_code != 200:
                print("    " + nombre + " no pudo abrir " + pagina)
                bien = False
        elif destino(respuesta) != "/inicio":
            print("    " + nombre + " pudo abrir " + pagina)
            bien = False
    revisar(nombre + " solo abre las páginas que le tocan", bien)


def texto(respuesta):
    return respuesta.get_data(as_text=True)


def clave_en(html):
    marca = 'class="clave-temporal">'
    inicio = html.find(marca)
    if inicio == -1:
        return ""
    inicio = inicio + len(marca)
    return html[inicio:html.find("<", inicio)]


def matricula_de(estudiante_id):
    return base_datos.matricula_activa(estudiante_id, 2026)


def formulario_periodos(cambios):
    formulario = {"accion": "guardar"}
    for periodo in base_datos.periodos_del_anio(1, 2026):
        clave = str(periodo["id"])
        formulario["nombre-" + clave] = periodo["nombre"]
        formulario["inicio-" + clave] = periodo["fecha_inicio"]
        formulario["fin-" + clave] = periodo["fecha_fin"]
        formulario["porcentaje-" + clave] = str(periodo["porcentaje"])
        if periodo["abierto"] == 1:
            formulario["abierto-" + clave] = "1"
    for campo in cambios:
        formulario[campo] = cambios[campo]
    return formulario


def formulario_asignaciones(grupo_id, cambios):
    formulario = {"accion": "asignaciones"}
    actuales = {}
    for asignacion in base_datos.asignaciones_del_grupo(grupo_id):
        actuales[asignacion["materia_id"]] = asignacion
    for materia in base_datos.materias_del_colegio(1):
        clave = str(materia["id"])
        formulario["docente-" + clave] = ""
        formulario["horas-" + clave] = ""
        if materia["id"] in actuales:
            formulario["docente-" + clave] = str(actuales[materia["id"]]["docente_id"])
            formulario["horas-" + clave] = str(actuales[materia["id"]]["horas_semana"])
    for campo in cambios:
        formulario[campo] = cambios[campo]
    return formulario


def datos_persona(persona_id, cambios):
    persona = base_datos.buscar_usuario_por_id(persona_id)
    formulario = {"accion": "datos", "nombre": persona["nombre"], "documento": persona["documento"],
                  "correo": persona["correo"], "telefono": persona["telefono"], "roles": base_datos.roles_de(persona_id)}
    for campo in cambios:
        formulario[campo] = cambios[campo]
    return formulario


def asignacion(grupo_id, materia_id):
    return base_datos.consultar_uno("SELECT * FROM asignaciones WHERE grupo_id = ? AND materia_id = ?", [grupo_id, materia_id])


print("Otro colegio de prueba")
clave_cifrada = generate_password_hash("pijao2026")
vecino = base_datos.ejecutar("INSERT INTO colegios (nombre, nombre_corto, municipio, departamento, anio) VALUES (?, ?, ?, ?, ?)",
                             ["Colegio Vecino de Génova", "Colegio Vecino", "Génova", "Quindío", 2026])
sede_vecina = base_datos.ejecutar("INSERT INTO sedes (colegio_id, nombre, jornada) VALUES (?, ?, ?)", [vecino, "Sede Vecina", "Mañana"])
grado_vecino = base_datos.ejecutar("INSERT INTO grados (colegio_id, nombre, nivel, orden) VALUES (?, ?, ?, ?)",
                                   [vecino, "Sexto", "Básica secundaria", 6])
grupo_vecino = base_datos.ejecutar("INSERT INTO grupos (colegio_id, anio, grado_id, sede_id, nombre) VALUES (?, ?, ?, ?, ?)",
                                   [vecino, 2026, grado_vecino, sede_vecina, "6-Z"])
estudiante_vecino = base_datos.ejecutar("INSERT INTO usuarios (colegio_id, usuario, clave, nombre, documento) VALUES (?, ?, ?, ?, ?)",
                                        [vecino, "pedro.vecino", clave_cifrada, "Pedro Vecino Lejano", "99887766"])
base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [estudiante_vecino, "estudiante"])
admin_vecino = base_datos.ejecutar("INSERT INTO usuarios (colegio_id, usuario, clave, nombre) VALUES (?, ?, ?, ?)",
                                   [vecino, "admin.vecino", clave_cifrada, "Administradora Vecina"])
base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [admin_vecino, "administrador"])
materia_vecina = base_datos.ejecutar("INSERT INTO materias (colegio_id, nombre, corto, area) VALUES (?, ?, ?, ?)",
                                     [vecino, "Química Vecina", "Quim", "Ciencias"])
base_datos.ejecutar("INSERT INTO registro_accesos (colegio_id, usuario_id, fecha, accion, detalle) VALUES (?, ?, ?, ?, ?)",
                    [vecino, admin_vecino, "2026-11-17 08:00", "Acción secreta del vecino", ""])
revisar("se creó un segundo colegio para las pruebas", vecino != 1)

print("Funciones de apoyo")
revisar("quita tildes y eñes del usuario", modulo_admin.generar_usuario("Ñoño Álvarez") == "nono.alvarez")
revisar("con 4 palabras toma la tercera como apellido", modulo_admin.generar_usuario("Ana María Peña Gómez") == "ana.pena")
revisar("con 3 palabras toma la última", modulo_admin.generar_usuario("Melany Osorio Cárdenas") == "melany.cardenas")
revisar("si el usuario existe le agrega un número", modulo_admin.generar_usuario("Juan Pablo Restrepo") == "juan.restrepo2")
clave = modulo_admin.clave_temporal()
confusas = 0
for letra in clave:
    if letra in "0Ol1I":
        confusas = confusas + 1
revisar("la clave temporal tiene 8 caracteres sin letras confusas", len(clave) == 8 and confusas == 0)
revisar("acepta una fecha válida", modulo_admin.fecha_valida("2026-11-17"))
revisar("acepta el 29 de febrero en año bisiesto", modulo_admin.fecha_valida("2028-02-29"))
revisar("rechaza el 29 de febrero en año no bisiesto", not modulo_admin.fecha_valida("2026-02-29"))
revisar("rechaza fechas con otro formato", not modulo_admin.fecha_valida("17/11/2026") and not modulo_admin.fecha_valida("2026-13-01"))

print("Permisos por rol")
admin = entrar("admin")
coordinadora = entrar("coordinadora")
secretaria = entrar("secretaria")
rectora = entrar("rectora")
revisar_acceso("la administradora", admin, PAGINAS)
revisar_acceso("la coordinadora", coordinadora, ["/admin", "/admin/periodos", "/admin/materias", "/admin/grupos", "/admin/grupos/1"])
revisar_acceso("la secretaria", secretaria, ["/admin", "/admin/grupos", "/admin/grupos/1", "/admin/usuarios", "/admin/usuarios/nuevo",
                                             "/admin/usuarios/13", "/admin/cargue"])
revisar_acceso("la rectora", rectora, ["/admin/registro"])
revisar_acceso("la docente", entrar("c.munoz"), [])
revisar_acceso("el director de grupo", entrar("h.aguirre"), [])
revisar_acceso("la estudiante", entrar("melany.osorio"), [])
revisar_acceso("la acudiente", entrar("gloria.cardenas"), [])
revisar_acceso("la orientadora", entrar("orientadora"), [])
revisar_acceso("quien no ha entrado", ayuda.app.test_client(), [])
html = texto(secretaria.get("/admin"))
revisar("el tablero de la secretaria no muestra períodos ni datos del colegio",
        'href="/admin/periodos"' not in html and 'href="/admin/colegio"' not in html and 'href="/admin/cargue"' in html)
html = texto(coordinadora.get("/admin"))
revisar("el tablero de la coordinadora no muestra usuarios", 'href="/admin/usuarios"' not in html and 'href="/admin/materias"' in html)
revisar("la administración aparece en el menú de la secretaria", 'href="/admin"' in texto(secretaria.get("/inicio")))
revisar("la administración no aparece en el menú de la rectora", 'href="/admin"' not in texto(rectora.get("/inicio")))

print("Datos del colegio")
escala_buena = {"nombre": "Institución Educativa Instituto Pijao", "nombre_corto": "I.E. Instituto Pijao", "municipio": "Pijao",
                "departamento": "Quindío", "codigo_dane": "163548000123", "lema": "Lema nuevo de prueba",
                "nota_minima": "1", "limite_basico": "3", "limite_alto": "4", "limite_superior": "4,6", "nota_maxima": "5",
                "anio": "2030"}
mala = {}
for campo in escala_buena:
    mala[campo] = escala_buena[campo]
mala["limite_basico"] = "4.5"
respuesta = admin.post("/admin/colegio", data=mala)
revisar("rechaza una escala desordenada", "La escala debe cumplir" in texto(respuesta))
revisar("la escala desordenada no se guarda", base_datos.buscar_colegio(1)["limite_basico"] == 3.0)
mala["limite_basico"] = "3"
mala["codigo_dane"] = "123"
revisar("rechaza un código DANE incompleto", "12 dígitos" in texto(admin.post("/admin/colegio", data=mala)))
respuesta = admin.post("/admin/colegio", data=escala_buena)
colegio = base_datos.buscar_colegio(1)
revisar("guarda los datos del colegio", "Datos del colegio guardados" in texto(respuesta) and colegio["lema"] == "Lema nuevo de prueba")
revisar("guarda la escala con coma decimal", colegio["limite_superior"] == 4.6)
revisar("el año no cambia desde esta página", colegio["anio"] == 2026)
revisar("la coordinadora no puede cambiar el colegio", destino(coordinadora.post("/admin/colegio", data=escala_buena)) == "/inicio")

print("Sedes")
admin.post("/admin/sedes", data={"accion": "crear", "nombre": "Sede Rural La Mina", "jornada": "Tarde"})
sede_nueva = base_datos.consultar_uno("SELECT * FROM sedes WHERE nombre = 'Sede Rural La Mina'", [])
revisar("crea una sede", sede_nueva is not None and sede_nueva["colegio_id"] == 1 and sede_nueva["jornada"] == "Tarde")
respuesta = admin.post("/admin/sedes", data={"accion": "crear", "nombre": "Sede Norte", "jornada": "Siempre"})
revisar("rechaza una jornada que no está en la lista", "Elige una jornada" in texto(respuesta))
respuesta = admin.post("/admin/sedes", data={"accion": "crear", "nombre": "Sede Rural La Mina", "jornada": "Tarde"})
revisar("no repite una sede con la misma jornada", "Ya existe la sede" in texto(respuesta))
admin.post("/admin/sedes", data={"accion": "editar", "sede_id": str(sede_nueva["id"]), "nombre": "Sede La Mina", "jornada": "Única"})
revisar("edita una sede", base_datos.consultar_uno("SELECT * FROM sedes WHERE id = ?", [sede_nueva["id"]])["jornada"] == "Única")
admin.post("/admin/sedes", data={"accion": "editar", "sede_id": str(sede_vecina), "nombre": "Sede Cambiada", "jornada": "Tarde"})
revisar("no edita la sede de otro colegio",
        base_datos.consultar_uno("SELECT * FROM sedes WHERE id = ?", [sede_vecina])["nombre"] == "Sede Vecina")

print("Períodos")
respuesta = coordinadora.post("/admin/periodos", data=formulario_periodos({"porcentaje-1": "30"}))
revisar("los porcentajes deben sumar 100", "deben sumar 100" in texto(respuesta))
respuesta = coordinadora.post("/admin/periodos", data=formulario_periodos({"inicio-2": "2026-02-30"}))
revisar("rechaza una fecha que no existe", "fechas válidas" in texto(respuesta))
respuesta = coordinadora.post("/admin/periodos", data=formulario_periodos({"fin-3": "2026-07-01"}))
revisar("rechaza un inicio después del fin", "no puede ser después" in texto(respuesta))
respuesta = coordinadora.post("/admin/periodos", data=formulario_periodos({"inicio-2": "2026-04-01"}))
revisar("rechaza períodos que se cruzan", "después de que termine" in texto(respuesta))
revisar("con errores no se guarda nada", base_datos.periodos_del_anio(1, 2026)[0]["porcentaje"] == 25)
cambios = {"porcentaje-1": "20", "porcentaje-4": "30", "nombre-1": "Primer período ajustado"}
respuesta = coordinadora.post("/admin/periodos", data=formulario_periodos(cambios))
periodos = base_datos.periodos_del_anio(1, 2026)
revisar("guarda nombres y porcentajes", "Períodos guardados" in texto(respuesta) and periodos[0]["nombre"] == "Primer período ajustado"
        and periodos[3]["porcentaje"] == 30)
formulario = formulario_periodos({})
formulario.pop("abierto-4")
coordinadora.post("/admin/periodos", data=formulario)
revisar("cierra un período", base_datos.periodos_del_anio(1, 2026)[3]["abierto"] == 0)
coordinadora.post("/admin/periodos", data=formulario_periodos({"abierto-4": "1"}))
revisar("vuelve a abrir un período", base_datos.periodos_del_anio(1, 2026)[3]["abierto"] == 1)
coordinadora.post("/admin/periodos", data={"accion": "agregar"})
periodos = base_datos.periodos_del_anio(1, 2026)
revisar("agrega un período al final con 0 %", len(periodos) == 5 and periodos[4]["porcentaje"] == 0
        and periodos[4]["fecha_inicio"] == "2026-11-28")
coordinadora.post("/admin/periodos", data={"accion": "quitar"})
revisar("quita el último período si no tiene notas", len(base_datos.periodos_del_anio(1, 2026)) == 4)
respuesta = coordinadora.post("/admin/periodos", data={"accion": "quitar"})
revisar("no quita un período que ya tiene notas", "ya tiene notas" in texto(respuesta) and len(base_datos.periodos_del_anio(1, 2026)) == 4)
revisar("la secretaria no cambia períodos", destino(secretaria.post("/admin/periodos", data={"accion": "agregar"})) == "/inicio")

print("Materias")
coordinadora.post("/admin/materias", data={"accion": "crear", "nombre": "Ética y Valores", "corto": "Ética", "area": "Ética"})
etica = base_datos.consultar_uno("SELECT * FROM materias WHERE nombre = 'Ética y Valores'", [])
revisar("crea una materia", etica is not None and etica["colegio_id"] == 1)
respuesta = coordinadora.post("/admin/materias", data={"accion": "crear", "nombre": "matematicas", "corto": "Mat2", "area": ""})
revisar("no repite una materia aunque cambien las tildes", "Ya existe la materia" in texto(respuesta))
respuesta = coordinadora.post("/admin/materias", data={"accion": "crear", "nombre": "", "corto": "", "area": ""})
revisar("pide nombre y nombre corto", "Escribe el nombre de la materia" in texto(respuesta) and "nombre corto" in texto(respuesta))
coordinadora.post("/admin/materias", data={"accion": "editar", "materia_id": str(etica["id"]), "nombre": "Ética", "corto": "Étic",
                                           "area": "Educación ética"})
revisar("edita una materia", base_datos.consultar_uno("SELECT * FROM materias WHERE id = ?", [etica["id"]])["corto"] == "Étic")
coordinadora.post("/admin/materias", data={"accion": "editar", "materia_id": str(materia_vecina), "nombre": "Robada", "corto": "Rob",
                                           "area": ""})
revisar("no edita la materia de otro colegio",
        base_datos.consultar_uno("SELECT * FROM materias WHERE id = ?", [materia_vecina])["nombre"] == "Química Vecina")

print("Grupos")
nuevo_grupo = {"accion": "crear", "grado_id": "7", "sede_id": "1", "nombre": "6-A", "director_id": "9"}
revisar("la secretaria no crea grupos", destino(secretaria.post("/admin/grupos", data=nuevo_grupo)) == "/inicio")
coordinadora.post("/admin/grupos", data=nuevo_grupo)
grupo_6a = base_datos.consultar_uno("SELECT * FROM grupos WHERE nombre = '6-A' AND colegio_id = 1", [])
revisar("la coordinadora crea un grupo", grupo_6a is not None and grupo_6a["director_id"] == 9 and grupo_6a["anio"] == 2026)
respuesta = coordinadora.post("/admin/grupos", data={"accion": "crear", "grado_id": "11", "sede_id": "1", "nombre": "10 - a",
                                                     "director_id": ""})
revisar("no repite el nombre de un grupo", "Ya existe el grupo 10-A" in texto(respuesta))
respuesta = coordinadora.post("/admin/grupos", data={"accion": "crear", "grado_id": "7", "sede_id": "1", "nombre": "6-B",
                                                     "director_id": "13"})
revisar("el director debe ser docente", "docente activo" in texto(respuesta))
respuesta = coordinadora.post("/admin/grupos", data={"accion": "crear", "grado_id": str(grado_vecino), "sede_id": str(sede_vecina),
                                                     "nombre": "6-C", "director_id": ""})
revisar("no usa grados ni sedes de otro colegio", "Elige un grado" in texto(respuesta) and "Elige una sede" in texto(respuesta))
revisar("la secretaria ve la lista de grupos", "6-A" in texto(secretaria.get("/admin/grupos")))
grupo_6a_id = grupo_6a["id"]
ruta_6a = "/admin/grupos/" + str(grupo_6a_id)
coordinadora.post(ruta_6a, data={"accion": "datos", "nombre": "6-A", "sede_id": str(sede_nueva["id"]), "director_id": "6"})
grupo_6a = base_datos.buscar_grupo(grupo_6a_id)
revisar("edita sede y director del grupo", grupo_6a["sede_id"] == sede_nueva["id"] and grupo_6a["director_id"] == 6)

print("Asignaciones")
coordinadora.post(ruta_6a, data=formulario_asignaciones(grupo_6a_id, {"docente-1": "5", "horas-1": "5", "docente-2": "6",
                                                                      "horas-2": "4"}))
revisar("asigna docentes a las materias", asignacion(grupo_6a_id, 1)["docente_id"] == 5 and asignacion(grupo_6a_id, 2) is not None)
respuesta = coordinadora.post(ruta_6a, data=formulario_asignaciones(grupo_6a_id, {"horas-1": "0"}))
revisar("rechaza horas fuera de rango", "número entero de 1 a 40" in texto(respuesta) and asignacion(grupo_6a_id, 1)["horas_semana"] == 5)
respuesta = coordinadora.post(ruta_6a, data=formulario_asignaciones(grupo_6a_id, {"docente-3": "13", "horas-3": "2"}))
revisar("rechaza a quien no es docente", "elige un docente" in texto(respuesta) and asignacion(grupo_6a_id, 3) is None)
coordinadora.post(ruta_6a, data=formulario_asignaciones(grupo_6a_id, {"docente-2": "", "horas-1": "3"}))
revisar("quita una asignación sin notas y cambia horas", asignacion(grupo_6a_id, 2) is None and asignacion(grupo_6a_id, 1)["horas_semana"] == 3)
respuesta = coordinadora.post("/admin/grupos/1", data=formulario_asignaciones(1, {"docente-1": ""}))
revisar("no quita una asignación con notas y avisa", "ya tiene notas" in texto(respuesta) and asignacion(1, 1) is not None)
revisar("la secretaria no cambia asignaciones",
        destino(secretaria.post("/admin/grupos/1", data=formulario_asignaciones(1, {"docente-8": ""}))) == "/inicio")

print("Matrículas")
id_matricula = matricula_de(22)["id"]
revisar("la coordinadora no retira estudiantes",
        destino(coordinadora.post("/admin/grupos/1", data={"accion": "retirar", "matricula_id": str(id_matricula)})) == "/inicio")
secretaria.post("/admin/grupos/1", data={"accion": "retirar", "matricula_id": str(id_matricula)})
retirada = base_datos.consultar_uno("SELECT * FROM matriculas WHERE id = ?", [id_matricula])
revisar("la secretaria retira a un estudiante", retirada["estado"] == "retirada" and retirada["fecha_retiro"] == hoy())
revisar("el retirado sale de la lista del grupo", matricula_de(22) is None)
secretaria.post(ruta_6a, data={"accion": "matricular", "estudiante_id": "22"})
revisar("matricula a un estudiante sin matrícula", matricula_de(22)["grupo_id"] == grupo_6a_id)
respuesta = secretaria.post(ruta_6a, data={"accion": "matricular", "estudiante_id": "13"})
revisar("no matricula dos veces en el mismo año", "Elige un estudiante activo" in texto(respuesta) and matricula_de(13)["grupo_id"] == 1)
secretaria.post(ruta_6a, data={"accion": "matricular", "estudiante_id": str(estudiante_vecino)})
revisar("no matricula a un estudiante de otro colegio", base_datos.matricula_activa(estudiante_vecino, 2026) is None)
id_matricula = matricula_de(21)["id"]
secretaria.post("/admin/grupos/1", data={"accion": "trasladar", "matricula_id": str(id_matricula), "grupo_destino": "2"})
anterior = base_datos.consultar_uno("SELECT * FROM matriculas WHERE id = ?", [id_matricula])
revisar("traslada a otro grupo del año", matricula_de(21)["grupo_id"] == 2 and anterior["estado"] == "trasladada")
id_matricula = matricula_de(20)["id"]
respuesta = secretaria.post("/admin/grupos/1", data={"accion": "trasladar", "matricula_id": str(id_matricula),
                                                     "grupo_destino": str(grupo_vecino)})
revisar("no traslada a un grupo de otro colegio", "Elige otro grupo" in texto(respuesta) and matricula_de(20)["grupo_id"] == 1)
respuesta = secretaria.post("/admin/grupos/2", data={"accion": "retirar", "matricula_id": str(id_matricula)})
revisar("no retira con una matrícula de otro grupo", "no está activa en este grupo" in texto(respuesta) and matricula_de(20) is not None)

print("Crear usuarios")
nueva = {"nombre": "Ana María  Peña Gómez", "documento": "1.094.555.111", "correo": "", "telefono": "310 555 1111",
         "roles": "estudiante", "grupo_id": "1"}
respuesta = secretaria.post("/admin/usuarios/nuevo", data=nueva)
html = texto(respuesta)
ana = base_datos.buscar_usuario("ana.pena")
clave_ana = clave_en(html)
revisar("crea el usuario a partir del nombre", ana is not None and "ana.pena" in html and ana["nombre"] == "Ana María Peña Gómez")
revisar("guarda el documento sin puntos", ana["documento"] == "1094555111")
revisar("muestra una clave temporal de 8 caracteres", len(clave_ana) == 8)
revisar("la clave se guarda cifrada", ana["clave"] != clave_ana and check_password_hash(ana["clave"], clave_ana))
revisar("debe cambiar la clave al entrar", ana["debe_cambiar_clave"] == 1)
revisar("queda matriculada en el grupo elegido", matricula_de(ana["id"])["grupo_id"] == 1)
nuevo_cliente = ayuda.app.test_client()
revisar("entra con la clave temporal", destino(nuevo_cliente.post("/", data={"usuario": "ana.pena", "clave": clave_ana})) == "/inicio")
revisar("y la plataforma le pide cambiarla", destino(nuevo_cliente.get("/mis-notas")) == "/mi-cuenta")
otra = {"nombre": "Ana Peña", "documento": "22223333", "correo": "", "telefono": "", "roles": "estudiante", "grupo_id": ""}
secretaria.post("/admin/usuarios/nuevo", data=otra)
revisar("si el usuario existe le agrega un 2", base_datos.buscar_usuario("ana.pena2") is not None)
respuesta = secretaria.post("/admin/usuarios/nuevo", data=otra)
revisar("no repite documentos del colegio", "Ya hay otra persona" in texto(respuesta) and base_datos.buscar_usuario("ana.pena3") is None)
jefe = {"nombre": "Mario Jefe Falso", "documento": "33334444", "correo": "", "telefono": "", "roles": ["docente", "administrador"]}
respuesta = secretaria.post("/admin/usuarios/nuevo", data=jefe)
revisar("la secretaria no puede crear administradores", "Solo la administración" in texto(respuesta)
        and base_datos.buscar_usuario("mario.falso") is None)
jefe["roles"] = ["coordinador"]
secretaria.post("/admin/usuarios/nuevo", data=jefe)
revisar("la secretaria no puede crear coordinadores", base_datos.buscar_usuario("mario.falso") is None)
respuesta = secretaria.post("/admin/usuarios/nuevo", data={"nombre": "Sincero Tesorero", "documento": "44445555", "correo": "",
                                                           "telefono": "", "roles": "tesoreria"})
revisar("la secretaria no puede dar roles con datos sensibles (tesorería)", base_datos.buscar_usuario("sincero.tesorero") is None)
respuesta = secretaria.post("/admin/usuarios/nuevo", data={"nombre": "Sincero Bibliotecario", "documento": "44445556", "correo": "",
                                                           "telefono": "", "roles": "bibliotecario"})
revisar("la secretaria sí puede dar los demás roles nuevos (biblioteca)", "bibliotecario" in base_datos.roles_de(base_datos.buscar_usuario("sincero.bibliotecario")["id"]))
respuesta = secretaria.get("/admin/usuarios/12")
revisar("la secretaria ve a la orientadora solo en lectura", "solo la administración puede cambiar" in texto(respuesta))
respuesta = secretaria.post("/admin/usuarios/12", data={"accion": "clave"})
revisar("la secretaria no puede restablecer la clave de la orientadora", destino(respuesta) == "/inicio")
admin.post("/admin/usuarios/nuevo", data={"nombre": "Carlos Andrés Mejía", "documento": "55556666", "correo": "carlos@colegio.edu.co",
                                          "telefono": "", "roles": "coordinador"})
carlos = base_datos.buscar_usuario("carlos.mejia")
revisar("la administradora sí crea coordinadores", carlos is not None and base_datos.roles_de(carlos["id"]) == ["coordinador"])
respuesta = secretaria.post("/admin/usuarios/nuevo", data={"nombre": "Lucía", "documento": "abc", "correo": "sin-arroba",
                                                           "telefono": "llámame", "roles": []})
html = texto(respuesta)
revisar("valida nombre, documento, correo, teléfono y roles", "nombre completo" in html and "El documento solo puede" in html
        and "correo no parece" in html and "teléfono solo puede" in html and "al menos un rol" in html)
respuesta = secretaria.post("/admin/usuarios/nuevo", data={"nombre": "Laura Docente Nueva", "documento": "66667777", "correo": "",
                                                           "telefono": "", "roles": "docente", "grupo_id": "1"})
revisar("solo matricula a estudiantes", "rol Estudiante" in texto(respuesta) and base_datos.buscar_usuario("laura.nueva") is None)
secretaria.post("/admin/usuarios/nuevo", data={"nombre": "Pedro Lejano Vecino", "documento": "99887766", "correo": "",
                                               "telefono": "", "roles": "estudiante"})
revisar("un documento de otro colegio no cuenta como repetido", base_datos.buscar_usuario("pedro.vecino2") is not None)

print("Lista de usuarios")
html = texto(secretaria.get("/admin/usuarios?rol=acudiente"))
revisar("filtra por rol", "Gloria Inés Cárdenas" in html and "Melany Osorio" not in html)
html = texto(secretaria.get("/admin/usuarios?texto=cardenas"))
revisar("busca sin importar las tildes", "Gloria Inés Cárdenas" in html and "Melany Osorio Cárdenas" in html and "Esteban" not in html)
revisar("busca por documento", "Ana María Peña Gómez" in texto(secretaria.get("/admin/usuarios?texto=1094555")))
html = texto(admin.get("/admin/usuarios"))
revisar("no muestra personas de otro colegio", "Administradora Vecina" not in html and "Pedro Vecino Lejano" not in html)

print("Editar usuarios")
respuesta = admin.post("/admin/usuarios/1", data={"accion": "desactivar"})
revisar("nadie puede desactivarse a sí mismo", "propio usuario" in texto(respuesta) and base_datos.buscar_usuario_por_id(1)["activo"] == 1)
respuesta = admin.post("/admin/usuarios/1", data=datos_persona(1, {"documento": "11112222", "roles": ["docente"]}))
revisar("la administradora no puede quitarse su rol", "No puedes quitarte" in texto(respuesta) and "administrador" in base_datos.roles_de(1))
respuesta = admin.post("/admin/usuarios/1", data={"accion": "restablecer"})
revisar("no restablece su propia contraseña aquí", "Mi cuenta" in texto(respuesta))
revisar("la secretaria ve a la coordinadora sin poder cambiarla", "solo la administración puede cambiar" in texto(secretaria.get("/admin/usuarios/3")))
respuesta = secretaria.post("/admin/usuarios/3", data={"accion": "restablecer"})
revisar("la secretaria no restablece la clave de una directiva", destino(respuesta) == "/inicio"
        and check_password_hash(base_datos.buscar_usuario_por_id(3)["clave"], "pijao2026"))
secretaria.post("/admin/usuarios/1", data={"accion": "desactivar"})
revisar("la secretaria no desactiva a la administradora", base_datos.buscar_usuario_por_id(1)["activo"] == 1)
respuesta = secretaria.post("/admin/usuarios/14", data={"accion": "restablecer"})
juan = base_datos.buscar_usuario_por_id(14)
clave_juan = clave_en(texto(respuesta))
revisar("restablece la contraseña y la muestra una vez", len(clave_juan) == 8 and check_password_hash(juan["clave"], clave_juan))
revisar("la clave vieja deja de servir", not check_password_hash(juan["clave"], "pijao2026") and juan["debe_cambiar_clave"] == 1)
secretaria.post("/admin/usuarios/7", data={"accion": "desactivar"})
revisar("desactiva a un docente", base_datos.buscar_usuario_por_id(7)["activo"] == 0)
respuesta = ayuda.app.test_client().post("/", data={"usuario": "s.londono", "clave": "pijao2026"})
revisar("el usuario desactivado no puede entrar", "desactivado" in texto(respuesta))
revisar("aparece en el filtro de inactivos", "Sebastián Londoño" in texto(secretaria.get("/admin/usuarios?estado=inactivos")))
secretaria.post("/admin/usuarios/7", data={"accion": "activar"})
revisar("lo vuelve a activar", base_datos.buscar_usuario_por_id(7)["activo"] == 1)
respuesta = secretaria.post("/admin/usuarios/13", data=datos_persona(13, {"documento": "1094000013", "roles": ["acudiente"]}))
revisar("no quita el rol de estudiante con matrícula activa", "Tiene matrícula activa" in texto(respuesta) and "estudiante" in base_datos.roles_de(13))
respuesta = secretaria.post("/admin/usuarios/5", data=datos_persona(5, {"documento": "1094000005", "roles": ["orientador"]}))
revisar("no quita el rol de docente con clases", "Tiene materias" in texto(respuesta) and "docente" in base_datos.roles_de(5))
respuesta = secretaria.post("/admin/usuarios/30", data=datos_persona(30, {"documento": "75000111", "telefono": "300 123 4567"}))
revisar("edita datos de contacto", "Datos guardados" in texto(respuesta) and base_datos.buscar_usuario_por_id(30)["telefono"] == "300 123 4567")
respuesta = secretaria.post("/admin/usuarios/30", data=datos_persona(30, {"roles": ["acudiente", "rector"]}))
revisar("la secretaria no da el rol de rectoría al editar", "Solo la administración" in texto(respuesta) and "rector" not in base_datos.roles_de(30))
admin.post("/admin/usuarios/" + str(carlos["id"]), data=datos_persona(carlos["id"], {"roles": ["coordinador", "docente"]}))
revisar("la administradora agrega roles", base_datos.roles_de(carlos["id"]) == ["coordinador", "docente"])
revisar("la secretaria no ve usuarios de otro colegio", destino(secretaria.get("/admin/usuarios/" + str(estudiante_vecino))) == "/admin/usuarios")

print("Acudientes")
secretaria.post("/admin/usuarios/29", data={"accion": "agregar_acudido", "estudiante_id": "15", "parentesco": "Tía"})
relacion = base_datos.consultar_uno("SELECT * FROM acudientes WHERE acudiente_id = 29 AND estudiante_id = 15", [])
revisar("agrega un estudiante a cargo", relacion is not None and relacion["parentesco"] == "Tía" and relacion["colegio_id"] == 1)
respuesta = secretaria.post("/admin/usuarios/29", data={"accion": "agregar_acudido", "estudiante_id": "16", "parentesco": "Vecina"})
revisar("el parentesco debe estar en la lista", "parentesco de la lista" in texto(respuesta))
respuesta = secretaria.post("/admin/usuarios/29", data={"accion": "agregar_acudido", "estudiante_id": "5", "parentesco": "Madre"})
revisar("solo se agregan estudiantes", "Elige un estudiante" in texto(respuesta))
secretaria.post("/admin/usuarios/29", data={"accion": "agregar_acudido", "estudiante_id": str(estudiante_vecino), "parentesco": "Madre"})
revisar("no agrega estudiantes de otro colegio",
        base_datos.consultar_uno("SELECT * FROM acudientes WHERE estudiante_id = ?", [estudiante_vecino]) is None)
respuesta = secretaria.post("/admin/usuarios/29", data={"accion": "agregar_acudido", "estudiante_id": "15", "parentesco": "Tía"})
revisar("no repite un estudiante a cargo", "ya está a cargo" in texto(respuesta))
secretaria.post("/admin/usuarios/29", data={"accion": "quitar_acudido", "estudiante_id": "15"})
revisar("quita un estudiante a cargo",
        base_datos.consultar_uno("SELECT * FROM acudientes WHERE acudiente_id = 29 AND estudiante_id = 15", []) is None)
respuesta = secretaria.post("/admin/usuarios/29", data=datos_persona(29, {"documento": "24000111", "roles": ["docente"]}))
revisar("no quita el rol de acudiente con estudiantes a cargo", "Tiene estudiantes a cargo" in texto(respuesta))
html = texto(secretaria.get("/admin/usuarios/13"))
revisar("la página del estudiante muestra su grupo y su acudiente", "10-A" in html and "Gloria Inés Cárdenas" in html)

print("Cargue masivo")
lineas = "\n".join([
    "Pedro Pablo Pérez Ruiz;1094000111;10-A",
    "Lina Gómez;1094000111;11-A",
    "Mario Ruiz;1094000222;12-C",
    "Solo Nombre;",
    "Sara López\t1094000333\t11 - a",
    "",
    "Juan Vecino Lejos;55443322;6-Z",
    "Tomás;1094000444;10-A",
])
revisar("la coordinadora no hace cargues", destino(coordinadora.post("/admin/cargue", data={"lineas": lineas})) == "/inicio"
        and base_datos.buscar_usuario("pedro.perez") is None)
respuesta = secretaria.post("/admin/cargue", data={"lineas": lineas})
html = texto(respuesta)
pedro = base_datos.buscar_usuario("pedro.perez")
sara = base_datos.buscar_usuario("sara.lopez")
revisar("crea y matricula las líneas buenas", pedro is not None and sara is not None and matricula_de(pedro["id"])["grupo_id"] == 1
        and matricula_de(sara["id"])["grupo_id"] == 2)
revisar("muestra usuarios y claves de los creados", "pedro.perez" in html and "sara.lopez" in html and len(clave_en(html)) == 8)
revisar("informa el documento repetido", "Línea 2: el documento 1094000111 ya está registrado" in html)
revisar("informa el grupo que no existe", "Línea 3: el grupo 12-C no existe" in html)
revisar("informa la línea incompleta", "Línea 4: la línea está incompleta" in html)
revisar("no usa grupos de otro colegio", "Línea 7: el grupo 6-Z no existe" in html)
revisar("pide nombre y apellido", "Línea 8: escribe el nombre completo" in html)
revisar("deja las líneas con error para corregirlas", "Mario Ruiz;1094000222;12-C" in html and "Pedro Pablo" not in html.split("<textarea")[1])
revisar("los creados deben cambiar la clave", pedro["debe_cambiar_clave"] == 1 and "estudiante" in base_datos.roles_de(pedro["id"]))

print("Registro de actividad")
html = texto(admin.get("/admin/registro"))
revisar("la administradora ve el registro", "Cargue masivo de estudiantes" in html and "Restableció una contraseña" in html)
revisar("el registro no muestra otro colegio", "Acción secreta del vecino" not in html)
revisar("el registro no guarda claves", clave_juan not in html and clave_ana not in html)
html = texto(rectora.get("/admin/registro?texto=restableci"))
revisar("la rectora filtra el registro", "Restableció una contraseña" in html and "Cargue masivo" not in html)

print("La administradora del otro colegio")
vecina = entrar("admin.vecino")
revisar("solo ve su colegio", "Melany" not in texto(vecina.get("/admin/usuarios")) and "Pedro Vecino Lejano" in texto(vecina.get("/admin/usuarios")))
revisar("no abre grupos del piloto", destino(vecina.get("/admin/grupos/1")) == "/admin/grupos")
revisar("no abre usuarios del piloto", destino(vecina.get("/admin/usuarios/13")) == "/admin/usuarios")
revisar("el tablero cuenta solo su colegio", "Colegio Vecino" in texto(vecina.get("/admin")))

ayuda.terminar()
