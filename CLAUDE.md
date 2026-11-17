# Plataforma de Notas 10° · Instituto Pijao

Página web local hecha en Python con Flask para manejar las notas del grado Décimo de la Institución Educativa Instituto Pijao (Pijao, Quindío). Es un proyecto de clase del SENA. No usa base de datos: todos los datos están en `datos.py`.

## Reglas para trabajar en este proyecto

- Todo en español: nombres de variables, funciones, rutas y textos de la página.
- No escribir comentarios en el código. Solo lo necesario.
- Mantenerlo sencillo. En clase solo se han visto: secuenciales, condicionales (`if`, `elif`, `else`), ciclo `for` y ciclo `while`. También se permiten variables, listas, diccionarios, funciones (`def`) y Flask, porque son necesarios para la página.
- Evitar lo que no se ha visto: clases, `lambda`, listas por comprensión, `try`/`except`, `sorted` con `key`, decoradores propios, librerías extra.
- No conectar base de datos hasta que se pida (la próxima meta es SQLite).
- Mantener el diseño actual (ver "Diseño").
- Soy principiante: explica cada cambio con palabras sencillas y dime cómo probarlo.

## Cómo se ejecuta (Windows, terminal de VS Code)

```
py -m pip install flask
py app.py
```

Luego abrir http://127.0.0.1:5000 en el navegador.

## Estructura

- `app.py`: rutas, permisos por rol y cálculos.
- `datos.py`: `COLEGIO`, `GRADO`, `ANIO`, `PERIODOS`, `USUARIOS` (lista de diccionarios), `MATERIAS` (lista de diccionarios) y `NOTAS` (diccionario: estudiante → materia → lista de 4 notas; `None` = nota pendiente).
- `templates/`: `base.html`, `login.html`, `materias.html`, `calificar.html`, `consolidado.html`, `boletin.html` (plantillas Jinja).
- `static/`: `estilos.css` y `escudo.png`.

Las notas que se cambian en la página viven en memoria: al cerrar el programa vuelven las de `datos.py`.

## Roles y permisos

Contraseña de prueba para todos: `pijao2026`.

- `rectora` y `coordinadora`: ven el consolidado del grado (`/consolidado`) y el boletín de cualquier estudiante. Solo lectura.
- `director` (`h.aguirre`, Hernán Darío Aguirre, dicta Filosofía y Ciencias Sociales): califica sus materias y ve el consolidado como "Mi grupo".
- `profesor`: solo ve y califica sus materias (`/materias`, `/calificar/<id_materia>`).
- `estudiante`: solo ve su propio boletín (`/boletin/<usuario>`).

10 estudiantes de prueba, 8 materias, 7 docentes, 4 períodos.

## Reglas de las notas

- Escala de 1.0 a 5.0, un decimal.
- Desempeño: Bajo 1.0–2.9, Básico 3.0–3.9, Alto 4.0–4.5, Superior 4.6–5.0, Pendiente si no hay nota.
- Promedio de una materia: promedio de las notas de los períodos que ya existen.
- Promedio general: promedio de las 8 materias.
- Puesto: 1 + número de compañeros con mejor promedio (los empates comparten puesto).

## Dónde se usa cada tema de clase

- Secuenciales: `datos.py`.
- `while`: `buscar_usuario` (búsqueda del usuario al iniciar sesión).
- `if` / `elif` / `else`: `desempeno`, el login, los permisos de cada ruta y el mensaje del boletín.
- `for`: `promedio`, `tabla_grupo` (puestos), alertas, resumen por materia y guardar notas.

## Diseño

- Colores: azul `#1E3A5F`, azul oscuro `#122844`, verde cafetero `#3F6B4A`, verde oscuro `#2C4E35`, terracota `#BD5B2E`, dorado `#C98A2B`, crema `#FBF8F2`.
- Fuentes: Fraunces (títulos) e Inter (texto), desde Google Fonts.
- Montañas del Paisaje Cultural Cafetero en el login y franja bajo la barra superior.

## Estado y próximas metas

Ya existe una presentación del proyecto para el SENA. Próximas metas:

1. Guardar las notas en una base de datos (SQLite).
2. Ampliar a todos los grados, de Transición a Once.
3. Contraseña propia y cifrada para cada usuario.
4. Un rol de administrador que cree usuarios y materias desde la página.
5. Asistencia, agenda y anotaciones de los profesores.
6. Recordatorios por WhatsApp y correo.
7. Publicarla en internet (PythonAnywhere).
