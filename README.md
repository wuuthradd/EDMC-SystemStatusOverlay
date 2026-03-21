# EDMC-SystemStatusOverlay

A target system info overlay plugin for [Elite Dangerous Market Connector (EDMC)](https://github.com/EDCD/EDMarketConnector).

When you select a target system, this plugin queries EDSM (and optionally Spansh) to show scan status directly on the game overlay via [EDMCOverlay](https://github.com/inorton/EDMCOverlay) / [EDMCModernOverlay](https://github.com/SweetJonnySauce/EDMCModernOverlay).

| Status | Meaning |
|--------|---------|
| 🟥 **Not Found** | System not in database |
| 🟧 **Logged** | In database, no bodies scanned |
| 🟨 **Scanned** | Some bodies scanned |
| 🟩 **Fully Scanned** | All bodies scanned |

## Features

- **Color-coded scan status** — Not Found (red), Logged (yellow), Fully Scanned (green)
- **Body count tracking** — Shows discovered vs total bodies (e.g., `Logged 3/10 (K)`)
- **Star class display** — Main star type shown
- **Dual data source** — EDSM by default, optional Spansh queries
- **Screen-aware visibility** — Show/hide overlay per screen (Galaxy Map, System Map, Cockpit, Panels)
- **Persistent or timed display** — Keep overlay until system reached, or auto-hide after 5-30 seconds
- **Auto-clear** — Overlay clears on arrival at target system, route clearing, or EDMC shutdown
- **Customizable appearance** — Color picker, font size, position

## Display Examples

EDSM only (default):
```
Target: Proxima Centauri
Fully Scanned 3/3 (M)
```

With Spansh enabled:
```
Target: Wolf 1453
EDSM: Logged 3/10 (K)
Spansh: Fully Scanned 10/10 (K)
```

## Requirements

- [EDMC](https://github.com/EDCD/EDMarketConnector) (v5.0+)
- [EDMCOverlay](https://github.com/inorton/EDMCOverlay) or [EDMCModernOverlay](https://github.com/SweetJonnySauce/EDMCModernOverlay)

## Installation

1. Download the latest release zip from the [Releases](../../releases) page
2. Extract into your EDMC plugins folder:
   - Windows: `%LOCALAPPDATA%\EDMarketConnector\plugins\EDMC-SystemStatusOverlay`
   - Linux: `~/.local/share/EDMarketConnector/plugins/EDMC-SystemStatusOverlay`
   - Linux (Flatpak): `~/.var/app/io.edcd.EDMarketConnector/data/EDMarketConnector/plugins/EDMC-SystemStatusOverlay`
3. Restart EDMC

## Settings

All settings are accessible from EDMC's Settings > EDMC-SystemStatusOverlay tab.

| Setting | Default | Description |
|---------|---------|-------------|
| Enable overlay | On | Master toggle |
| Also query Spansh | Off | Enable secondary Spansh data source |
| Show on Galaxy Map | On | Overlay visibility per screen |
| Show on System Map | Off | |
| Show on Cockpit | On | |
| Show on Panels | Off | Internal, external, comms, role, station panels |
| Text color | #ff8c00 | Header/target name color (via color picker) |
| Font size | normal | small, normal, large |
| Position X | 20 | 0–1280 (overlay canvas coordinates) |
| Position Y | 80 | 0–960 |
| Display mode | Persistent | Persistent (until arrival) or Timed (TTL) |
| Display time | 15s | 5–30 seconds (only in Timed mode) |

> Note: Status text colors (red/yellow/green) are fixed and not affected by the text color setting.

## How It Works

1. Player selects a target system in-game (FSDTarget journal event)
2. Plugin queries EDSM's bodies and estimated-value APIs (and Spansh if enabled)
3. Results are displayed on the overlay with color-coded status
4. Overlay auto-hides/shows based on current screen and visibility settings
5. Overlay clears when arriving at the target system or clearing the route
