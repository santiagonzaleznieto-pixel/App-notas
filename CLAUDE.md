# Plataforma de gestión escolar

Plataforma web en Python con Flask y SQLite para manejar todo un colegio colombiano: notas, asistencia, convivencia, horas sociales, certificados, familias, circulares, orientación, elecciones, tesorería y servicios escolares. Se venderá a instituciones públicas y privadas, de Transición a Once. Empezó como proyecto de clase del SENA con las notas de Décimo de la Institución Educativa Instituto Pijao (Pijao, Quindío), que ahora es el **colegio piloto**.

- Repositorio: https://github.com/santiagonzaleznieto-pixel/App-notas (público, rama `main`)
- Demo de solo lectura (GitHub Pages, carpeta `docs`): https://santiagonzaleznieto-pixel.github.io/App-notas/
- Plan maestro (visión, ley, roles, módulos, fases): https://claude.ai/artifact/QQYMz3DWLH2gvuDGn6a4yu

Este repositorio es solo para la plataforma escolar. El sitio del restaurante Amo Pijao Terraza es otro proyecto, en otro repositorio y otra sesión: no se mezclan.

## Reglas para trabajar en este proyecto

- Todo en español: nombres de variables, funciones, rutas, tablas, columnas y textos de la página.
- No escribir comentarios en el código. Solo lo necesario.
- Mantenerlo sencillo. Se permiten: variables, `if`/`elif`/`else`, `for`, `while`, listas, diccionarios, funciones (`def`), Flask (incluidos sus decoradores como `@app.route`, `@app.before_request`), `sqlite3`, `werkzeug.security` y módulos estándar simples (`os`, `datetime`, `secrets`).
- Evitar lo que no se ha visto: clases propias, `lambda`, listas por comprensión, `try`/`except`, `with`, operador ternario, `sorted` con `key`, decoradores propios, f-strings (se usa `+` y `str()`), librerías externas.
- Todo debe servir para cualquier colegio: cada tabla lleva `colegio_id` y cada consulta comprueba que el registro es del colegio del usuario (`g.colegio["id"]`). Nunca confiar en ids que llegan por la URL o el formulario.
- Lo que cambia de un colegio a otro (escala, períodos, grados, materias, sedes) se guarda en la base de datos, no en el código.
- Base de datos: SQLite hasta la fase 4 del plan maestro; luego PostgreSQL.
- El repositorio es público: nunca escribir claves ni contraseñas reales en el código.
- Mantener el diseño (ver "Diseño"). Todo debe verse bien en celular.
- Soy principiante: explica cada cambio con palabras sencillas y dime cómo probarlo.

## Cómo se ejecuta (Windows, terminal de VS Code)

Desde la carpeta del proyecto:

```
py -m pip install flask
py app.py
```

Abrir http://127.0.0.1:5000. La primera vez se crea `plataforma.db` (al lado de `base_datos.py`) con los datos de `datos.py` y los ejemplos de cada módulo. Para volver a empezar: cerrar el programa, borrar `plataforma.db` y abrirlo otra vez. Si cambia la estructura de alguna tabla, también hay que borrar `plataforma.db`.

Pruebas automáticas (una por módulo): `py pruebas/prueba_notas.py`, `py pruebas/prueba_admin.py`, etc. Cada una usa una base temporal y no toca `plataforma.db`.

## Arquitectura

- `app.py`: arranca la plataforma; solo importa los módulos. El orden de los `import` es el orden del menú.
- `nucleo.py`: crea la app de Flask, prepara la base, carga la sesión (`g.yo`, `g.colegio`), permisos (`tiene_rol`, `tiene_alguno`, `puede_ver_grupo`, `puede_ver_estudiante`, `puede_anotar_estudiante`, `dicta_en_grupo`), escala (`desempeno`), promedios (`promedio`, `nota_final` con porcentajes), `numero()` para leer números sin `try`, `registrar()` para el registro de accesos, el menú (`agregar_menu`) y la seguridad (formularios de otros sitios, cabeceras, cookies, cambio obligatorio de clave temporal).
- `base_datos.py`: conexión y funciones del núcleo (`consultar`, `consultar_uno`, `ejecutar`, `crear_tablas`) y tablas del núcleo.
- `semilla.py` y `datos.py`: datos iniciales del colegio piloto (solo se usan si la base está vacía).
- `modulo_*.py`: un archivo por módulo con sus tablas (`TABLAS_...` + `crear_tablas`), sus datos de ejemplo (`sembrar_...`), su entrada al menú y sus rutas. Sus plantillas empiezan por el nombre del módulo y su CSS extra va en `static/<modulo>.css`.
- `templates/base.html`: barra, menú automático según los roles, bloques `contenido` (con sesión), `publico` (sin sesión) y `estilos`.
- `generar_demo.py`: crea la demo de solo lectura en `docs/` recorriendo la plataforma como cada usuario de acceso rápido. Correrlo (`py generar_demo.py`) después de cambiar diseño, módulos o datos de prueba.
- `pruebas/`: `ayuda.py` (base temporal, `entrar`, `revisar`) y una prueba por módulo.

## Tablas del núcleo

`colegios` (datos y escala), `sedes`, `grados` (Transición a Once, con `orden`), `usuarios` (clave cifrada, `activo`, `debe_cambiar_clave`), `roles_usuario` (varios roles por persona), `grupos` (por año, con director), `matriculas` (estudiante en grupo por año, `activa` o `retirada`), `acudientes` (acudiente ↔ estudiante con parentesco), `materias`, `asignaciones` (grupo + materia + docente + horas), `periodos` (fechas, porcentaje, abierto o cerrado), `notas` (año, estudiante, materia, período, valor; `NULL` = pendiente), `registro_accesos`.

## Roles

`administrador`, `rector`, `coordinador`, `docente`, `secretaria`, `orientador`, `estudiante`, `acudiente`, `tesoreria`, `bibliotecario`, `enfermeria`, `porteria`. `director` no se guarda: se agrega solo cuando el docente dirige un grupo del año. Una persona puede tener varios roles.

Usuarios de prueba (contraseña `pijao2026`, `CLAVE_PRUEBA` en `datos.py`): `admin`, `rectora`, `coordinadora`, `h.aguirre` (director de 10-A, Sociales y Filosofía), `c.munoz` (Matemáticas), `s.grajales` (directora de 11-A), `secretaria`, `orientadora`, `melany.osorio` y 9 estudiantes más en 10-A, `esteban.ramirez` y 5 más en 11-A, acudientes `gloria.cardenas` (madre de Melany), `jorge.restrepo`, `olga.gomez`, y `tesoreria`, `biblioteca`, `enfermeria`, `porteria`.

Los botones de acceso rápido solo aparecen en modo pruebas: sin la variable `CLAVE_SECRETA`, o con `MODO_PRUEBAS=1`.

## Reglas de las notas

- Escala por colegio (en `colegios`): por defecto de 1.0 a 5.0. Desempeño (escala nacional del Decreto 1290 de 2009): Bajo menos de 3.0, Básico desde 3.0, Alto desde 4.0, Superior desde 4.6, Pendiente si no hay nota.
- Nota final de una materia: promedio ponderado por el porcentaje de cada período, solo con los períodos que tienen nota.
- Promedio general: promedio de las materias. Puesto: 1 + compañeros con mejor promedio (los empates comparten puesto).
- Los docentes solo cambian notas de períodos abiertos.

## Dónde se usa cada tema de clase

- Secuenciales: `datos.py`.
- `while`: `enlaces_internos` en `generar_demo.py`, `ordenar_de_mayor_a_menor` en `modulo_tablero.py`, la generación de usuarios y códigos únicos (administración, certificados, recibos).
- `if` / `elif` / `else`: `desempeno`, el login, los permisos de cada ruta, el mensaje del boletín.
- `for`: promedios, puestos, alertas, resúmenes, guardar notas, sembrar datos.
- Funciones: un archivo `modulo_*.py` por módulo, con una función por consulta y por ruta.

## Diseño

- Colores: azul `#1E3A5F`, azul oscuro `#122844`, verde cafetero `#3F6B4A`, verde oscuro `#2C4E35`, terracota `#BD5B2E`, dorado `#C98A2B`, crema `#FBF8F2`.
- Fuentes: Fraunces (títulos) e Inter (texto), desde Google Fonts.
- Montañas del Paisaje Cultural Cafetero en el login y franja bajo la barra superior.
- Gráficas de indicadores (`static/tablero.css`): niveles Bajo `#B4532A`, Básico `#D29A2E`, Alto `#53A86E`, Superior `#1B7444`, Pendiente `#D9D3C7` (paleta validada para daltonismo), barras de máximo 24 px, separación de 2 px, leyenda y tabla de datos.

## Publicación

- Demo en GitHub Pages: carpeta `docs/` de la rama `main` (páginas fijas; no se inicia sesión de verdad ni se guarda nada).
- Plataforma real: PythonAnywhere (pasos en `README.md`). Variables: `CLAVE_SECRETA` (obligatoria en internet) y `MODO_PRUEBAS=1` solo para demos.
- `/privacidad`: política de tratamiento de datos (borrador para revisión de un abogado).

## Estado

Ver la sección "Avance" del plan maestro y la lista de pendientes del dueño en `PENDIENTES.md`.
