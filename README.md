# Antigravity Discord Rich Presence 🚀

> Discord Rich Presence para **Google Antigravity CLI** (`agy`). Muestra automáticamente tu proyecto activo, estado del agente y tiempo transcurrido en tu perfil de Discord.

---

## ✨ Características

- 🌌 **Logo de Gemini Minimalista:** Estrella oficial de Google Gemini estilizada y centrada con márgenes limpios.
- 🚦 **Puntos de Estado Sutiles:** Badges circulares minimalistas que cambian en tiempo real:
  - 🟢 **Verde:** Listo / Esperando prompt (`Idle`).
  - 🟡 **Amarillo / Dorado:** Agente pensando / generando respuesta.
  - 🟠 **Naranja:** Ejecutando herramientas o comandos en la terminal.
- 🪟 **Cambio Dinámico por Ventana:** Si tienes múltiples terminales de Alacritty (u otras terminales) abiertas con diferentes proyectos, el Rich Presence cambia automáticamente al proyecto de la terminal que estés enfocando.
- ⚡ **Auto-standby y Cierre Inmediato:** Al cerrar tus terminales, el estado de Discord se limpia en ~0.8s. Al volver a abrir `agy`, reaparece de inmediato sin tener que enviar un prompt primero.
- 🐧 **Compatibilidad Universal:** Funciona con Discord en **Flatpak**, **Snap**, paquetes nativos (.deb, Arch/AUR, etc.).
- 📦 **Cero dependencias:** No requiere `pip` ni paquetes de Python externos (funciona 100% con la librería estándar de Python 3).

---

## 🚀 Instalación Rápida

Elige el método que prefieras:

### Opción A: Vía `npx` (Recomendada)
Si tienes Node.js instalado, solo ejecuta:
```bash
npx agy-rich-presence
```

### Opción B: Vía `curl` (Un solo comando)
```bash
curl -fsSL https://raw.githubusercontent.com/GodDoesNotPlayDice/agy-rich-presence/main/install.sh | bash
```

### Opción C: Clonado Manual de Git
```bash
git clone https://github.com/GodDoesNotPlayDice/agy-rich-presence.git ~/.gemini/config/plugins/agy-rich-presence
```

---

## 🛠️ Comandos de Utilidad (`npx`)

Una vez instalado, puedes gestionar el plugin fácilmente:

```bash
# Ver estado del daemon, socket de Discord y proyectos activos
npx agy-rich-presence status

# Iniciar manualmente el servicio
npx agy-rich-presence start

# Detener el servicio
npx agy-rich-presence stop

# Reiniciar
npx agy-rich-presence restart

# Desinstalar completamente
npx agy-rich-presence uninstall
```

---

## ⚙️ Personalización

Puedes personalizar el nombre de la aplicación o tu propio Discord Application ID creando o editando `~/.gemini/antigravity-cli/discord_rpc_config.json`:

```json
{
  "client_id": "1510513707073929367",
  "app_name": "Antigravity better all <3"
}
```

> **Nota:** Si creas una aplicación personalizada en el [Discord Developer Portal](https://discord.com/developers/applications), coloca su Application ID en `"client_id"` y el nombre en `"app_name"`.

---

## 📄 Licencia

MIT License © 2026 Vicente Vasquez ([GodDoesNotPlayDice](https://github.com/GodDoesNotPlayDice))
