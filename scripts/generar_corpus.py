"""
Genera el corpus SINTÉTICO de la Mesa de Ayuda de "Andina Tech S.A.S." (empresa ficticia).

Todo el contenido fue redactado para fines académicos; no corresponde a ninguna organización
real y es apto para procesarse con servicios externos (OpenRouter / Hugging Face).

Formatos producidos (3 formatos, 5 archivos):
  corpus/manual_vpn_acceso_remoto.pdf        (PDF con texto seleccionable, 3 páginas)
  corpus/guia_seguridad_puesto_trabajo.pdf   (PDF con texto seleccionable, 2 páginas)
  corpus/politica_cuentas_contrasenas.docx   (DOCX con secciones)
  corpus/faq_correo_impresion.md             (Markdown)
  corpus/catalogo_servicios_sla.md           (Markdown)

Uso:  python scripts/generar_corpus.py
"""
from pathlib import Path

from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
AVISO = ("DOCUMENTO SINTÉTICO: contenido ficticio creado para un proyecto académico de RAG. "
         "Andina Tech S.A.S. no es una empresa real.")

# --------------------------------------------------------------------------------------
# 1) PDF — Manual de acceso remoto (VPN)
# --------------------------------------------------------------------------------------
PDF_PAGINAS = [
    [  # Página 1
        ("h1", "Manual de Acceso Remoto (VPN) - Versión 3.2"),
        ("p", AVISO),
        ("h2", "1. Propósito y alcance"),
        ("p", "Este manual describe cómo instalar, configurar y usar el cliente de red privada virtual "
              "NovaConnect para acceder a los sistemas internos de Andina Tech desde fuera de las oficinas. "
              "Está dirigido a teletrabajadores, personal en comisión y contratistas autorizados. La Mesa de Ayuda "
              "de Tecnología es el área responsable de mantener este manual y de atender las incidencias relacionadas."),
        ("p", "El servicio VPN permite usar el ERP, las carpetas compartidas de red, la intranet y los escritorios "
              "remotos. El correo electrónico y AndinaDrive no requieren VPN, porque se publican directamente en Internet "
              "con autenticación multifactor."),
        ("h2", "2. Requisitos previos"),
        ("p", "Para usar la VPN se necesita: un equipo con Windows 10, Windows 11 o macOS 13 o superior; el cliente "
              "NovaConnect versión 5.4 o posterior; una cuenta corporativa activa; y el segundo factor de autenticación "
              "registrado en la aplicación AndinaAuth del teléfono móvil."),
        ("p", "Los contratistas, además, deben contar con el formulario FR-VPN-02 firmado por el jefe del área que los "
              "contrata. Sin ese formulario la Mesa de Ayuda no habilita el perfil de acceso remoto, aunque la cuenta "
              "esté activa."),
        ("p", "El equipo debe tener el antivirus corporativo actualizado. El cliente NovaConnect verifica la postura del "
              "equipo al conectarse y rechaza la conexión si las firmas del antivirus tienen más de 7 días de antigüedad."),
    ],
    [  # Página 2
        ("h2", "3. Instalación del cliente"),
        ("p", "En Windows, descargue el instalador desde el Centro de Software (software.andinatech.example), ejecútelo "
              "con permisos de administrador y acepte los valores predeterminados. Al finalizar, reinicie el equipo para "
              "que se cargue el controlador de red virtual."),
        ("p", "En macOS, descargue el paquete .pkg desde el mismo Centro de Software. Durante la instalación el sistema "
              "solicitará autorizar la extensión de red en Configuración del Sistema > Privacidad y seguridad. Si no se "
              "autoriza la extensión, el cliente se instala pero no logra crear el túnel."),
        ("p", "En ambos sistemas, la primera vez que abra NovaConnect cree un perfil con los siguientes datos: nombre del "
              "perfil Andina Remoto, servidor vpn.andinatech.example y puerto 443. El modo de túnel predeterminado es IPsec."),
        ("h2", "4. Conexión y uso diario"),
        ("p", "Para conectarse, escriba su usuario corporativo sin el dominio (por ejemplo, jperez y no "
              "jperez@andinatech.example) y su contraseña. A continuación, ingrese el código de seis dígitos que muestra "
              "AndinaAuth. Cada código es válido durante 30 segundos."),
        ("p", "Una sesión VPN dura como máximo 10 horas continuas; al cumplirse ese tiempo el cliente se desconecta y es "
              "necesario autenticarse de nuevo. Además, la sesión se cierra automáticamente tras 30 minutos sin tráfico "
              "hacia la red interna."),
        ("p", "No se permite mantener conectadas dos VPN al mismo tiempo. Si usa otra VPN personal o de un cliente, "
              "desconéctela antes de abrir NovaConnect, porque las rutas de ambas redes entran en conflicto."),
    ],
    [  # Página 3
        ("h2", "5. Errores frecuentes y solución"),
        ("p", "Error VPN-401 (credenciales inválidas): el usuario o la contraseña no son correctos. Verifique que escribió "
              "el usuario sin dominio. Si cambió su contraseña recientemente, actualice la contraseña guardada en el perfil "
              "de NovaConnect, porque el cliente sigue enviando la contraseña anterior."),
        ("p", "Error VPN-619 (conexión interrumpida): la conexión a Internet se cortó o hay otra VPN activa. Compruebe su "
              "conexión, desconecte cualquier otra VPN y reinicie el servicio NovaConnect desde el menú Ayuda > Reiniciar "
              "servicio."),
        ("p", "Error VPN-809 (tráfico de túnel bloqueado): la red desde la que se conecta bloquea el tráfico IPsec, algo "
              "común en hoteles, aeropuertos y redes de invitados. Cambie el modo de túnel a SSL/TLS en Configuración > "
              "Avanzado > Modo de túnel y vuelva a conectarse. Si el error persiste, conéctese desde otra red, por ejemplo "
              "la red de datos del teléfono."),
        ("p", "Error VPN-722 (segundo factor rechazado): el código de AndinaAuth no fue aceptado. La causa más frecuente es "
              "que la hora del teléfono no está sincronizada; active la hora automática del teléfono. Después de tres "
              "rechazos consecutivos el token de AndinaAuth queda bloqueado y es necesario solicitar la reinscripción del "
              "segundo factor a la Mesa de Ayuda."),
        ("h2", "6. Cambio de contraseña y acceso remoto"),
        ("p", "Cuando cambie su contraseña, cierre la sesión VPN y vuelva a conectarse con la contraseña nueva. Mientras "
              "el cliente conserve la contraseña anterior, cada intento automático de reconexión se registra como un intento "
              "fallido de inicio de sesión y puede provocar el bloqueo de la cuenta según la política de cuentas."),
        ("p", "Para reportar un problema que no se resuelva con este manual, comuníquese con la Mesa de Ayuda e indique el "
              "código de error, la hora aproximada del fallo y la red desde la que intentaba conectarse."),
    ],
]


# --------------------------------------------------------------------------------------
# 5) PDF — Guía de seguridad del puesto de trabajo (distractor temático: contraseñas, correo,
#    copias de seguridad) para que la recuperación no sea trivial.
# --------------------------------------------------------------------------------------
PDF_SEGURIDAD = [
    [
        ("h1", "Guía de Seguridad del Puesto de Trabajo - GU-SEG-007"),
        ("p", AVISO),
        ("h2", "1. Bloqueo del equipo y escritorio limpio"),
        ("p", "Bloquee su equipo cada vez que se levante del puesto, con la combinación Windows + L en Windows o "
              "Control + Comando + Q en macOS. Si lo olvida, el equipo se bloquea automáticamente tras 5 minutos de "
              "inactividad. No deje documentos impresos con información confidencial sobre el escritorio al terminar "
              "la jornada."),
        ("p", "Nunca anote contraseñas en papel ni en archivos de texto sin cifrar. Para guardar las contraseñas de las "
              "aplicaciones del área, use el gestor de contraseñas corporativo AndinaVault, disponible en el Centro de "
              "Software."),
        ("h2", "2. Correos sospechosos (phishing)"),
        ("p", "Desconfíe de los correos que piden actualizar la contraseña, confirmar datos bancarios o abrir adjuntos "
              "inesperados, aunque parezcan venir de la Mesa de Ayuda. La Mesa de Ayuda nunca solicita contraseñas ni "
              "códigos de AndinaAuth por correo, chat o teléfono."),
        ("p", "Si recibe un correo sospechoso, no haga clic en los enlaces. Use el botón Reportar phishing de la barra "
              "del cliente de correo; el mensaje se envía al equipo de Seguridad de la Información y se elimina de su "
              "bandeja. Si ya hizo clic o escribió su contraseña, cámbiela de inmediato y llame a la extensión 4400."),
        ("p", "Los correos que llegan desde fuera de la empresa muestran la etiqueta [EXTERNO] al inicio del asunto. "
              "Preste especial atención a los mensajes externos que se hacen pasar por directivos de la empresa."),
    ],
    [
        ("h2", "3. Dispositivos y redes"),
        ("p", "Solo se permite conectar a los equipos corporativos memorias USB cifradas entregadas por el área de "
              "Tecnología. Los puertos USB de almacenamiento están deshabilitados para cualquier otro dispositivo. Para "
              "intercambiar archivos con terceros use AndinaDrive."),
        ("p", "Evite conectarse a redes Wi-Fi públicas sin VPN. Cuando trabaje desde un hotel, un aeropuerto o una "
              "cafetería, conéctese siempre a la VPN corporativa antes de abrir cualquier aplicación interna."),
        ("h2", "4. Copias de seguridad de la información del usuario"),
        ("p", "Los archivos de trabajo deben guardarse en AndinaDrive y no en el disco local del equipo, porque el disco "
              "local no tiene copia de seguridad. AndinaDrive conserva versiones anteriores de cada archivo durante 30 "
              "días."),
        ("p", "Para recuperar una versión anterior de un archivo, haga clic derecho sobre el archivo en AndinaDrive y "
              "elija Historial de versiones. Para recuperar un archivo borrado, búsquelo en la Papelera de AndinaDrive, "
              "donde permanece 30 días. Pasado ese plazo, la recuperación debe solicitarse a la Mesa de Ayuda y solo es "
              "posible si el archivo existía en la copia semanal de los últimos 90 días."),
        ("h2", "5. Reporte de incidentes de seguridad"),
        ("p", "Reporte de inmediato la pérdida o el robo de un equipo portátil o de un teléfono con AndinaAuth "
              "llamando a la extensión 4400; fuera del horario de atención use la línea de guardia 4499. El equipo de "
              "Seguridad bloqueará remotamente el dispositivo y las sesiones activas de la cuenta."),
    ],
]


def generar_pdf(path: Path, paginas=None, titulo="Manual de Acceso Remoto (VPN)") -> None:
    paginas = paginas or PDF_PAGINAS
    styles = getSampleStyleSheet()
    estilo = {"h1": styles["Title"], "h2": styles["Heading2"], "p": styles["BodyText"]}
    story = []
    for i, pagina in enumerate(paginas):
        for tipo, texto in pagina:
            story.append(Paragraph(texto, estilo[tipo]))
            story.append(Spacer(1, 6))
        if i < len(paginas) - 1:
            story.append(PageBreak())
    SimpleDocTemplate(str(path), pagesize=letter, title=titulo,
                      author="Andina Tech (ficticia)").build(story)


# --------------------------------------------------------------------------------------
# 2) DOCX — Política de cuentas y contraseñas
# --------------------------------------------------------------------------------------
DOCX_SECCIONES = [
    ("1. Objetivo", [
        "Esta política (código PO-SEG-004, versión 2.0) establece las reglas para crear, proteger, bloquear, restablecer "
        "y retirar las cuentas de usuario de Andina Tech, con el fin de reducir el riesgo de accesos no autorizados.",
    ]),
    ("2. Alcance", [
        "Aplica a todos los empleados, practicantes y contratistas que tengan una cuenta corporativa, y a todos los "
        "sistemas que usan el directorio corporativo para autenticar: equipos de escritorio, correo electrónico, VPN, "
        "intranet, ERP y portal de Recursos Humanos.",
        "Las cuentas de servicio usadas por aplicaciones se rigen por el procedimiento PR-SEG-011 y no están cubiertas "
        "por este documento.",
    ]),
    ("3. Requisitos de las contraseñas", [
        "Las contraseñas deben tener como mínimo 12 caracteres e incluir al menos tres de estas cuatro categorías: "
        "letras mayúsculas, letras minúsculas, números y símbolos.",
        "No se permite usar el nombre, el apellido, el usuario corporativo ni el nombre de la empresa dentro de la "
        "contraseña. El sistema recuerda las últimas 10 contraseñas y no permite reutilizarlas.",
        "Las contraseñas vencen cada 90 días. El sistema envía un aviso por correo 10 días antes del vencimiento y otro "
        "el día anterior. Una contraseña vencida solo permite iniciar sesión para cambiarla.",
        "Está prohibido compartir la contraseña con otras personas, incluido el personal de la Mesa de Ayuda, que nunca "
        "la solicitará por teléfono ni por correo.",
    ]),
    ("4. Bloqueo de cuenta", [
        "Una cuenta se bloquea automáticamente cuando se registran 5 intentos fallidos de inicio de sesión en un lapso "
        "de 10 minutos. Los intentos se cuentan en todos los sistemas conectados al directorio, incluida la VPN.",
        "El bloqueo dura 30 minutos; pasado ese tiempo la cuenta se desbloquea sola sin intervención de nadie.",
        "Si el usuario necesita el desbloqueo antes de que transcurran los 30 minutos, debe comunicarse con la Mesa de "
        "Ayuda. El analista verificará su identidad con el número de documento de empleado y la pregunta de seguridad "
        "registrada antes de desbloquear la cuenta.",
        "Tres bloqueos en un mismo día generan una alerta al equipo de Seguridad de la Información, que podrá revisar "
        "la actividad de la cuenta.",
    ]),
    ("5. Restablecimiento de contraseña por autoservicio", [
        "Si olvidó su contraseña, puede restablecerla en el portal de autoservicio clave.andinatech.example. Para usarlo "
        "es indispensable tener registrado el segundo factor de autenticación en AndinaAuth.",
        "El portal envía un código de verificación al teléfono registrado. El código es válido durante 10 minutos. Tras "
        "validarlo, el usuario define la nueva contraseña cumpliendo los requisitos de la sección 3.",
        "La nueva contraseña se propaga a todos los sistemas en un tiempo de hasta 15 minutos. Durante ese lapso la VPN "
        "y el correo pueden seguir rechazando la contraseña nueva; se recomienda esperar antes de reintentar para no "
        "acumular intentos fallidos.",
        "Si el usuario no tiene AndinaAuth registrado, debe solicitar el restablecimiento a la Mesa de Ayuda, que "
        "verificará su identidad mediante videollamada.",
    ]),
    ("6. Autenticación multifactor (MFA)", [
        "El segundo factor es obligatorio para la VPN, para el acceso al correo desde fuera de la red corporativa y para "
        "el portal de Recursos Humanos. El único método aprobado es la aplicación AndinaAuth.",
        "Si el usuario cambia o pierde su teléfono, debe solicitar la reinscripción del segundo factor a la Mesa de Ayuda. "
        "La reinscripción requiere verificación de identidad por videollamada.",
    ]),
    ("7. Cuentas de contratistas", [
        "Las cuentas de contratistas se crean con una fecha de expiración igual a la fecha de fin del contrato, con un "
        "máximo de 6 meses. Para ampliarla, el jefe que patrocina al contratista debe solicitar la renovación antes del "
        "vencimiento.",
    ]),
    ("8. Cuentas inactivas", [
        "Una cuenta sin inicios de sesión durante 60 días consecutivos se deshabilita. Si permanece deshabilitada 180 días "
        "más, se elimina junto con su buzón de correo, previa notificación al jefe inmediato.",
    ]),
    ("9. Incumplimiento", [
        "El incumplimiento de esta política se tratará conforme al reglamento interno de trabajo y a las cláusulas de "
        "seguridad de los contratos de prestación de servicios.",
    ]),
]


def generar_docx(path: Path) -> None:
    doc = Document()
    doc.core_properties.title = "Política de Cuentas y Contraseñas PO-SEG-004"
    doc.core_properties.author = "Andina Tech (ficticia)"
    doc.add_heading("Política de Cuentas y Contraseñas (PO-SEG-004)", level=0)
    doc.add_paragraph(AVISO)
    for titulo, parrafos in DOCX_SECCIONES:
        doc.add_heading(titulo, level=1)
        for p in parrafos:
            doc.add_paragraph(p)
    doc.save(str(path))


# --------------------------------------------------------------------------------------
# 3) Markdown — FAQ de correo e impresión
# --------------------------------------------------------------------------------------
FAQ_MD = f"""# Preguntas frecuentes: correo electrónico e impresión

> {AVISO}

Este documento reúne las preguntas más frecuentes que recibe la Mesa de Ayuda sobre el correo corporativo y el servicio de impresión. Última revisión: marzo de 2026.

## Correo electrónico

### ¿Cuánto espacio tiene mi buzón?

Cada buzón corporativo tiene una cuota de 50 GB. Cuando el buzón alcanza 45 GB, el sistema envía un aviso diario. Al llegar a 49,5 GB el usuario ya no puede enviar mensajes, aunque todavía puede recibirlos. Al llegar a 50 GB el buzón deja de recibir mensajes y los remitentes reciben un rechazo.

Para liberar espacio, vacíe la carpeta Elementos eliminados, borre los mensajes con adjuntos grandes o mueva correos antiguos a un archivo local. Si su trabajo exige más espacio, puede solicitar un aumento de cuota según el Catálogo de Servicios.

### ¿Cuál es el tamaño máximo de un adjunto?

El tamaño máximo de un mensaje, incluidos sus adjuntos, es de 25 MB. Para compartir archivos más grandes, súbalos a AndinaDrive y envíe un enlace de uso compartido en lugar del adjunto.

### ¿Qué significa el error 552 al enviar un correo?

El error 552 indica que el mensaje supera el tamaño máximo permitido de 25 MB. Reduzca el tamaño de los adjuntos o use un enlace de AndinaDrive.

### ¿Qué significa el error 550 5.7.1?

El servidor rechazó el mensaje por una regla de seguridad. Las causas más comunes son que el dominio del destinatario está en la lista de bloqueo o que se intentó reenviar automáticamente correo corporativo a una cuenta personal, lo cual está deshabilitado por política.

### ¿Cuánto tiempo se conservan los correos eliminados?

Los mensajes de la carpeta Elementos eliminados se conservan 30 días. Después de ese plazo se borran definitivamente y la Mesa de Ayuda no puede recuperarlos.

### ¿Cómo obtengo acceso a un buzón compartido?

Solicite el acceso desde el portal de soporte, en la categoría Correo > Buzón compartido. La solicitud debe ser aprobada por el responsable del buzón; una vez aprobada, el acceso aparece en su cliente de correo en un plazo de hasta 2 horas.

## Impresión

### ¿Cómo instalo una impresora?

Las impresoras se nombran según el piso y la zona, por ejemplo IMP-P3-NORTE. Abra el Centro de Software, busque el nombre de la impresora y pulse Instalar. No descargue controladores desde Internet.

### ¿Cómo imprimo a color?

La impresión a color requiere un código de centro de costos. Al enviar el trabajo, la impresora solicita el código en su pantalla. Si su área no tiene código asignado, el jefe del área debe pedirlo al área Financiera.

### La cola de impresión aparece detenida, ¿qué hago?

Cancele todos los trabajos pendientes desde la ventana de la cola, reinicie el servicio de cola de impresión del equipo y vuelva a enviar el documento. Si la impresora muestra un error en su pantalla, repórtelo a la Mesa de Ayuda indicando el nombre de la impresora y el mensaje exacto.

### ¿Puedo imprimir desde mi equipo personal?

No. Las impresoras corporativas solo aceptan trabajos de equipos registrados en el dominio de Andina Tech.
"""

# --------------------------------------------------------------------------------------
# 4) Markdown — Catálogo de servicios y SLA
# --------------------------------------------------------------------------------------
CATALOGO_MD = f"""# Catálogo de servicios y acuerdos de nivel de servicio (SLA) de la Mesa de Ayuda

> {AVISO}

## 1. Canales de atención y horario

La Mesa de Ayuda de Tecnología atiende por tres canales: el portal de soporte (soporte.andinatech.example), la extensión telefónica 4400 y el correo mesadeayuda@andinatech.example. El portal es el canal preferido porque permite adjuntar capturas y hacer seguimiento al caso.

El horario de atención es de lunes a viernes de 7:00 a 19:00 y los sábados de 8:00 a 12:00. Fuera de ese horario solo se atienden incidentes de prioridad P1, a través de la línea de guardia 4499.

## 2. Matriz de prioridades

La prioridad de un caso se asigna según su impacto y su urgencia. Los tiempos de respuesta se cuentan desde el registro del caso y los de resolución se cuentan en horario hábil, salvo para P1.

| Prioridad | Criterio | Tiempo de respuesta | Tiempo de resolución |
|---|---|---|---|
| P1 Crítica | Un servicio está caído para un área completa o para toda la empresa | 15 minutos | 4 horas (24x7) |
| P2 Alta | Un usuario individual no puede trabajar y no existe alternativa | 30 minutos | 8 horas hábiles |
| P3 Media | El servicio funciona de forma degradada o existe una alternativa temporal | 4 horas | 3 días hábiles |
| P4 Baja | Solicitudes de servicio, consultas y cambios programables | 1 día hábil | 5 días hábiles |

Ejemplos de P2: cuenta bloqueada de un usuario que no puede iniciar sesión, teletrabajador sin acceso a la VPN, equipo que no enciende sin equipo de reemplazo disponible.

## 3. Solicitudes de servicio frecuentes

### 3.1 Aumento de cuota de buzón

Se solicita en el portal de soporte, categoría Correo > Aumento de cuota. Requiere la aprobación del jefe inmediato del usuario. La cuota puede ampliarse hasta un máximo de 100 GB por buzón. Una vez aprobada, la solicitud se atiende en un plazo de 3 días hábiles.

### 3.2 Creación de cuenta para personal nuevo

La solicita el área de Recursos Humanos con al menos 3 días hábiles de anticipación a la fecha de ingreso. Para contratistas, la solicita el jefe patrocinador adjuntando el formulario FR-VPN-02 si se requiere acceso remoto.

### 3.3 Instalación de software

El software incluido en el Centro de Software se instala por autoservicio. El software que no está en el catálogo requiere aprobación del equipo de Arquitectura y se clasifica como P4.

### 3.4 Reinscripción del segundo factor (AndinaAuth)

Se atiende tras verificar la identidad del usuario por videollamada. Si el usuario no puede trabajar mientras tanto, el caso se clasifica como P2.

## 4. Escalamiento

Los casos los atiende primero el nivel 1 (Mesa de Ayuda). Si un caso no se resuelve en 2 horas hábiles, o requiere acceso administrativo a servidores, se escala al nivel 2 (Soporte de Infraestructura). Los casos de seguridad, como sospechas de suplantación o correos de phishing, se escalan de inmediato al equipo de Seguridad de la Información.

## 5. Fuera de alcance

La Mesa de Ayuda no da soporte a equipos personales, a la conexión a Internet del hogar de los teletrabajadores ni a software sin licencia. Tampoco atiende solicitudes de desarrollo de nuevas funcionalidades en las aplicaciones de negocio, que se gestionan con la Oficina de Proyectos.
"""


def main() -> None:
    CORPUS.mkdir(parents=True, exist_ok=True)
    generar_pdf(CORPUS / "manual_vpn_acceso_remoto.pdf")
    generar_pdf(CORPUS / "guia_seguridad_puesto_trabajo.pdf", PDF_SEGURIDAD,
                "Guía de Seguridad del Puesto de Trabajo")
    generar_docx(CORPUS / "politica_cuentas_contrasenas.docx")
    (CORPUS / "faq_correo_impresion.md").write_text(FAQ_MD, encoding="utf-8")
    (CORPUS / "catalogo_servicios_sla.md").write_text(CATALOGO_MD, encoding="utf-8")
    for f in sorted(CORPUS.iterdir()):
        print(f"  {f.name:40s} {f.stat().st_size:>8,d} bytes")


if __name__ == "__main__":
    main()
