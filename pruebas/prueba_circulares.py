import ayuda
from ayuda import entrar, revisar, destino
import modulo_inicio
import modulo_notas
import modulo_familias
import modulo_circulares
import base_datos
from werkzeug.security import generate_password_hash


def contar(sql, valores):
    return len(base_datos.consultar(sql, valores))


def ids_de(personas):
    ids = []
    for persona in personas:
        ids.append(persona["id"])
    return ids


clave = generate_password_hash("pijao2026")
portero = base_datos.buscar_usuario("porteria")["id"]
activos = contar("SELECT id FROM usuarios WHERE colegio_id = 1 AND activo = 1", [])

print("Menú")
for usuario in ["admin", "rectora", "c.munoz", "secretaria", "orientadora", "melany.osorio", "gloria.cardenas", "tesoreria", "biblioteca", "enfermeria", "porteria"]:
    html = entrar(usuario).get("/inicio").get_data(as_text=True)
    revisar(usuario + " ve Circulares y Agenda", "/circulares" in html and "/agenda" in html)

print("Quién recibe cada circular")
circular_todos = base_datos.consultar_uno("SELECT * FROM circulares WHERE id = 1", [])
circular_grupo = base_datos.consultar_uno("SELECT * FROM circulares WHERE id = 2", [])
revisar("la circular de rectoría es para todos", circular_todos["destinatarios"] == "todos" and circular_todos["autor_id"] == 2)
revisar("la de la salida es para 10-A y pide confirmar", circular_grupo["grupo_id"] == 1 and circular_grupo["requiere_confirmacion"] == 1)
para_todos = ids_de(modulo_circulares.destinatarios_de(circular_todos))
revisar("'todos' incluye a todos los usuarios activos, también portería", len(para_todos) == activos and portero in para_todos)
para_grupo = ids_de(modulo_circulares.destinatarios_de(circular_grupo))
esperados = [4, 5, 6, 7, 8, 9, 10, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 29, 30]
revisar("'grupo' son los estudiantes, sus acudientes y los docentes del grupo", sorted(para_grupo) == esperados)
revisar("'grupo' no incluye a otro grupo ni a otras familias", 23 not in para_grupo and 31 not in para_grupo)
coinciden = True
for tipo in ["todos", "docentes", "familias", "estudiantes", "grupo"]:
    prueba = dict(circular_grupo)
    prueba["destinatarios"] = tipo
    lista = ids_de(modulo_circulares.destinatarios_de(prueba))
    for persona in base_datos.usuarios_del_colegio(1):
        if (persona["id"] in lista) != modulo_circulares.es_destinatario(persona, prueba):
            coinciden = False
            print("    no coincide " + tipo + " " + persona["usuario"])
    if tipo == "docentes":
        revisar("'docentes' incluye docentes y directivos, no secretaría ni familias",
                4 in lista and 2 in lista and 1 in lista and 11 not in lista and 29 not in lista)
    if tipo == "familias":
        revisar("'familias' son los acudientes", sorted(lista) == [29, 30, 31])
    if tipo == "estudiantes":
        revisar("'estudiantes' son los 16 estudiantes", len(lista) == 16 and 13 in lista and 29 not in lista)
revisar("la lista de destinatarios coincide con el permiso de cada persona", coinciden)

print("Lista de circulares")
madre = entrar("gloria.cardenas")
html = madre.get("/circulares").get_data(as_text=True)
revisar("la madre ve las dos circulares", "Entrega de boletines del cuarto período" in html and "Jardín Botánico" in html)
revisar("le muestra una sin leer", "<strong>1</strong>" in html and "circular sin leer" in html)
revisar("le muestra que falta confirmar", "Falta confirmar" in html)
revisar("la no leída está resaltada", 'class="no-leida"' in html)
revisar("la madre no puede publicar", "Nueva circular" not in html)
otra_madre = entrar("olga.gomez")
html = otra_madre.get("/circulares").get_data(as_text=True)
revisar("la madre de 11-A no ve la circular de 10-A", "Jardín Botánico" not in html and "Entrega de boletines" in html)
revisar("la madre de 11-A no abre la circular de 10-A", destino(otra_madre.get("/circulares/2")) == "/inicio")
revisar("el estudiante de 11-A no abre la circular de 10-A", destino(entrar("esteban.ramirez").get("/circulares/2")) == "/inicio")
revisar("la secretaria no abre la circular de un grupo", destino(entrar("secretaria").get("/circulares/2")) == "/inicio")
revisar("la docente que dicta en 10-A sí la ve", "Jardín Botánico" in entrar("c.munoz").get("/circulares").get_data(as_text=True))
revisar("portería ve la circular para todos", entrar("porteria").get("/circulares/1").status_code == 200)
rectora = entrar("rectora")
html = rectora.get("/circulares").get_data(as_text=True)
revisar("la rectora ve todas y puede publicar", "Jardín Botánico" in html and "Nueva circular" in html)

print("Leer y confirmar")
madre.get("/circulares/1")
revisar("abrir la circular la marca leída", contar("SELECT id FROM lecturas_circular WHERE circular_id = 1 AND usuario_id = 29", []) == 1)
madre.get("/circulares/1")
revisar("abrirla otra vez no duplica la lectura", contar("SELECT id FROM lecturas_circular WHERE circular_id = 1 AND usuario_id = 29", []) == 1)
revisar("ya no queda sin leer", "circulares sin leer" in madre.get("/circulares").get_data(as_text=True))
html = madre.get("/circulares/2").get_data(as_text=True)
revisar("a la acudiente le pide confirmar y estar enterada", "Confirmo que la leí y estoy enterado" in html)
revisar("la acudiente no ve el reporte", "Quiénes faltan" not in html)
html = madre.post("/circulares/2").get_data(as_text=True)
lectura = base_datos.consultar_uno("SELECT * FROM lecturas_circular WHERE circular_id = 2 AND usuario_id = 29", [])
revisar("confirma la lectura", "Lectura confirmada" in html and lectura["confirmada_en"] != "")
revisar("la confirmación queda registrada", contar("SELECT id FROM registro_accesos WHERE usuario_id = 29 AND accion = 'Confirmó la lectura de una circular'", []) == 1)
estudiante = entrar("melany.osorio")
html = estudiante.get("/circulares/2").get_data(as_text=True)
revisar("al estudiante le pide solo confirmar que la leyó", "Confirmo que la leí</button>" in html and "estoy enterado" not in html)
html = madre.post("/circulares/1").get_data(as_text=True)
revisar("no confirma una circular que no lo pide", "no te pide confirmar" in html)
rectora.get("/circulares/2")
revisar("la rectora no queda como lectora de una circular que no le llegó", contar("SELECT id FROM lecturas_circular WHERE circular_id = 2 AND usuario_id = 2", []) == 0)

print("Reporte de lectura")
html = entrar("coordinadora").get("/circulares/2").get_data(as_text=True)
revisar("la autora ve el reporte", "Quiénes faltan por leer o confirmar" in html)
revisar("cuenta los destinatarios", "<span>Destinatarios</span>\n    <strong>19</strong>" in html)
revisar("cuenta quiénes la leyeron y confirmaron", "<strong>2<small> · 11 %</small></strong>" in html and "<strong>1<small> · 5 %</small></strong>" in html)
revisar("lista a quienes faltan", "Juan Pablo Restrepo" in html and "Leída, sin confirmar" in html and "Gloria Inés Cárdenas" not in html)

print("Publicar")
for usuario in ["c.munoz", "melany.osorio", "gloria.cardenas", "porteria"]:
    cliente = entrar(usuario)
    revisar(usuario + " no puede publicar", destino(cliente.get("/circulares/nueva")) == "/inicio")
    cliente.post("/circulares/nueva", data={"titulo": "Intrusa", "cuerpo": "x", "destinatarios": "todos"})
revisar("nadie sin permiso publicó", contar("SELECT id FROM circulares WHERE titulo = 'Intrusa'", []) == 0)
director = entrar("h.aguirre")
html = director.get("/circulares/nueva").get_data(as_text=True)
revisar("el director de grupo puede escribir circulares", "Publicar circular" in html and 'value="grupo"' in html and 'value="todos"' not in html)
html = director.post("/circulares/nueva", data={"titulo": "Para todos", "cuerpo": "x", "destinatarios": "todos"}).get_data(as_text=True)
revisar("el director no publica para todo el colegio", "aviso error" in html)
html = director.post("/circulares/nueva", data={"titulo": "Para 11-A", "cuerpo": "x", "destinatarios": "grupo", "grupo_id": "2"}).get_data(as_text=True)
revisar("el director no publica a un grupo ajeno", "aviso error" in html)
respuesta = director.post("/circulares/nueva", data={"titulo": "Reunión de padres de 10-A", "cuerpo": "Línea uno\nLínea dos",
                                                     "destinatarios": "grupo", "grupo_id": "1", "requiere_confirmacion": "1"})
nueva = base_datos.consultar_uno("SELECT * FROM circulares WHERE titulo = 'Reunión de padres de 10-A'", [])
revisar("el director publica a su grupo", nueva is not None and destino(respuesta).startswith("/circulares/" + str(nueva["id"])))
revisar("la circular queda bien guardada", nueva["colegio_id"] == 1 and nueva["autor_id"] == 4 and nueva["grupo_id"] == 1 and nueva["requiere_confirmacion"] == 1)
revisar("la publicación queda registrada", contar("SELECT id FROM registro_accesos WHERE usuario_id = 4 AND accion = 'Publicó una circular'", []) == 1)
html = director.get("/circulares/" + str(nueva["id"])).get_data(as_text=True)
revisar("el autor ve el reporte de su circular", "Destinatarios" in html)
revisar("respeta los saltos de línea sin usar safe", "Línea uno\nLínea dos" in html)
coordinadora = entrar("coordinadora")
casos = [["sin título", {"titulo": "", "cuerpo": "x", "destinatarios": "todos"}],
         ["sin texto", {"titulo": "Aviso", "cuerpo": "", "destinatarios": "todos"}],
         ["con destinatarios raros", {"titulo": "Aviso", "cuerpo": "x", "destinatarios": "hackers"}],
         ["a un grupo sin elegirlo", {"titulo": "Aviso", "cuerpo": "x", "destinatarios": "grupo", "grupo_id": "abc"}]]
for caso in casos:
    revisar("no publica una circular " + caso[0], "aviso error" in coordinadora.post("/circulares/nueva", data=caso[1]).get_data(as_text=True))
revisar("las circulares inválidas no se guardan", contar("SELECT id FROM circulares WHERE titulo = 'Aviso'", []) == 0)
coordinadora.post("/circulares/nueva", data={"titulo": "Reunión de familias", "cuerpo": "Todas las familias", "destinatarios": "familias"})
familias = base_datos.consultar_uno("SELECT * FROM circulares WHERE titulo = 'Reunión de familias'", [])
revisar("la coordinadora publica para las familias", familias is not None and familias["grupo_id"] is None)
revisar("la recibe la acudiente", "Reunión de familias" in madre.get("/circulares").get_data(as_text=True))
revisar("no la recibe la estudiante", destino(estudiante.get("/circulares/" + str(familias["id"]))) == "/inicio")
entrar("secretaria").post("/circulares/nueva", data={"titulo": "Horario de secretaría", "cuerpo": "x", "destinatarios": "todos"})
revisar("la secretaria publica para todos", contar("SELECT id FROM circulares WHERE titulo = 'Horario de secretaría'", []) == 1)

print("Agenda")
html = madre.get("/agenda").get_data(as_text=True)
revisar("la acudiente ve la entrega de boletines y la escuela para familias", "Entrega de boletines" in html and "Escuela para familias" in html)
revisar("la acudiente no ve eventos de docentes", "Comisión de evaluación" not in html)
revisar("la acudiente no puede crear eventos", "Agregar un evento" not in html)
docente = entrar("c.munoz")
html = docente.get("/agenda").get_data(as_text=True)
revisar("la docente ve eventos de docentes en los pasados", "Comisión de evaluación" in html and "Ya pasaron este año" in html)
revisar("la docente no ve eventos de familias", "Escuela para familias" not in html)
html = estudiante.get("/agenda").get_data(as_text=True)
revisar("la estudiante ve la ceremonia de grado", "Ceremonia de grado" in html and "Comisión" not in html)
html = rectora.get("/agenda").get_data(as_text=True)
revisar("la rectora ve todos los eventos y puede crearlos", "Comisión" in html and "Escuela para familias" in html and "Agregar un evento" in html)
revisar("portería ve la agenda general", "Ceremonia de grado" in entrar("porteria").get("/agenda").get_data(as_text=True))
secretaria = entrar("secretaria")
nuevo = {"titulo": "Izada de bandera", "fecha": "2026-11-20", "hora": "07:00", "lugar": "Patio", "descripcion": "", "para": "todos"}
casos = [["sin nombre", "titulo", ""], ["con fecha inválida", "fecha", "20-11-2026"], ["con hora inválida", "hora", "7am"],
         ["para nadie", "para", "vecinos"]]
for caso in casos:
    formulario = dict(nuevo)
    formulario[caso[1]] = caso[2]
    revisar("no crea un evento " + caso[0], "aviso error" in secretaria.post("/agenda", data=formulario).get_data(as_text=True))
html = secretaria.post("/agenda", data=nuevo).get_data(as_text=True)
evento = base_datos.consultar_uno("SELECT * FROM eventos WHERE titulo = 'Izada de bandera'", [])
revisar("la secretaria crea un evento", "Evento agregado" in html and evento is not None and evento["colegio_id"] == 1)
revisar("el evento aparece a los estudiantes", "Izada de bandera" in estudiante.get("/agenda").get_data(as_text=True))
revisar("una docente no crea eventos", destino(docente.post("/agenda", data={"titulo": "X", "fecha": "2026-12-01", "para": "todos"})) == "/inicio")
revisar("una acudiente no crea eventos", destino(madre.post("/agenda", data={"titulo": "X", "fecha": "2026-12-01", "para": "todos"})) == "/inicio")
revisar("los eventos sin permiso no se guardan", contar("SELECT id FROM eventos WHERE titulo = 'X'", []) == 0)
revisar("una docente no borra eventos", destino(docente.post("/agenda/" + str(evento["id"]) + "/borrar")) == "/inicio")
revisar("el evento sigue ahí", contar("SELECT id FROM eventos WHERE id = ?", [evento["id"]]) == 1)
respuesta = entrar("orientadora").post("/agenda/" + str(evento["id"]) + "/borrar")
revisar("la orientadora borra el evento", destino(respuesta) == "/agenda?borrado=1" and contar("SELECT id FROM eventos WHERE id = ?", [evento["id"]]) == 0)
revisar("el borrado queda registrado", contar("SELECT id FROM registro_accesos WHERE accion = 'Borró un evento de la agenda'", []) == 1)

print("Aislamiento entre colegios")
otro = base_datos.ejecutar("INSERT INTO colegios (nombre, nombre_corto, municipio, departamento, anio) VALUES (?, ?, ?, ?, ?)",
                           ["Colegio de Génova", "Colegio Génova", "Génova", "Quindío", 2026])
rector_otro = base_datos.ejecutar("INSERT INTO usuarios (colegio_id, usuario, clave, nombre) VALUES (?, ?, ?, ?)",
                                  [otro, "rector.otro", clave, "Rector de Génova"])
base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [rector_otro, "rector"])
sede = base_datos.ejecutar("INSERT INTO sedes (colegio_id, nombre, jornada) VALUES (?, ?, ?)", [otro, "Principal", "Mañana"])
grado = base_datos.ejecutar("INSERT INTO grados (colegio_id, nombre, nivel, orden) VALUES (?, ?, ?, ?)", [otro, "Once", "Media", 11])
grupo_otro = base_datos.ejecutar("INSERT INTO grupos (colegio_id, anio, grado_id, sede_id, nombre) VALUES (?, ?, ?, ?, ?)",
                                 [otro, 2026, grado, sede, "11-G"])
ajena = base_datos.ejecutar(
    "INSERT INTO circulares (colegio_id, titulo, cuerpo, autor_id, publicada_en, destinatarios) VALUES (?, ?, ?, ?, ?, ?)",
    [otro, "Circular de Génova", "x", rector_otro, "2026-11-15 08:00", "todos"])
evento_ajeno = base_datos.ejecutar("INSERT INTO eventos (colegio_id, titulo, fecha, para) VALUES (?, ?, ?, ?)",
                                   [otro, "Feria de Génova", "2026-12-10", "todos"])
revisar("no abre circulares de otro colegio", destino(madre.get("/circulares/" + str(ajena))) == "/inicio")
revisar("un directivo no abre circulares de otro colegio", destino(rectora.get("/circulares/" + str(ajena))) == "/inicio")
revisar("no lista circulares de otro colegio", "Circular de Génova" not in rectora.get("/circulares").get_data(as_text=True))
revisar("abrir una circular ajena no la marca leída", contar("SELECT id FROM lecturas_circular WHERE circular_id = ?", [ajena]) == 0)
coordinadora.post("/circulares/nueva", data={"titulo": "Grupo ajeno", "cuerpo": "x", "destinatarios": "grupo", "grupo_id": str(grupo_otro)})
revisar("no publica a un grupo de otro colegio", contar("SELECT id FROM circulares WHERE titulo = 'Grupo ajeno'", []) == 0)
revisar("no ve eventos de otro colegio", "Feria de Génova" not in rectora.get("/agenda").get_data(as_text=True))
revisar("no borra eventos de otro colegio", destino(rectora.post("/agenda/" + str(evento_ajeno) + "/borrar")) == "/inicio"
        and contar("SELECT id FROM eventos WHERE id = ?", [evento_ajeno]) == 1)
rector_genova = entrar("rector.otro")
revisar("el otro colegio no abre circulares del piloto", destino(rector_genova.get("/circulares/1")) == "/inicio")
revisar("el otro colegio solo ve su agenda", "Feria de Génova" in rector_genova.get("/agenda").get_data(as_text=True)
        and "Ceremonia de grado" not in rector_genova.get("/agenda").get_data(as_text=True))

ayuda.terminar()
