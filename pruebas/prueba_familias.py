import ayuda
from ayuda import entrar, revisar, destino
import modulo_inicio
import modulo_notas
import modulo_familias
import modulo_circulares
import base_datos
import nucleo
from werkzeug.security import generate_password_hash


def contar(sql, valores):
    return len(base_datos.consultar(sql, valores))


print("Fechas")
revisar("acepta una fecha correcta", modulo_familias.fecha_valida("2026-11-28"))
revisar("rechaza una fecha con barras", not modulo_familias.fecha_valida("28/11/2026"))
revisar("rechaza un mes 13", not modulo_familias.fecha_valida("2026-13-01"))
revisar("rechaza el 30 de febrero", not modulo_familias.fecha_valida("2026-02-30"))
revisar("acepta el 29 de febrero en año bisiesto", modulo_familias.fecha_valida("2028-02-29"))
revisar("rechaza letras", not modulo_familias.fecha_valida("2026-1a-01"))
revisar("acepta una hora correcta", modulo_familias.hora_valida("14:30"))
revisar("rechaza la hora 25", not modulo_familias.hora_valida("25:00"))
revisar("escribe la fecha larga", modulo_familias.fecha_larga("2026-11-28") == "sábado 28 de noviembre de 2026")
revisar("escribe la hora con a. m. y p. m.", modulo_familias.hora_texto("14:30") == "2:30 p. m.")
revisar("entero no acepta números raros", modulo_familias.entero("²") is None and modulo_familias.entero("4") == 4)

print("Menú y permisos")
madre = entrar("gloria.cardenas")
padre = entrar("jorge.restrepo")
coordinadora = entrar("coordinadora")
docente = entrar("c.munoz")
estudiante = entrar("melany.osorio")
revisar("la acudiente ve Mi familia en el inicio", "/familia" in madre.get("/inicio").get_data(as_text=True))
revisar("la docente no ve Mi familia", "/familia\"" not in docente.get("/inicio").get_data(as_text=True))
revisar("la coordinadora ve Escuela para familias", "/escuela-familias" in coordinadora.get("/inicio").get_data(as_text=True))
revisar("la acudiente entra a Mi familia", madre.get("/familia").status_code == 200)
revisar("la docente no entra a Mi familia", destino(docente.get("/familia")) == "/inicio")
revisar("la estudiante no entra a Mi familia", destino(estudiante.get("/familia")) == "/inicio")
revisar("sin sesión no entra a Mi familia", destino(ayuda.app.test_client().get("/familia")) == "/inicio")
for usuario in ["coordinadora", "rectora", "orientadora", "admin"]:
    revisar(usuario + " entra a la escuela para familias", entrar(usuario).get("/escuela-familias").status_code == 200)
for usuario in ["c.munoz", "h.aguirre", "secretaria", "gloria.cardenas", "melany.osorio"]:
    cliente = entrar(usuario)
    revisar(usuario + " no entra a la escuela para familias", destino(cliente.get("/escuela-familias")) == "/inicio")
    revisar(usuario + " no ve la caracterización", destino(cliente.get("/escuela-familias/caracterizacion")) == "/inicio")
    revisar(usuario + " no toma asistencia", destino(cliente.post("/escuela-familias/1", data={"asistio-29": "1"})) == "/inicio")

print("Mi familia")
html = madre.get("/familia").get_data(as_text=True)
periodos = base_datos.periodos_del_anio(1, 2026)
todas = base_datos.notas_del_estudiante(13, 2026, len(periodos))
finales = []
for asignacion in base_datos.asignaciones_del_grupo(1):
    finales.append(nucleo.nota_final(todas[asignacion["materia_id"]], periodos))
esperado = nucleo.promedio(finales)
revisar("muestra a su hija con su grupo", "Melany Osorio Cárdenas" in html and "Grupo 10-A" in html)
revisar("muestra al director de grupo", "Hernán Darío Aguirre" in html)
revisar("muestra el promedio general del año", "<strong>" + str(esperado) + "</strong>" in html)
revisar("el promedio coincide con el boletín", "<strong>" + str(esperado) + "</strong>" in madre.get("/boletin/13").get_data(as_text=True))
enlaces = ["/boletin/13", "/asistencia/estudiante/13", "/observador/estudiante/13", "/horas/estudiante/13", "/certificados"]
todos_los_enlaces = True
for enlace in enlaces:
    if enlace not in html:
        todos_los_enlaces = False
revisar("tiene los enlaces de boletín, asistencia, observador, horas y certificados", todos_los_enlaces)
revisar("no muestra hijos ajenos", "Juan Pablo Restrepo" not in html and "/boletin/14" not in html)
revisar("con el compromiso aceptado no pide aceptarlo otra vez", "Acepto el compromiso" not in html)
revisar("muestra el próximo encuentro", "Prevención del consumo de sustancias psicoactivas" in html)
revisar("muestra que asistió al encuentro pasado", "Cómo acompañar las tareas en casa" in html and "Asististe" in html)

print("Compromiso")
html = padre.get("/familia").get_data(as_text=True)
revisar("al padre le pide aceptar el compromiso", "Acepto el compromiso" in html and "Ley 2025 de 2020" in html)
revisar("el padre solo ve a su hijo", "Juan Pablo Restrepo" in html and "Melany Osorio" not in html)
html = padre.post("/familia", data={"accion": "compromiso", "estudiante_id": "13"}).get_data(as_text=True)
revisar("acepta el compromiso", "quedó registrado" in html and "Acepto el compromiso" not in html)
revisar("guarda el compromiso de su hijo", contar("SELECT id FROM compromisos_familia WHERE acudiente_id = 30 AND estudiante_id = 14 AND anio = 2026 AND colegio_id = 1", []) == 1)
revisar("no firma por estudiantes ajenos", contar("SELECT id FROM compromisos_familia WHERE acudiente_id = 30 AND estudiante_id = 13", []) == 0)
padre.post("/familia", data={"accion": "compromiso"})
revisar("aceptar dos veces no duplica", contar("SELECT id FROM compromisos_familia WHERE acudiente_id = 30", []) == 1)
revisar("queda en el registro de accesos", contar("SELECT id FROM registro_accesos WHERE usuario_id = 30 AND accion = 'Aceptó el compromiso de la escuela para familias'", []) >= 1)

print("Caracterización de la familia")
malos = [
    {"accion": "caracterizacion", "personas_hogar": "0", "tiene_internet": "si", "medio_preferido": "whatsapp"},
    {"accion": "caracterizacion", "personas_hogar": "²", "tiene_internet": "si", "medio_preferido": "whatsapp"},
    {"accion": "caracterizacion", "personas_hogar": "4", "tiene_internet": "tal vez", "medio_preferido": "whatsapp"},
    {"accion": "caracterizacion", "personas_hogar": "4", "tiene_internet": "no", "medio_preferido": "telegrama"},
    {"accion": "caracterizacion", "personas_hogar": "4", "tiene_internet": "no", "medio_preferido": "llamada", "necesidades": "x" * 1001},
]
todos_con_error = True
for formulario in malos:
    if "aviso error" not in padre.post("/familia", data=formulario).get_data(as_text=True):
        todos_con_error = False
revisar("rechaza datos de familia inválidos", todos_con_error)
revisar("no guarda datos inválidos", contar("SELECT id FROM caracterizacion_familias WHERE acudiente_id = 30", []) == 0)
html = padre.post("/familia", data={"accion": "caracterizacion", "personas_hogar": "5", "tiene_internet": "no",
                                    "medio_preferido": "llamada", "necesidades": "Vivimos en la vereda"}).get_data(as_text=True)
revisar("guarda la caracterización", "quedaron guardados" in html)
padre.post("/familia", data={"accion": "caracterizacion", "personas_hogar": "6", "tiene_internet": "no", "medio_preferido": "llamada"})
fichas = base_datos.consultar("SELECT * FROM caracterizacion_familias WHERE acudiente_id = 30", [])
revisar("editarla no crea otra fila", len(fichas) == 1 and fichas[0]["personas_hogar"] == 6 and fichas[0]["colegio_id"] == 1)
revisar("el formulario muestra lo guardado", 'value="6"' in padre.get("/familia").get_data(as_text=True))

print("Escuela para familias")
html = coordinadora.get("/escuela-familias").get_data(as_text=True)
revisar("cuenta las familias con compromiso", "2<small> de 3</small>" in html)
revisar("calcula la asistencia promedio", "67 %" in html)
revisar("cuenta las familias caracterizadas", "Familias caracterizadas" in html and "67 % de las familias" in html)
nuevo = {"titulo": "Pautas de crianza", "tema": "Crianza amorosa", "fecha": "2026-12-01", "hora": "14:00",
         "lugar": "Auditorio", "descripcion": "Taller"}
casos = [["sin título", "titulo", ""], ["fecha con barras", "fecha", "01/12/2026"], ["fecha imposible", "fecha", "2026-02-30"],
         ["fecha de otro año", "fecha", "2025-12-01"], ["hora inválida", "hora", "25:00"], ["sin lugar", "lugar", ""]]
for caso in casos:
    formulario = dict(nuevo)
    formulario[caso[1]] = caso[2]
    revisar("no crea un encuentro " + caso[0], "aviso error" in coordinadora.post("/escuela-familias", data=formulario).get_data(as_text=True))
revisar("los encuentros inválidos no se guardan", contar("SELECT id FROM encuentros_familias", []) == 2)
html = coordinadora.post("/escuela-familias", data=nuevo).get_data(as_text=True)
revisar("crea un encuentro", "Encuentro creado" in html and "Pautas de crianza" in html)
creado = base_datos.consultar_uno("SELECT * FROM encuentros_familias WHERE titulo = 'Pautas de crianza'", [])
revisar("el encuentro queda en el colegio y año correctos", creado["colegio_id"] == 1 and creado["anio"] == 2026 and creado["creado_por"] == 3)
docente.post("/escuela-familias", data={"titulo": "Intruso", "tema": "x", "fecha": "2026-12-01", "hora": "08:00", "lugar": "x"})
revisar("una docente no puede crear encuentros", contar("SELECT id FROM encuentros_familias WHERE titulo = 'Intruso'", []) == 0)

print("Asistencia a un encuentro")
html = coordinadora.get("/escuela-familias/1").get_data(as_text=True)
revisar("lista a los acudientes del colegio", "Gloria Inés Cárdenas" in html and "Jorge Iván Restrepo" in html and "Olga Lucía Gómez" in html)
revisar("muestra los estudiantes de cada acudiente", "Melany Osorio Cárdenas (10-A)" in html)
revisar("muestra la asistencia guardada", 'name="asistio-29" value="1" checked' in html)
html = coordinadora.post("/escuela-familias/1", data={"asistio-31": "1", "asistio-999": "1"}).get_data(as_text=True)
revisar("guarda la asistencia", "Asistencia guardada: 1 de 3" in html)
marcas = {}
for fila in base_datos.consultar("SELECT acudiente_id, asistio FROM asistencia_encuentros WHERE encuentro_id = 1", []):
    marcas[fila["acudiente_id"]] = fila["asistio"]
revisar("desmarca a quien no se marcó", marcas[29] == 0 and marcas[30] == 0 and marcas[31] == 1)
revisar("ignora ids que no son acudientes del colegio", 999 not in marcas)
html = coordinadora.post("/escuela-familias/2", data={"asistio-29": "1"}).get_data(as_text=True)
revisar("no toma asistencia de un encuentro futuro", "todavía no se ha realizado" in html)
revisar("el encuentro futuro queda sin asistencia", contar("SELECT id FROM asistencia_encuentros WHERE encuentro_id = 2", []) == 0)
revisar("un encuentro que no existe lleva al inicio", destino(coordinadora.get("/escuela-familias/9999")) == "/inicio")
html = madre.get("/familia").get_data(as_text=True)
revisar("la madre ve que no quedó como asistente", "No asististe" in html)

print("Caracterización para directivos")
html = coordinadora.get("/escuela-familias/caracterizacion").get_data(as_text=True)
revisar("muestra la tabla de familias", "Gloria Inés Cárdenas" in html and "Jorge Iván Restrepo" in html and "WhatsApp" in html)
revisar("marca a quien no está caracterizado", "Sin caracterizar" in html)
html = coordinadora.get("/escuela-familias/caracterizacion?internet=no").get_data(as_text=True)
revisar("filtra las familias sin internet", "Jorge Iván Restrepo" in html and "Gloria Inés Cárdenas" not in html)
html = coordinadora.get("/escuela-familias/caracterizacion?medio=whatsapp").get_data(as_text=True)
revisar("filtra por medio preferido", "Gloria Inés Cárdenas" in html and "Jorge Iván Restrepo" not in html)

print("Aislamiento entre colegios")
clave = generate_password_hash("pijao2026")
otro = base_datos.ejecutar("INSERT INTO colegios (nombre, nombre_corto, municipio, departamento, anio) VALUES (?, ?, ?, ?, ?)",
                           ["Colegio de Génova", "Colegio Génova", "Génova", "Quindío", 2026])
rosa = base_datos.ejecutar("INSERT INTO usuarios (colegio_id, usuario, clave, nombre) VALUES (?, ?, ?, ?)",
                           [otro, "rosa.otro", clave, "Rosa Elvira Otálvaro"])
base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [rosa, "acudiente"])
rector_otro = base_datos.ejecutar("INSERT INTO usuarios (colegio_id, usuario, clave, nombre) VALUES (?, ?, ?, ?)",
                                  [otro, "rector.otro", clave, "Rector de Génova"])
base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [rector_otro, "rector"])
ajeno = base_datos.ejecutar(
    "INSERT INTO encuentros_familias (colegio_id, anio, titulo, tema, fecha, hora, lugar, creado_por) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    [otro, 2026, "Encuentro de Génova", "Otro tema", "2026-11-30", "08:00", "Génova", rector_otro])
revisar("no ve encuentros de otro colegio", destino(coordinadora.get("/escuela-familias/" + str(ajeno))) == "/inicio")
coordinadora.post("/escuela-familias/" + str(ajeno), data={"asistio-29": "1"})
revisar("no toma asistencia en otro colegio", contar("SELECT id FROM asistencia_encuentros WHERE encuentro_id = ?", [ajeno]) == 0)
revisar("la escuela no lista encuentros de otro colegio", "Encuentro de Génova" not in coordinadora.get("/escuela-familias").get_data(as_text=True))
revisar("la acudiente no ve encuentros de otro colegio", "Encuentro de Génova" not in madre.get("/familia").get_data(as_text=True))
revisar("los acudientes de otro colegio no aparecen", "Rosa Elvira" not in coordinadora.get("/escuela-familias/1").get_data(as_text=True))
rector_genova = entrar("rector.otro")
revisar("el otro colegio no ve encuentros del piloto", destino(rector_genova.get("/escuela-familias/1")) == "/inicio")
revisar("el otro colegio no ve la caracterización del piloto", "Gloria" not in rector_genova.get("/escuela-familias/caracterizacion").get_data(as_text=True))

ayuda.terminar()
