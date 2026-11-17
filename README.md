# Plataforma de gestión escolar

Plataforma web para manejar todo un colegio colombiano, de Transición a Once. Está hecha en Python con Flask y SQLite, y pensada para usarse desde el celular.

Empezó como proyecto de clase del SENA con las notas del grado Décimo de la Institución Educativa Instituto Pijao (Pijao, Quindío), que es el colegio piloto.

- **Demo de solo lectura (GitHub Pages):** https://santiagonzaleznieto-pixel.github.io/App-notas/
- **Plan maestro:** https://claude.ai/artifact/QQYMz3DWLH2gvuDGn6a4yu

## Módulos

| Módulo | Para quién | Qué hace |
| --- | --- | --- |
| Inicio y mi cuenta | Todos | Panel según el rol, cambio de contraseña y datos de contacto |
| Notas | Docentes, directivos, estudiantes, familias | Calificar por período, consolidado por grupo con puestos y alertas, boletín |
| Indicadores | Rectoría, coordinación | Desempeño por grupo, promedio por materia y alertas del colegio |
| Administración | Administración, coordinación, secretaría | Usuarios, roles, grupos, matrículas, materias, asignaciones, períodos, escala y registro de accesos |
| Asistencia | Docentes, directivos, estudiantes, familias | Tomar lista, alertas de inasistencia (Resolución 5862 de 2024) y excusas |
| Observador y convivencia | Docentes, coordinación, orientación | Anotaciones y casos tipo I, II y III con su protocolo (Ley 1620 de 2013) |
| Horas sociales | Estudiantes de 10° y 11°, docentes, coordinación | 80 horas de servicio social (Resolución 4210 de 1996) y 50 de estudios constitucionales (Ley 107 de 1994) |
| Certificados | Secretaría, estudiantes, familias | Constancias y certificados con código de verificación pública |
| Familias | Acudientes, orientación | Portal de los hijos, compromiso y escuela para familias (Ley 2025 de 2020) |
| Circulares y agenda | Todos | Comunicados con confirmación de lectura y fechas del año |
| Orientación y PIAR | Orientación, docentes, familias | Atenciones confidenciales, remisiones y PIAR (Decreto 1421 de 2017) |
| Elecciones | Estudiantes, directivos | Personero, contralor y representantes con voto secreto (Decreto 1860 de 1994) |
| Tesorería | Tesorería, familias | Cobros, pagos, cartera, recibos y paz y salvo |
| Servicios escolares | Biblioteca, enfermería, portería, familias | Préstamos, fichas de salud, autorizados para recoger y visitantes |

Usuarios de prueba (contraseña `pijao2026`): `admin`, `rectora`, `coordinadora`, `h.aguirre` (director de grupo), `c.munoz` (docente), `secretaria`, `orientadora`, `melany.osorio` (estudiante), `gloria.cardenas` (acudiente), `tesoreria`, `biblioteca`, `enfermeria`, `porteria`.

## Cómo ejecutarla en tu computador (Windows)

```
py -m pip install flask
py app.py
```

Luego abre http://127.0.0.1:5000. La primera vez se crea `plataforma.db` con los datos de prueba. Para volver a empezar, borra `plataforma.db`.

## Pruebas automáticas

Cada módulo tiene su prueba en la carpeta `pruebas`. Por ejemplo:

```
py pruebas/prueba_notas.py
```

Cada prueba usa una base temporal: no toca `plataforma.db`.

## Cómo actualizar la demo de GitHub Pages

```
py generar_demo.py
```

El programa recorre la plataforma como cada usuario de prueba y guarda las páginas en la carpeta `docs`. Después sube los cambios a GitHub y la demo se actualiza sola en uno o dos minutos.

## Cómo publicarla de verdad en PythonAnywhere

1. Crea una cuenta gratis en https://www.pythonanywhere.com (plan Beginner).
2. Abre **Consoles → Bash** y escribe:
   ```
   git clone https://github.com/santiagonzaleznieto-pixel/App-notas.git
   ```
3. Ve a **Web → Add a new web app → Next → Manual configuration → Python 3.13** (o la versión más nueva que aparezca).
4. En la misma página, abre el enlace del **WSGI configuration file**, borra todo y pega esto (cambia `TU_USUARIO` y la frase secreta):
   ```python
   import os
   import sys
   os.environ["CLAVE_SECRETA"] = "escribe-aqui-una-frase-larga-que-nadie-conozca"
   os.environ["MODO_PRUEBAS"] = "1"
   sys.path.insert(0, "/home/TU_USUARIO/App-notas")
   from app import app as application
   ```
   `MODO_PRUEBAS = "1"` deja los botones de acceso rápido para mostrar la demo. Para un colegio real, quítalo y agrega `os.environ["DATOS_DE_EJEMPLO"] = "0"`.
5. En **Static files** agrega: URL `/static/` y directorio `/home/TU_USUARIO/App-notas/static/`.
6. Oprime **Reload**. La plataforma queda en `https://TU_USUARIO.pythonanywhere.com`.

Para actualizarla: en la consola Bash escribe `cd App-notas && git pull` y oprime **Reload**. En el plan gratis hay que entrar a la pestaña Web al menos una vez cada tres meses y oprimir el botón para mantenerla activa.

## Dar de alta un colegio real

Con `DATOS_DE_EJEMPLO = "0"` la base empieza vacía. En la consola Bash, dentro de la carpeta del proyecto:

```
DATOS_DE_EJEMPLO=0 python3 crear_colegio.py
```

El programa pregunta el nombre del colegio, el municipio, el año y la persona administradora, y muestra el usuario y la clave temporal del administrador. Desde ahí, todo se configura en la página: sedes, períodos, materias, grupos, docentes y estudiantes (también con cargue masivo).

## Seguridad y datos personales

- Contraseñas cifradas, cambio obligatorio de las claves temporales y bloqueo de 15 minutos tras 5 intentos fallidos.
- Cada persona solo ve lo que su rol le permite y nunca datos de otro colegio.
- Se rechazan formularios enviados desde otros sitios web.
- Registro de accesos y de cambios importantes.
- La clave secreta (`CLAVE_SECRETA`) nunca se escribe en el código ni se sube a GitHub.
- `/privacidad` publica la política de tratamiento de datos (Ley 1581 de 2012). Es un borrador: un abogado debe revisarla antes de usar datos reales.
