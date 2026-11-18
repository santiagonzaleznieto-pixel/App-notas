from nucleo import app
import modulo_inicio
import modulo_notas
import modulo_tablero
import modulo_familias
import modulo_circulares
import modulo_asistencia
import modulo_observador
import modulo_horas
import modulo_certificados
import modulo_orientacion
import modulo_gobierno
import modulo_tesoreria
import modulo_servicios
import modulo_admin
import base_datos

base_datos.soltar_preparacion()

if __name__ == "__main__":
    app.run(debug=True)
