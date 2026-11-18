import ayuda
from ayuda import entrar, revisar, destino
import nucleo
from werkzeug.security import generate_password_hash


def hoy_de_prueba():
    return "2026-11-17"


def ahora_de_prueba():
    return "2026-11-17 10:30"


nucleo.hoy = hoy_de_prueba
nucleo.ahora = ahora_de_prueba

import modulo_inicio
import modulo_notas
import modulo_servicios
import base_datos


def texto(respuesta):
    return respuesta.get_data(as_text=True)


def contar(sql, valores):
    return base_datos.consultar_uno("SELECT COUNT(*) AS total FROM " + sql, valores)["total"]


def ultimo_registro():
    return base_datos.consultar_uno("SELECT * FROM registro_accesos ORDER BY id DESC LIMIT 1", [])


print("Datos de ejemplo")
revisar("siembra 12 libros", contar("libros WHERE colegio_id = 1", []) == 12)
revisar("siembra 3 préstamos", contar("prestamos WHERE colegio_id = 1", []) == 3)
revisar("siembra 2 fichas de salud", contar("fichas_salud", []) == 2)
revisar("siembra una atención de ayer", contar("atenciones_enfermeria WHERE fecha = '2026-11-16'", []) == 1)
revisar("siembra 2 autorizados para Melany", contar("autorizados_recoger WHERE estudiante_id = 13", []) == 2)
revisar("siembra una salida y un visitante de hoy",
        contar("salidas WHERE fecha = '2026-11-17'", []) == 1 and contar("ingresos_visitantes WHERE fecha = '2026-11-17'", []) == 1)
revisar("valida fechas sin try", modulo_servicios.fecha_valida("2028-02-29") and not modulo_servicios.fecha_valida("2026-02-29")
        and not modulo_servicios.fecha_valida("2026-13-01") and not modulo_servicios.fecha_valida("17/11/2026"))

print("Otro colegio para probar el aislamiento")
otro_colegio = base_datos.ejecutar(
    "INSERT INTO colegios (nombre, nombre_corto, municipio, departamento, anio) VALUES (?, ?, ?, ?, ?)",
    ["Colegio de Prueba", "C. Prueba", "Génova", "Quindío", 2026],
)
clave = generate_password_hash("pijao2026")
ajenos = {}
for usuario, rol in [("enfermera.dos", "enfermeria"), ("porteria.dos", "porteria"), ("biblio.dos", "bibliotecario"),
                     ("estudiante.dos", "estudiante")]:
    ajenos[usuario] = base_datos.ejecutar("INSERT INTO usuarios (colegio_id, usuario, clave, nombre) VALUES (?, ?, ?, ?)",
                                          [otro_colegio, usuario, clave, "Persona " + usuario])
    base_datos.ejecutar("INSERT INTO roles_usuario (usuario_id, rol) VALUES (?, ?)", [ajenos[usuario], rol])
libro_ajeno = base_datos.ejecutar("INSERT INTO libros (colegio_id, titulo, ejemplares) VALUES (?, ?, ?)",
                                  [otro_colegio, "Libro del otro colegio", 2])
prestamo_ajeno = base_datos.ejecutar(
    "INSERT INTO prestamos (colegio_id, libro_id, usuario_id, prestado_en, fecha_devolucion) VALUES (?, ?, ?, ?, ?)",
    [otro_colegio, libro_ajeno, ajenos["estudiante.dos"], "2026-11-10", "2026-11-18"],
)

print("Biblioteca: permisos")
melany = entrar("melany.osorio")
respuesta = melany.get("/biblioteca")
html = texto(respuesta)
revisar("la estudiante ve el catálogo", respuesta.status_code == 200 and "Cien años de soledad" in html)
revisar("la estudiante ve sus préstamos", "Mis préstamos" in html and "Faltan 5 días" in html)
revisar("la estudiante no ve la gestión", "Agregar libro" not in html and "Préstamos vencidos" not in html)
revisar("la estudiante no puede prestar", destino(melany.get("/biblioteca/prestar")) == "/inicio")
revisar("la estudiante no puede crear libros",
        destino(melany.post("/biblioteca/libro/nuevo", data={"titulo": "Pirata", "ejemplares": "1"})) == "/inicio"
        and contar("libros WHERE titulo = 'Pirata'", []) == 0)
revisar("la estudiante no puede recibir devoluciones",
        destino(melany.post("/biblioteca/devolver/1")) == "/inicio")
juan = entrar("juan.restrepo")
html = texto(juan.get("/biblioteca"))
revisar("el préstamo vencido de Juan se resalta", "fila-vencida" in html and "Vencido hace 12 días" in html)
docente = entrar("a.trejos")
revisar("el docente ve su préstamo", "Crónica de una muerte anunciada" in texto(docente.get("/biblioteca")))
revisar("una acudiente no entra a la biblioteca", destino(entrar("gloria.cardenas").get("/biblioteca")) == "/inicio")
revisar("portería no entra a la biblioteca", destino(entrar("porteria").get("/biblioteca")) == "/inicio")
html = texto(melany.get("/biblioteca?buscar=vorágine"))
revisar("el buscador filtra por título", "La vorágine" in html and "Delirio" not in html)
html = texto(melany.get("/biblioteca?buscar=Isaacs"))
revisar("el buscador filtra por autor", "María" in html and "Delirio" not in html)

print("Biblioteca: gestión")
biblio = entrar("biblioteca")
html = texto(biblio.get("/biblioteca"))
revisar("la bibliotecaria ve los vencidos con días de retraso",
        "Préstamos vencidos" in html and "Juan Pablo Restrepo" in html and "12 días" in html)
revisar("los ejemplares disponibles descuentan los préstamos", "3 de 4" in html)
html = texto(biblio.post("/biblioteca/libro/nuevo", data={"titulo": "", "ejemplares": "-1"}))
revisar("un libro sin título da error", "Escribe el título" in html)
revisar("ejemplares negativos dan error", "número entero" in html)
html = texto(biblio.post("/biblioteca/libro/nuevo", data={"titulo": "Libro", "ejemplares": "1", "isbn": "12345"}))
revisar("un ISBN mal escrito da error", "ISBN" in html and contar("libros WHERE titulo = 'Libro'", []) == 0)
respuesta = biblio.post("/biblioteca/libro/nuevo", data={"titulo": "Cóndores no entierran todos los días", "autor": "Gustavo Álvarez Gardeazábal",
                                                       "ejemplares": "1", "isbn": "978-958-42-0000-1", "ubicacion": "Estante A3"})
nuevo = base_datos.consultar_uno("SELECT * FROM libros WHERE titulo LIKE 'Cóndores%'", [])
revisar("la bibliotecaria agrega un libro", destino(respuesta).startswith("/biblioteca") and nuevo is not None
        and nuevo["colegio_id"] == 1 and nuevo["isbn"] == "9789584200001")
vorágine = base_datos.consultar_uno("SELECT id FROM libros WHERE titulo = 'La vorágine'", [])["id"]
html = texto(biblio.post("/biblioteca/libro/" + str(vorágine), data={"titulo": "La vorágine", "ejemplares": "0", "activo": "1"}))
revisar("no deja menos ejemplares que los prestados", "no puedes dejar menos" in html)
revisar("el formulario de préstamo propone 8 días", 'value="2026-11-25"' in texto(biblio.get("/biblioteca/prestar?persona=sharon")))
revisar("la búsqueda de personas solo muestra el colegio", "Persona estudiante.dos" not in texto(biblio.get("/biblioteca/prestar?persona=Persona")))

html = texto(biblio.post("/biblioteca/prestar", data={"persona_id": "14", "libro_id": "2", "fecha_devolucion": "2026-11-25"}))
revisar("no presta a quien tiene vencidos", "préstamos vencidos" in html and contar("prestamos WHERE usuario_id = 14", []) == 1)
html = texto(biblio.post("/biblioteca/prestar", data={"persona_id": "15", "libro_id": "2", "fecha_devolucion": "2026-02-30"}))
revisar("una fecha inválida da error", "no es válida" in html)
html = texto(biblio.post("/biblioteca/prestar", data={"persona_id": "15", "libro_id": "2", "fecha_devolucion": "2026-11-17"}))
revisar("la devolución debe ser después de hoy", "entre mañana" in html)
respuesta = biblio.post("/biblioteca/prestar", data={"persona_id": "15", "libro_id": str(nuevo["id"]), "fecha_devolucion": "2026-11-25"})
revisar("presta un libro", destino(respuesta).startswith("/biblioteca")
        and contar("prestamos WHERE usuario_id = 15 AND libro_id = ? AND prestado_por = 33", [nuevo["id"]]) == 1)
html = texto(biblio.post("/biblioteca/prestar", data={"persona_id": "16", "libro_id": str(nuevo["id"]), "fecha_devolucion": "2026-11-25"}))
revisar("no presta si no hay ejemplares", "No hay ejemplares disponibles" in html and contar("prestamos WHERE usuario_id = 16", []) == 0)
html = texto(biblio.post("/biblioteca/prestar", data={"persona_id": str(ajenos["estudiante.dos"]), "libro_id": "2",
                                                    "fecha_devolucion": "2026-11-25"}))
revisar("no presta a personas de otro colegio", "Elige a la persona" in html
        and contar("prestamos WHERE usuario_id = ?", [ajenos["estudiante.dos"]]) == 1)
html = texto(biblio.post("/biblioteca/prestar", data={"persona_id": "16", "libro_id": str(libro_ajeno), "fecha_devolucion": "2026-11-25"}))
revisar("no presta libros de otro colegio", "Elige un libro" in html)
revisar("no edita libros de otro colegio", destino(biblio.get("/biblioteca/libro/" + str(libro_ajeno))) == "/inicio")
biblio.post("/biblioteca/devolver/" + str(prestamo_ajeno))
revisar("no recibe préstamos de otro colegio",
        base_datos.consultar_uno("SELECT devuelto_en FROM prestamos WHERE id = ?", [prestamo_ajeno])["devuelto_en"] == "")

prestamo_juan = base_datos.consultar_uno("SELECT id FROM prestamos WHERE usuario_id = 14", [])["id"]
respuesta = biblio.post("/biblioteca/devolver/" + str(prestamo_juan))
revisar("recibe la devolución", destino(respuesta) == "/biblioteca?aviso=devuelto"
        and base_datos.consultar_uno("SELECT devuelto_en FROM prestamos WHERE id = ?", [prestamo_juan])["devuelto_en"] == "2026-11-17")
revisar("deja constancia en el registro", ultimo_registro()["accion"] == "Recibió la devolución de un libro")
respuesta = biblio.post("/biblioteca/prestar", data={"persona_id": "14", "libro_id": "2", "fecha_devolucion": "2026-11-25"})
revisar("después de devolver ya puede pedir prestado", destino(respuesta).startswith("/biblioteca"))
revisar("la otra bibliotecaria no ve el catálogo ajeno", "Cien años" not in texto(entrar("biblio.dos").get("/biblioteca")))

print("Enfermería: confidencialidad")
enfermera = entrar("enfermeria")
html = texto(enfermera.get("/enfermeria?buscar=melany"))
revisar("la enfermera busca estudiantes", "Melany Osorio Cárdenas" in html and "Alergias" in html)
html = texto(enfermera.get("/enfermeria/estudiante/13"))
revisar("la enfermera ve la ficha y la alerta", "Penicilina" in html and "Tiene alergias registradas: Penicilina" in html)
revisar("la enfermera ve la atención de ayer", "Dificultad para respirar" in texto(enfermera.get("/enfermeria/estudiante/23")))
for usuario in ["h.aguirre", "c.munoz", "rectora", "coordinadora", "admin", "orientadora", "melany.osorio", "porteria", "biblioteca"]:
    cliente = entrar(usuario)
    revisar(usuario + " no ve fichas de salud",
            destino(cliente.get("/enfermeria")) == "/inicio" and destino(cliente.get("/enfermeria/estudiante/13")) == "/inicio")
director = entrar("h.aguirre")
revisar("el boletín del director no muestra datos de salud", "Penicilina" not in texto(director.get("/boletin/13")))
revisar("el director no ve la ficha de las familias", destino(director.get("/mi-ficha-salud")) == "/inicio")
revisar("portería no ve datos de salud", "Penicilina" not in texto(entrar("porteria").get("/porteria/estudiante/13")))
enfermera_dos = entrar("enfermera.dos")
revisar("la enfermera de otro colegio no ve estudiantes ajenos",
        destino(enfermera_dos.get("/enfermeria/estudiante/13")) == "/inicio"
        and "Melany Osorio" not in texto(enfermera_dos.get("/enfermeria?buscar=melany")))

contexto = ayuda.app.test_request_context()
contexto.push()
nucleo.g.colegio = base_datos.buscar_colegio(1)
revisar("tiene_alergias da la alerta mínima", modulo_servicios.tiene_alergias(13) == "Tiene alergias registradas: Penicilina")
revisar("tiene_alergias no dice nada si no hay alergias", modulo_servicios.tiene_alergias(23) == "")
revisar("tiene_alergias no dice nada sin ficha", modulo_servicios.tiene_alergias(14) == "")
contexto.pop()

print("Enfermería: atenciones")
html = texto(enfermera.post("/enfermeria/estudiante/13", data={"accion": "atencion", "motivo": "", "atencion": "Reposo"}))
revisar("una atención sin motivo da error", "Escribe el motivo" in html)
html = texto(enfermera.post("/enfermeria/estudiante/13", data={"accion": "atencion", "motivo": "Fiebre de 38,5", "atencion": "Paños de agua tibia",
                                                             "envio_a_casa": "1"}))
revisar("no envía a casa sin avisar al acudiente", "Avisé al acudiente" in html and contar("atenciones_enfermeria WHERE estudiante_id = 13", []) == 0)
html = texto(enfermera.post("/enfermeria/estudiante/13", data={"accion": "atencion", "motivo": "Fiebre de 38,5", "atencion": "Paños de agua tibia",
                                                             "envio_a_casa": "1", "acudiente_avisado": "1"}))
atencion = base_datos.consultar_uno("SELECT * FROM atenciones_enfermeria WHERE estudiante_id = 13", [])
revisar("registra la atención con fecha y hora", atencion is not None and atencion["fecha"] == "2026-11-17"
        and atencion["hora"] == "10:30" and atencion["envio_a_casa"] == 1 and atencion["atendido_por"] == 34)
revisar("al enviar a casa muestra el teléfono del acudiente", "Envío a casa registrado" in html and "310 456 7890" in html
        and "Gloria Inés Cárdenas" in html)
revisar("el registro no guarda datos de salud", "Fiebre" not in ultimo_registro()["detalle"]
        and ultimo_registro()["detalle"] == "Melany Osorio Cárdenas")
revisar("aparece en las atenciones de hoy", "Fiebre de 38,5" in texto(enfermera.get("/enfermeria")))
html = texto(enfermera.post("/enfermeria/estudiante/14", data={"accion": "ficha", "contacto_emergencia": "Jorge Iván Restrepo",
                                                             "telefono_emergencia": "abc"}))
revisar("una ficha con teléfono inválido da error", "entre 7 y 15 dígitos" in html and contar("fichas_salud WHERE estudiante_id = 14", []) == 0)
enfermera.post("/enfermeria/estudiante/14", data={"accion": "ficha", "eps": "Sanitas", "tipo_sangre": "B+", "alergias": "Ninguna",
                                                  "contacto_emergencia": "Jorge Iván Restrepo", "telefono_emergencia": "318 222 3344"})
ficha_juan = base_datos.consultar_uno("SELECT * FROM fichas_salud WHERE estudiante_id = 14", [])
revisar("la enfermera registra una ficha", ficha_juan is not None and ficha_juan["colegio_id"] == 1 and ficha_juan["actualizado_por"] == 34)

print("Ficha de salud del acudiente")
madre = entrar("gloria.cardenas")
html = texto(madre.get("/mi-ficha-salud"))
revisar("la madre ve la ficha de su hija", "Penicilina" in html and "Melany Osorio Cárdenas" in html)
revisar("la madre ve las atenciones de su hija", "Fiebre de 38,5" in html)
revisar("la madre no ve la ficha de otro estudiante", destino(madre.get("/mi-ficha-salud?estudiante=14")) == "/inicio")
datos_ficha = {"estudiante_id": "13", "eps": "Nueva EPS", "tipo_sangre": "O+", "alergias": "Penicilina y mariscos",
               "condiciones": "", "medicamentos": "", "contacto_emergencia": "Gloria Inés Cárdenas", "telefono_emergencia": "310 456 7890"}
html = texto(madre.post("/mi-ficha-salud", data=datos_ficha))
revisar("pide la autorización de datos sensibles", "autorización" in html
        and base_datos.consultar_uno("SELECT alergias FROM fichas_salud WHERE estudiante_id = 13", [])["alergias"] == "Penicilina")
datos_ficha["autorizo"] = "1"
datos_ficha["tipo_sangre"] = "Z+"
revisar("valida el tipo de sangre", "tipo de sangre" in texto(madre.post("/mi-ficha-salud", data=datos_ficha)))
datos_ficha["tipo_sangre"] = "O+"
html = texto(madre.post("/mi-ficha-salud", data=datos_ficha))
ficha = base_datos.consultar_uno("SELECT * FROM fichas_salud WHERE estudiante_id = 13", [])
revisar("la madre actualiza la ficha", "guardada" in html and ficha["alergias"] == "Penicilina y mariscos" and ficha["actualizado_por"] == 29)
datos_ficha["estudiante_id"] = "23"
revisar("la madre no puede cambiar la ficha de otro estudiante", destino(madre.post("/mi-ficha-salud", data=datos_ficha)) == "/inicio"
        and base_datos.consultar_uno("SELECT alergias FROM fichas_salud WHERE estudiante_id = 23", [])["alergias"] == "")
html = texto(entrar("olga.gomez").get("/mi-ficha-salud"))
revisar("cada acudiente ve solo a sus hijos", "Salbutamol" in html and "Penicilina" not in html)
revisar("la estudiante no ve la página de acudientes", destino(melany.get("/mi-ficha-salud")) == "/inicio")

print("Portería")
portero = entrar("porteria")
html = texto(portero.get("/porteria"))
revisar("portería ve las salidas y visitantes de hoy", "Rosalba Cárdenas Arango" in html and "Ana María Bedoya" in html)
revisar("busca estudiantes", "Melany Osorio Cárdenas" in texto(portero.get("/porteria?buscar=osorio")))
html = texto(portero.get("/porteria/estudiante/13"))
revisar("muestra el grupo y los autorizados", "10-A" in html and "Rosalba Cárdenas Arango" in html and "Carlos Mario Osorio" in html)
revisar("coordinación entra a portería", entrar("coordinadora").get("/porteria").status_code == 200)
for usuario in ["melany.osorio", "c.munoz", "enfermeria", "gloria.cardenas", "biblioteca"]:
    revisar(usuario + " no entra a portería", destino(entrar(usuario).get("/porteria")) == "/inicio")
revisar("portería de otro colegio no ve estudiantes ajenos", destino(entrar("porteria.dos").get("/porteria/estudiante/13")) == "/inicio")

autorizado_melany = base_datos.consultar_uno("SELECT id FROM autorizados_recoger WHERE nombre = 'Carlos Mario Osorio'", [])["id"]
salidas_antes = contar("salidas", [])
html = texto(portero.post("/porteria/estudiante/14", data={"motivo": "Cita médica", "recoge": "autorizado-" + str(autorizado_melany),
                                                         "autorizado_por": "3"}))
revisar("no deja usar un autorizado de otro estudiante", "Elige quién recoge" in html and contar("salidas", []) == salidas_antes)
html = texto(portero.post("/porteria/estudiante/13", data={"motivo": "Cita médica", "recoge": "autorizado-" + str(autorizado_melany),
                                                         "autorizado_por": "14"}))
revisar("quien autoriza debe ser del personal del colegio", "quién autorizó" in html and contar("salidas", []) == salidas_antes)
html = texto(portero.post("/porteria/estudiante/13", data={"motivo": "", "recoge": "otro", "autorizado_por": "3"}))
revisar("otra persona necesita nombre y documento", "nombre completo" in html and "documento" in html)
html = texto(portero.post("/porteria/estudiante/13", data={"motivo": "Cita médica", "recoge": "autorizado-" + str(autorizado_melany),
                                                         "autorizado_por": "3"}))
salida = base_datos.consultar_uno("SELECT * FROM salidas ORDER BY id DESC LIMIT 1", [])
revisar("registra la salida con un autorizado", "salió a las 10:30" in html and salida["estudiante_id"] == 13
        and "Carlos Mario Osorio" in salida["recogido_por"] and salida["autorizado_por"] == 3 and salida["registrado_por"] == 35)
portero.post("/porteria/estudiante/14", data={"motivo": "Calamidad doméstica", "recoge": "otro", "otro_nombre": "Luz Dary Restrepo",
                                              "otro_documento": "1.094.555.666", "autorizado_por": "3"})
salida = base_datos.consultar_uno("SELECT * FROM salidas ORDER BY id DESC LIMIT 1", [])
revisar("registra la salida con otra persona y lo deja claro", salida["estudiante_id"] == 14
        and "no estaba en la lista" in salida["recogido_por"] and "1094555666" in salida["recogido_por"])
portero.post("/porteria/estudiante/14", data={"motivo": "Diligencia familiar", "recoge": "acudiente-30", "autorizado_por": "4"})
revisar("el acudiente registrado puede recogerlo", "Jorge Iván Restrepo" in base_datos.consultar_uno(
    "SELECT recogido_por FROM salidas ORDER BY id DESC LIMIT 1", [])["recogido_por"])

html = texto(portero.post("/porteria", data={"accion": "visitante", "nombre": "", "documento": "12", "motivo": "x", "a_quien_visita": ""}))
revisar("un visitante sin datos da error", "nombre completo" in html and "documento" in html)
portero.post("/porteria", data={"accion": "visitante", "nombre": "Fernando Ospina", "documento": "18.456.789",
                                "motivo": "Reunión con coordinación", "a_quien_visita": "Coordinación"})
visitante = base_datos.consultar_uno("SELECT * FROM ingresos_visitantes WHERE nombre = 'Fernando Ospina'", [])
revisar("registra la entrada de un visitante", visitante is not None and visitante["hora_entrada"] == "10:30"
        and visitante["documento"] == "18456789" and visitante["hora_salida"] == "")
portero.post("/porteria", data={"accion": "salida_visitante", "visitante_id": str(visitante["id"])})
revisar("marca la salida del visitante",
        base_datos.consultar_uno("SELECT hora_salida FROM ingresos_visitantes WHERE id = ?", [visitante["id"]])["hora_salida"] == "10:30")
revisar("una fecha de consulta inválida da error", "no es válida" in texto(portero.get("/porteria?fecha=2026-02-31")))

print("Quién recoge (acudientes)")
html = texto(madre.get("/autorizados"))
revisar("la madre ve a los autorizados de su hija", "Rosalba Cárdenas Arango" in html and "Melany Osorio Cárdenas" in html)
html = texto(madre.post("/autorizados", data={"accion": "agregar", "estudiante_id": "13", "nombre": "Pe", "documento": "abc",
                                              "parentesco": "Primo lejano", "telefono": "1"}))
revisar("valida los datos del autorizado", "nombre completo" in html and "solo números" in html and "parentesco" in html
        and "teléfono" in html)
madre.post("/autorizados", data={"accion": "agregar", "estudiante_id": "13", "nombre": "Martha Lucía Osorio", "documento": "1.094.333.222",
                                 "parentesco": "Tía", "telefono": "320 111 2233"})
nueva = base_datos.consultar_uno("SELECT * FROM autorizados_recoger WHERE nombre = 'Martha Lucía Osorio'", [])
revisar("la madre agrega una persona autorizada", nueva is not None and nueva["documento"] == "1094333222"
        and nueva["registrado_por"] == 29 and nueva["colegio_id"] == 1)
html = texto(madre.post("/autorizados", data={"accion": "agregar", "estudiante_id": "13", "nombre": "Martha Lucía Osorio",
                                              "documento": "1094333222", "parentesco": "Tía", "telefono": "320 111 2233"}))
revisar("no repite a la misma persona", "ya está autorizada" in html)
revisar("no autoriza para hijos ajenos", destino(madre.post("/autorizados", data={
    "accion": "agregar", "estudiante_id": "14", "nombre": "Alguien Extraño", "documento": "123456", "parentesco": "Tía",
    "telefono": "3001234567"})) == "/inicio" and contar("autorizados_recoger WHERE estudiante_id = 14", []) == 0)
padre = entrar("jorge.restrepo")
padre.post("/autorizados", data={"accion": "agregar", "estudiante_id": "14", "nombre": "Luz Dary Restrepo", "documento": "1094555666",
                                 "parentesco": "Abuela", "telefono": "3109998877"})
autorizado_juan = base_datos.consultar_uno("SELECT id FROM autorizados_recoger WHERE estudiante_id = 14", [])["id"]
html = texto(padre.get("/autorizados"))
revisar("cada acudiente ve solo a los suyos", "Luz Dary Restrepo" in html and "Rosalba" not in html)
revisar("el acudiente ve quién recogió a su hijo", "Calamidad doméstica" in html)
revisar("no quita autorizados de otra familia", destino(madre.post("/autorizados", data={
    "accion": "desactivar", "autorizado_id": str(autorizado_juan)})) == "/inicio"
    and base_datos.consultar_uno("SELECT activo FROM autorizados_recoger WHERE id = ?", [autorizado_juan])["activo"] == 1)
madre.post("/autorizados", data={"accion": "desactivar", "autorizado_id": str(nueva["id"])})
revisar("la madre quita una autorización",
        base_datos.consultar_uno("SELECT activo FROM autorizados_recoger WHERE id = ?", [nueva["id"]])["activo"] == 0)
revisar("portería ya no la ofrece", "Martha Lucía Osorio" not in texto(portero.get("/porteria/estudiante/13")))
html = texto(portero.post("/porteria/estudiante/13", data={"motivo": "Cita", "recoge": "autorizado-" + str(nueva["id"]), "autorizado_por": "3"}))
revisar("portería no acepta a un autorizado desactivado", "Elige quién recoge" in html)
revisar("la estudiante no gestiona autorizados", destino(melany.get("/autorizados")) == "/inicio")

ayuda.terminar()
