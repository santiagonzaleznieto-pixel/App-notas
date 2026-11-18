import ayuda
from ayuda import entrar, revisar, destino
import modulo_inicio
import modulo_notas
import base_datos

print("Inicio de sesión")
cliente = ayuda.app.test_client()
respuesta = cliente.post("/", data={"usuario": "rectora", "clave": "mala"})
revisar("una contraseña mala no deja entrar", "no son correctos" in respuesta.get_data(as_text=True))
revisar("la contraseña se guarda cifrada", base_datos.buscar_usuario("rectora")["clave"] != "pijao2026")

print("Permisos")
docente = entrar("c.munoz")
revisar("la docente ve sus clases", docente.get("/mis-clases").status_code == 200)
revisar("la docente no ve boletines ajenos", destino(docente.get("/boletin/13")) == "/inicio")
director = entrar("h.aguirre")
revisar("el director ve el boletín de su grupo", director.get("/boletin/13").status_code == 200)
revisar("el director no ve el boletín de otro grupo", destino(director.get("/boletin/23")) == "/inicio")
madre = entrar("gloria.cardenas")
revisar("la acudiente ve el boletín de su hija", madre.get("/boletin/13").status_code == 200)
revisar("la acudiente no ve otros boletines", destino(madre.get("/boletin/14")) == "/inicio")
estudiante = entrar("melany.osorio")
revisar("la estudiante ve su boletín", estudiante.get("/boletin/13").status_code == 200)
revisar("la estudiante no ve el de un compañero", destino(estudiante.get("/boletin/14")) == "/inicio")
revisar("la estudiante no puede calificar", destino(estudiante.get("/calificar/1")) == "/inicio")
revisar("la docente no califica clases ajenas", destino(docente.get("/calificar/5")) == "/inicio")

print("Actividades y definitivas")
import nucleo
import modulo_notas
def hoy_fijo():
    return "2026-11-17"


nucleo.hoy = hoy_fijo
modulo_notas.hoy = nucleo.hoy
revisar("se ve la página de la clase", docente.get("/calificar/1").status_code == 200)
antes = base_datos.consultar_uno("SELECT COUNT(*) AS n FROM actividades WHERE asignacion_id = 1", [])["n"]
respuesta = docente.post("/calificar/1?periodo=4", data={"accion": "nueva_actividad", "nombre": "Quiz final", "fecha": "2026-06-01", "descripcion": ""})
revisar("no acepta una fecha fuera del período", "dentro del" in respuesta.get_data(as_text=True))
respuesta = docente.post("/calificar/1?periodo=4", data={"accion": "nueva_actividad", "nombre": "Quiz final", "fecha": "2026-11-10", "descripcion": "Temas del período"})
nueva = base_datos.consultar_uno("SELECT * FROM actividades WHERE asignacion_id = 1 AND nombre = 'Quiz final'", [])
revisar("crea la actividad y lleva a calificarla", nueva is not None and "/actividad/" + str(nueva["id"]) in destino(respuesta))
ruta = "/calificar/1/actividad/" + str(nueva["id"])
datos = {"nombre": "Quiz final", "fecha": "2026-11-10", "descripcion": "Temas del período",
         "nota-13": "4,8", "obs-13": "Muy bien", "nota-14": "9", "obs-14": "", "nota-15": "", "obs-15": ""}
html = docente.post(ruta, data=datos).get_data(as_text=True)
revisar("una nota fuera de rango da error", "debe estar entre" in html)
calificaciones = base_datos.calificaciones_del_periodo(1, 2026, 4)
revisar("la nota y la observación se guardan", calificaciones[13][nueva["id"]]["valor"] == 4.8 and calificaciones[13][nueva["id"]]["observacion"] == "Muy bien")
revisar("la nota inválida no se guarda", 14 not in calificaciones or nueva["id"] not in calificaciones[14])
revisar("otro docente no abre la actividad", destino(entrar("a.trejos").get(ruta)) == "/inicio")

valores = []
for fila in base_datos.consultar("SELECT valor FROM calificaciones JOIN actividades ON actividades.id = calificaciones.actividad_id "
                                 "WHERE actividades.asignacion_id = 1 AND actividades.periodo = 4 AND calificaciones.estudiante_id = 13", []):
    valores.append(fila["valor"])
esperado = nucleo.promedio(valores)
revisar("antes de guardar, el boletín no muestra la definitiva del período", base_datos.notas_del_estudiante(13, 2026, 4)[1][3] is None)
docente.post("/calificar/1?periodo=4", data={"accion": "definitivas", "definitiva-13": "auto", "definitiva-14": "Básico"})
revisar("la definitiva automática es el promedio de las actividades", base_datos.notas_del_estudiante(13, 2026, 4)[1][3] == esperado)
manuales = base_datos.desempenos_manuales_de(14, 2026)
revisar("la definitiva manual guarda solo el desempeño", manuales[1][4] == "Básico")
rectora = entrar("rectora")
html = rectora.get("/boletin/14").get_data(as_text=True)
revisar("el boletín no muestra las actividades", "Quiz final" not in html and "Taller de funciones" not in html)
fila_mate = html.split("Matemáticas")[1].split("</tr>")[0]
revisar("el boletín muestra el desempeño manual sin número", '<span class="chip Básico">Básico</span>' in fila_mate)
html = docente.get("/calificar/1?periodo=4").get_data(as_text=True)
revisar("la clase muestra la definitiva como guardada", "Guardada" in html and "Manual" in html)

respuesta = docente.post("/calificar/1?periodo=1", data={"accion": "nueva_actividad", "nombre": "Tarde", "fecha": "2026-02-10", "descripcion": ""})
revisar("en un período cerrado no se crean actividades", base_datos.consultar_uno("SELECT id FROM actividades WHERE nombre = 'Tarde'", []) is None)
revisar("una definitiva de período cerrado no cambia", base_datos.notas_del_estudiante(15, 2026, 4)[1][0] == 3.9)

docente.post("/calificar/1?periodo=final", data={"final-13": "Superior"})
revisar("la definitiva del año puede ser manual", base_datos.desempenos_manuales_de(13, 2026)[1][0] == "Superior")
html = rectora.get("/boletin/13").get_data(as_text=True)
fila_mate = html.split("Matemáticas")[1].split("</tr>")[0]
revisar("el boletín muestra el desempeño final manual", fila_mate.strip().endswith('<td><span class="chip Superior">Superior</span></td>'))
docente.post(ruta, data={"accion": "borrar"})
revisar("se puede borrar una actividad", base_datos.buscar_actividad(nueva["id"]) is None)
revisar("al borrarla se van sus notas", base_datos.consultar_uno("SELECT id FROM calificaciones WHERE actividad_id = ?", [nueva["id"]]) is None)

print("Cuenta")
respuesta = estudiante.post("/mi-cuenta", data={"accion": "clave", "actual": "pijao2026", "nueva": "corta", "repetida": "corta"})
revisar("no acepta contraseñas cortas", "al menos 8" in respuesta.get_data(as_text=True))
respuesta = estudiante.post("/mi-cuenta", data={"accion": "clave", "actual": "pijao2026", "nueva": "nuevaclave1", "repetida": "nuevaclave1"})
revisar("cambia la contraseña", "Contraseña cambiada" in respuesta.get_data(as_text=True))
nuevo = ayuda.app.test_client()
revisar("entra con la contraseña nueva", destino(nuevo.post("/", data={"usuario": "melany.osorio", "clave": "nuevaclave1"})) == "/inicio")

print("Seguridad")
ajeno = ayuda.app.test_client()
respuesta = ajeno.post("/", data={"usuario": "rectora", "clave": "pijao2026"}, headers={"Origin": "https://sitio-malo.com"})
revisar("rechaza formularios enviados desde otro sitio", respuesta.status_code == 403)
propio = ayuda.app.test_client()
respuesta = propio.post("/", data={"usuario": "rectora", "clave": "pijao2026"}, headers={"Origin": "http://localhost"})
revisar("acepta formularios de la misma plataforma", destino(respuesta) == "/inicio")
revisar("envía cabeceras de seguridad", respuesta.headers.get("X-Frame-Options") == "SAMEORIGIN")
intruso = ayuda.app.test_client()
for i in range(5):
    intruso.post("/", data={"usuario": "coordinadora", "clave": "adivinando"})
respuesta = intruso.post("/", data={"usuario": "coordinadora", "clave": "pijao2026"})
revisar("bloquea el usuario tras 5 intentos fallidos", "demasiados intentos" in respuesta.get_data(as_text=True))

publico = ayuda.app.test_client()
revisar("la política de datos se ve sin iniciar sesión", "Ley 1581" in publico.get("/privacidad").get_data(as_text=True))
revisar("en modo pruebas se ven los accesos rápidos", "Acceso rápido" in publico.get("/").get_data(as_text=True))

revisar("el trabajador sin conexión se sirve como JavaScript", publico.get("/sw.js").mimetype == "application/javascript")
revisar("la página sin conexión se ve sin sesión", "No hay conexión" in publico.get("/sin-conexion").get_data(as_text=True))

ayuda.terminar()
