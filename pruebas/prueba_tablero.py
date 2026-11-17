import ayuda
from ayuda import entrar, revisar, destino
import modulo_inicio
import modulo_notas
import modulo_tablero

rectora = entrar("rectora")
respuesta = rectora.get("/indicadores")
html = respuesta.get_data(as_text=True)
revisar("la rectora ve los indicadores", respuesta.status_code == 200)
revisar("muestra los dos grupos", "10-A" in html and "11-A" in html)
revisar("muestra el promedio por materia", "Matemáticas" in html and "Promedio por materia" in html)
revisar("cuenta 16 estudiantes", ">16<" in html)
revisar("un docente no ve los indicadores", destino(entrar("c.munoz").get("/indicadores")) == "/inicio")
revisar("una acudiente no ve los indicadores", destino(entrar("gloria.cardenas").get("/indicadores")) == "/inicio")
ayuda.terminar()
