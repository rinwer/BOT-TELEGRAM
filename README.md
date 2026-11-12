# 🤖 BOT-TELEGRAM (TSS Checklist Bot)

Bot de Telegram desarrollado en Python para la gestión e inspección técnica de sitios de telecomunicaciones en campo (torres, antenas, SM, FPFH, equipos de fuerza, tableros AC, etc.). Permite a los técnicos reportar paso a paso el checklist de cada sitio, adjuntar fotografías clasificadas automáticamente y registrar datos de mediciones.

---

## 🏗️ Arquitectura y Estructura del Proyecto

```text
TSS BOT/
├── .github/
│   └── workflows/
│       └── deploy.yml          # Pipeline CI/CD automático para despliegue en VPS
├── bot.py                      # Punto de entrada principal (Long-Polling Telegram Bot)
├── checklist.py                # Definición estructurada de bloques de inspección
├── checklist.json              # Esquema de navegación jerárquica generado
├── convertir_excel.py          # Script de utilidad: transforma Excel en checklist.json
├── sesiones_v2.json            # Estado y avance persistente de técnicos y sitios
├── requirements.txt            # Dependencias oficiales (python-telegram-bot, openpyxl, etc.)
├── Dockerfile                  # Contenedor optimizado Python 3.12-slim
├── docker-compose.yml          # Orquestador con persistencia en volumen y rotación de logs
├── .env.example                # Plantilla de variables de entorno
└── .gitignore                  # Exclusiones de Git (seguridad y artefactos)
```

---

## ⚙️ Configuración y Variables de Entorno

Copia el archivo de plantilla `.env.example` a `.env` y define tus credenciales:

```bash
cp .env.example .env
```

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `TELEGRAM_TOKEN` | Token de acceso del Bot proporcionado por @BotFather | *(Requerido)* |
| `STORAGE_PATH` | Ruta para fotos y registros generados en inspecciones | `/app/storage` |
| `SESSION_DIR` | Ruta donde se almacena el archivo de persistencia `sesiones_v2.json` | `/app/storage` |
| `PROXY_URL` | URL de proxy HTTP/SOCKS5 (si aplica) | *(Opcional)* |
| `FILEBROWSER_PORT` | Puerto web para la interfaz de visualización y descarga de fotos | `8080` |

---

## 📂 Visualización y Descarga Online (FileBrowser)

El proyecto incluye el servicio **FileBrowser** para acceder a todas las fotos y carpetas de sitios vía web:
- **URL:** `http://IP_DE_TU_VPS:8080` (o a través de tu dominio si configuras proxy inverso).
- **Usuario inicial:** `admin`
- **Contraseña inicial:** `admin` *(recomendado cambiarla al primer ingreso en Configuración > Perfil)*.
- **Funcionalidades:**
  - Ver fotos y miniaturas en alta resolución en tiempo real.
  - Descargar carpetas enteras de sitios en formato `.ZIP` con un solo clic.

---

## 🚀 Despliegue con Docker Compose (Recomendado para VPS)

1. **Construir y levantar el contenedor en segundo plano:**
   ```bash
   docker compose up -d --build
   ```

2. **Verificar estado y logs en tiempo real:**
   ```bash
   docker compose ps
   docker compose logs -f tss-bot
   ```

3. **Detener el servicio:**
   ```bash
   docker compose down
   ```

---

## 🔄 CI/CD Automatizado con GitHub Actions

El proyecto cuenta con un workflow en `.github/workflows/deploy.yml` que se ejecuta automáticamente ante cada `push` a la rama `master`:
1. Sincroniza el código fuente hacia la VPS mediante `rsync` sobre SSH.
2. Ejecuta `docker compose up -d --build` en la VPS asegurando disponibilidad continua.

### Secrets Requeridos en GitHub
En tu repositorio de GitHub (**Settings > Secrets and variables > Actions**):
- `VPS_HOST`: IP pública o dominio de tu servidor VPS.
- `VPS_USER`: Usuario SSH del servidor (ej. `root` o `ubuntu`).
- `VPS_SSH_KEY`: Clave privada SSH con acceso al servidor.

---

## 💻 Desarrollo Local (Sin Docker)

```bash
# 1. Crear y activar entorno virtual
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Definir token y ejecutar
$env:TELEGRAM_TOKEN="tu_token_aqui"  # En PowerShell
python bot.py
```
