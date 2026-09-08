# Introducción al proyecto
En ese contexto tienes que generar un prototipo dónde:
Tenemos 3 capas de código en el prototipo:
- Backend que es una API de Django Rest Framework (DRF) que funciona para hacer CRUD y comunicación con web sockets
- Avacom OPS Master - Funciona cómo Frontend que corre en el host maestro que normalmente maneja el profesor y que de allí debería verse sintetizada el cliente (quiénes suelen ser los estudiantes)
- Avacom Student que es el front que ven los clientes, es la app que manejan  los estudiantes directamente.
- La app de AVACOM OPS Master está en Windows
- La app de AVACOM Student está en Android y en Windows
- Backend funciona cómo en API dónde tienes los CRUD para crear registros, actualizarlos, eliminarlos o leerlos (hacer CRUDs)
# Objetivo del prototipo
En este prototipo queremos explorar cómo sería la experiencia de experiencia de usuario a la hora de crear un curso y asignarlo a un estudiante
Objetivo específicos
- Usar el AVACOM OPS Master para mostrar un curso ya creado y que pueda mostrar el consolidado de 1 actividad de los estudiantes
- Se muestra la experiencia de crear un curso desde cero
- Explorarlo con una información demo llamado Algebra Octavo B
- Los estudiantes pueden ver al menos 3 Lessons cada una con 2 sections del curso
- En la última Lesson Item  (o lección item) debe aparecer una actividad  que es un quiz
- La actividad tipo Quiz son 5 preguntas generales sobre méxico
- En comunicación con Web Sockets se ve en qué pregunta está el estudiante
- Se realiza el registro de la actividad y su correspondiente nota por estudiante
## En el AVACOM Student
- Se muestra la experiencia de abrir el curso
- De ver todas las secciones del curso
- De ver cada lección de la sección
- De ver cada item de lección (Lesson Item)
- Realizar la actividad realizada
Condiciones de comunicación
- El sistema cuenta con un instalable porque el host es una pantalla interactiva gigante que maneja un sistema llamado OPS que es un Windows dentro, ese instalable debe ser practico como se muestra en el installer que está configurado. Dado que este no cuenta con teclado y es difícil hacer debug de qué podría salir mal
- La API debe correr en el 0.0.0.0:8000 porque debe ser accesible desde la LAN
- En la pantalla AVACOM OPS se muestra si la conexión fue un éxito o si está fallando, cómo está actualmente en el código
- En la pantalla de AVACOM Student se coloca el nombre y la dirección a la que está conectando


El frontend contiene 22 rutas concretas, tres experiencias por rol y cinco familias visuales. La referencia que compartiste coincide especialmente con la pantalla /lista-asignaturas: allí sí existe una matriz exacta de 4–5–4 hexágonos sobre fondo pastel.

Hay una diferencia importante respecto al ejemplo: el código actual utiliza un único linear-gradient(120deg, ...), no varios gradientes radiales. El menú principal tampoco usa el fondo pastel; utiliza gris #F1F1F1 y un aro hexagonal multicolor en SVG.

# Estilos a usar en el LMS


Validé el código y el render real en 1920×1080, 1440×900 y 390×844. No modifiqué archivos.

1. Estructura de estilos
 Los estilos son CSS convencional por componente, con nomenclatura BEM:
.subject-hive
.subject-hive__board
.subject-hive__slot
.subject-hive__help
Existen dos sistemas de tokens:
- Sistema global: Inter, colores generales y variables en :root.
- Sistema ui-kit: Geist, Geist Mono, gradiente pastel, sombras y radios propios. Está aislado bajo .ui-kit y se usa principalmente en el login.
Fuentes principales:
- Aplicación: Inter, con fallback a Segoe UI y fuentes del sistema.
- Login: Geist.
- Textos técnicos del login: Geist Mono.
- Los iconos provienen de Phosphor Icons y normalmente usan peso regular o duotone.
Componentes visuales fundamentales para MAUI:
- ModuleLayout: encabezado fijo, contenido central y navegación inferior.
- HexCell: hexágono blanco reutilizable.
- SubjectHive: matriz 4–5–4 de asignaturas.
- DesktopHexMenu: panal del menú principal.
- ResponsiveHexMenu: reemplazo del panal para anchos menores a 1280 px.
- MainNavbar: píldora inferior expansible.
- ModuleCard: tarjeta blanca de contenido.
- Modal: overlay y diálogo.
- ContentRow: carrusel horizontal de recursos.
Archivos clave:
- [AppRoutes.jsx](C:/projects/test-lms01/frontend/src/routes/AppRoutes.jsx)
- [ModuleLayout.css](C:/projects/test-lms01/frontend/src/components/templates/ModuleLayout/ModuleLayout.css)
- [SubjectHive.css](C:/projects/test-lms01/frontend/src/components/organisms/SubjectHive/SubjectHive.css)
- [HexCell.jsx](C:/projects/test-lms01/frontend/src/components/atoms/HexCell/HexCell.jsx)
- [DesktopHexMenu.css](C:/projects/test-lms01/frontend/src/components/organisms/DesktopHexMenu/DesktopHexMenu.css)
- [ui-kit.css](C:/projects/test-lms01/frontend/src/styles/ui-kit.css)
2. Paleta consolidada
Token MAUI recomendado	Color	Uso
BrandRed	#E5262B	CTA principal, guardar, acciones críticas
BrandRedIcon	#E5282C	Iconos del panal
BrandRedDark	#A20D12	Texto rojo y estados hover
BrandRedDeep	#781215	Gradientes rojos
BrandYellow	#F3C701	Ayuda, advertencias y unidades
BrandYellowIcon	#F2C600	Iconos del panal
BrandYellowDark	#6B5800	Texto sobre amarillo
BrandGreen	#019D60	Éxito, asistencia y progreso
BrandGreenDark	#016940	Hover y texto de éxito
ProgressRing	#00E89B	Anillo de hitos completados
BrandBlue	#01A4E1	Ayuda, información y recursos
BrandBlueIcon	#15A3DD	Iconos
BrandBlueDark	#016E97	Texto informativo
BrandViolet	#A81D81	Perfil, comunicación y acciones
BrandVioletIcon	#A62080	Iconos del panal
BrandVioletDark	#37105E	Gradientes violetas
Ink	#18181B	Texto principal
InkSecondary	#3F3F46	Etiquetas y botones
InkMuted	#52525B	Descripciones
InkSubtle	#71717A	Metadatos
White	#FFFFFF	Tarjetas y hexágonos
WarmWhite	#FDFBF8	Tarjetas secundarias
CanvasGray	#F1F1F1	Menú principal
Border	rgba(24,24,27,0.09)	Separadores
ErrorSoft	#FDECEC	Fondo de error
WarningSoft	#FEF9E6	Fondo de advertencia
InfoSoft	#E6F6FC	Fondo informativo
SuccessSoft	#E6F5EE	Fondo de éxito


Gradiente de login y módulos:
120 grados
0%   #FDECEC
42%  #E6F6FC
78%  #FEF9E6
100% #F5E8F1
En MAUI debe implementarse como LinearGradientBrush. Si se busca el acabado todavía más etéreo del ejemplo, pueden superponerse elipses muy difuminadas, pero eso sería una mejora sobre el código actual.
3. Especificación exacta del panal 4–5–4
Esta composición corresponde a /lista-asignaturas.
Fondo
- Ocupa todo el área debajo del encabezado.
- Utiliza el gradiente pastel anterior.
- No tiene textura ni ruido.
- El contenido útil está limitado a 1152 px.
- Encabezado fijo de 68 px.
- Se reserva espacio inferior para la navegación flotante.
Geometría del hexágono
- Orientación vertical: punta superior e inferior.
- Relación exacta: alto = ancho × 1.1547.
- Ancho:
clamp(74px, min(11vw, (viewportHeight - 420px) / 3.1), 158px)
En 1920×1080:
- Ancho base: aproximadamente 158 px.
- Alto base: aproximadamente 182.4 px.
- Matriz visible: aproximadamente 865 × 492 px.
- Ocupa alrededor del 45 % del ancho de pantalla.
El contorno redondeado se basa en esta geometría normalizada:
M .42,.04
Q .50,0 .58,.04
L .92,.21
Q 1,.25 1,.33
L 1,.67
Q 1,.75 .92,.79
L .58,.96
Q .50,1 .42,.96
L .08,.79
Q 0,.75 0,.67
L 0,.33
Q 0,.25 .08,.21
Z
En MAUI conviene crear un HexagonView con GraphicsView o Path, reutilizando esta geometría escalada al tamaño disponible.
Apariencia
- Relleno: #FFFFFF.
- Sin borde visible.
- Texto: #3F3F46.
- Icono centrado y coloreado según la materia.
- Icono: aproximadamente 23.5 % del ancho.
- Etiqueta: aproximadamente 8.8 % del ancho, peso 700.
- Sombra normal:
0 1px 1px rgba(24,24,27,0.05)
0 4px 8px rgba(24,24,27,0.09)
- Hover: fondo #FDFBF8, escala 1.04 y sombra más intensa.
- Presionado: escala 0.97.
- Foco: contorno rojo interior de 3 px.
Distribución
Filas visuales:
          Biología | Lengua | Sociales | Artística

Ed. Física | Inglés | Matemáticas | Física | Ética

       Saber | Química | Tecnología | Proyectos
Cálculos:
- Distancia entre centros horizontales: 1.117 × ancho.
- Separación visible horizontal: 0.117 × ancho.
- A 158 px: aproximadamente 18.5 px.
- Distancia entre centros verticales: 0.973 × ancho.
- Superposición vertical: aproximadamente 28.7 px.
La segunda fila tiene cinco elementos y se desplaza medio hexágono respecto a las filas de cuatro.
Responsive
A ≤900 px deja de mostrarse como panal:
- Ancho del hexágono: clamp(120px, 44vw, 200px).
- Se transforma en una lista vertical en zigzag.
- Elementos impares hacia la izquierda y pares hacia la derecha.
- Solo el área del panal hace scroll.
- La tarjeta informativa de hover desaparece.
- Los hexágonos flotan 9 px verticalmente durante 2200 ms.
- Aparece durante cuatro segundos un indicador circular de scroll de 46 px.
4. Menú principal hexagonal
No debe confundirse con el panal de asignaturas.
Desktop, desde 1280 px
- Fondo sólido #F1F1F1.
- Logo y perfil en las esquinas superiores.
- SVG hexagonal multicolor detrás de las tarjetas.
- Hexágonos blancos con la misma relación 1 : 1.1547.
- Tamaño máximo 222 × 256.3 px.
- En 1920×1080, el conjunto del estudiante mide aproximadamente 718 × 688 px.
Distribución del estudiante y administrador: siete tarjetas en patrón 2–3–2, con Perfil en el centro.
El profesor agrega cuatro satélites:
- Reportes arriba.
- Asistencia a la izquierda.
- Historial a la derecha.
- Estudiantes abajo.
Total visible para profesor: 11 hexágonos. Ayuda se omite del panal del profesor y permanece en la navegación inferior.
Menos de 1280 px
- Se usa otra composición con encabezado de bienvenida.
- El hexágono se calcula como:
min(148px, (viewportWidth - 56px) / 3)
- En 390 px mide aproximadamente 111 × 128.5 px.
- La salida de sesión se representa como otro hexágono inferior.
- La navegación flotante se reduce a Menú, Ayuda y Cerrar sesión.
5. Pantallas
Ruta	Composición principal

/login	Tarjeta blanca de 496 px sobre gradiente pastel; campos deshabilitados y tres botones de rol.
/mainmenu	Panal de módulos según estudiante, profesor o administrador.
/lista-asignaturas	Breadcrumb, título y matriz 4–5–4. Profesor/admin ven “Crear Asignatura”.
/nueva-asignatura	Galería horizontal de plantillas, filtros por grado/país, importación y editor jerárquico.
/lista-asignaturas/:id	Dos modos: ruta de aprendizaje hexagonal y vista general por unidades.
/enciclopedia	Hero rojo, filtros, banderas, carruseles de clases, exámenes, libros y visores.
/progreso	Última clase, indicadores hexagonales y contenido dependiente del rol.
/calendario	Calendario blanco con vistas mes/semana/día y chips de eventos.
/comunicacion	Tableros de avisos institucionales y del profesor; compositores según permisos.
/ayuda	Excepción visual: fondo azul, texto blanco, CTA amarillo, categorías y visor de artículos.
/perfil	Identidad, cursos impartidos, seguridad y accesibilidad; predominio magenta.
/asistencia	Profesor: tabla y llamado de lista. Estudiante: indicadores e historial. Admin: cumplimiento.
/clase-de-hoy	Talleres en vivo, monitoreo de conectados y contenido compartido.
/estudiantes	Observaciones, mensajes y contraseñas del profesor.
/administracion/estudiantes	Tabla administrativa de estudiantes y acciones.
/reportes	Reportes de notas, uso y reportes individuales.
/historial	Actividad reciente y tabla histórica.
/profesores	Tabla de profesores y control de asignaturas.
/certificados	Lista editable de plantillas de certificados.
/logs-bitacora	Pestañas para comportamiento y errores.
/configuraciones	Idioma, escala de notas, sistema y versión.

## Estructura de componentes del Login

El Login en MAUI .NET debería lucir como una tarjeta de login tradicional, usando una tarjeta que permita el ingreso de correo electrónico y contraseña:
En el sistema LMS que corre en .NET MAUI C# debes colocar un estilo visual que permita manejar WebViews de la siguiente manera:
1. Tener una pantalla muy similar o idéntica en lo posible a la imagen ./referencias_gráficas/login.png
2. Tener una tarjeta con los botones de demo para inicar cómo profesor o como estudiante
3. Recuerda que debe lucir con un poco de sombras los botones 

## Estructura del main menú para estudiantes

Tenemos unos hexágonos de manera central de la pantalla que permiten la navegación. En una versión de prototipo el HTML resultante salía:

<div class="main-page" style="--cluster-half: 1.617; --cluster-height: 3.1;"><header class="main-page__header"><div class="main-page__brand"><img src="/src/assets/avacom-logo.svg?no-inline" alt="AVACOM"><span>CLASSROOM</span></div><div class="main-page__user" aria-label="Ethan, Estudiante"><span class="main-page__avatar" aria-hidden="true" style="background-color: rgb(107, 107, 107);">EM</span><span><strong>Ethan</strong><small>Estudiante</small></span></div></header><main class="responsive-hex-menu responsive-hex-menu--estudiante"><svg class="responsive-hex-menu__defs" width="0" height="0" aria-hidden="true"><defs><clipPath id="responsiveMainMenuHex" clipPathUnits="objectBoundingBox"><path d="M0.43,0.025 Q0.5,0 0.57,0.025 L0.9,0.19 Q0.99,0.235 0.99,0.335 L0.99,0.665 Q0.99,0.765 0.9,0.81 L0.57,0.975 Q0.5,1 0.43,0.975 L0.1,0.81 Q0.01,0.765 0.01,0.665 L0.01,0.335 Q0.01,0.235 0.1,0.19 Z"></path></clipPath></defs></svg><header class="responsive-hex-menu__intro"><h1>Bienvenido, Ethan</h1><p>¿Qué quieres hacer hoy? Toca una opción para entrar.</p></header><section class="responsive-hex-menu__core" aria-label="Menú principal"><img class="responsive-hex-menu__background" src="/src/assets/mainmenu/ColorHexagon.svg?no-inline" alt="" aria-hidden="true"><div class="responsive-hex-menu__rows"><div class="responsive-hex-menu__row"><div class="responsive-hex-menu__cell" style="--responsive-delay: 0ms;"><div class="responsive-hex-menu__shadow"><button class="responsive-hex-menu__button" type="button"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="#e5282c" viewBox="0 0 256 256" aria-hidden="true" class="responsive-hex-menu__icon"><path d="M232,48H160a40,40,0,0,0-32,16A40,40,0,0,0,96,48H24a8,8,0,0,0-8,8V200a8,8,0,0,0,8,8H96a24,24,0,0,1,24,24,8,8,0,0,0,16,0,24,24,0,0,1,24-24h72a8,8,0,0,0,8-8V56A8,8,0,0,0,232,48ZM96,192H32V64H96a24,24,0,0,1,24,24V200A39.81,39.81,0,0,0,96,192Zm128,0H160a39.81,39.81,0,0,0-24,8V88a24,24,0,0,1,24-24h64Z"></path></svg><span>Asignaturas</span></button></div></div><div class="responsive-hex-menu__cell" style="--responsive-delay: 220ms;"><div class="responsive-hex-menu__shadow"><button class="responsive-hex-menu__button" type="button"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="#c8222f" viewBox="0 0 256 256" aria-hidden="true" class="responsive-hex-menu__icon"><path d="M221.8,175.94C216.25,166.38,208,139.33,208,104a80,80,0,1,0-160,0c0,35.34-8.26,62.38-13.81,71.94A16,16,0,0,0,48,200H88.81a40,40,0,0,0,78.38,0H208a16,16,0,0,0,13.8-24.06ZM128,216a24,24,0,0,1-22.62-16h45.24A24,24,0,0,1,128,216ZM48,184c7.7-13.24,16-43.92,16-80a64,64,0,1,1,128,0c0,36.05,8.28,66.73,16,80Z"></path></svg><span>Comunicación</span></button></div></div></div><div class="responsive-hex-menu__row"><div class="responsive-hex-menu__cell" style="--responsive-delay: 55ms;"><div class="responsive-hex-menu__shadow"><button class="responsive-hex-menu__button" type="button"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="#f2c600" viewBox="0 0 256 256" aria-hidden="true" class="responsive-hex-menu__icon"><path d="M231.65,194.55,198.46,36.75a16,16,0,0,0-19-12.39L132.65,34.42a16.08,16.08,0,0,0-12.3,19l33.19,157.8A16,16,0,0,0,169.16,224a16.25,16.25,0,0,0,3.38-.36l46.81-10.06A16.09,16.09,0,0,0,231.65,194.55ZM136,50.15c0-.06,0-.09,0-.09l46.8-10,3.33,15.87L139.33,66Zm6.62,31.47,46.82-10.05,3.34,15.9L146,97.53Zm6.64,31.57,46.82-10.06,13.3,63.24-46.82,10.06ZM216,197.94l-46.8,10-3.33-15.87L212.67,182,216,197.85C216,197.91,216,197.94,216,197.94ZM104,32H56A16,16,0,0,0,40,48V208a16,16,0,0,0,16,16h48a16,16,0,0,0,16-16V48A16,16,0,0,0,104,32ZM56,48h48V64H56Zm0,32h48v96H56Zm48,128H56V192h48v16Z"></path></svg><span>Enciclopedia</span></button></div></div><div class="responsive-hex-menu__cell" style="--responsive-delay: 330ms;"><div class="responsive-hex-menu__shadow"><button class="responsive-hex-menu__button" type="button"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="#18181b" viewBox="0 0 256 256" aria-hidden="true" class="responsive-hex-menu__icon"><path d="M230.92,212c-15.23-26.33-38.7-45.21-66.09-54.16a72,72,0,1,0-73.66,0C63.78,166.78,40.31,185.66,25.08,212a8,8,0,1,0,13.85,8c18.84-32.56,52.14-52,89.07-52s70.23,19.44,89.07,52a8,8,0,1,0,13.85-8ZM72,96a56,56,0,1,1,56,56A56.06,56.06,0,0,1,72,96Z"></path></svg><span>Perfil</span></button></div></div><div class="responsive-hex-menu__cell" style="--responsive-delay: 110ms;"><div class="responsive-hex-menu__shadow"><button class="responsive-hex-menu__button" type="button"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="#a62080" viewBox="0 0 256 256" aria-hidden="true" class="responsive-hex-menu__icon"><path d="M232,208a8,8,0,0,1-8,8H32a8,8,0,0,1-8-8V48a8,8,0,0,1,16,0V156.69l50.34-50.35a8,8,0,0,1,11.32,0L128,132.69,180.69,80H160a8,8,0,0,1,0-16h40a8,8,0,0,1,8,8v40a8,8,0,0,1-16,0V91.31l-58.34,58.35a8,8,0,0,1-11.32,0L96,123.31l-56,56V200H224A8,8,0,0,1,232,208Z"></path></svg><span>Progreso</span></button></div></div></div><div class="responsive-hex-menu__row"><div class="responsive-hex-menu__cell" style="--responsive-delay: 165ms;"><div class="responsive-hex-menu__shadow"><button class="responsive-hex-menu__button" type="button"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="#009c60" viewBox="0 0 256 256" aria-hidden="true" class="responsive-hex-menu__icon"><path d="M208,32H184V24a8,8,0,0,0-16,0v8H88V24a8,8,0,0,0-16,0v8H48A16,16,0,0,0,32,48V208a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V48A16,16,0,0,0,208,32ZM72,48v8a8,8,0,0,0,16,0V48h80v8a8,8,0,0,0,16,0V48h24V80H48V48ZM208,208H48V96H208V208Zm-68-76a12,12,0,1,1-12-12A12,12,0,0,1,140,132Zm44,0a12,12,0,1,1-12-12A12,12,0,0,1,184,132ZM96,172a12,12,0,1,1-12-12A12,12,0,0,1,96,172Zm44,0a12,12,0,1,1-12-12A12,12,0,0,1,140,172Zm44,0a12,12,0,1,1-12-12A12,12,0,0,1,184,172Z"></path></svg><span>Calendario</span></button></div></div><div class="responsive-hex-menu__cell" style="--responsive-delay: 275ms;"><div class="responsive-hex-menu__shadow"><button class="responsive-hex-menu__button" type="button"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="#15a3dd" viewBox="0 0 256 256" aria-hidden="true" class="responsive-hex-menu__icon"><path d="M140,180a12,12,0,1,1-12-12A12,12,0,0,1,140,180ZM128,72c-22.06,0-40,16.15-40,36v4a8,8,0,0,0,16,0v-4c0-11,10.77-20,24-20s24,9,24,20-10.77,20-24,20a8,8,0,0,0-8,8v8a8,8,0,0,0,16,0v-.72c18.24-3.35,32-17.9,32-35.28C168,88.15,150.06,72,128,72Zm104,56A104,104,0,1,1,128,24,104.11,104.11,0,0,1,232,128Zm-16,0a88,88,0,1,0-88,88A88.1,88.1,0,0,0,216,128Z"></path></svg><span>Ayuda</span></button></div></div></div></div></section><div class="responsive-hex-menu__logout"><div class="responsive-hex-menu__cell" style="--responsive-delay: 385ms;"><div class="responsive-hex-menu__shadow"><button class="responsive-hex-menu__button" type="button"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="#e5262b" viewBox="0 0 256 256" aria-hidden="true" class="responsive-hex-menu__icon"><path d="M120,216a8,8,0,0,1-8,8H48a8,8,0,0,1-8-8V40a8,8,0,0,1,8-8h64a8,8,0,0,1,0,16H56V208h56A8,8,0,0,1,120,216Zm109.66-93.66-40-40a8,8,0,0,0-11.32,11.32L204.69,120H112a8,8,0,0,0,0,16h92.69l-26.35,26.34a8,8,0,0,0,11.32,11.32l40-40A8,8,0,0,0,229.66,122.34Z"></path></svg><span>Cerrar sesión</span></button></div></div></div></main><main class="desktop-hex-menu"><svg class="desktop-hex-menu__defs" width="0" height="0" aria-hidden="true"><defs><clipPath id="mainMenuHex" clipPathUnits="objectBoundingBox"><path d="M0.42,0.04 Q0.5,0 0.58,0.04 L0.92,0.21 Q1,0.25 1,0.33 L1,0.67 Q1,0.75 0.92,0.79 L0.58,0.96 Q0.5,1 0.42,0.96 L0.08,0.79 Q0,0.75 0,0.67 L0,0.33 Q0,0.25 0.08,0.21 Z"></path></clipPath></defs></svg><div class="desktop-hex-menu__cluster"><img class="desktop-hex-menu__background" src="/src/assets/mainmenu/ColorHexagon.svg?no-inline" alt="" aria-hidden="true"><div class="desktop-hex-menu__cell" style="--hex-x: -0.5585; --hex-y: -0.973; --hex-delay: 151ms;"><div class="desktop-hex-menu__shadow"><button class="desktop-hex-menu__button" type="button"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="#e5282c" viewBox="0 0 256 256" aria-hidden="true" class="desktop-hex-menu__icon"><path d="M232,48H160a40,40,0,0,0-32,16A40,40,0,0,0,96,48H24a8,8,0,0,0-8,8V200a8,8,0,0,0,8,8H96a24,24,0,0,1,24,24,8,8,0,0,0,16,0,24,24,0,0,1,24-24h72a8,8,0,0,0,8-8V56A8,8,0,0,0,232,48ZM96,192H32V64H96a24,24,0,0,1,24,24V200A39.81,39.81,0,0,0,96,192Zm128,0H160a39.81,39.81,0,0,0-24,8V88a24,24,0,0,1,24-24h64Z"></path></svg><span>Asignaturas</span></button></div></div><div class="desktop-hex-menu__cell" style="--hex-x: -1.117; --hex-y: 0; --hex-delay: 151ms;"><div class="desktop-hex-menu__shadow"><button class="desktop-hex-menu__button" type="button"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="#f2c600" viewBox="0 0 256 256" aria-hidden="true" class="desktop-hex-menu__icon"><path d="M231.65,194.55,198.46,36.75a16,16,0,0,0-19-12.39L132.65,34.42a16.08,16.08,0,0,0-12.3,19l33.19,157.8A16,16,0,0,0,169.16,224a16.25,16.25,0,0,0,3.38-.36l46.81-10.06A16.09,16.09,0,0,0,231.65,194.55ZM136,50.15c0-.06,0-.09,0-.09l46.8-10,3.33,15.87L139.33,66Zm6.62,31.47,46.82-10.05,3.34,15.9L146,97.53Zm6.64,31.57,46.82-10.06,13.3,63.24-46.82,10.06ZM216,197.94l-46.8,10-3.33-15.87L212.67,182,216,197.85C216,197.91,216,197.94,216,197.94ZM104,32H56A16,16,0,0,0,40,48V208a16,16,0,0,0,16,16h48a16,16,0,0,0,16-16V48A16,16,0,0,0,104,32ZM56,48h48V64H56Zm0,32h48v96H56Zm48,128H56V192h48v16Z"></path></svg><span>Enciclopedia</span></button></div></div><div class="desktop-hex-menu__cell" style="--hex-x: 1.117; --hex-y: 0; --hex-delay: 151ms;"><div class="desktop-hex-menu__shadow"><button class="desktop-hex-menu__button" type="button"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="#a62080" viewBox="0 0 256 256" aria-hidden="true" class="desktop-hex-menu__icon"><path d="M232,208a8,8,0,0,1-8,8H32a8,8,0,0,1-8-8V48a8,8,0,0,1,16,0V156.69l50.34-50.35a8,8,0,0,1,11.32,0L128,132.69,180.69,80H160a8,8,0,0,1,0-16h40a8,8,0,0,1,8,8v40a8,8,0,0,1-16,0V91.31l-58.34,58.35a8,8,0,0,1-11.32,0L96,123.31l-56,56V200H224A8,8,0,0,1,232,208Z"></path></svg><span>Progreso</span></button></div></div><div class="desktop-hex-menu__cell" style="--hex-x: -0.5585; --hex-y: 0.973; --hex-delay: 151ms;"><div class="desktop-hex-menu__shadow"><button class="desktop-hex-menu__button" type="button"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="#009c60" viewBox="0 0 256 256" aria-hidden="true" class="desktop-hex-menu__icon"><path d="M208,32H184V24a8,8,0,0,0-16,0v8H88V24a8,8,0,0,0-16,0v8H48A16,16,0,0,0,32,48V208a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V48A16,16,0,0,0,208,32ZM72,48v8a8,8,0,0,0,16,0V48h80v8a8,8,0,0,0,16,0V48h24V80H48V48ZM208,208H48V96H208V208Zm-68-76a12,12,0,1,1-12-12A12,12,0,0,1,140,132Zm44,0a12,12,0,1,1-12-12A12,12,0,0,1,184,132ZM96,172a12,12,0,1,1-12-12A12,12,0,0,1,96,172Zm44,0a12,12,0,1,1-12-12A12,12,0,0,1,140,172Zm44,0a12,12,0,1,1-12-12A12,12,0,0,1,184,172Z"></path></svg><span>Calendario</span></button></div></div><div class="desktop-hex-menu__cell" style="--hex-x: 0.5585; --hex-y: -0.973; --hex-delay: 151ms;"><div class="desktop-hex-menu__shadow"><button class="desktop-hex-menu__button" type="button"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="#c8222f" viewBox="0 0 256 256" aria-hidden="true" class="desktop-hex-menu__icon"><path d="M221.8,175.94C216.25,166.38,208,139.33,208,104a80,80,0,1,0-160,0c0,35.34-8.26,62.38-13.81,71.94A16,16,0,0,0,48,200H88.81a40,40,0,0,0,78.38,0H208a16,16,0,0,0,13.8-24.06ZM128,216a24,24,0,0,1-22.62-16h45.24A24,24,0,0,1,128,216ZM48,184c7.7-13.24,16-43.92,16-80a64,64,0,1,1,128,0c0,36.05,8.28,66.73,16,80Z"></path></svg><span>Comunicación</span></button></div></div><div class="desktop-hex-menu__cell" style="--hex-x: 0.5585; --hex-y: 0.973; --hex-delay: 151ms;"><div class="desktop-hex-menu__shadow"><button class="desktop-hex-menu__button" type="button"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="#15a3dd" viewBox="0 0 256 256" aria-hidden="true" class="desktop-hex-menu__icon"><path d="M140,180a12,12,0,1,1-12-12A12,12,0,0,1,140,180ZM128,72c-22.06,0-40,16.15-40,36v4a8,8,0,0,0,16,0v-4c0-11,10.77-20,24-20s24,9,24,20-10.77,20-24,20a8,8,0,0,0-8,8v8a8,8,0,0,0,16,0v-.72c18.24-3.35,32-17.9,32-35.28C168,88.15,150.06,72,128,72Zm104,56A104,104,0,1,1,128,24,104.11,104.11,0,0,1,232,128Zm-16,0a88,88,0,1,0-88,88A88.1,88.1,0,0,0,216,128Z"></path></svg><span>Ayuda</span></button></div></div><div class="desktop-hex-menu__cell" style="--hex-x: 0; --hex-y: 0; --hex-delay: 0ms;"><div class="desktop-hex-menu__shadow"><button class="desktop-hex-menu__button" type="button"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="#18181b" viewBox="0 0 256 256" aria-hidden="true" class="desktop-hex-menu__icon"><path d="M230.92,212c-15.23-26.33-38.7-45.21-66.09-54.16a72,72,0,1,0-73.66,0C63.78,166.78,40.31,185.66,25.08,212a8,8,0,1,0,13.85,8c18.84-32.56,52.14-52,89.07-52s70.23,19.44,89.07,52a8,8,0,1,0,13.85-8ZM72,96a56,56,0,1,1,56,56A56.06,56.06,0,0,1,72,96Z"></path></svg><span>Perfil</span></button></div></div></div></main><nav class="main-navbar main-navbar--estudiante" aria-label="Navegación principal"><div class="main-navbar__pill is-open"><button class="main-navbar__home" type="button" aria-label="Contraer navegación" aria-expanded="true"><img src="/src/assets/avacom-symbol.svg?no-inline" alt=""></button><div class="main-navbar__clip" aria-hidden="false"><div class="main-navbar__items"><button class="main-navbar__item main-navbar__item--compact" type="button" title="Menú principal" tabindex="0" style="--item-delay: 90ms; --item-close-delay: 110ms;"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="currentColor" viewBox="0 0 256 256" aria-hidden="true" class="main-navbar__icon"><path d="M104,40H56A16,16,0,0,0,40,56v48a16,16,0,0,0,16,16h48a16,16,0,0,0,16-16V56A16,16,0,0,0,104,40Zm0,64H56V56h48v48Zm96-64H152a16,16,0,0,0-16,16v48a16,16,0,0,0,16,16h48a16,16,0,0,0,16-16V56A16,16,0,0,0,200,40Zm0,64H152V56h48v48Zm-96,32H56a16,16,0,0,0-16,16v48a16,16,0,0,0,16,16h48a16,16,0,0,0,16-16V152A16,16,0,0,0,104,136Zm0,64H56V152h48v48Zm96-64H152a16,16,0,0,0-16,16v48a16,16,0,0,0,16,16h48a16,16,0,0,0,16-16V152A16,16,0,0,0,200,136Zm0,64H152V152h48v48Z"></path></svg><span>Menú principal</span></button><button class="main-navbar__item" type="button" title="Asignaturas" tabindex="0" style="--item-delay: 145ms; --item-close-delay: 88ms;"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="currentColor" viewBox="0 0 256 256" aria-hidden="true" class="main-navbar__icon"><path d="M232,48H160a40,40,0,0,0-32,16A40,40,0,0,0,96,48H24a8,8,0,0,0-8,8V200a8,8,0,0,0,8,8H96a24,24,0,0,1,24,24,8,8,0,0,0,16,0,24,24,0,0,1,24-24h72a8,8,0,0,0,8-8V56A8,8,0,0,0,232,48ZM96,192H32V64H96a24,24,0,0,1,24,24V200A39.81,39.81,0,0,0,96,192Zm128,0H160a39.81,39.81,0,0,0-24,8V88a24,24,0,0,1,24-24h64Z"></path></svg><span>Asignaturas</span></button><button class="main-navbar__item" type="button" title="Enciclopedia" tabindex="0" style="--item-delay: 200ms; --item-close-delay: 66ms;"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="currentColor" viewBox="0 0 256 256" aria-hidden="true" class="main-navbar__icon"><path d="M231.65,194.55,198.46,36.75a16,16,0,0,0-19-12.39L132.65,34.42a16.08,16.08,0,0,0-12.3,19l33.19,157.8A16,16,0,0,0,169.16,224a16.25,16.25,0,0,0,3.38-.36l46.81-10.06A16.09,16.09,0,0,0,231.65,194.55ZM136,50.15c0-.06,0-.09,0-.09l46.8-10,3.33,15.87L139.33,66Zm6.62,31.47,46.82-10.05,3.34,15.9L146,97.53Zm6.64,31.57,46.82-10.06,13.3,63.24-46.82,10.06ZM216,197.94l-46.8,10-3.33-15.87L212.67,182,216,197.85C216,197.91,216,197.94,216,197.94ZM104,32H56A16,16,0,0,0,40,48V208a16,16,0,0,0,16,16h48a16,16,0,0,0,16-16V48A16,16,0,0,0,104,32ZM56,48h48V64H56Zm0,32h48v96H56Zm48,128H56V192h48v16Z"></path></svg><span>Enciclopedia</span></button><button class="main-navbar__item" type="button" title="Perfil" tabindex="0" style="--item-delay: 255ms; --item-close-delay: 44ms;"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="currentColor" viewBox="0 0 256 256" aria-hidden="true" class="main-navbar__icon"><path d="M230.92,212c-15.23-26.33-38.7-45.21-66.09-54.16a72,72,0,1,0-73.66,0C63.78,166.78,40.31,185.66,25.08,212a8,8,0,1,0,13.85,8c18.84-32.56,52.14-52,89.07-52s70.23,19.44,89.07,52a8,8,0,1,0,13.85-8ZM72,96a56,56,0,1,1,56,56A56.06,56.06,0,0,1,72,96Z"></path></svg><span>Perfil</span></button><button class="main-navbar__item main-navbar__item--compact" type="button" title="Ayuda" tabindex="0" style="--item-delay: 310ms; --item-close-delay: 22ms;"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="currentColor" viewBox="0 0 256 256" aria-hidden="true" class="main-navbar__icon"><path d="M140,180a12,12,0,1,1-12-12A12,12,0,0,1,140,180ZM128,72c-22.06,0-40,16.15-40,36v4a8,8,0,0,0,16,0v-4c0-11,10.77-20,24-20s24,9,24,20-10.77,20-24,20a8,8,0,0,0-8,8v8a8,8,0,0,0,16,0v-.72c18.24-3.35,32-17.9,32-35.28C168,88.15,150.06,72,128,72Zm104,56A104,104,0,1,1,128,24,104.11,104.11,0,0,1,232,128Zm-16,0a88,88,0,1,0-88,88A88.1,88.1,0,0,0,216,128Z"></path></svg><span>Ayuda</span></button><button class="main-navbar__item main-navbar__item--compact" type="button" title="Cerrar sesión" tabindex="0" style="--item-delay: 365ms; --item-close-delay: 0ms;"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="currentColor" viewBox="0 0 256 256" aria-hidden="true" class="main-navbar__icon"><path d="M120,216a8,8,0,0,1-8,8H48a8,8,0,0,1-8-8V40a8,8,0,0,1,8-8h64a8,8,0,0,1,0,16H56V208h56A8,8,0,0,1,120,216Zm109.66-93.66-40-40a8,8,0,0,0-11.32,11.32L204.69,120H112a8,8,0,0,0,0,16h92.69l-26.35,26.34a8,8,0,0,0,11.32,11.32l40-40A8,8,0,0,0,229.66,122.34Z"></path></svg><span>Cerrar sesión</span></button></div></div><button class="main-navbar__toggle" type="button" aria-label="Contraer navegación" aria-expanded="true"><svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" fill="currentColor" viewBox="0 0 256 256" class="main-navbar__toggle-icon is-open" aria-hidden="true"><path d="M144.49,136.49l-80,80a12,12,0,0,1-17-17L119,128,47.51,56.49a12,12,0,0,1,17-17l80,80A12,12,0,0,1,144.49,136.49Zm80-17-80-80a12,12,0,1,0-17,17L199,128l-71.52,71.51a12,12,0,0,0,17,17l80-80A12,12,0,0,0,224.49,119.51Z"></path></svg></button></div></nav></div>

Recuerda que debe construirse de manera idéntica en MAUI de .NET C#:

1. Puedes tomar de referencia la imagen de 

Todas las pantallas de módulos comparten:
- Topbar fija de 68 px.
- Título a la izquierda.
- Logo centrado.
- Avatar y rol a la derecha.
- Contenido máximo de 1152 px.
- Navegación inferior flotante.
- Tarjetas de 24 px de radio.
- Botones y filtros con forma de píldora.
- Altura táctil mínima de 44–50 px.
6. Flujos principales
Entrada por rol
Portada /
→ “Ingresar en esta pantalla”
→ /login
→ Demo Estudiante | Demo Profesor | Demo Administrador
→ /mainmenu[?role=...]
→ selección de módulo
Asignatura y ruta de aprendizaje
Menú
→ Asignaturas
→ tocar hexágono de materia
→ detalle del curso
→ Ruta de aprendizaje, modo inicial
→ tocar hito hexagonal
→ modal de unidad
→ “Ver en vista general”
→ vista general desplazada hasta la unidad seleccionada
Crear asignatura
Asignaturas del profesor/admin
→ Crear Asignatura
→ filtrar por grado y estándar
→ seleccionar plantilla o “Nueva Plantilla”
→ editor de nombre, grado, unidades, temas y actividades
→ Crear asignatura
→ confirmación y regreso a la galería
Ruta alternativa:
Crear Asignatura
→ Importar curso
→ SCORM | Moodle | OpenEDX | AVACOM
→ aviso para elegir archivo
La subida real todavía no está implementada.
Enciclopedia
Menú
→ Enciclopedia
→ filtro de grado y país
→ recurso
→ ficha lateral o modal
→ acción según rol
Los vídeos abren un lightbox de pantalla completa y los PDF un visor independiente.
Asistencia del profesor
Menú profesor
→ Asistencia
→ seleccionar asignatura
→ modo “En computador” o “Llamar lista”
→ marcar presente/tarde/excusa/ausente
→ exportar CSV o XLSX
7. Recomendación de implementación MAUI
La réplica debería usar:
- MVVM y un estado global de rol e idioma.
- Rutas de Shell, pero sin usar la barra visual predeterminada de Shell.
- Un ModulePageBase con Grid: topbar fija, ScrollView central y navegación flotante superpuesta.
- HexagonView reutilizable con GraphicsView/Path, sombra y contenido centrado.
- AbsoluteLayout para los panales y rutas de aprendizaje.
- CollectionView horizontal para carruseles.
- VisualStateManager para los cortes de 1280, 900, 820, 760 y 620 px.
- SVG locales para logos, aro multicolor e iconos; no depender de fuentes remotas.
- Tokens en Colors.xaml, Styles.xaml, Dimensions.xaml y Shadows.xaml.
- Servicio de accesibilidad para texto grande, alto contraste y reducción de movimiento.
8. Hallazgos que no deberían portarse ciegamente
- El login real antiguo y ProtectedRoute existen, pero no están conectados al enrutamiento activo.
- La portada intenta navegar a /dashboard tras autenticarse, pero esa ruta no existe.
- Los roles se controlan actualmente mediante ?role=; en producción deben venir de la sesión autenticada.
- ModuleDock, MenuButtons, LoginPage y AuthTemplate son implementaciones antiguas o sin uso activo.
- Comunicación administrativa y Certificados tienen rutas, pero no aparecen en el menú principal del administrador.
- El panal extendido del profesor puede acercarse o superponerse ligeramente con la navegación inferior; conviene conservar la composición y corregir esa colisión en MAUI.
- El desenfoque backdrop-filter no tiene equivalencia uniforme en MAUI. Debe aproximarse con superficies translúcidas y, solo si es imprescindible, efectos nativos por plataforma.


## Estructura Backend

Este backend debe estar desarroillado en Django Rest Framework, usando también websockets y conexiones HTTP para hacer CRUDs a la base de datos. 

Recuerda estas reglas más importantes:

1. EL backend del proyecto debe correr en el 0.0.0.0:8000
2. La idea es usar web sockets para ver conexiones en vivo de algunos estudiantes

# Prompt Spec-Driven Development · Backend AVACOM LMS

| Campo | Valor |
|---|---|
| Tipo | Especificación inversa de un proyecto existente (*brownfield*) |
| Alcance analizado | `./backend` |
| Fecha de corte | 2026-09-07 |
| Método | Spec Kit (`/speckit.*`) |
| Objetivo | Formalizar y poder reproducir el comportamiento del backend sin convertir defectos accidentales en requisitos |

## Cómo usar este documento

Ejecuta los bloques en orden. Cada bloque es un prompt independiente para su comando. Revisa y aprueba la salida de una fase antes de avanzar a la siguiente. La Fase 3 no tiene comando: debe ser una conversación y puede bloquear el plan.

Este es un proyecto existente. Para resolver discrepancias usa esta prioridad:

1. Constitución aprobada.
2. Decisiones explícitas obtenidas en la clarificación.
3. Especificación y criterios de aceptación aprobados.
4. Pruebas automatizadas que expresen correctamente esas decisiones.
5. Comportamiento observable del código actual.
6. Comentarios y documentación histórica.

No asumas que el código actual es correcto sólo porque existe. Tampoco cambies un comportamiento observable sin una decisión explícita y una prueba que documente el nuevo contrato.

## Línea base recuperada de `./backend`

El backend actual cubre siete áreas funcionales:

1. Catálogo académico: marcos curriculares, cursos, versiones, secciones, lecciones, recursos, actividades e inscripciones.
2. Publicación versionada: instalación, activación, retiro y reversión de fotografías inmutables de un curso.
3. Inventario por OPS: presencia física, disponibilidad para estudiantes, verificación e historial de paquetes por host.
4. Progreso: avance por lección lógica, promedio del curso e historial que sobrevive a cambios de versión.
5. Quiz: definición, intentos, respuestas idempotentes, calificación, consolidado y actualización en vivo.
6. Paquetes: formato nativo AVACOM, SCORM 1.2, SCORM 2004, cmi5 y AVACOM-Contenido, todos normalizados al mismo árbol académico.
7. Integración local con AVACOM-Contenido: catálogo delegado, materiales referenciados, reparto al aula, reconciliación y exámenes condicionados por capacidades.

La persistencia actual contiene 19 entidades de dominio:

| Área | Entidades |
|---|---|
| Catálogo | `CurriculumFramework`, `Course`, `CourseVersion`, `Section`, `Lesson`, `LessonItem`, `LearningResource`, `Activity` |
| Expediente | `CourseEnrollment`, `LessonProgress`, `AuditLog` |
| Quiz | `QuizQuestion`, `QuizOption`, `QuizAttempt`, `QuizAnswer` |
| Host e integración | `CourseHost`, `UnidadMaterial`, `ExamenPregunta`, `RepartoActivo` |

### Hallazgos que no deben ocultarse

- La documentación antigua sólo enumera 14 tablas; el código y las migraciones actuales contienen 19.
- La regla escrita dice que desinstalar contenido no equivale a borrar un curso. Sin embargo, el detalle de curso implementa `DELETE /api/courses/{id}/`.
- Las versiones se describen como fotografías inmutables, pero su CRUD genérico expone actualización y borrado.
- La auditoría se presenta como registro histórico, pero también tiene CRUD de escritura y borrado.
- La presencia por host debe conservar historial, pero el detalle de `CourseHost` permite borrarlo.
- Las preguntas públicas ocultan `es_correcta`, pero los CRUD administrativos y el detalle de resultados revelan la solución y actualmente no tienen autorización.
- `client_event_id` se acepta al registrar respuestas, pero no se persiste ni participa en la deduplicación. La idempotencia real es por intento y pregunta.
- La instalación de un ZIP importa estructura y registra presencia, pero este backend no administra de forma general los binarios físicos ni los elimina del disco.
- La presencia y el canal de eventos viven en memoria del proceso; el contrato actual presupone una sola instancia del servidor.
- No existe autenticación ni autorización. Cualquier separación entre docente y estudiante es hoy una convención del cliente, no una garantía del backend.

Estos hallazgos son entradas de la clarificación, no permisos para corregir el código durante la especificación.

---

## Fase 1 · Constitución

```text
/speckit.constitution

Crea o actualiza la constitución del backend AVACOM LMS. Este es un sistema local de aula existente; las siguientes reglas son no negociables y deben redactarse como principios verificables, con justificación y consecuencias para desarrollo, revisión y pruebas.

1. Separación entre contenido físico y expediente académico
   - Desinstalar, retirar, perder o volver a instalar un paquete nunca elimina ni modifica automáticamente el curso, las inscripciones, el progreso, los intentos, las respuestas ni las calificaciones.
   - El estado editorial de un curso es distinto de su presencia y disponibilidad en una OPS.
   - Una ausencia debe explicarse con estado y fecha; no debe hacer desaparecer silenciosamente el historial del estudiante.

2. Curso permanente y contenido versionado
   - El curso representa identidad estable; una versión representa una fotografía de contenido.
   - Una versión instalada no se edita destructivamente.
   - Un curso habilitado debe tener una versión activa.
   - Sólo puede existir una versión activa por curso.
   - La versión activa debe pertenecer al mismo curso.
   - Activar o revertir conserva las fotografías anteriores y deja auditoría.

3. Identidad lógica y física
   - Secciones y lecciones de distintas versiones son filas físicas distintas.
   - Sus códigos lógicos permiten reconocer la misma unidad conceptual entre versiones.
   - El progreso pertenece al curso, a la persona y al código lógico de lección, no a una fila física de una versión.

4. Neutralidad del formato de entrada
   - SCORM 1.2, SCORM 2004, cmi5, el paquete nativo y AVACOM-Contenido son formatos de entrada, no modelos académicos distintos.
   - Todo formato compatible se transforma al mismo árbol curso → sección → lección → ítem.
   - No se implementan runtimes completos de SCORM, cmi5, xAPI o LRS dentro de este alcance.

5. Operaciones transaccionales e idempotentes
   - Instalar o reinstalar el mismo curso y versión no crea duplicados.
   - Registrar de nuevo la respuesta de una pregunta actualiza la respuesta existente.
   - Finalizar de nuevo un intento ya finalizado no recalcula ni duplica el resultado.
   - Los cambios de versión, presencia y disponibilidad deben mantener las invariantes incluso ante fallos parciales.
   - Una operación fallida no deja fotografías incompletas publicadas; el fallo relevante queda diagnosticable.

6. Custodia de respuestas y privacidad
   - La clave de respuestas nunca forma parte del catálogo ni del quiz entregado al estudiante.
   - Los resultados detallados y las funciones administrativas se consideran información privilegiada.
   - Ningún registro, error o evento destinado a estudiantes debe filtrar una clave de respuesta.

7. AVACOM-Contenido es otro producto
   - El LMS no lee su base, no descifra sus paquetes y no replica su catálogo.
   - El LMS conserva referencias estables y versión; los datos de presentación se resuelven desde el dueño del catálogo.
   - Las tabletas nunca se conectan directamente al componente local.
   - El componente puede estar ausente: el LMS degrada la experiencia con una explicación y no colapsa.
   - Una biblioteca inaccesible no significa que todo su contenido haya sido retirado; la reconciliación no escribe si no pudo obtener una fuente válida.

8. Topología local y operación de aula
   - El backend principal debe ser accesible desde la LAN de la OPS por el puerto 8000 y exponer un diagnóstico de salud.
   - AVACOM-Contenido sólo se consume por loopback, con dirección dinámica y ficha tomada de su nota de enlace.
   - El flujo local de instalar, usar, calificar, desinstalar y reinstalar debe funcionar sin Internet.
   - La limitación actual a un solo proceso para presencia y eventos debe ser explícita; escalar requiere una decisión de arquitectura.

9. Integridad impuesta en profundidad
   - Las reglas críticas se validan en el límite de entrada, en los servicios de dominio y, cuando el motor lo permite, mediante restricciones de persistencia.
   - Una limitación del mapeador que impida una restricción compuesta debe compensarse con un único servicio autorizado y pruebas permanentes.
   - Los borrados peligrosos se rechazan o se reemplazan por transiciones explícitas.

10. Auditoría confiable
    - Instalación, reinstalación, activación, reversión, retiro, disponibilidad, verificación y reconciliación material dejan actor, momento, objeto, estado anterior, estado nuevo y resultado.
    - La auditoría no se usa como catálogo operativo y no se modifica como si fuera contenido ordinario.

11. Simplicidad del prototipo
    - Conservar una estructura directa y legible; no añadir capas, colas, servicios, motores ni tablas sin un requisito aprobado.
    - Mantener las 19 entidades existentes. Cualquier tabla adicional exige clarificación, justificación en el plan y aprobación explícita.
    - Preferir contratos pequeños y operaciones del dominio sobre abstracciones genéricas que permitan estados inválidos.

12. Contrato verificable
    - Cada requisito funcional y cada invariante debe tener una prueba automatizada trazable.
    - Los contratos públicos deben conservar UTF-8, errores comprensibles e identificadores y tiempos portables.
    - Ninguna fase puede declarar éxito sin ejecutar comprobaciones de configuración, migraciones, pruebas y escenarios de aceptación aplicables.

13. El progreso se registra en el LMS:
    - Todo respecto a las actividades y calificables de cada acción del estudiante debe revisarse dentro del LMS
    - La creación de cursos, contenidos deben estar dentro de AVACOM Biblioteca

Incluye en la constitución un proceso de enmienda: toda excepción debe indicar qué principio cambia, por qué, qué contratos afecta, qué migración requiere y qué pruebas la hacen segura. No describas endpoints ni funciones concretas en esta fase.
```

---

## Fase 2 · Especificación

El siguiente bloque describe intención y comportamiento observable. Deliberadamente no nombra lenguajes, bibliotecas, protocolos, bases de datos, clases, archivos ni patrones técnicos.

```text
/speckit.specify

Título: Catálogo local de cursos, continuidad académica y actividad de aula AVACOM

Problema

Una OPS debe permitir que el docente publique cursos y que los estudiantes los usen dentro de la red del aula. El material puede provenir de varios estándares, cambiar de versión, dejar de estar instalado o volver a aparecer. Ninguno de esos cambios físicos debe borrar el expediente académico ni obligar al estudiante a empezar de nuevo. El docente también necesita observar el avance de un quiz mientras ocurre, obtener la nota y diagnosticar si el contenido local está disponible.

Actores

- Docente: crea y publica cursos, asigna estudiantes, instala contenido, controla su disponibilidad, reparte material y consulta resultados.
- Estudiante: consulta sus cursos, navega la versión publicada, registra progreso y realiza quizzes.
- Técnico de soporte: verifica salud, presencia, integridad, historial y causas de indisponibilidad.
- Biblioteca local de contenido: es dueña de su catálogo, sus medios y sus claves de evaluación; puede estar instalada, cerrada, desactualizada o sin una capacidad opcional.

Historias de usuario prioritarias

US-01 · P1 · Curso navegable
Como estudiante asignado quiero abrir un curso habilitado y recorrer sus secciones, lecciones e ítems en orden para continuar mi aprendizaje.

US-02 · P1 · Quiz calificable
Como estudiante quiero iniciar o reanudar un quiz, responder cada pregunta y finalizarlo para que mi intento, respuestas y nota queden registrados una sola vez.

US-03 · P1 · Seguimiento del docente
Como docente quiero ver cuántos estudiantes están conectados, en qué pregunta está cada uno y cuándo finaliza para acompañar la actividad en tiempo real.

US-04 · P1 · Continuidad ante desinstalación
Como estudiante quiero seguir viendo el curso y mi progreso histórico aunque su contenido no esté disponible en esta OPS, con una explicación clara de su estado.

US-05 · P1 · Reinstalación sin duplicados
Como docente quiero reinstalar el mismo curso para volver a ofrecerlo sin duplicar el curso, la matrícula, el progreso o la calificación.

US-06 · P2 · Versionado y reversión
Como docente quiero instalar una nueva fotografía del contenido, publicarla o volver a una anterior sin alterar el expediente existente.

US-07 · P2 · Paquetes interoperables
Como docente quiero inspeccionar e importar contenido compatible proveniente de SCORM 1.2, SCORM 2004, cmi5, formato nativo o AVACOM-Contenido y obtener siempre la misma jerarquía académica.

US-08 · P2 · Inventario por OPS
Como técnico quiero distinguir lo instalado, lo verificado y lo habilitado en cada equipo para diagnosticar sin confundir el estado físico con el editorial.

US-09 · P2 · Material de biblioteca
Como docente quiero asociar a una lección material ofrecido por la biblioteca local y resolver su nombre y disponibilidad actuales sin duplicar su catálogo.

US-10 · P2 · Reparto de aula
Como docente quiero repartir y retirar temporalmente un material; como estudiante quiero ver sólo lo repartido y saber si dejó de estar disponible.

US-11 · P3 · Reconciliación
Como docente quiero comparar las referencias usadas por los cursos con el catálogo vigente para marcar ausencias y reapariciones, cerrar repartos inválidos y conservar todo el expediente.

US-12 · P3 · Evaluaciones delegadas por capacidad
Como docente quiero montar preguntas procedentes de una evaluación o banco local cuando esa capacidad exista; como estudiante quiero que mi respuesta se compruebe donde vive la clave sin recibirla.

Requisitos funcionales

RF-001. El sistema administra marcos curriculares, cursos, fotografías versionadas, inscripciones, secciones, lecciones, ítems, recursos, actividades y trazas de auditoría.
RF-002. La jerarquía visible de un curso sale exclusivamente de su fotografía activa; un curso sin fotografía activa devuelve una jerarquía vacía.
RF-003. Un curso sólo puede estar habilitado si apunta a una fotografía activa propia.
RF-004. Sólo una fotografía puede estar activa por curso y las anteriores deben conservarse.
RF-005. Publicar o revertir una fotografía actualiza el puntero visible de forma indivisible y deja trazabilidad.
RF-006. Secciones y lecciones tienen identidad lógica estable y orden único dentro de su padre.
RF-007. Cada ítem apunta exactamente a una de estas alternativas: un recurso, una actividad o una referencia externa.
RF-008. Una versión concreta de un recurso o actividad conserva identidad propia y no se sobrescribe al publicar otra.

RF-009. Una inscripción pertenece a la identidad permanente del curso, no a una fotografía.
RF-010. No se crea una entidad local adicional para una persona; se usa su identificador externo.
RF-011. El progreso se registra una sola vez por curso, persona y código lógico de lección.
RF-012. El progreso está entre 0 y 100 y no disminuye por recibir un estado anterior o retrasado.
RF-013. Una lección completada tiene 100% y fecha de finalización.
RF-014. Cada lección pesa igual en el progreso total del curso.
RF-015. El progreso de una lección es el mayor entre el avance registrado y la mejor nota finalizada de sus actividades calificables.
RF-016. Lecciones con progreso que ya no están en la fotografía activa siguen visibles en el historial, identificadas como históricas.

RF-017. El quiz público entrega enunciados y opciones en orden sin indicadores de corrección.
RF-018. Iniciar un quiz activo crea un intento o reanuda el intento abierto de la misma persona, dispositivo y actividad.
RF-019. El intento conserva nombre visible, identificador de persona, dispositivo, pregunta actual, respuestas, estado, nota y tiempos.
RF-020. Una opción sólo es válida si pertenece a una pregunta del mismo quiz del intento.
RF-021. Reenviar la respuesta de la misma pregunta reemplaza la selección anterior y no duplica filas.
RF-022. La nota final es aciertos × puntaje máximo ÷ total de preguntas, redondeada a dos decimales.
RF-023. Finalizar un intento es idempotente y actualiza el progreso de la lección que contiene el quiz.
RF-024. El docente puede consultar un consolidado por actividad y el detalle de respuestas de un intento, sujeto a la política de acceso que se resuelva en clarificación.
RF-025. El docente recibe presencia, avance de pregunta y finalización mientras la actividad ocurre.

RF-026. La presencia física se registra por OPS, curso y fotografía; reinstalar la misma combinación no crea otra presencia.
RF-027. Pueden coexistir varias fotografías instaladas del mismo curso, pero sólo una puede estar disponible para estudiantes en la misma OPS.
RF-028. Un contenido sólo puede estar disponible para estudiantes si está presente localmente.
RF-029. Retirar contenido apaga presencia y disponibilidad, registra cuándo ocurrió y no cambia el estado editorial del curso.
RF-030. Consultar cursos disponibles devuelve únicamente presencias locales y habilitadas para el equipo consultado.
RF-031. Consultar los cursos de una persona parte de sus inscripciones e incluye disponibles y no disponibles con progreso y explicación.
RF-032. Un curso creado manualmente y sin registro de presencia se rige por su estado editorial; una vez que tiene historial de presencia en una OPS, su visibilidad allí se rige por esa presencia.
RF-033. Si varias presencias históricas describen un curso, se prefiere la disponible, luego una presente y por último la retirada más reciente.
RF-034. Verificar una huella distinta cierra la disponibilidad, registra el fallo y exige reinstalación antes de reabrir.

RF-035. Inspeccionar un paquete no modifica el estado y devuelve identidad, versión, formato, huella, conteos y si ya existe.
RF-036. Importar un paquete válido normaliza su estructura al árbol común y realiza la instalación completa o no publica nada.
RF-037. Un paquete sin descriptor reconocible, sin secciones, con órdenes repetidos, sin lecciones o sin ítems se rechaza con una explicación.
RF-038. Reimportar el mismo curso, fotografía y huella es idempotente.
RF-039. El alcance interpreta estructura, recursos y actividades; no ejecuta el runtime completo de los estándares importados.
RF-040. En un paquete AVACOM-Contenido, la taxonomía de profundidad libre se aplana a secciones, lecciones e ítems; una sección vacía no se crea y una lista de lección se expande conservando su orden.
RF-041. Las preguntas incompletas de un manifiesto AVACOM-Contenido no se convierten en un quiz contestable; la actividad informa cuántas preguntas quedaron fuera.

RF-042. La comunicación con la biblioteca local usa su contrato publicado y vuelve a descubrir su dirección e identidad en cada operación.
RF-043. Si la biblioteca no está disponible, el estado lo explica; las pantallas académicas continúan funcionando.
RF-044. El catálogo de la biblioteca se consulta con su política ya aplicada y no se replica como catálogo del LMS.
RF-045. Asociar material a una lección guarda referencia, versión, tipo, taxonomía y estado de la última revisión; el título se resuelve en vivo.
RF-046. Sólo puede asociarse material que la biblioteca ofrezca en ese momento y no puede repetirse la misma referencia y versión en la misma lección.
RF-047. Quitar una asociación no desinstala el paquete de la biblioteca.
RF-048. Repartir material exige equipo, sesión y referencia válida; repetir el mismo reparto abierto es idempotente.
RF-049. Cerrar un reparto conserva cuándo y qué se mostró.
RF-050. El estudiante sólo ve repartos abiertos aplicables, no el catálogo completo.
RF-051. Reconciliar sólo escribe tras obtener un catálogo válido; marca ausencias y reapariciones con fecha, cierra repartos imposibles y no borra expediente.
RF-052. Para cursos cuyo contenido pertenece a la biblioteca, el catálogo vigente decide presencia; para contenido importado y administrado por el LMS, el inventario del LMS decide presencia.
RF-053. Las capacidades opcionales no se simulan: si montar o comprobar una evaluación no está soportado, se informa explícitamente.
RF-054. La clave de una evaluación delegada no entra al LMS; sólo se envía la respuesta y vuelve el veredicto.

RF-055. El sistema ofrece diagnóstico de salud, respuestas de texto internacional correctas y errores comprensibles.
RF-056. Las operaciones de dominio relevantes dejan trazabilidad con actor, objeto, antes, después, resultado y momento.
RF-057. El flujo local completo funciona sin Internet.

Datos demostrativos obligatorios

- Curso “Álgebra Octavo B”, marco SEP México y una primera fotografía publicada.
- Dos secciones, tres lecciones y seis ítems, dos por lección.
- Tres estudiantes inscritos y resultados demostrativos terminados y en progreso.
- El último ítem es “Quiz de cultura general sobre México”, de 100 puntos y cinco preguntas.
- Respuestas correctas: Hugo Sánchez; Mario Molina; Luis Ernesto Miramontes; 1810; Chihuahua.
- La carga se puede repetir sin duplicar la demo y existe una opción explícita de recrearla para desarrollo.

Criterios de aceptación

CA-01. Un paquete válido de cada formato soportado produce el mismo tipo de árbol académico y registra presencia en la OPS.
CA-02. Un curso sólo se abre cuando está presente y disponible en esa OPS.
CA-03. Retirar un curso apaga ambas banderas y registra la fecha sin eliminar curso, matrícula, progreso, intento, respuesta ni nota.
CA-04. Tras el retiro, el curso desaparece de disponibles pero permanece en el historial y en los cursos de la persona como no disponible.
CA-05. Reinstalar devuelve la disponibilidad y conserva exactamente el progreso anterior sin duplicar entidades.
CA-06. La misma lógica de presencia funciona con SCORM y cmi5.
CA-07. Instalar, avanzar, calificar, retirar y reinstalar se completa sin Internet.
CA-08. Activar dos fotografías simultáneas o una fotografía de otro curso se rechaza.
CA-09. Revertir conserva el contenido saliente y deja trazabilidad.
CA-10. Un progreso atrasado menor no reduce el avance y 100% sella la finalización.
CA-11. Completar un quiz calcula la nota una vez, conserva una respuesta por pregunta y alimenta el progreso de su lección.
CA-12. El payload del estudiante no contiene indicadores ni claves de corrección.
CA-13. El docente recibe presencia, pregunta actual y resultado final de cada intento.
CA-14. La ausencia de la biblioteca produce un estado degradado, no un fallo general ni una reconciliación destructiva.
CA-15. Desinstalar y reinstalar un paquete de biblioteca hace desaparecer y reaparecer el material sin borrar sus referencias.
CA-16. Repartir, repetir y cerrar material conserva una sola sesión abierta y luego su historial.
CA-17. Una capacidad de evaluación ausente responde como función no soportada; una capacidad presente se utiliza sin exponer la clave.

Fuera de alcance

- Gestión de identidades, grupos o padrón de estudiantes dentro del LMS.
- Autenticación y autorización hasta que su política se decida explícitamente.
- Sincronización entre varias OPS o con servicios en la nube.
- Distribución general y almacenamiento de binarios de contenido por este backend.
- Runtime completo de SCORM, cmi5, xAPI o LRS.
- Actualización automática de paquetes y resolución avanzada de conflictos.
- Escalado a varios procesos o servidores.
- Calificación automática de preguntas abiertas.

Medidas de éxito

- El escenario retirar → conservar → reinstalar se demuestra sin pérdida y sin duplicados.
- Cada invariante crítica tiene una prueba negativa además del camino feliz.
- Los contratos de estudiante nunca revelan soluciones.
- La indisponibilidad de un componente opcional no impide gestionar cursos, inscripciones, progreso o resultados existentes.

No añadas decisiones técnicas a la especificación. Si detectas una ambigüedad, enumérala para la Fase 3 en lugar de resolverla.
```

---

## Fase 3 · Clarificación

No avances al plan hasta registrar respuesta del responsable de producto o arquitectura para cada pregunta marcada **bloqueante**. No conviertas el comportamiento accidental actual en respuesta implícita.

```text
Analiza la constitución y la especificación aprobadas y presenta estas preguntas de clarificación con: evidencia actual, impacto de cada alternativa y la decisión que debe tomar el responsable. No elijas por él.

Q-01 · ¿Debe existir DELETE /api/courses/{id}/?
No, todo lo relacionado a crear o eliminar cursos debe ser del dominio y servicio de AVACOM Biblioteca. El progreso del estudiante, entiendase cómo progreso
todo aquello que realiza el estudiante, entrar a actividades, realizar quizes, recibir sus notas, etc; todo eso debe estar registrado en el LMS

Q-02 · ¿Qué significa que una versión sea inmutable?
Las versiones inmutables deben estar relacionados al AVACOM Biblioteca, ahora bien, si en el progre

Q-03 · ¿La auditoría y la presencia histórica son append-only?
La auditoría es que se puedan generar reportes de las actividades del estudiante dentro del LMS, también ver el progreso del profesor y uso de la plataforma de ambas partes.

Q-04 · ¿Cuál es la política mínima de autenticación y autorización?
Por ahora no habrá proceso de autenticación porque estamos en fase de prototipo, pero sí sería prudente dejar un modelo de datos que nos acerque a las necesidades de diseñar
el modulo de acceso y autenticación.

Q-05 · BLOQUEANTE · ¿Quién puede ver soluciones y resultados detallados?
Por ahora dejemoslo para todos los tipos de usuario, porque no existe modulo de acceso y privilegios

Q-06  · ¿La instalación administra archivos físicos o sólo estructura y presencia?
La instalación no administra los archivos físicos del LMS, solamente de AVACOM Biblioteca y esto no está bajo el dominio de este backend. 

Q-07 · ¿Se debe preservar exactamente el contrato actual o corregir primero sus contradicciones?
El contrato se definirá en la primera edición del AVACOM Biblioteca.

Q-08 · ¿Qué garantía necesita client_event_id?
Hoy se acepta pero se ignora; la respuesta sólo se deduplica por intento y pregunta. Definir si se elimina del contrato, se valida sin persistir o exige deduplicación durable por evento. La última opción puede requerir cambiar el modelo de datos.

Q-09 · ¿Cómo se valida una conexión en vivo?
Hoy cualquier rol distinto de “student” actúa como docente, un estudiante sólo necesita un attempt_id y la conexión puede aceptarse aunque el intento no exista. Definir roles válidos, pertenencia del intento, cierre esperado y códigos de rechazo.

Q-10 · ¿El progreso puede disminuir por una acción explícita del docente?
Hoy nunca disminuye. Definir si correcciones administrativas, reinicios de curso o invalidación de intentos requieren una operación separada y auditada.

Q-11 · ¿Cómo se pondera un curso real?
Hoy cada lección pesa igual y se toma el mayor avance entre registro y mejor nota. Confirmar si esta regla es definitiva o sólo del prototipo.

Q-12 · ¿Qué hacer si una nueva versión elimina o cambia el código lógico de una lección?
Hoy el progreso anterior se conserva como histórico. Definir si existe mapeo explícito, fusión, retiro o sólo visualización separada.

Q-13 · ¿Cuál es el contrato definitivo de AVACOM-Contenido?
Confirmar ubicación y permisos de la nota de enlace, versión de contrato, tiempo de espera, nombres de capacidades, forma de errores, campos de catálogo y disponibilidad real de las seis capacidades previstas.

Q-14 · ¿Cuáles son los límites de paquetes?
Definir tamaño máximo, número de archivos, profundidad, compresión, rutas inseguras, XML hostil, duración máxima de análisis y política frente a paquetes cifrados o firmados.

Q-15 · ¿Qué significa “offline” para Student?
El backend funciona sin Internet dentro de la LAN, pero no existe sincronización durable cuando Student pierde la LAN. Confirmar si eso basta o si se requiere cola local y reconciliación posterior.

Q-16 · ¿Cuándo deja de ser válido el supuesto de un único proceso?
La presencia y los eventos actuales son locales al proceso. Definir capacidad prevista, número máximo de estudiantes y si habrá más de una instancia.

Q-17 · ¿Qué política de retención aplica a intentos, respuestas, progreso, auditoría y repartos cerrados?
Definir duración, exportación, anonimización y borrado legal. No inferirla a partir del prototipo.

Q-18 · ¿El contrato de errores se unifica?
Algunas respuestas usan un sobre error/details y otras detail. Definir forma, códigos funcionales, correlación y compatibilidad con los clientes actuales.

Entrega una tabla de decisiones con estado “resuelta” o “abierta”. Detente si Q-01 a Q-07 siguen abiertas. No escribas plan ni código.
```

---

## Fase 4 · Plan

Este bloque sí contiene decisiones técnicas recuperadas del backend actual. Sustituye en él cualquier punto que haya cambiado durante la clarificación.

```text
/speckit.plan

Genera el plan técnico para el backend AVACOM LMS como evolución brownfield. Usa la constitución, la especificación y el registro de clarificación aprobados. No dividas todavía el trabajo en tareas ni escribas código.

Restricciones de plataforma actuales

- Python 3.12.
- Django 5.2.3.
- Django REST Framework 3.16.1 con APIView; no ViewSets ni routers.
- Channels 4.3.1 y Daphne 4.2.1.
- SQLite como única persistencia del prototipo.
- Canal en memoria y registro de presencia local al proceso; una sola instancia de Daphne.
- django-cors-headers 4.7.0 y python-dotenv 1.1.1.
- Servicio ASGI en 0.0.0.0:8000; salud en /health/.
- JSON UTF-8 explícito; decimales como números.
- Sin autenticación en la línea base. Implementar otra política sólo si Q-04 la aprobó.
- Variables: DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS, AVACOM_DATA_DIR, AVACOM_HOST_ID, AVACOM_CONTENIDO_ENLACE y DJANGO_LOG_LEVEL.
- Datos y registros deben vivir en una ruta escribible; el fallo al abrir un archivo de log no puede impedir el arranque.
- Tiempos de dominio en milisegundos Unix; identificadores compactos de 24 caracteres hexadecimales, salvo claves externas.

Arquitectura interna que debe conservarse

1. exam_master: configuración, salud, enrutamiento HTTP/ASGI.
2. exams.models: las 19 entidades y restricciones del dominio.
3. exams.serializers: validación de entrada y proyecciones públicas/administrativas.
4. exams.views y exams.views_contenido: controladores APIView directos.
5. exams.catalog: transiciones atómicas de activación, retiro y rollback.
6. exams.package_install: validación e instalación transaccional de avacom-course-package/v1.
7. exams.packages: detección y adaptación de SCORM 1.2/2004, cmi5 y AVACOM-Contenido al paquete intermedio común.
8. exams.hosts: presencia física, disponibilidad, verificación e historial por OPS.
9. exams.progress: upsert monotónico, promedio y derivación desde intentos.
10. exams.contenido: único cliente permitido hacia AVACOM-Contenido.
11. exams.reconciliacion: comparación de referencias, saneamiento y cierre de repartos inválidos.
12. exams.consumers y exams.presence: eventos de actividad y conteo por intento conectado.

Modelo y restricciones

- Mantener exactamente las tablas actuales: m05_marco_curricular, m05_curso, m05_curso_version, m05_curso_estudiante, m05_seccion, m05_leccion, m05_leccion_item, m05_recurso_aprendizaje, m10_actividad, m19_auditoria, m10_quiz_pregunta, m10_quiz_opcion, m10_quiz_intento, m10_quiz_respuesta, m05_curso_host, m05_progreso_leccion, m05_unidad_material, m05_examen_pregunta y m05_reparto_activo.
- Usar PROTECT en relaciones académicas históricas; conservar CASCADE sólo donde la definición subordinada realmente no tiene vida independiente y la clarificación lo permita.
- Mantener unicidad de curso+versión; una versión activa parcial por curso; curso habilitado con versión; fechas de ciclo coherentes.
- Mantener identidad lógica única de sección y lección en cada padre y orden único.
- Mantener recurso por ref+versión, actividad por ref+versión e ítem por lección+orden.
- Mantener respuesta por intento+pregunta.
- Mantener presencia por host+curso+versión, una presencia sin versión por host+curso y una sola disponible por host+curso.
- Mantener disponible implica presente; retirado implica fecha.
- Mantener progreso por curso+persona+código, rango 0..100 y completado implica 100 con fecha.
- Mantener material por lección+referencia+versión y ausencia con fecha.
- Mantener pregunta externa por actividad+persona+referencia y por actividad+persona+orden.
- Mantener un solo reparto abierto por host+sesión+referencia y cierre posterior a apertura.
- Para las dos invariantes de pertenencia de versión que el ORM no expresa como clave compuesta, centralizar la escritura en catalog.activate_version y hosts.register_install, y cubrirlas con pruebas negativas.

Contratos HTTP actuales que el plan debe inventariar y versionar si cambian

- GET /health/.
- CRUD APIView: /api/curriculum-frameworks/, /api/courses/, /api/course-versions/, /api/enrollments/, /api/sections/, /api/lessons/, /api/lesson-items/, /api/learning-resources/, /api/activities/, /api/audit-logs/, /api/quiz-questions/, /api/quiz-options/ y sus detalles. Ajustar métodos peligrosos según Q-01 a Q-05.
- Curso y catálogo: GET /api/courses/?student=1&host_id=, GET /api/courses/?estado=, GET /api/courses/{id}/, GET /api/courses/{id}/manifest/, GET /api/courses/{id}/versions/, POST /api/courses/{id}/rollback/, GET /api/course-versions/{id}/package/ y POST /api/course-versions/{id}/activate/.
- Paquetes: POST /api/course-packages/inspect/, POST /api/course-packages/import/ y POST /api/course-packages/install/. La última acepta multipart con package/file o JSON con package_base64, y preview no escribe.
- Host: /api/course-hosts/, /formats/, /install/, /retire/, /availability/, /verify/, detalle; GET /api/hosts/{host}/courses/; GET /api/hosts/{host}/installed/; GET /api/students/{persona}/host-catalog/.
- Estudiante y progreso: GET /api/courses/available/, GET /api/courses/history/, POST /api/courses/{id}/uninstall/, GET /api/students/{id}/courses/ y GET/POST /api/students/{id}/courses/{course}/progress/.
- Quiz: GET /api/quizzes/{activity}/, POST /api/quiz-attempts/start/, /progress/, /answer/, /finish/, GET /api/quiz-results/ y GET /api/quiz-results/{attempt}/.
- Contenido: GET /api/contenido/estado/, GET/POST /api/contenido/reconciliar/, GET /api/contenido/catalogo/, GET /api/contenido/taxonomia/, GET /api/contenido/elemento/{ref}/, POST /api/contenido/mostrar/, GET /api/courses/{course}/contenido/, GET/POST /api/lecciones/{lesson}/materiales/, DELETE /api/materiales/{id}/, GET/POST /api/contenido/reparto/, POST /api/contenido/reparto/{id}/cerrar/, GET /api/students/{persona}/contenido/, POST /api/contenido/examen/montar/ y /comprobar/.

Contrato en vivo actual

- Ruta /ws/activities/{activity_id}/.
- Profesor: role=professor.
- Estudiante: role=student&attempt_id={attempt_id}.
- Cierre 4404 si la actividad no existe o no es quiz; 4400 si falta attempt_id al estudiante. Endurecer según Q-09.
- Eventos: presence_changed, activity_state, student_progress, attempt_finished y pong.
- student_progress y attempt_finished se envían sólo al grupo docente.
- La presencia cuenta intentos de estudiante únicos, no conexiones; varias conexiones del mismo intento cuentan una vez.
- ping o heartbeat recibe pong.

Integración con AVACOM-Contenido

- Leer en cada llamada la nota %ProgramData%/AVACOM/contenido/enlace.json o AVACOM_CONTENIDO_ENLACE.
- Aceptar claves PascalCase o minúsculas: Contrato, Puerto, Ficha, Proceso.
- Conectar sólo a 127.0.0.1, enviar X-Avacom-Ficha, usar contrato soportado 1 y tiempo de espera actual de 3 segundos.
- Nunca leer directamente su base ni cachear su catálogo.
- Consumir /v1/salud, /v1/catalogo, /v1/taxonomia, /v1/elemento/{ref} y /v1/mostrar.
- Condicionar /v1/leccion, /v1/evaluacion/{ref}, /v1/banco/{ref}/extraer, /v1/comprobar, /v1/medio/{ref} y /v1/repaso a las capacidades publicadas.
- Preferir generacion como huella de catálogo, luego huella_catalogo y como último recurso contadores derivados.
- No confundir componente detenido con contenido retirado.

Flujos técnicos obligatorios

1. Curso manual: crear curso borrador → crear versión instalada → crear árbol → activar por servicio → curso habilitado.
2. Paquete: leer bytes → detectar descriptor → analizar sin escribir → adaptar al schema común → instalación atómica → registro de host → disponibilidad sólo después de validación.
3. Reinstalación: resolver curso y versión existentes → comparar huella → no duplicar árbol → reabrir presencia → conservar expediente.
4. Quiz: iniciar/reanudar → validar y upsert de respuesta → publicar progreso → finalizar bajo bloqueo transaccional → calcular nota → registrar progreso → publicar finalización.
5. Retiro: actualizar todas las presencias objetivo → sellar fecha → conservar estado editorial y expediente → separar disponible de histórico.
6. Reconciliación: obtener catálogo válido → comparar referencias → marcar cambios → sanear sólo presencia de AVACOM-Contenido → cerrar repartos imposibles → auditar; si el componente falla, responder degradado sin escribir.

Pruebas y verificación del plan

- Preservar y organizar pruebas de modelos, catálogo versionado, API de curso, inscripción, respuestas, resultados, eventos, host, progreso, paquetes, criterios AC-01..AC-12 e integración AVACOM-Contenido.
- Añadir pruebas de contrato para cada decisión de Q-01 a Q-18.
- Incluir pruebas negativas de restricciones y pertenencia entre curso y versión.
- Incluir una prueba que inspeccione recursivamente todo payload del estudiante para impedir es_correcta, correcta, clave u otras variantes de solución.
- Incluir pruebas de atomicidad e idempotencia bajo reintentos.
- Incluir escenario integral instalar → asignar → avanzar → quiz → retirar → consultar historial → reinstalar → continuar.
- Incluir comprobación de configuración, migraciones, integridad y claves foráneas.
- Incluir prueba sin red de Internet y prueba con AVACOM-Contenido ausente.

Entrega del plan

- Contexto técnico y decisiones confirmadas.
- Diagrama de componentes y fronteras.
- Modelo de datos con invariantes y estrategia de migración.
- Contratos HTTP y en vivo, incluyendo compatibilidad y versionado.
- Diseño de transacciones, idempotencia, errores, auditoría y seguridad.
- Estrategia de pruebas y observabilidad.
- Riesgos y mitigaciones.
- Tabla de trazabilidad desde RF/CA hacia componentes y pruebas.

No generes tareas ni código en esta fase. Señala cualquier decisión abierta y detén el plan si contradice una respuesta de clarificación.
```

---

## Fase 5 · Tareas

```text
/speckit.tasks

Genera una lista ordenada, atómica y ejecutable a partir de la especificación y el plan aprobados. Este es un proyecto brownfield: cada tarea debe indicar si conserva, prueba, corrige o elimina comportamiento existente. No escribas código.

Formato obligatorio por tarea:

- ID estable T###.
- Historia o requisito asociado: US-##, RF-### y CA-##.
- Ruta exacta de los archivos afectados.
- Precondiciones.
- Una sola acción principal.
- Resultado observable.
- Prueba o comando de verificación.
- Marcador [P] sólo si puede ejecutarse en paralelo sin escribir los mismos archivos ni depender de una tarea incompleta.

Orden mínimo de trabajo:

1. Congelar la línea base observable con pruebas de caracterización y registrar las decisiones Q-01..Q-18.
2. Corregir primero los contratos destructivos o de acceso que la clarificación haya rechazado.
3. Alinear modelos, restricciones y migraciones sin añadir tablas no aprobadas.
4. Asegurar transiciones de catálogo y rollback.
5. Asegurar análisis, normalización e instalación idempotente de paquetes.
6. Asegurar presencia, disponibilidad, verificación, retiro e historial por host.
7. Asegurar progreso monotónico e integración con la nota del quiz.
8. Asegurar contrato público del quiz, intentos, respuestas, finalización y resultados.
9. Asegurar presencia y eventos en vivo, incluyendo validación de roles e intentos según Q-09.
10. Asegurar la frontera con AVACOM-Contenido, la degradación y la reconciliación.
11. Asegurar datos demo idempotentes con Álgebra Octavo B y las cinco preguntas exactas.
12. Actualizar contrato y arquitectura para que enumeren las 19 entidades y el comportamiento real.
13. Ejecutar pruebas unitarias, integración, escenario integral, comprobación del proyecto y verificación de migraciones.

Reglas de granularidad:

- Separar una migración de su cambio de modelo y de la prueba de datos si cualquiera puede fallar de manera independiente.
- Separar cambios de contrato público de cambios internos.
- No agrupar “implementar todos los endpoints” ni “escribir todas las pruebas”.
- Crear primero la prueba que demuestra una regresión, luego la corrección y finalmente la verificación integral.
- No crear una tarea para una decisión que siga abierta; marcarla como bloqueo.
- No modificar los frontends ni el instalador salvo que una decisión aprobada cambie su contrato; en ese caso crear tareas separadas y explícitas.

Finaliza con:

- Grafo de dependencias.
- Ruta crítica.
- Oportunidades reales de paralelismo.
- Matriz RF/CA → tareas → pruebas.
- Lista de bloqueos pendientes.

No implementes ninguna tarea.
```

---

## Fase 6 · Implementación

```text
/speckit.implement

Implementa únicamente las tareas aprobadas de la especificación del backend AVACOM LMS.

Reglas de ejecución:

1. Antes de editar, comprueba el estado del repositorio. Conserva cambios del usuario y no sobrescribas trabajo ajeno.
2. No empieces si existe una pregunta bloqueante de clarificación sin respuesta.
3. Ejecuta tareas en orden de dependencias; usa paralelismo sólo para tareas marcadas [P].
4. Para cada corrección brownfield: reproduce el problema con una prueba, aplica el cambio mínimo y demuestra que la prueba pasa.
5. No redefinas alcance, no agregues tablas o dependencias y no cambies contratos fuera de las decisiones aprobadas.
6. Usa APIViews y serializers directos; no introduzcas ViewSets, routers, repositorios genéricos ni una arquitectura adicional.
7. Mantén las operaciones de catálogo, host, progreso, instalación y finalización en sus servicios de dominio y con límites transaccionales explícitos.
8. No uses borrado físico donde corresponda retiro, cierre o conservación histórica.
9. No expongas es_correcta ni la solución en ningún contrato de estudiante, registro o evento no privilegiado.
10. La indisponibilidad de AVACOM-Contenido debe producir degradación explícita y nunca escrituras basadas en un catálogo desconocido.
11. Mantén el servidor principal en 0.0.0.0:8000 y el componente de contenido limitado a loopback.
12. Tras cada bloque coherente, ejecuta las pruebas focalizadas. Al final ejecuta comprobación del proyecto, migraciones, suite completa y escenario integral.
13. Si una prueba existente contradice la constitución o una decisión aprobada, no adaptes el código para satisfacerla silenciosamente: actualiza primero la prueba de contrato y documenta por qué.
14. Si una tarea revela una decisión nueva, detente y vuelve a clarificación; no inventes la respuesta.

Verificación final mínima:

- La configuración del proyecto es válida.
- No hay migraciones de modelos pendientes.
- Todas las migraciones se aplican desde una base limpia.
- Toda la suite automatizada pasa.
- El seed se puede ejecutar dos veces sin duplicar la demo.
- El quiz público no contiene soluciones.
- La finalización repetida conserva una sola nota.
- El retiro conserva curso, matrícula, progreso, intentos y respuestas.
- La reinstalación recupera disponibilidad sin duplicar esos registros.
- El flujo funciona sin Internet y con la biblioteca opcional apagada.
- Los eventos del docente reflejan presencia, pregunta actual y finalización.
- La documentación final coincide con las 19 entidades y los contratos realmente aprobados.

Informe final:

- Tareas completadas y omitidas.
- Archivos y migraciones modificados.
- Decisiones aplicadas.
- Pruebas ejecutadas con resultado.
- Diferencias de contrato y pasos requeridos para actualizar consumidores.
- Riesgos o bloqueos remanentes.

No declares completado el trabajo si alguna comprobación obligatoria no se ejecutó o falló.
```

## Definición de terminado de la especificación

El proceso Spec-Driven se considera listo para implementar cuando:

- La constitución fue ratificada.
- Q-01 a Q-07 tienen respuesta explícita.
- La especificación no contiene decisiones tecnológicas.
- El plan refleja las decisiones de clarificación y no la contradice.
- Cada requisito y criterio tiene trazabilidad a tareas y pruebas.
- Las contradicciones del backend actual se conservaron como deuda consciente o se aprobaron como cambios; ninguna quedó oculta.




## Reglas del código

El código debe ser fácil de realizar mantenimiento siguiendo:
1. Los principios de SOLID
2. Documentando Specs para realizar correcciones a futuro (en el formato Spec Driven Dev


