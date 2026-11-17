# Plataforma de gestión escolar

Plataforma web para manejar todo un colegio colombiano: notas, asistencia, convivencia, horas sociales, familias y reportes. Está hecha en Python con Flask y SQLite.

Empezó como proyecto de clase del SENA con las notas del grado Décimo de la Institución Educativa Instituto Pijao (Pijao, Quindío), que es el colegio piloto.

- **Demo de solo lectura (GitHub Pages):** https://santiagonzaleznieto-pixel.github.io/plataforma-escolar/
- **Plan maestro:** https://claude.ai/artifact/QQYMz3DWLH2gvuDGn6a4yu

Usuarios de prueba (contraseña `pijao2026`): `rectora`, `coordinadora`, `h.aguirre` (director de grupo), `c.munoz` (profesora), `melany.osorio` (estudiante).

## Qué hace hoy

- Inicio de sesión por rol, con contraseñas cifradas.
- Docentes: califican sus materias por período.
- Director de grupo, coordinación y rectoría: consolidado del grado con puestos, alertas y resumen por materia.
- Estudiantes: su boletín con promedio, desempeño y puesto.
- Las notas se guardan en una base de datos SQLite (`plataforma.db`).

## Cómo ejecutarla en tu computador (Windows)

```
py -m pip install flask
py app.py
```

Luego abre http://127.0.0.1:5000. La primera vez se crea `plataforma.db` con los datos de `datos.py`. Para volver a empezar, borra `plataforma.db`.

## Cómo actualizar la demo de GitHub Pages

```
py generar_demo.py
```

Este programa abre cada página como si fuera cada usuario de prueba y guarda el resultado en la carpeta `docs`. Después sube los cambios a GitHub y la demo se actualiza sola en uno o dos minutos.

## Cómo publicarla de verdad en PythonAnywhere

1. Crea una cuenta gratis en https://www.pythonanywhere.com (plan Beginner).
2. Abre **Consoles → Bash** y escribe:
   ```
   git clone https://github.com/santiagonzaleznieto-pixel/plataforma-escolar.git
   ```
3. Ve a **Web → Add a new web app → Next → Manual configuration → Python 3.13** (o la versión más nueva que aparezca).
4. En la misma página, abre el enlace del **WSGI configuration file**, borra todo y pega esto (cambia `TU_USUARIO` y la frase secreta):
   ```python
   import os
   import sys
   os.environ["CLAVE_SECRETA"] = "escribe-aqui-una-frase-larga-que-nadie-conozca"
   sys.path.insert(0, "/home/TU_USUARIO/plataforma-escolar")
   from app import app as application
   ```
5. En **Static files** agrega: URL `/static/` y directorio `/home/TU_USUARIO/plataforma-escolar/static/`.
6. Oprime **Reload**. La plataforma queda en `https://TU_USUARIO.pythonanywhere.com`.

Para actualizarla después: en la consola Bash escribe `cd plataforma-escolar && git pull` y oprime **Reload** en la pestaña Web. En el plan gratis hay que entrar a la pestaña Web al menos una vez cada tres meses y oprimir el botón para mantenerla activa.

La clave secreta (`CLAVE_SECRETA`) protege las sesiones. Nunca la escribas en el código ni la subas a GitHub.
