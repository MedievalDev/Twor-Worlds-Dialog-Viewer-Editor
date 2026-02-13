# TW1 Quest Editor

Editor and viewer for Two Worlds 1 quest data files. Supports three formats: `.idx` (SOAP-XML), `.qtx` (plaintext), and `.shf` (WhizzEdit binary, read-only).

## Features

- **Three format support**: .idx (full edit/save), .qtx (full edit/save), .shf (read-only viewer)
- **Tree view** with lazy loading — categorized by region groups (ASHOS, BORDER, CATHALON, etc.)
- **Quest detail view** — all fields: activation type, guild, group, reputation, quest state, notes
- **NPC detail view** — 12 fields including sector, size, position, faction, plus drop items (OBJECTS)
- **Dialog view** — structured quest dialog trees with text, lector/speaker, camera, animations
- **GIVER/FC/AOQ/ACTION/REWARD** sub-type editors for quest logic
- **Drop items** — OBJECTS field correctly parsed with item lists (e.g. `QITEM_221`, `MAGIC_POISONDART`)
- **Full-text search** across all entries
- **Edit & save** with format-preserving output (.idx and .qtx)
- **SHF string extraction** — 23,329 strings organized into 7 categories from .NET BinaryFormatter data
- Dark theme, adjustable font size

## Requirements

```
Python 3.8+
```

No additional packages needed (uses only standard library: tkinter, xml.etree).

## Usage

```bash
python tw1_quest_editor.py
```

Or double-click `START_QUEST_EDITOR.bat`.

1. Click **Load** and select a `.idx`, `.qtx`, or `.shf` file
2. Browse the tree — quests grouped by region, NPCs by type
3. Click entries to view/edit details
4. Modify fields in the detail panel
5. Click **Save** to write changes (disabled for .shf)

## Supported Files

| File | Format | Entries | Mode |
|------|--------|---------|------|
| TwoWorldsQuests.idx | SOAP-XML | ~500 quests, 6,942 dialogs | Read/Write |
| TwoWorldsQuests.qtx | Plaintext | ~500 quests, NPCs, locations | Read/Write |
| TwoWorldsQuests-Quests.shf | .NET Binary | 333 quests, 4,838 dialogs | Read-only |
| Any .idx/.qtx/.shf | varies | varies | varies |

## Format Comparison

| Feature | .idx | .qtx | .shf |
|---------|------|------|------|
| Quest definitions | Yes | Yes | Yes |
| Dialog trees | Yes (full) | No | Yes (extracted) |
| NPC definitions | Yes | Yes | Yes (extracted) |
| Location definitions | Yes | Yes | Yes (extracted) |
| Item drop lists (OBJECTS) | Yes | Yes | No |
| Editable | Yes | Yes | No |
| Source | WhizzEdit XML export | Game-compiled | WhizzEdit project |

## File Relationships

The same quest data exists in multiple formats produced by WhizzEdit:

```
WhizzEdit Project
  ├── .shf files (binary project, per folder)
  ├── .idx export (SOAP-XML, all data in one file)
  └── Compiled output
       ├── .qtx (quest logic for game engine)
       └── .lan (localized text for game engine)
```

For full editing, use the `.idx` file (8 MB, contains everything). The `.qtx` has quest logic but no dialog text. The `.shf` files are WhizzEdit's internal format — use only if .idx is unavailable.

## QTX OBJECTS Field

The OBJECTS line in QTX NPC definitions can contain item drop lists:

```
OBJECTS True QITEM_221 QITEM_221 QITEM_221 MAGIC_POISONDART
```

- `True/False` — whether the NPC has objects
- Followed by space-separated item IDs (the actual drops)
- 18 NPCs in the vanilla game have drop items
- Items are editable in the NPC detail view

## Notes

- Save produces format-identical output for both .idx and .qtx
- SHF files show a red ".SHF" indicator and disable the Save button
- None/null values in XML are handled gracefully (no crashes)
- The editor is a modern Python replacement for WhizzEdit's viewer functionality
- Place the `.bat` file in the same folder as the `.py` file
