# TW1 LAN Viewer

Viewer and editor for Two Worlds 1 language files (`.lan`). Parses all three data sections: translations, aliases, and quest dialog trees.

## Features

- **16,194 translations** organized into 17 categories (Dialogs, Quests, NPC Names, Rumors, Weapons, Armor, Skills, etc.)
- **215 alias entries** — dialog key redirects (e.g. shared dialog lines across quest states)
- **583 quest dialog trees** with 9,799 structured entries including lector/speaker IDs, sound cues, next dialog links, camera angles, animations, and flags
- **Chat-bubble dialog view** — Hero (green, right-aligned) vs NPC (left-aligned), grouped by quest with German quest names
- **Quest detail view** — Name, Take/Solve/Close descriptions per quest
- **Compare mode** — Load a second .lan file, differences highlighted in yellow (e.g. Patch vs Main)
- **Full-text search** across keys and values
- **Edit & save** with byte-perfect roundtrip
- **Statistics page** with category bar chart
- **Lazy loading** tree for fast startup even with 16,000+ entries
- **Auto-load** — finds .lan file in same folder on startup
- Dark theme, adjustable font size

## Requirements

```
Python 3.8+
```

No additional packages needed (uses only standard library).

## Usage

```bash
python tw1_lan_viewer.py
```

Or double-click `START_LAN_VIEWER.bat`.

1. Click **Load** and select a `.lan` file
2. Browse categories in the tree (click to expand, lazy-loaded)
3. Click a dialog group to see chat bubbles, click a quest group for detail view
4. Use the search bar and press Enter to find entries
5. Click **Compare** to load a second .lan and see differences
6. Edit values in the detail view and save

## Supported Files

| File | Entries | Description |
|------|---------|-------------|
| TwoWorldsQuests.lan | 16,194 | Main language file (quests, dialogs, items, NPCs) |
| TwoWorldsPatch1_6.lan | 33 | Patch 1.6 text changes |
| RegistrationCountries.lan | 2 | Registration country list |
| Any .lan | variable | Custom or modded language files |

## Categories

Translations are automatically sorted by key prefix:

DQ_ → Dialogs, Q_ → Quests, NPCName → NPC Names, NPC_ → NPC Refs, RUMORS_ → Rumors, TALK_ → Casual Talks, EVENT_ → Events, CUTSCENE_ → Cutscenes, Citizen_ → Citizens, Guard_ → Guards, QITEM_ → Quest Items, ING_ → Ingredients, WP_ → Weapons, AR_ → Armor, Tip_ → Tips, Net_ → Network, Skill → Skills, everything else → Other

## Hero/NPC Detection

Dialog states determine the speaker:
- **Hero**: States containing CLOSE, QC, QNS, QS (player choices and responses)
- **NPC**: All other states (FT.AS, QT, etc.)

## Notes

- Keys in the file start with "translate" prefix which is stripped for display
- The viewer preserves all binary data exactly — save produces byte-identical output
- Place the `.bat` file in the same folder as the `.py` file
