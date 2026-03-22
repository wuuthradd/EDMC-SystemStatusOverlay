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

- **Body count tracking** — Shows discovered vs total bodies
- **Star class display** — Main star type shown
- **Dual data source** — EDSM by default, optional Spansh queries
- **Screen-aware visibility** — Show/hide overlay per screen (Galaxy Map, System Map, Cockpit, Panels)
- **Auto-clear** — Overlay clears on arrival at target system, route clearing
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

- [EDMC](https://github.com/EDCD/EDMarketConnector)
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

> Note: Status text colors (red/yellow/green) are fixed and not affected by the text color setting.
