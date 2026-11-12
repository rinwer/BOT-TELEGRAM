import os
import re
import json
import html
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)  # evita imprimir el token

# --- Configuración -----------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TOKEN = os.environ["TELEGRAM_TOKEN"]
PROXY_URL = os.environ.get("PROXY_URL") or None  # opcional

ONEDRIVE_BASE_PATH = os.environ.get(
    "STORAGE_PATH",
    os.environ.get("ONEDRIVE_BASE_PATH", r"C:\Users\usuario microsoft\OneDrive\TSS\MOD_5G TEMWOK\INFO BOT TSS")
)
SESSION_DIR = os.environ.get("SESSION_DIR", BASE_DIR)
SESSION_FILE = os.environ.get("SESSION_FILE", "sesiones_v2.json")
CHECKLIST_FILE = os.environ.get("CHECKLIST_FILE", "checklist.json")

POR_PAGINA = 20  # botones de carpeta por pantalla

# Símbolos (se pueden cambiar aquí)
ICONO_OK = "✅"          # carpeta lista
ICONO_NA = "🚫"          # carpeta que no aplica
ICONO_PROCESO = "🔸"     # tiene fotos pero aún no se marcó como lista

# --- Checklist ---------------------------------------------------------------
# checklist.json:
#   menú: {"nombre", "hijos": [...], "nota": "texto opcional", "virtual": true/false}
#   ítem: {"nombre", "detalle", "tipo": "foto" | "lista"}
#
#   - Los menús (Carpeta / Sub-Carpeta) son BOTONES.
#   - Los ítems (columna Descripción) son una LISTA de recordatorio, sin estado.
#   - El check ✅ (o 🚫 No aplica) es GENERAL por carpeta, ej. "RR ANTENA 1".
#   - "virtual" = solo agrupa botones; no crea carpeta en OneDrive.
with open(os.path.join(BASE_DIR, CHECKLIST_FILE), "r", encoding="utf-8") as f:
    ARBOL = json.load(f)

RAIZ = {"nombre": "", "hijos": ARBOL}

# Estructura de sesiones (cada técnico trabaja con su propio estado):
#   "usuarios": {"<chat>:<usuario>": {"sitio": ..., "categoria_activa": {...}}}
#   "progreso": {"<sitio>": {"<ruta carpeta>": {"estado": None|"ok"|"na", "fotos": n}}}
#   "mensajes": {"<chat>:<mensaje>": "<chat>:<usuario>"}   (dueño de cada menú)
#   "sitios_chat": {"<chat_id>": "<nombre_sitio>"}          (sitio asignado a grupos)
sesiones = {"usuarios": {}, "progreso": {}, "mensajes": {}, "sitios_chat": {}}


def cargar_sesiones():
    global sesiones
    ruta = os.path.join(SESSION_DIR, SESSION_FILE)
    if not os.path.exists(ruta):
        ruta_alt = os.path.join(BASE_DIR, SESSION_FILE)
        if os.path.exists(ruta_alt):
            ruta = ruta_alt
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                sesiones = json.load(f)
        except Exception:
            logging.exception("No se pudo leer el archivo de sesiones")
    for k in ("usuarios", "progreso", "mensajes", "sitios_chat"):
        sesiones.setdefault(k, {})


def uk_de(chat_id, user_id):
    """Clave de un técnico: cada persona en cada chat tiene su propio sitio y carpeta activa."""
    return f"{chat_id}:{user_id}"


def usuario(uk):
    return sesiones["usuarios"].setdefault(uk, {})


def registrar_dueno(chat_id, msg_id, uk):
    """Recuerda de quién es cada menú, para que otro técnico no lo pise."""
    m = sesiones["mensajes"]
    m[f"{chat_id}:{msg_id}"] = uk
    while len(m) > 300:
        m.pop(next(iter(m)))


def guardar_sesiones():
    os.makedirs(SESSION_DIR, exist_ok=True)
    with open(os.path.join(SESSION_DIR, SESSION_FILE), "w", encoding="utf-8") as f:
        json.dump(sesiones, f, ensure_ascii=False, indent=4)


# --- Utilidades --------------------------------------------------------------
def limpiar_nombre(nombre: str) -> str:
    nombre = re.sub(r'[<>:"/\\|?*]', "-", nombre).strip().rstrip(".")
    return nombre or "SIN_NOMBRE"


def esc(texto: str) -> str:
    return html.escape(texto)


def obtener_sitio_chat(chat, user_id=None):
    """
    Obtiene el sitio asociado al chat o usuario.
    Si es un grupo (group/supergroup), toma automáticamente el nombre del grupo
    para que los técnicos en campo no tengan que configurarlo manualmente.
    """
    chat_id = str(chat.id) if chat else ""
    sitios_chat = sesiones.setdefault("sitios_chat", {})

    # 1. Si ya se guardó para este grupo/chat
    if chat_id in sitios_chat and sitios_chat[chat_id]:
        sitio = sitios_chat[chat_id]
        if user_id:
            usuario(uk_de(chat_id, user_id))["sitio"] = sitio
        return sitio

    # 2. Si es un grupo con título, derivarlo automáticamente del título del grupo
    if chat and chat.type in ("group", "supergroup") and chat.title:
        sitio = limpiar_nombre(chat.title.strip().upper())
        sitios_chat[chat_id] = sitio
        if user_id:
            usuario(uk_de(chat_id, user_id))["sitio"] = sitio
        os.makedirs(os.path.join(ONEDRIVE_BASE_PATH, sitio), exist_ok=True)
        guardar_sesiones()
        return sitio

    # 3. Si es chat privado, consultar la sesión del usuario
    if user_id and chat_id:
        return usuario(uk_de(chat_id, user_id)).get("sitio")

    return None


def carpeta_destino(sitio, ruta):
    return os.path.join(ONEDRIVE_BASE_PATH, sitio, *[limpiar_nombre(p) for p in ruta])


def hojas_de(nodo):
    """Ítems (lista de fotos requeridas) de un menú."""
    return [h for h in nodo.get("hijos", []) if "hijos" not in h]


def menus_de(nodo):
    """Submenús (botones) de un menú, con su índice real."""
    return [(i, h) for i, h in enumerate(nodo.get("hijos", [])) if "hijos" in h]


def nodo_por_indices(indices):
    """
    Devuelve (nodo, nombres, ruta_carpeta).
      nombres      = ruta que ve el técnico en los menús
      ruta_carpeta = ruta real en OneDrive (sin los menús "virtual")
    Con indices vacío devuelve la raíz.
    """
    nodo, nombres, ruta = RAIZ, [], []
    for i in indices:
        nodo = nodo["hijos"][i]
        nombres.append(nodo["nombre"])
        if not nodo.get("virtual"):
            ruta.append(nodo["nombre"])
    return nodo, nombres, ruta


# --- Progreso por carpeta ----------------------------------------------------
# El avance es por SITIO: dos técnicos en el mismo sitio comparten el avance.
def clave(ruta):
    return "/".join(ruta)


def leer_prog(sitio, ruta):
    base = sesiones["progreso"].get(sitio, {})
    return base.get(clave(ruta), {"estado": None, "fotos": 0})


def guardar_prog(sitio, ruta, prog):
    sesiones["progreso"].setdefault(sitio, {})[clave(ruta)] = prog


def avance_nodo(sitio, nodo, ruta):
    """(carpetas resueltas, carpetas totales) de un menú y todo lo que contiene."""
    hechos = total = 0
    if hojas_de(nodo):
        total = 1
        if leer_prog(sitio, ruta)["estado"] in ("ok", "na"):
            hechos = 1
    for _, h in menus_de(nodo):
        r = ruta + ([] if h.get("virtual") else [h["nombre"]])
        a, b = avance_nodo(sitio, h, r)
        hechos, total = hechos + a, total + b
    return hechos, total


def etiqueta_boton(sitio, hijo, ruta_hijo):
    nombre = hijo["nombre"]
    hechos, total = avance_nodo(sitio, hijo, ruta_hijo)
    if total == 0:
        return nombre

    if hojas_de(hijo) and not menus_de(hijo):  # carpeta con lista de fotos
        prog = leer_prog(sitio, ruta_hijo)
        if prog["estado"] == "ok":
            return f"{ICONO_OK} {nombre}"
        if prog["estado"] == "na":
            return f"{ICONO_NA} {nombre}"
        if prog["fotos"]:
            return f"{ICONO_PROCESO} {nombre}"
        return nombre

    # Grupo de carpetas (ej. RR ANTENA)
    if hechos >= total:
        return f"{ICONO_OK} {nombre}"
    if hechos:
        return f"{ICONO_PROCESO} {nombre} ({hechos}/{total})"
    return nombre


# --- Callback data -----------------------------------------------------------
# "n:<indices>[:<página>]"  navegar a un menú
# "a:<l|x|r>:<indices>"     acción: l=listo, x=no aplica, r=reabrir
def cb(indices, pagina=0):
    base = "n:" + ".".join(str(i) for i in indices)
    return f"{base}:{pagina}" if pagina else base


def cb_accion(accion, indices):
    return f"a:{accion}:" + ".".join(str(i) for i in indices)


def parse_indices(cuerpo):
    return [int(x) for x in cuerpo.split(".")] if cuerpo else []


# --- Pantallas ---------------------------------------------------------------
def teclado_nodo(sitio, indices, pagina=0):
    nodo, nombres, ruta = nodo_por_indices(indices)
    keyboard = []

    if hojas_de(nodo):
        estado = leer_prog(sitio, ruta)["estado"]
        if estado in ("ok", "na"):
            keyboard.append([InlineKeyboardButton("↩️ Reabrir", callback_data=cb_accion("r", indices))])
        else:
            keyboard.append([
                InlineKeyboardButton(f"{ICONO_OK} Listo", callback_data=cb_accion("l", indices)),
                InlineKeyboardButton(f"{ICONO_NA} No aplica", callback_data=cb_accion("x", indices)),
            ])

    menus = menus_de(nodo)
    inicio = pagina * POR_PAGINA
    fin = inicio + POR_PAGINA
    for i, hijo in menus[inicio:fin]:
        r = ruta + ([] if hijo.get("virtual") else [hijo["nombre"]])
        keyboard.append([
            InlineKeyboardButton(etiqueta_boton(sitio, hijo, r), callback_data=cb(indices + [i]))
        ])

    nav = []
    if pagina > 0:
        nav.append(InlineKeyboardButton("◀️ Anterior", callback_data=cb(indices, pagina - 1)))
    if fin < len(menus):
        nav.append(InlineKeyboardButton("Siguiente ▶️", callback_data=cb(indices, pagina + 1)))
    if nav:
        keyboard.append(nav)

    if indices:
        etiqueta = "⬅️ Volver" if len(indices) > 1 else "⬅️ Volver al Menú"
        keyboard.append([InlineKeyboardButton(etiqueta, callback_data=cb(indices[:-1]))])
    return InlineKeyboardMarkup(keyboard)


def texto_nodo(sitio, indices, pagina=0, nombre=""):
    nodo, nombres, ruta = nodo_por_indices(indices)
    if not indices:
        quien = f"👤 <b>{esc(nombre)}</b>\n" if nombre else ""
        return (
            f"📂 <b>Menú de Inspección</b>\n{quien}"
            f"📍 <b>Sitio:</b> <code>{esc(sitio)}</code>\nSeleccione una categoría:"
        )

    texto = f"📁 <b>{esc(' > '.join(nombres))}</b>"
    if nodo.get("nota"):
        texto += f"\n<i>{esc(nodo['nota'])}</i>"

    hojas = hojas_de(nodo)
    if hojas:
        prog = leer_prog(sitio, ruta)

        if prog["estado"] == "ok":
            texto += f"\n{ICONO_OK} <b>Carpeta lista</b>"
        elif prog["estado"] == "na":
            texto += f"\n{ICONO_NA} <b>No aplica</b>"

        lineas = []
        for k, h in enumerate(hojas, 1):
            tipo = "📝 " if h.get("tipo") == "lista" else ""
            lineas.append(f"{k}. {tipo}{esc(h['detalle'])}")
        texto += "\n\n<b>Fotos requeridas:</b>\n" + "\n".join(lineas)

        texto += "\n\n📸 Envíe las fotos aquí; se guardan automáticamente en OneDrive."
        if any(h.get("tipo") == "lista" for h in hojas):
            texto += "\n📝 Los datos marcados con 📝 envíelos como mensaje de texto."
        texto += f"\nFotos enviadas: <b>{prog['fotos']}</b>"
        if prog["estado"] is None:
            texto += f"\n\nCuando termine pulse <b>{ICONO_OK} Listo</b>. Si no corresponde, <b>{ICONO_NA} No aplica</b>."

    menus = menus_de(nodo)
    if menus:
        texto += "\n\nSeleccione una opción:"
        if len(menus) > POR_PAGINA:
            paginas = (len(menus) + POR_PAGINA - 1) // POR_PAGINA
            texto += f" (página {pagina + 1} de {paginas})"
    return texto


async def refrescar_lista(context, chat_id, sitio, activa):
    """Actualiza el mensaje de la lista (contador de fotos) después de guardar algo."""
    msg_id = activa.get("msg_id")
    if not msg_id:
        return
    indices = activa["indices"]
    try:
        await context.bot.edit_message_text(
            chat_id=int(chat_id),
            message_id=msg_id,
            text=texto_nodo(sitio, indices),
            reply_markup=teclado_nodo(sitio, indices),
            parse_mode="HTML",
        )
    except Exception as e:  # mensaje borrado, sin cambios, límite de ediciones, etc.
        logging.debug("No se pudo refrescar la lista: %s", e)


# --- Comandos ----------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    chat_id = str(chat.id) if chat else ""
    user_id = user.id if user else 0
    uk = uk_de(chat_id, user_id)
    sitio_actual = obtener_sitio_chat(chat, user_id) or "No configurado"

    texto = (
        "🤖 <b>Bot de Inspección TSS - Claro</b>\n\n"
        f"📍 <b>Sitio Actual:</b> <code>{esc(sitio_actual)}</code>\n\n"
    )
    if chat and chat.type in ("group", "supergroup"):
        texto += (
            "✅ <i>Sitio asignado automáticamente desde este grupo.</i>\n\n"
            "Comandos disponibles:\n"
            "• <code>/menu</code> - Muestra el checklist de inspección.\n"
            "• <code>/sitio [NOMBRE]</code> - Consultar o cambiar el sitio si se requiere."
        )
    else:
        texto += (
            "Comandos disponibles:\n"
            "• <code>/sitio NOMBRE_SITIO</code> - Configura el sitio activo.\n"
            "• <code>/menu</code> - Muestra el checklist de inspección."
        )

    await update.message.reply_text(texto, parse_mode="HTML")


async def set_sitio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    chat_id = str(chat.id) if chat else ""
    user_id = user.id if user else 0
    uk = uk_de(chat_id, user_id)

    if not context.args:
        sitio_actual = obtener_sitio_chat(chat, user_id)
        if sitio_actual:
            await update.message.reply_text(
                f"📍 <b>Sitio actual:</b> <code>{esc(sitio_actual)}</code>\n\n"
                "Para cambiarlo escriba: <code>/sitio NUEVO_NOMBRE</code>",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                "⚠️ Indique el nombre del sitio. Ej: <code>/sitio TFO_BOGOTÁ</code>",
                parse_mode="HTML",
            )
        return

    nombre_sitio = limpiar_nombre("_".join(context.args).upper())
    sesiones.setdefault("sitios_chat", {})[chat_id] = nombre_sitio
    usuario(uk)["sitio"] = nombre_sitio
    usuario(uk).pop("categoria_activa", None)
    guardar_sesiones()

    os.makedirs(os.path.join(ONEDRIVE_BASE_PATH, nombre_sitio), exist_ok=True)
    await update.message.reply_text(
        f"✅ <b>Sitio configurado:</b>\n<code>{esc(nombre_sitio)}</code>\n\nCarpeta lista en el almacenamiento.",
        parse_mode="HTML",
    )


async def mostrar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    chat_id = str(chat.id) if chat else ""
    user_id = user.id if user else 0
    uk = uk_de(chat_id, user_id)

    sitio = obtener_sitio_chat(chat, user_id)
    if not sitio:
        await update.message.reply_text(
            "⚠️ Primero configure su sitio con <code>/sitio NOMBRE_SITIO</code>",
            parse_mode="HTML",
        )
        return

    usuario(uk)["sitio"] = sitio
    usuario(uk).pop("categoria_activa", None)
    msg = await update.message.reply_text(
        texto_nodo(sitio, [], nombre=user.first_name if user else ""),
        reply_markup=teclado_nodo(sitio, []),
        parse_mode="HTML",
    )
    registrar_dueno(chat_id, msg.message_id, uk)  # este menú es de quien lo pidió
    guardar_sesiones()


# --- Botones -----------------------------------------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = str(query.message.chat.id)
    uk = uk_de(chat_id, query.from_user.id)

    # Cada menú es de quien lo abrió con /menu: otro técnico no puede moverlo
    clave_msg = f"{chat_id}:{query.message.message_id}"
    dueno = sesiones["mensajes"].get(clave_msg)
    if dueno and dueno != uk:
        await query.answer("🔒 Este menú es de otro técnico. Escriba /menu para abrir el suyo.", show_alert=True)
        return
    if not dueno:
        registrar_dueno(chat_id, query.message.message_id, uk)
    await query.answer()

    sitio = usuario(uk).get("sitio")
    if not sitio:
        sitio = obtener_sitio_chat(query.message.chat, query.from_user.id)
        if sitio:
            usuario(uk)["sitio"] = sitio
    if not sitio:
        await query.edit_message_text("⚠️ Configure su sitio primero con /sitio")
        return

    try:
        data = query.data
        pagina = 0

        if data.startswith("a:"):
            # Listo / No aplica / Reabrir (check general de la carpeta)
            _, accion, cuerpo = data.split(":", 2)
            indices = parse_indices(cuerpo)
            nodo, nombres, ruta = nodo_por_indices(indices)
            if hojas_de(nodo):
                prog = leer_prog(sitio, ruta)
                if accion == "l":
                    prog["estado"] = "ok"
                elif accion == "x":
                    prog["estado"] = "na"
                elif accion == "r":
                    prog["estado"] = None
                guardar_prog(sitio, ruta, prog)
                if accion in ("l", "x") and indices:
                    indices = indices[:-1]  # vuelve al menú anterior para seguir con la siguiente carpeta
        else:
            cuerpo = data[2:]
            if ":" in cuerpo:
                cuerpo, p = cuerpo.split(":", 1)
                pagina = int(p)
            indices = parse_indices(cuerpo)

        nodo, nombres, ruta = nodo_por_indices(indices)

        # Botón viejo de un ítem (versión anterior): se abre su menú
        if indices and "hijos" not in nodo:
            indices, pagina = indices[:-1], 0
            nodo, nombres, ruta = nodo_por_indices(indices)

        if hojas_de(nodo):
            # Las fotos y textos que lleguen ahora se guardan en esta carpeta
            usuario(uk)["categoria_activa"] = {
                "indices": indices,
                "msg_id": query.message.message_id,
            }
        else:
            usuario(uk).pop("categoria_activa", None)
        guardar_sesiones()

        await query.edit_message_text(
            texto_nodo(sitio, indices, pagina, nombre=query.from_user.first_name or ""),
            reply_markup=teclado_nodo(sitio, indices, pagina),
            parse_mode="HTML",
        )

    except BadRequest as e:
        if "not modified" not in str(e).lower():
            raise
    except (IndexError, ValueError, KeyError):
        logging.exception("callback_data inválido: %s", query.data)
        await query.edit_message_text("⚠️ Opción no válida. Use /menu para empezar de nuevo.")


# --- Fotos y texto -----------------------------------------------------------
def obtener_activa(uk, chat=None, user_id=None):
    """(sitio, activa, nombres, ruta, hojas) del técnico, o None si no tiene una carpeta con lista abierta."""
    sesion = usuario(uk)
    sitio = sesion.get("sitio")
    if not sitio and chat:
        sitio = obtener_sitio_chat(chat, user_id)
        if sitio:
            sesion["sitio"] = sitio
    activa = sesion.get("categoria_activa")
    if not sitio or not isinstance(activa, dict) or "indices" not in activa:
        return None
    try:
        nodo, nombres, ruta = nodo_por_indices(activa["indices"])
    except (IndexError, KeyError):
        return None
    hojas = hojas_de(nodo)
    if not hojas:
        return None
    return sitio, activa, nombres, ruta, hojas


async def confirmar(update: Update):
    """Confirma con una reacción 👍 al mensaje (sin escribir otro mensaje en el chat)."""
    try:
        await update.message.set_reaction("👍")
    except Exception as e:
        logging.debug("No se pudo reaccionar: %s", e)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    chat_id = str(chat.id) if chat else ""
    if not user:
        return
    uk = uk_de(chat_id, user.id)
    estado = obtener_activa(uk, chat=chat, user_id=user.id)

    if not estado:
        sitio = obtener_sitio_chat(chat, user.id)
        if sitio:
            await update.message.reply_text(
                f"⚠️ Para el sitio <b>{esc(sitio)}</b>, primero abra la carpeta en <code>/menu</code> para clasificar las fotos.",
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                "⚠️ Antes de enviar fotos, configure el sitio (/sitio) y abra una carpeta con su lista de fotos en /menu."
            )
        return

    sitio, activa, nombres, ruta, hojas = estado

    msg = update.message
    if msg.photo:
        origen, ext = msg.photo[-1], ".jpg"
    elif msg.document and (msg.document.mime_type or "").startswith("image/"):
        origen = msg.document  # imagen enviada "como archivo"
        ext = os.path.splitext(msg.document.file_name or "")[1].lower() or ".jpg"
    else:
        return

    destino = carpeta_destino(sitio, ruta)
    os.makedirs(destino, exist_ok=True)

    archivo = await context.bot.get_file(origen.file_id)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    await archivo.download_to_drive(os.path.join(destino, f"{marca}_{origen.file_unique_id}{ext}"))

    prog = leer_prog(sitio, ruta)
    prog["fotos"] = prog.get("fotos", 0) + 1
    if prog["estado"] == "na":  # llegó una foto: ya no es "no aplica"
        prog["estado"] = None
    guardar_prog(sitio, ruta, prog)
    guardar_sesiones()

    await confirmar(update)
    await refrescar_lista(context, chat_id, sitio, activa)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    chat_id = str(chat.id) if chat else ""
    if not user:
        return
    uk = uk_de(chat_id, user.id)
    estado = obtener_activa(uk, chat=chat, user_id=user.id)
    if not estado:
        return

    sitio, activa, nombres, ruta, hojas = estado

    # Solo se guarda texto en carpetas que piden datos como texto (📝)
    if not any(h.get("tipo") == "lista" for h in hojas):
        return

    destino = carpeta_destino(sitio, ruta)
    os.makedirs(destino, exist_ok=True)

    marca = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(destino, "registro.txt"), "a", encoding="utf-8") as f:
        f.write(f"--- {marca} ---\n{update.message.text}\n\n")

    await confirmar(update)


# --- Eventos de Grupo (Autodetección de Sitio) ------------------------------
async def on_bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detecta cuando el bot ingresa a un grupo para tomar el nombre/ID automáticamente."""
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        return

    es_nuevo = False
    if update.message and update.message.new_chat_members:
        for m in update.message.new_chat_members:
            if m.id == context.bot.id:
                es_nuevo = True
                break
    elif update.my_chat_member:
        nuevo_estado = update.my_chat_member.new_chat_member.status
        if nuevo_estado in ("member", "administrator"):
            es_nuevo = True

    if es_nuevo and chat.title:
        nombre_sitio = limpiar_nombre(chat.title.strip().upper())
        sesiones.setdefault("sitios_chat", {})[str(chat.id)] = nombre_sitio
        os.makedirs(os.path.join(ONEDRIVE_BASE_PATH, nombre_sitio), exist_ok=True)
        guardar_sesiones()

        texto = (
            "🤖 <b>¡Bot TSS conectado al grupo!</b>\n\n"
            f"📍 <b>Sitio detectado automáticamente:</b>\n"
            f"<code>{esc(nombre_sitio)}</code>\n\n"
            "✅ Carpeta de almacenamiento lista.\n"
            "Los técnicos en campo <b>no</b> necesitan configurar el sitio.\n\n"
            "👉 Escriban <code>/menu</code> para abrir el checklist y comenzar la inspección."
        )
        try:
            await context.bot.send_message(chat_id=chat.id, text=texto, parse_mode="HTML")
        except Exception as e:
            logging.warning("No se pudo enviar mensaje de bienvenida al grupo: %s", e)


async def on_new_chat_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Actualiza el sitio si los técnicos cambian el título del grupo."""
    chat = update.effective_chat
    if not chat or not update.message or not update.message.new_chat_title:
        return
    nombre_sitio = limpiar_nombre(update.message.new_chat_title.strip().upper())
    sesiones.setdefault("sitios_chat", {})[str(chat.id)] = nombre_sitio
    os.makedirs(os.path.join(ONEDRIVE_BASE_PATH, nombre_sitio), exist_ok=True)
    guardar_sesiones()

    await update.message.reply_text(
        f"🔄 <b>Nombre del sitio actualizado según el nuevo título del grupo:</b>\n<code>{esc(nombre_sitio)}</code>",
        parse_mode="HTML",
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error("Error en el bot:", exc_info=context.error)


# --- Main --------------------------------------------------------------------
def main():
    cargar_sesiones()

    request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=30.0,
        read_timeout=60.0,
        write_timeout=60.0,
        pool_timeout=30.0,
        proxy=PROXY_URL,
    )

    app = ApplicationBuilder().token(TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sitio", set_sitio))
    app.add_handler(CommandHandler("menu", mostrar_menu))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    # Eventos de grupo (Autodetección de Sitio)
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_bot_added_to_group))
    app.add_handler(ChatMemberHandler(on_bot_added_to_group, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_TITLE, on_new_chat_title))
    app.add_error_handler(error_handler)

    print("🤖 Bot corriendo...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
