# Checklist TSS v4 (convertido del Excel Check_List_TSS_v4.xlsx)
#
# Cada bloque tiene:
#   seccion: carpeta principal (Video / Piso / Torre / Comissioning)
#   nombre:  nombre del bloque (subcarpeta)
#   repetir: (opcional) pregunta de cuántas unidades hay; el bot repite
#            todos los ítems del bloque por cada unidad (0 = se omite el bloque)
#   items:   lista ordenada de lo que debe enviar el técnico

ANTENA_RR = [
    "Foto +30° (objetivo de radiación, ~5% de cielo, parte superior de la antena visible)",
    "Foto -30° (objetivo de radiación, ~5% de cielo, parte superior de la antena visible)",
    "Panorámica de radiación (objetivo de radiación, ~5% de cielo)",
    "Antena completa (debe verse entera)",
    "TM: parte trasera de la antena, en el centro",
    "TE",
    "Serial / referencia de la antena (tomar la foto aunque el serial no sea visible)",
    "Altura con cinta métrica (real, desde el piso hasta la mitad de la antena)",
    "Azimuth (foto desde el piso con brújula o Pointer)",
    "Recorrido de jumpers antena-RF",
    "Marquillas + objetivo de radiación",
    "Foto de la antena desde el piso (que se vea su posición)",
    "Herrajes de la antena, superior e inferior",
]
# Nota: las fotos RR deben ir con buena resolución y marca de agua [SiteName + GSP + Fecha]

CHECKLIST = [
    # ───────────────────────── VIDEO ─────────────────────────
    {"seccion": "Video", "nombre": "Video", "items": [
        "Video de INGRESO: desde el ingreso a la estación, todos los equipos abiertos, recorrido por todo el interior, buena resolución",
        "Video de SALIDA: estado en que se deja la estación",
        "Video de CANASTILLA: equipos y antenas en canastilla, más estado de soportería y estructura",
        "Video equipos de otro operador: especificar cantidad de antenas y RRU",
        "Video de PARARRAYOS: condiciones, mostrar la guaya e indicar en qué arista está",
        "Video 360°: desde la altura máxima de la torre",
    ]},

    # ───────────────────────── PISO ─────────────────────────
    {"seccion": "Piso", "nombre": "Posicionamiento", "items": [
        "Screenshot del celular con las coordenadas GPS (Imagen 2)",
    ]},
    {"seccion": "Piso", "nombre": "SM", "repetir": "¿Cuántos SM hay? (una carpeta por tecnología GSM/UMTS/LTE y BB; Flexi/Ultra/AirScale)", "items": [
        "Panorámica módulo abierto",
        "Panorámica módulo cerrado",
        "Panorámica marquillas en el módulo",
        "Panorámica caja de alarmas (abierta + cerrada)",
        "Panorámica general del SM donde se vea su instalación, desde diferentes ángulos",
        "Busbar",
    ]},
    {"seccion": "Piso", "nombre": "FPFH piso", "repetir": "¿Cuántos FPFH hay instalados en piso?", "items": [
        "Panorámica módulo abierto",
        "Puertos DC libres",
        "Panorámica módulo cerrado",
        "Panorámica marquillado del módulo",
        "Panorámica general del módulo, desde diferentes ángulos",
        "OVPs de piso y busbar al que están aterrizados",
        "Detalle de las marquillas de los equipos conectados",
        "Busbar",
    ]},
    {"seccion": "Piso", "nombre": "Equipo TX", "repetir": "¿Cuántos equipos TX hay?", "items": [
        "Panorámica de todos los radios",
        "Fotos generales del cuarto de equipos, ingreso de cables, etc.",
        "Panorámica gabinete abierto",
        "Panorámica gabinete cerrado",
        "Busbar",
        "Foto de etiquetas de los enlaces",
        "Toma de corriente DC en cada uno de los equipos",
        "Referencia de los equipos",
    ]},
    {"seccion": "Piso", "nombre": "Planta eléctrica", "repetir": "¿Cuántas plantas eléctricas hay?", "items": [
        "Fotos generales de la planta desde varios ángulos",
        "Tablero de transferencia",
        "Tanques de combustible",
        "Etiqueta con la referencia y capacidad de la planta",
    ]},
    {"seccion": "Piso", "nombre": "Equipo de fuerza", "repetir": "¿Cuántos equipos de FUERZA/POWER hay? (Eltek / ZTE / FPMA)", "items": [
        "Panorámica general abierto",
        "Panorámica general cerrado",
        "Panorámica rectificadores",
        "Panorámica baterías",
        "Etiqueta de baterías donde se vea la capacidad",
        "Barraje (+)",
        "Barraje (-)",
        "Solo FPMA: medir la salida del equipo con multímetro",
        "Panorámica breakers instalados",
        "Marquillas de breakers",
        "Medición de corriente por breaker DC (si no hay consumo total en pantalla)",
        "Foto del consumo total de corriente en el display del controlador",
        "Busbar",
    ]},
    {"seccion": "Piso", "nombre": "AC - TGD", "items": [
        "Panorámica tablero abierto",
        "Panorámica tablero cerrado",
        "Capacidad de breakers",
        "Medición de voltaje L1-N",
        "Medición de voltaje L2-N",
        "Medición de voltaje L3-N",
        "Medición de voltaje L1-L2",
        "Medición de voltaje L1-L3",
        "Medición de voltaje L2-L3",
        "Medición de corriente L1",
        "Medición de corriente L2",
        "Medición de corriente L3",
    ]},
    {"seccion": "Piso", "nombre": "AC - Acometida", "items": [
        "Panorámicas generales del contador",
        "Registro de consumo del contador por cada fase",
        "Evidencia de la capacidad del totalizador",
        "Panorámica del transformador",
    ]},
    {"seccion": "Piso", "nombre": "DC - PDB", "repetir": "¿Cuántos PDB hay?", "items": [
        "Gabinete abierto",
        "Gabinete cerrado",
        "Evidencia de todos los breakers o interruptores instalados en el tablero",
        "Toma de corriente DC del ramal A y ramal B",
        "Toma de corriente en cada equipo TX conectado al PDB",
    ]},
    {"seccion": "Piso", "nombre": "Anillo de tierras", "items": [
        "Foto por cada pata de la torre + recorrido de guayas",
        "Busbar en el sitio (BTS, escalerillas, etc.)",
        "Anillo de tierras",
    ]},
    {"seccion": "Piso", "nombre": "General piso", "items": [
        "Fotos generales de acceso",
        "Panorámicas generales de la fachada desde diferentes ángulos",
        "Fotos generales desde cada esquina dentro del sitio hacia los equipos",
        "Fotos de todas las escalerillas en sitio",
        "Arista A de la torre, de abajo hacia arriba, desde la calle (se ve la torre y sus equipos)",
        "Arista B de la torre, de abajo hacia arriba, desde la calle",
        "Arista C de la torre, de abajo hacia arriba, desde la calle",
        "Arista D de la torre, de abajo hacia arriba, desde la calle",
        "Cara A_B de la torre desde la calle",
        "Cara B_C de la torre desde la calle",
        "Cara C_A de la torre desde la calle",
        "Base de la torre",
        "Panorámica arista A + ampliada mitad de torre hacia arriba y abajo",
        "Panorámica arista B + ampliada mitad de torre hacia arriba y abajo",
        "Panorámica arista C + ampliada mitad de torre hacia arriba y abajo",
    ]},
    {"seccion": "Piso", "nombre": "Plano mano alzada piso", "items": [
        "Plano tipo planta con distribución de equipos y sus nombres: escalerillas, SM, POWER, TX, planta. "
        "Incluir: distancias de recorrido de escalerillas (horizontal + vertical), distancias entre equipos, "
        "medidas del perímetro del sitio, puertas de acceso, cuarto de equipos + perímetro + distribución interior. "
        "Marcar puntos cardinales (norte, sur, oriente, occidente). Ver Imagen 4",
    ]},
    {"seccion": "Piso", "nombre": "Plano mano alzada torre", "items": [
        "Plano de torre con alturas de soportes + antenas + canastillas + soportes libres + azimuth de antenas. "
        "Identificar puntos cardinales. Ver Imagen 5",
    ]},

    # ───────────────────────── TORRE ─────────────────────────
    {"seccion": "Torre", "nombre": "RR 360", "items": [
        "36 fotos, una cada 10°, desde la parte superior de la estructura",
        "Video 360°",
        "Vista planta: panorámicas desde la parte superior hacia abajo por cada arista (debe verse toda la estación en piso)",
    ]},
    {"seccion": "Torre", "nombre": "RR Antena", "repetir": "¿Cuántas antenas RR hay? (una por tecnología GSM/UMTS/LTE y antena)", "items": ANTENA_RR},
    {"seccion": "Torre", "nombre": "RF", "repetir": "¿Cuántos RF hay? (una carpeta por tecnología y RF)", "items": [
        "Panorámica módulo cerrado",
        "Panorámica marquillado del módulo",
        "Panorámica general del módulo, desde diferentes ángulos",
        "Busbar",
        "Panorámica general de soportes: todas las antenas + RFs + soportería (Imagen 3)",
        "Soportes libres",
    ]},
    {"seccion": "Torre", "nombre": "MW", "repetir": "¿Cuántas antenas MW hay en la torre?", "items": [
        "Panorámica de la antena completa desde varios ángulos",
        "Marquillado",
        "Altura con cinta métrica",
        "Azimuth",
        "Medida de la MW (0,3 - 0,6 - 1,2 m, etc.)",
        "Panorámica general de la instalación MW",
    ]},
    {"seccion": "Torre", "nombre": "FPFH torre", "repetir": "¿Cuántos FPFH hay instalados en torre?", "items": [
        "Panorámica módulo abierto",
        "Panorámica módulo cerrado",
        "Puertos DC libres",
        "Panorámica marquillado del módulo",
        "Panorámica general del módulo, desde diferentes ángulos",
        "Busbar",
        "Detalle de las marquillas de los equipos conectados",
    ]},
    {"seccion": "Torre", "nombre": "SPT", "items": [
        "Busbar principales",
        "Recorrido de bajantes",
        "Pararrayos",
    ]},
    {"seccion": "Torre", "nombre": "Torre", "items": [
        "Recorrido de guías",
        "Recorrido de DC",
        "Luz de obstrucción",
    ]},
    {"seccion": "Torre", "nombre": "Proyección", "items": [
        "Fotos de espacios disponibles para nuevos equipos (torre / piso)",
        "Fotos de CWs existentes libres",
        "Fotos de espacios disponibles para CW",
    ]},
    {"seccion": "Torre", "nombre": "Panorámicas 5G", "repetir": "¿Cuántos sectores 5G se proyectan?", "items": [
        "Foto del AZ central con el que se proyecta el sector",
        "+60° respecto al AZ central (eje horizontal)",
        "-60° respecto al AZ central (eje horizontal)",
        "+30° respecto al AZ central (eje vertical)",
        "-30° respecto al AZ central (eje vertical)",
        "Foto desde la parte superior de donde se hace la proyección de la antena (Imagen 5)",
    ]},

    # ───────────────────────── COMISSIONING ─────────────────────────
    {"seccion": "Comissioning", "nombre": "Comissioning", "items": [
        "Ultrasite + Flexi + MR: screenshot principal señalando las celdas con sus TRX, SiteInfo y snapshot",
        "UMTS + SRAN: screenshot principal WCDMA + snapshot en modo current [IMS-XML] (Imagen 6)",
        "LTE: screenshot principal LTE + snapshot en modo current [IMS-XML] (Imagen 7)",
    ]},
]
