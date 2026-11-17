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

print("Calificar")
formulario = {"nota-13-4": "4,8", "nota-14-4": "9", "nota-15-1": "1.0"}
respuesta = docente.post("/calificar/1", data=formulario)
html = respuesta.get_data(as_text=True)
revisar("una nota fuera de rango da error", "debe estar entre" in html)
notas = base_datos.notas_del_estudiante(13, 2026, 4)
revisar("la nota del período abierto se guarda", notas[1][3] == 4.8)
revisar("una nota en período cerrado no se cambia", base_datos.notas_del_estudiante(15, 2026, 4)[1][0] == 3.9)
revisar("la nota inválida no se guarda", base_datos.notas_del_estudiante(14, 2026, 4)[1][3] is None)

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

ayuda.terminar()
