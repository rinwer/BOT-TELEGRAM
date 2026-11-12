"""
Convierte Check_list_BOT.xlsx en checklist.json (el que lee bot.py).

Uso:  python convertir_excel.py [archivo.xlsx]
Necesita:  pip install openpyxl

Reglas (columnas del Excel):
  Carpeta      -> menú / carpeta en OneDrive
  Sub-Carpeta  -> si es una etiqueta corta (ej. TGD, SPT) es una subcarpeta;
                  si es una nota larga se muestra como texto en el menú:
                    "(Tecnico envia listado de conexiones)" -> ítem de texto "Listado de conexiones"
                    "(Tecnico define de que sector, altura...)" -> ítem de texto con esos datos
  Descripcion  -> ítems de foto
Carpetas con numeración (RR ANTENA 1..14, RF-1..24, Equipo Fuerza-1..3,
FPFH LOWER-1..3, MW-1...) se agrupan en un menú, sin carpeta extra en OneDrive.
"""
import re
import sys
import json
import copy
from openpyxl import load_workbook

ARCHIVO = sys.argv[1] if len(sys.argv) > 1 else "Check_list_BOT.xlsx"
SALIDA = "checklist.json"

TECNOLOGIAS = ["GSM", "UMTS", "LTE", "FLEXI", "ULTRA", "AIRSCALE"]
RENOMBRAR_GRUPO = {"FPFH LOWER": "FPFH Piso"}

MAX_NOMBRE = 45
SUELTAS = {"de", "del", "la", "las", "el", "los", "y", "en", "con", "por", "un", "una",
           "que", "al", "se", "desde", "donde", "para", "hacia", "su", "sus", "o"}


def limpio(v):
    if v is None:
        return ""
    return re.sub(r"\s+", " ", str(v)).strip()


def sin_corchetes(texto):
    """Quita [ ] solo si envuelven todo el texto (no los de 'Caja alarmas [Abierta + cerrada]')."""
    t = texto.strip()
    if t.startswith("[") and t.endswith("]"):
        t = t[1:-1].strip()
    return t


def nombre_corto(texto):
    t = sin_corchetes(texto)
    for corte in (" donde ", ". ", " al que ", " de los equipos "):
        i = t.find(corte)
        if i > 10:
            t = t[:i]
    t = t.rstrip(". ")
    if len(t) > MAX_NOMBRE:
        t = t[:MAX_NOMBRE].rsplit(" ", 1)[0]
        # quitar palabras sueltas que quedan colgando al cortar
        palabras = t.split(" ")
        while len(palabras) > 2 and palabras[-1].lower() in SUELTAS:
            palabras.pop()
        t = " ".join(palabras)
    return t


def hoja(nombre, detalle, tipo="foto"):
    return {"nombre": nombre, "detalle": detalle, "tipo": tipo}


def hacer_items(descripciones):
    items, usados = [], {}
    for d in descripciones:
        nombre = nombre_corto(d)
        usados[nombre] = usados.get(nombre, 0) + 1
        if usados[nombre] > 1:
            nombre = f"{nombre} ({usados[nombre]})"
        items.append(hoja(nombre, sin_corchetes(d)))
    return items


def items_de_nota(sub):
    """Ítems de texto que se deducen de las notas entre paréntesis."""
    extra = []
    if re.search(r"listado", sub, re.I):
        extra.append(hoja("Listado de conexiones", "Envíe el listado de conexiones como mensaje de texto", "lista"))
    m = re.search(r"define (?:de que )?([^)]*)\)?", sub, re.I)
    if m:
        datos = m.group(1).strip()
        extra.append(hoja(f"Datos - {datos}", f"Escriba como texto: {datos}", "lista"))
    return extra


def es_subcarpeta(sub, carpeta):
    if not sub or sub.lower() == carpeta.lower():
        return False
    if "tecnico" in sub.lower() or "(" in sub or "," in sub or "/" in sub or len(sub) > 30:
        return False
    return True


# --- Leer el Excel: carpeta -> bloques (sub, descripciones) ------------------
ws = load_workbook(ARCHIVO).active
carpetas = []  # [{"nombre", "bloques": [{"sub", "desc": []}]}]
for fila in ws.iter_rows(min_row=2, values_only=True):
    b, c, d = (list(fila) + [None] * 4)[1:4]
    b, c, d = limpio(b), limpio(c), limpio(d)
    if b:
        carpetas.append({"nombre": b, "bloques": [{"sub": c, "desc": []}]})
    elif c and carpetas:
        carpetas[-1]["bloques"].append({"sub": c, "desc": []})
    if d and carpetas and not d.lower().startswith("carpeta por"):
        carpetas[-1]["bloques"][-1]["desc"].append(d)


# --- Construir nodos ---------------------------------------------------------
def nodo_carpeta(c):
    nombre, bloques = c["nombre"], c["bloques"]
    hijos, nota = [], []
    repetidos = {}
    for bl in bloques:
        if bl["sub"] and not es_subcarpeta(bl["sub"], nombre):
            repetidos[bl["sub"]] = repetidos.get(bl["sub"], 0) + 1
    contador = {}

    for k, bl in enumerate(bloques):
        sub, desc = bl["sub"], bl["desc"]
        items = hacer_items(desc)

        if sub in repetidos and repetidos[sub] > 1:
            # El mismo bloque se repite varias veces (ej. 12 enlaces MW): se numera
            contador[sub] = contador.get(sub, 0) + 1
            base = re.sub(r"\(.*?\)", "", sub).strip().title()
            hijos.append({"nombre": f"{base} {contador[sub]}", "hijos": items_de_nota(sub) + items})
            print(f"  {nombre}: bloque '{base}' repetido {repetidos[sub]} veces -> {base} 1..{repetidos[sub]}")
            continue

        if "GSM / UMTS / LTE" in sub or sub.startswith("GSM / UMTS"):
            # SM / FCOB: una subcarpeta por tecnología
            for t in TECNOLOGIAS:
                hijos.append({"nombre": t, "hijos": copy.deepcopy(items)})
            continue

        if es_subcarpeta(sub, nombre):
            hijos.append({"nombre": sub, "hijos": items})
        else:
            if k == 0 and sub and sub.lower() != nombre.lower():
                nota.append(re.sub(r"\(.*?\)", "", sub).strip())
                hijos.extend(items_de_nota(sub))
            hijos.extend(items)

    nodo = {"nombre": nombre, "hijos": hijos}
    nota = " ".join(n for n in nota if n)
    if nota:
        nodo["nota"] = nota
    return nodo


nodos = [nodo_carpeta(c) for c in carpetas]


# --- Parches puntuales -------------------------------------------------------
def buscar(nombre):
    return next((n for n in nodos if n["nombre"].strip() == nombre), None)


# AC / TGD: "Medicion voltaje" y "Medicion corriente" son títulos, no fotos
ac = buscar("AC")
if ac:
    tgd = ac["hijos"][0]
    nombres = [h["nombre"] for h in tgd["hijos"]]
    try:
        iv, ic = nombres.index("Medicion voltaje"), nombres.index("Medicion corriente")
        hs = tgd["hijos"]
        voltaje = {"nombre": "Medicion voltaje", "hijos": hs[iv + 1:ic]}
        fin_c = next(i for i, h in enumerate(hs) if h["nombre"].lower().startswith("panormica tablero abierto"))
        corriente = {"nombre": "Medicion corriente", "hijos": hs[ic + 1:fin_c]}
        tgd["hijos"] = [voltaje, corriente] + hs[fin_c:]
    except (ValueError, StopIteration):
        print("Aviso: no se pudo reorganizar AC (el Excel cambió)")

# RIESGOS: la descripción es una instrucción para el técnico
rg = buscar("RIESGOS")
if rg:
    for h in rg["hijos"]:
        if h["nombre"].upper().startswith("CADA VEZ"):
            h["nombre"] = "Foto de riesgo"


# --- Agrupar carpetas numeradas ----------------------------------------------
arbol, grupos = [], {}
for n in nodos:
    n["nombre"] = n["nombre"].strip()
    m = re.match(r"^(.*?[A-Za-z])[\s-]*(\d+)$", n["nombre"])
    if m:
        base = m.group(1).strip()
        titulo = RENOMBRAR_GRUPO.get(base, base)
        if titulo not in grupos:
            grupos[titulo] = {"nombre": titulo, "virtual": True, "hijos": []}
            arbol.append(grupos[titulo])
        grupos[titulo]["hijos"].append(n)
    else:
        arbol.append(n)

with open(SALIDA, "w", encoding="utf-8") as f:
    json.dump(arbol, f, ensure_ascii=False, indent=2)


def contar(nodos):
    menus = hojas = 0
    for n in nodos:
        if "hijos" in n:
            menus += 1
            m2, h2 = contar(n["hijos"])
            menus, hojas = menus + m2, hojas + h2
        else:
            hojas += 1
    return menus, hojas


m, h = contar(arbol)
print(f"{SALIDA}: {len(arbol)} categorías principales, {m} menús, {h} ítems")
