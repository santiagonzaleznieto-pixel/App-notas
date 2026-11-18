import ayuda
from ayuda import entrar, revisar, destino
import modulo_inicio
import modulo_notas
import modulo_asistencia
import modulo_observador
import base_datos
import nucleo
from werkzeug.security import generate_password_hash


def hoy_de_prueba():
    return "2026-11-17"


nucleo.hoy = hoy_de_prueba


def contar(sql, valores):
    return base_datos.consultar_uno("SELECT COUNT(*) AS total FROM " + sql, valores)["total"]


def observacion(observacion_id):
    return base_datos.consultar_uno("SELECT * FROM observaciones WHERE id = ?", [observacion_id])


def paso(paso_id):
    return base_datos.consultar_uno("SELECT * FROM pasos_protocolo WHERE id = ?", [paso_id])


def ultima_observacion():
    return base_datos.consultar_uno("SELECT * FROM observaciones ORDER BY id DESC LIMIT 1", [])


print("Datos de ejemplo")
revisar("hay 4 anotaciones de ejemplo", contar("observaciones", []) == 4)
revisar("hay una positiva para Melany", contar("observaciones WHERE estudiante_id = 13 AND tipo = 'positiva'", []) == 1)
revisar("hay una por mejorar para Andrés", contar("observaciones WHERE estudiante_id = 25 AND tipo = 'por_mejorar'", []) == 1)
revisar("el caso tipo I tiene 4 pasos y 2 hechos",
        contar("pasos_protocolo WHERE observacion_id = 3", []) == 4 and contar("pasos_protocolo WHERE observacion_id = 3 AND hecho = 1", []) == 2)
caso_dos = observacion(4)
revisar("el caso tipo II es confidencial, abierto y sin reportar",
        caso_dos["situacion_tipo"] == 2 and caso_dos["confidencial"] == 1 and caso_dos["estado"] == "abierta" and caso_dos["reportado_siuce"] == 0)
revisar("el caso tipo II tiene los 7 pasos del protocolo", contar("pasos_protocolo WHERE observacion_id = 4", []) == 7)

print("Permisos")
anonimo = ayuda.app.test_client()
revisar("sin sesión no se entra al observador", destino(anonimo.get("/observador")) == "/inicio")
estudiante = entrar("melany.osorio")
revisar("la estudiante no entra al buscador", destino(estudiante.get("/observador")) == "/inicio")
revisar("la estudiante no entra a convivencia", destino(estudiante.get("/convivencia")) == "/inicio")
html = estudiante.get("/observador/estudiante/13").get_data(as_text=True)
revisar("la estudiante ve su observador", "río Lejos" in html and "Nueva anotación" not in html)
revisar("la estudiante no ve el de un compañero", destino(estudiante.get("/observador/estudiante/14")) == "/inicio")
docente = entrar("c.munoz")
html = docente.get("/observador").get_data(as_text=True)
revisar("la docente busca estudiantes de los grupos donde dicta", "Melany Osorio" in html and "Esteban Ramírez" in html)
revisar("la docente no entra a convivencia", destino(docente.get("/convivencia")) == "/inicio")
html = docente.get("/observador/estudiante/13").get_data(as_text=True)
revisar("la docente puede anotar a un estudiante de su clase", "Nueva anotación" in html)
revisar("la docente solo ve sus propias anotaciones", "río Lejos" not in html and "Solo ves las anotaciones que tú escribiste" in html)
revisar("la docente no ofrece tipo II ni confidencial", 'value="2"' not in html and 'name="confidencial"' not in html)
revisar("la docente ve su anotación de Andrés", "talleres de Matemáticas" in docente.get("/observador/estudiante/25").get_data(as_text=True))
revisar("la docente no abre casos ajenos", destino(docente.get("/observador/caso/3")) == "/inicio")
profesor_fisica = entrar("w.tapasco")
html = profesor_fisica.get("/observador/caso/3").get_data(as_text=True)
revisar("el autor docente abre su caso tipo I", "microfútbol" in html and "Agregar seguimiento" in html)
revisar("el autor docente no gestiona el protocolo", "Cerrar caso" not in html and 'name="paso_id"' not in html)
director = entrar("h.aguirre")
revisar("el director ve el caso tipo I de su grupo", "microfútbol" in director.get("/observador/estudiante/14").get_data(as_text=True))
html = director.get("/observador/caso/3").get_data(as_text=True)
revisar("el director abre el caso de su grupo sin gestionarlo", "microfútbol" in html and "Cerrar caso" not in html and "Agregar seguimiento" not in html)
html = director.get("/observador/estudiante/23").get_data(as_text=True)
revisar("el director anota en otro grupo pero no ve sus casos", "WhatsApp" not in html and "Solo ves las anotaciones" in html)
revisar("el director no abre el caso confidencial", destino(director.get("/observador/caso/4")) == "/inicio")
directora_once = entrar("s.grajales")
html = directora_once.get("/observador/estudiante/23").get_data(as_text=True)
revisar("la directora no ve el caso confidencial pero sabe que existe", "WhatsApp" not in html and "en manejo por coordinación" in html)
revisar("la directora no abre el caso confidencial", destino(directora_once.get("/observador/caso/4")) == "/inicio")
madre = entrar("olga.gomez")
html = madre.get("/observador/estudiante/23").get_data(as_text=True)
revisar("la acudiente no ve el caso tipo II", "WhatsApp" not in html and "en manejo por coordinación" in html)
revisar("la acudiente no abre el caso", destino(madre.get("/observador/caso/4")) == "/inicio")
revisar("la acudiente no ve otros estudiantes", destino(madre.get("/observador/estudiante/13")) == "/inicio")
revisar("el estudiante tampoco ve su caso tipo II", "WhatsApp" not in entrar("esteban.ramirez").get("/observador/estudiante/23").get_data(as_text=True))
orientadora = entrar("orientadora")
html = orientadora.get("/observador/estudiante/23").get_data(as_text=True)
revisar("la orientadora ve el caso confidencial", "WhatsApp" in html and "Confidencial" in html)
administradora = entrar("admin")
html = administradora.get("/observador/estudiante/23").get_data(as_text=True)
revisar("la administradora ve el observador pero no lo confidencial", "WhatsApp" not in html and "Nueva anotación" not in html)
revisar("la administradora no entra a convivencia", destino(administradora.get("/convivencia")) == "/inicio")
revisar("la secretaria no entra al observador", destino(entrar("secretaria").get("/observador")) == "/inicio")

print("Anotaciones")
nueva = {"tipo": "positiva", "situacion_tipo": "1", "descripcion": "Excelente exposición sobre funciones cuadráticas.", "compromiso": ""}
respuesta = docente.post("/observador/estudiante/13", data=nueva)
revisar("la docente guarda una anotación positiva", "guardada=1" in destino(respuesta))
revisar("la anotación queda con su autora", ultima_observacion()["autor_id"] == 5 and ultima_observacion()["tipo"] == "positiva")
total = contar("observaciones", [])
html = docente.post("/observador/estudiante/13", data={"tipo": "situacion", "situacion_tipo": "2", "descripcion": "Pelea fuerte en el descanso."}).get_data(as_text=True)
revisar("la docente no registra tipo II", "tipo II y III las registra" in html)
html = docente.post("/observador/estudiante/13", data={"tipo": "positiva", "descripcion": "Ayudó a un compañero.", "confidencial": "1"}).get_data(as_text=True)
revisar("la docente no marca confidencial", "pueden marcar una anotación como confidencial" in html)
html = docente.post("/observador/estudiante/13", data={"tipo": "chisme", "descripcion": "Texto de prueba largo."}).get_data(as_text=True)
revisar("un tipo inválido da error", "Elige el tipo" in html)
html = docente.post("/observador/estudiante/13", data={"tipo": "situacion", "situacion_tipo": "7", "descripcion": "Texto de prueba largo."}).get_data(as_text=True)
revisar("un tipo de situación inválido da error", "tipo I, II o III" in html)
html = docente.post("/observador/estudiante/13", data={"tipo": "positiva", "descripcion": "corta"}).get_data(as_text=True)
revisar("la descripción debe tener al menos 10 caracteres", "mínimo 10" in html)
revisar("con errores no se guarda nada", contar("observaciones", []) == total)
respuesta = docente.post("/observador/estudiante/13", data={"tipo": "situacion", "situacion_tipo": "1",
                                                            "descripcion": "Discusión con un compañero por un puesto en el salón."})
caso_docente = ultima_observacion()
revisar("la docente registra una situación tipo I y va al caso", destino(respuesta) == "/observador/caso/" + str(caso_docente["id"]) + "?creado=1")
revisar("la situación queda abierta con los 4 pasos del tipo I",
        caso_docente["estado"] == "abierta" and contar("pasos_protocolo WHERE observacion_id = ?", [caso_docente["id"]]) == 4)
ruta_caso = "/observador/caso/" + str(caso_docente["id"])
revisar("la docente abre su caso", "Caso registrado" in docente.get(ruta_caso + "?creado=1").get_data(as_text=True))
respuesta = docente.post(ruta_caso, data={"accion": "seguimiento", "texto": "Hablé con los dos y se dieron la mano."})
revisar("la docente agrega seguimiento a su caso", "seguimiento=1" in destino(respuesta)
        and contar("seguimientos WHERE observacion_id = ? AND autor_id = 5", [caso_docente["id"]]) == 1)
html = docente.post(ruta_caso, data={"accion": "seguimiento", "texto": "ok"}).get_data(as_text=True)
revisar("el seguimiento no puede estar vacío", "mínimo 5" in html)
primer_paso = base_datos.consultar_uno("SELECT id FROM pasos_protocolo WHERE observacion_id = ? ORDER BY id", [caso_docente["id"]])["id"]
html = docente.post(ruta_caso, data={"accion": "paso", "paso_id": str(primer_paso), "hecho": "1"}).get_data(as_text=True)
revisar("la docente no marca pasos", "Solo coordinación" in html and paso(primer_paso)["hecho"] == 0)
docente.post(ruta_caso, data={"accion": "cerrar"})
revisar("la docente no cierra casos", observacion(caso_docente["id"])["estado"] == "abierta")
total = contar("observaciones", [])
revisar("la estudiante no escribe en el observador", destino(estudiante.post("/observador/estudiante/13", data=nueva)) == "/inicio")
revisar("la acudiente no escribe en el observador", destino(entrar("gloria.cardenas").post("/observador/estudiante/13", data=nueva)) == "/inicio")
revisar("no se guardó nada de familia", contar("observaciones", []) == total)
coordinadora = entrar("coordinadora")
coordinadora.post("/observador/estudiante/23", data={"tipo": "situacion", "situacion_tipo": "2",
                                                     "descripcion": "Esteban y Kevin se golpearon en el descanso; Kevin tiene un raspón en el brazo."})
caso_abierto = ultima_observacion()
revisar("la coordinadora registra un tipo II con sus 7 pasos",
        caso_abierto["situacion_tipo"] == 2 and caso_abierto["confidencial"] == 0
        and contar("pasos_protocolo WHERE observacion_id = ?", [caso_abierto["id"]]) == 7)
coordinadora.post("/observador/estudiante/14", data={"tipo": "situacion", "situacion_tipo": "3", "confidencial": "1",
                                                     "descripcion": "Se recibió denuncia por amenazas graves contra el estudiante."})
caso_tres = ultima_observacion()
revisar("la coordinadora registra un tipo III confidencial con sus 6 pasos",
        caso_tres["situacion_tipo"] == 3 and caso_tres["confidencial"] == 1
        and contar("pasos_protocolo WHERE observacion_id = ?", [caso_tres["id"]]) == 6)
html = madre.get("/observador/estudiante/23").get_data(as_text=True)
revisar("la familia no ve un tipo II aunque no sea confidencial", "raspón" not in html and "Hay 2 casos de convivencia" in html)
html = directora_once.get("/observador/estudiante/23").get_data(as_text=True)
revisar("la directora ve el tipo II no confidencial de su grupo", "raspón" in html and "WhatsApp" not in html)
html = entrar("jorge.restrepo").get("/observador/estudiante/14").get_data(as_text=True)
revisar("la familia ve el tipo I pero no el tipo III", "microfútbol" in html and "amenazas" not in html and "en manejo por coordinación" in html)

print("Casos y protocolo")
html = coordinadora.get("/observador/caso/4").get_data(as_text=True)
revisar("la coordinadora abre el caso confidencial", "WhatsApp" in html and "Sin reportar en el SIUCE" in html)
coordinadora.post("/observador/caso/4", data={"accion": "paso", "paso_id": "5", "hecho": "1"})
revisar("marca un paso como hecho", paso(5)["hecho"] == 1 and paso(5)["hecho_por"] == 3)
html = coordinadora.post("/observador/caso/4", data={"accion": "paso", "paso_id": "1", "hecho": "0"}).get_data(as_text=True)
revisar("no cambia pasos de otro caso", "no pertenece" in html and paso(1)["hecho"] == 1)
coordinadora.post("/observador/caso/4", data={"accion": "paso", "paso_id": "5", "hecho": "0"})
revisar("desmarca un paso", paso(5)["hecho"] == 0 and paso(5)["hecho_por"] is None)
coordinadora.post("/observador/caso/4", data={"accion": "siuce", "valor": "1"})
revisar("marca el caso reportado en el SIUCE", observacion(4)["reportado_siuce"] == 1)
revisar("el reporte queda en los seguimientos", contar("seguimientos WHERE observacion_id = 4 AND texto LIKE '%SIUCE%'", []) == 1)
html = coordinadora.post("/observador/caso/3", data={"accion": "siuce", "valor": "1"}).get_data(as_text=True)
revisar("un tipo I no se reporta en el SIUCE", "Solo las situaciones tipo II y III" in html and observacion(3)["reportado_siuce"] == 0)
coordinadora.post("/observador/caso/4", data={"accion": "cerrar", "nota": "Se cumplieron los compromisos."})
revisar("cierra el caso", observacion(4)["estado"] == "cerrada")
revisar("el cierre queda en los seguimientos", contar("seguimientos WHERE observacion_id = 4 AND texto LIKE 'Cerró el caso.%'", []) == 1)
html = coordinadora.post("/observador/caso/4", data={"accion": "paso", "paso_id": "5", "hecho": "1"}).get_data(as_text=True)
revisar("con el caso cerrado no se cambian pasos", "Reábrelo" in html and paso(5)["hecho"] == 0)
html = coordinadora.post("/observador/caso/4", data={"accion": "cerrar"}).get_data(as_text=True)
revisar("no se cierra dos veces", "ya está cerrado" in html)
coordinadora.post("/observador/caso/4", data={"accion": "reabrir"})
revisar("reabre el caso", observacion(4)["estado"] == "abierta")
html = coordinadora.post("/observador/caso/4", data={"accion": "volar"}).get_data(as_text=True)
revisar("una acción inválida da error", "Acción no válida" in html)
html = coordinadora.post("/observador/caso/1", data={"accion": "cerrar"}).get_data(as_text=True)
revisar("una anotación positiva no se gestiona como caso", "no es un caso" in html)
orientadora.post("/observador/caso/3", data={"accion": "paso", "paso_id": "3", "hecho": "1"})
revisar("la orientadora también gestiona casos", paso(3)["hecho"] == 1 and paso(3)["hecho_por"] == 12)
coordinadora.post("/observador/caso/3", data={"accion": "cerrar"})

print("Convivencia")
html = coordinadora.get("/convivencia").get_data(as_text=True)
revisar("el tablero muestra los casos pendientes del SIUCE", "Pendientes de reportar en el SIUCE" in html and "/observador/caso/" + str(caso_abierto["id"]) in html)
revisar("el caso ya reportado no está pendiente", html.count('href="/observador/caso/4"') == 1)
revisar("el tablero muestra los casos cerrados", "Últimos casos cerrados" in html and "Juan Pablo Restrepo" in html)
revisar("el tablero cuenta las anotaciones del año", "Situación tipo III" in html)
revisar("la rectora entra a convivencia", entrar("rectora").get("/convivencia").status_code == 200)
revisar("la orientadora entra a convivencia", orientadora.get("/convivencia").status_code == 200)
revisar("el director no entra a convivencia", destino(director.get("/convivencia")) == "/inicio")

print("Búsqueda")
html = director.get("/observador?q=sharon").get_data(as_text=True)
revisar("busca por nombre", "Sharon Daniela Loaiza" in html and "Laura Sofía Patiño" not in html)
revisar("busca sin importar tildes", "Andrés Felipe Quintero" in coordinadora.get("/observador?q=andres").get_data(as_text=True))
html = coordinadora.get("/observador?grupo=2").get_data(as_text=True)
revisar("filtra por grupo", "Kevin Stiven Largo" in html and "Laura Sofía Patiño" not in html)
html = director.get("/observador").get_data(as_text=True)
revisar("las últimas anotaciones respetan los permisos", "WhatsApp" not in html and "amenazas" not in html)

print("Aislamiento entre colegios")
otro = base_datos.ejecutar("INSERT INTO colegios (nombre, nombre_corto, municipio, departamento, anio) VALUES (?, ?, ?, ?, ?)",
                           ["Colegio de prueba", "Col. prueba", "Génova", "Quindío", 2026])
clave = generate_password_hash("pijao2026")
orientador_otro = base_datos.ejecutar("INSERT INTO usuarios (colegio_id, usuario, clave, nombre) VALUES (?, ?, ?, ?)",
                                      [otro, "orienta.otro", clave, "Orientador de otro colegio"])
base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [orientador_otro, "orientador"])
alumno = base_datos.ejecutar("INSERT INTO usuarios (colegio_id, usuario, clave, nombre) VALUES (?, ?, ?, ?)",
                             [otro, "alumno.otro", clave, "Alumno de otro colegio"])
base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [alumno, "estudiante"])
caso_otro = modulo_observador.crear_observacion({
    "colegio_id": otro, "estudiante_id": alumno, "autor_id": orientador_otro, "fecha": "2026-11-16", "tipo": "situacion",
    "situacion_tipo": 2, "descripcion": "Caso secreto del otro colegio.", "compromiso": "", "confidencial": 0,
    "creado_en": "2026-11-16 08:00",
})
paso_otro = base_datos.consultar_uno("SELECT id FROM pasos_protocolo WHERE observacion_id = ? ORDER BY id", [caso_otro])["id"]
revisar("la coordinadora no ve estudiantes de otro colegio", destino(coordinadora.get("/observador/estudiante/" + str(alumno))) == "/inicio")
revisar("la coordinadora no abre casos de otro colegio", destino(coordinadora.get("/observador/caso/" + str(caso_otro))) == "/inicio")
coordinadora.post("/observador/caso/" + str(caso_otro), data={"accion": "cerrar"})
revisar("la coordinadora no cierra casos de otro colegio", observacion(caso_otro)["estado"] == "abierta")
html = coordinadora.post("/observador/caso/4", data={"accion": "paso", "paso_id": str(paso_otro), "hecho": "1"}).get_data(as_text=True)
revisar("no marca pasos de otro colegio", "no pertenece" in html and paso(paso_otro)["hecho"] == 0)
revisar("el tablero no muestra casos de otro colegio", "Caso secreto" not in coordinadora.get("/convivencia").get_data(as_text=True))
otro_orientador = entrar("orienta.otro")
revisar("el orientador de otro colegio no abre casos del piloto", destino(otro_orientador.get("/observador/caso/4")) == "/inicio")
revisar("el orientador de otro colegio no ve estudiantes del piloto", destino(otro_orientador.get("/observador/estudiante/23")) == "/inicio")
html = otro_orientador.get("/convivencia").get_data(as_text=True)
revisar("el orientador de otro colegio solo ve sus casos", "Caso secreto" not in html and "Alumno de otro colegio" in html and "Esteban" not in html)

ayuda.terminar()
