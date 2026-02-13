# Twor-Worlds-Dialog-Viewer-Editor

# Two Worlds 1 — Modding Tools

Open-source tools for modding Two Worlds 1 (2007, Reality Pump). Pure Python, no dependencies beyond the standard library, no SDK or WhizzEdit required.

## Tools

### LAN Viewer

Viewer and editor for the binary `.lan` language files that contain all localized game text — quest names, dialog lines, item descriptions, NPC names, tooltips.

- Parses all three data sections: 16,194 translations, 215 aliases, 583 quest dialog trees with 9,799 entries
- 17 auto-categorized categories (Dialogs, Quests, NPC Names, Rumors, Weapons, Armor, Skills...)
- Chat-style dialog view with automatic Hero/NPC speaker detection
- Compare mode to diff two .lan files (e.g. Patch vs Main)
- Edit and save with byte-perfect roundtrip
- Full-text search, statistics, lazy loading tree

### Quest & Dialog Editor

Editor and viewer for quest data in three formats: `.idx` (SOAP-XML, full read/write), `.qtx` (plaintext, full read/write), and `.shf` (WhizzEdit binary, read-only).

- Complete quest editing: activation, guild, group, reputation, state, developer notes
- NPC editing with 12 fields including drop items (OBJECTS with item lists)
- Quest logic sub-types: GIVER, FC, AOQ, ACTION, REWARD
- Dialog tree viewer with text, speaker, camera angles, animations
- SHF string extraction (23,329 strings from .NET BinaryFormatter)
- Format-preserving save for both .idx and .qtx

## Requirements

- Python 3.8+
- No pip packages needed (tkinter + xml.etree from standard library)
- Windows (BAT launchers included, scripts run cross-platform)

## Usage

Double-click the included `.bat` file or run directly:

```
python tw1_lan_viewer.py
python tw1_quest_editor.py
```

The BAT launchers auto-detect Python installations even if Python is not in PATH.

## File Formats

Both tools work with the quest/dialog pipeline that WhizzEdit produces:

```
WhizzEdit (Development Tool)
 ├── .shf    Native project format (binary, per folder)
 ├── .idx    XML export (SOAP-XML, complete)
 └── Compile
      ├── .qtx   Quest logic (plaintext, no dialogs)
      └── .lan   Localized text (binary, all strings)
```

Recommended workflow: use `.idx` for quest editing (contains everything), use `.lan` for text/translation work.

## Documentation

Each tool folder contains a README with usage instructions and a FORMAT_GUIDE with the full technical specification of the respective binary/text formats.

## Background

Two Worlds 1 shipped with WhizzEdit as its quest authoring tool, but WhizzEdit is a .NET application that barely runs on modern systems and only provides a viewer with no editing. The TW1 modding community has been essentially inactive — these are the first open-source tools for quest and dialog editing ever released for the game.

Format documentation is based on reverse engineering of the SDK files and BugLord's format specifications.

## License

MIT
