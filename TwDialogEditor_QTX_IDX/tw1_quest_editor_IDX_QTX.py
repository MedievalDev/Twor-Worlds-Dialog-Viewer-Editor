#!/usr/bin/env python3
"""
TW1 Quest Editor v1.2
Viewer/editor for TwoWorldsQuests files:
  .idx  = SOAP-XML (full edit + save)
  .qtx  = Plaintext (full edit + save)
  .shf  = .NET BinaryFormatter (read-only viewer)
WhizzEdit still needed for compiling QTX/LAN.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os, re, shutil, struct
import xml.etree.ElementTree as ET
from collections import OrderedDict

VERSION = "1.2"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# COLORS
# ============================================================
BG      = "#1a1a2e"
BG2     = "#16213e"
BG3     = "#0f3460"
FG      = "#e8e8e8"
FG_DIM  = "#999999"
ACCENT  = "#e94560"
GREEN   = "#4ecca3"
YELLOW  = "#ffaa00"
RED     = "#ff6b6b"
BLUE    = "#64b5f6"
ORANGE  = "#ff9f43"
CARD_BG = "#16213e"
CHAT_NPC  = "#1b3a4b"
CHAT_HERO = "#2d1b4e"
TREE_BG = "#111a2e"
TREE_FG = "#cccccc"

ICONS = {
    "NodeSharedFolder": "\U0001f4c1", "NodeFolder": "\U0001f4c2",
    "NodeQuest": "\U0001f4dc", "NodeQuestDialog": "\U0001f4ac",
    "NodeQuestDialogText": "\U0001f4ad", "NodeCharacter": "\U0001f464",
    "NodeEnemy": "\u2694", "NodeLocation": "\U0001f4cd",
    "NodeObject": "\U0001f4e6", "NodeLector": "\U0001f3ad",
    "NodeParty": "\u2691", "NodeGuild": "\U0001f3db",
    "NodeEffect": "\u2728", "NodeGroup": "\U0001f465",
    "NodeMapSign": "\U0001f5fa", "NodeText": "\U0001f4dd",
    "NodeQuestText": "\U0001f4cb", "NodeQuestAction": "\u26a1",
    "NodeQuestReward": "\U0001f381", "NodeQuestFC": "\U0001f517",
    "NodeQuestAOQ": "\U0001f527", "NodeQuestGiver": "\U0001f5e3",
    "NodeRumorsDialog": "\U0001f442", "NodeRumorsDialogText": "\U0001f5e8",
    "NodeDialogText": "\U0001f4ac", "NodeDialog": "\U0001f4ac",
    "QTX_NPC": "\U0001f464", "QTX_LOCATION": "\U0001f4cd",
    "QTX_QUEST": "\U0001f4dc", "QTX_ACTION": "\u26a1",
    "QTX_FC": "\U0001f517", "QTX_AOQ": "\U0001f527",
    "QTX_REWARD": "\U0001f381", "QTX_GIVER": "\U0001f5e3",
    "QTX_OBJECTS": "\U0001f4e6", "QTX_FOLDER": "\U0001f4c1",
    "QTX_ROOT": "\U0001f3ae",
    "SHF_ROOT": "\U0001f3ae", "SHF_FOLDER": "\U0001f4c1",
    "SHF_QUEST": "\U0001f4dc", "SHF_DIALOG": "\U0001f4ad",
    "SHF_TEXT": "\U0001f4dd", "SHF_GROUP": "\U0001f465",
}

NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
HIDDEN_FIELDS = {"nodes"}

# ============================================================
# GENERIC NODE
# ============================================================
class Node:
    __slots__ = ("node_type", "name", "props", "children", "element",
                 "line_start", "line_end", "raw_line")
    def __init__(self, node_type, name="", props=None, children=None,
                 element=None, line_start=-1, line_end=-1, raw_line=""):
        self.node_type = node_type
        self.name = name
        self.props = props or OrderedDict()
        self.children = children or []
        self.element = element
        self.line_start = line_start
        self.line_end = line_end
        self.raw_line = raw_line


# ============================================================
# IDX PARSER (SOAP-XML)
# ============================================================
def _strip(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag

def parse_idx(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    body = None
    for e in root:
        if _strip(e.tag) == "Body": body = e; break
    if body is None: raise ValueError("No SOAP-ENV:Body")
    ref_idx = {}
    for e in body:
        eid = e.get("id", "")
        if eid: ref_idx[eid] = e
    def resolve(href):
        if href and href.startswith("#"): return ref_idx.get(href[1:])
    def parse_el(elem):
        tag = _strip(elem.tag)
        if tag == "Array":
            ch = []
            for item in elem:
                ce = resolve(item.get("href", ""))
                if ce is not None:
                    cn = parse_el(ce)
                    if cn is not None: ch.append(cn)
            return ch
        props = OrderedDict(); name = ""; child_arr = None
        for child in elem:
            ct = _strip(child.tag)
            if child.get(f"{{{NS_XSI}}}null", "") == "1": props[ct] = None
            elif ct in ("n", "name"):
                name = (child.text or "").strip(); props["name"] = name
            elif ct == "nodes":
                ae = resolve(child.get("href", ""))
                if ae is not None: child_arr = parse_el(ae)
            else: props[ct] = (child.text or "").strip()
        children = child_arr if isinstance(child_arr, list) else []
        return Node(tag, name=name or props.get("iid","") or props.get("text","") or tag,
            props=props, children=children, element=elem)
    root_el = None
    for e in body:
        if _strip(e.tag) == "RootNode": root_el = e; break
    if root_el is None: raise ValueError("No RootNode")
    return parse_el(root_el), tree


# ============================================================
# QTX PARSER (TEXT) — with OBJECTS item list fix
# ============================================================
NPC_FIELDS = ["id","iid","marker","sector","angle","quest_ref",
              "level","party_ref","size","active","create_string","exp"]
LOC_FIELDS = ["id","iid","marker","sector","x","y"]
QUEST_FIELDS = ["id","group","iid","guild","min_rep","add_to_log"]

def _null(v): return None if v == "(null)" else v

def _parse_qtx_npc(lines, i):
    line = lines[i].strip()
    parts = line.split(" ", 12)
    props = OrderedDict()
    for j, f in enumerate(NPC_FIELDS):
        if j+1 < len(parts): props[f] = _null(parts[j+1])
    node = Node("QTX_NPC", name=props.get("id",""), props=props, line_start=i, raw_line=line)
    i += 1
    while i < len(lines):
        sl = lines[i].strip()
        if sl == "END": node.line_end = i; i += 1; break
        elif sl.startswith("OBJECTS "):
            obj_parts = sl.split(" ", 1)[1].split()
            props["objects"] = obj_parts[0]  # True/False
            if len(obj_parts) > 1:
                props["object_items"] = " ".join(obj_parts[1:])
            i += 1
        else: i += 1
    return node, i

def _parse_qtx_location(lines, i):
    line = lines[i].strip()
    parts = line.split(" ")
    props = OrderedDict()
    for j, f in enumerate(LOC_FIELDS):
        if j+1 < len(parts): props[f] = _null(parts[j+1])
    node = Node("QTX_LOCATION", name=props.get("id",""), props=props, line_start=i, raw_line=line)
    i += 1
    while i < len(lines):
        sl = lines[i]
        if sl.startswith("LOCATION ") or sl.startswith("QUEST "): break
        if sl.strip().startswith("NPC "):
            sub, i = _parse_qtx_npc(lines, i); node.children.append(sub)
        else: i += 1
    node.line_end = i - 1
    return node, i

def _parse_qtx_sub(line, ntype, li):
    parts = line.strip().split(" ")
    params = parts[1:]
    props = OrderedDict({"raw": line.strip()})
    if ntype == "QTX_ACTION" and len(params) >= 2:
        props["action_type"] = params[0]; props["trigger"] = params[1]
        props["params"] = " ".join(params[2:])
    elif ntype == "QTX_FC" and len(params) >= 1:
        props["fc_type"] = params[0]; props["params"] = " ".join(params[1:])
    elif ntype == "QTX_AOQ" and len(params) >= 2:
        props["aoq_action"] = params[0]; props["trigger"] = params[1]
        props["target"] = " ".join(params[2:])
    elif ntype == "QTX_REWARD" and len(params) >= 2:
        props["reward_type"] = params[0]; props["trigger"] = params[1]
        props["amount"] = " ".join(params[2:])
    elif ntype == "QTX_GIVER":
        for k, idx in [("status",0),("npc",1),("behavior",2),("on_solve",3)]:
            if len(params) > idx: props[k] = params[idx]
    return Node(ntype, name=line.strip(), props=props, line_start=li, raw_line=line.strip())

def _parse_qtx_quest(lines, i):
    line = lines[i].strip()
    parts = line.split(" ")
    props = OrderedDict()
    for j, f in enumerate(QUEST_FIELDS):
        if j+1 < len(parts): props[f] = _null(parts[j+1])
    node = Node("QTX_QUEST", name=props.get("id",""), props=props, line_start=i, raw_line=line)
    i += 1
    while i < len(lines):
        sl = lines[i].strip()
        if sl == "END": node.line_end = i; i += 1; break
        kw = sl.split(" ", 1)[0]
        type_map = {"ACTION":"QTX_ACTION","FC":"QTX_FC","AOQ":"QTX_AOQ",
                    "REWARD":"QTX_REWARD","GIVER":"QTX_GIVER"}
        if kw in type_map: node.children.append(_parse_qtx_sub(sl, type_map[kw], i))
        i += 1
    return node, i

def parse_qtx(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [l.rstrip("\n\r") for l in f.readlines()]
    root = Node("QTX_ROOT", name=os.path.basename(filepath))
    npcs = Node("QTX_FOLDER", name="NPCs")
    locs = Node("QTX_FOLDER", name="Locations")
    quests = Node("QTX_FOLDER", name="Quests")
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("NPC "):
            n, i = _parse_qtx_npc(lines, i); npcs.children.append(n)
        elif line.startswith("LOCATION "):
            n, i = _parse_qtx_location(lines, i); locs.children.append(n)
        elif line.startswith("QUEST "):
            n, i = _parse_qtx_quest(lines, i); quests.children.append(n)
        else: i += 1
    root.children = [npcs, locs, quests]
    return root, lines

def save_qtx(filepath, root_node, original_lines):
    out = []
    def write_npc(node, indent=""):
        parts = ["NPC"]
        for f in NPC_FIELDS:
            v = node.props.get(f); parts.append(v if v is not None else "(null)")
        out.append(indent + " ".join(parts))
        obj = node.props.get("objects", "False")
        items = node.props.get("object_items", "")
        obj_line = indent + "  OBJECTS " + obj
        if items: obj_line += " " + items
        out.append(obj_line)
        out.append(indent + "END")
    def write_location(node):
        parts = ["LOCATION"]
        for f in LOC_FIELDS:
            v = node.props.get(f); parts.append(v if v is not None else "(null)")
        out.append(" ".join(parts))
        for c in node.children:
            if c.node_type == "QTX_NPC": write_npc(c)
    def write_quest(node):
        parts = ["QUEST"]
        for f in QUEST_FIELDS:
            v = node.props.get(f); parts.append(v if v is not None else "(null)")
        out.append(" ".join(parts))
        for c in node.children: out.append("  " + c.props.get("raw", c.raw_line))
        out.append("END")
    for folder in root_node.children:
        if folder.name == "NPCs":
            for n in folder.children: write_npc(n)
        elif folder.name == "Locations":
            for n in folder.children: write_location(n)
        elif folder.name == "Quests":
            for n in folder.children: write_quest(n)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


# ============================================================
# SHF PARSER (.NET BinaryFormatter — read-only)
# ============================================================
def _read_7bit(data, pos):
    result = 0; shift = 0
    while pos < len(data):
        b = data[pos]; pos += 1
        result |= (b & 0x7f) << shift
        if not (b & 0x80): break
        shift += 7
    return result, pos

def _read_str(data, pos):
    slen, pos = _read_7bit(data, pos)
    if slen > 50000: return "", pos
    text = data[pos:pos+slen].decode("utf-8", errors="replace")
    return text, pos + slen

def parse_shf(filepath):
    """Parse .shf by extracting BinaryObjectString records and grouping them."""
    with open(filepath, "rb") as f:
        data = f.read()

    # Extract all BinaryObjectString records (type 0x06)
    strings = {}  # obj_id -> text
    pos = 0
    while pos < len(data) - 6:
        if data[pos] == 0x06:
            try:
                obj_id = struct.unpack_from("<I", data, pos + 1)[0]
                slen, spos = _read_7bit(data, pos + 5)
                if 0 < slen < 50000 and spos + slen <= len(data):
                    text = data[spos:spos+slen].decode("utf-8", errors="replace")
                    if text and not all(c == "\x00" for c in text):
                        strings[obj_id] = text
                        pos = spos + slen; continue
            except: pass
        pos += 1

    # Categorize strings
    root = Node("SHF_ROOT", name=os.path.basename(filepath))
    root.props["info"] = "Read-only (.NET BinaryFormatter)"

    # Quest groups (ASHOS, CATHALON etc)
    groups = sorted(set(v for v in strings.values() if re.match(r"^[A-Z][A-Z_]{2,30}$", v)
                         and not v.startswith("NPC_") and not v.startswith("Q_")
                         and not v.startswith("LOC_") and not v.startswith("QITEM_")))

    # Quest IDs
    quest_ids = sorted(set(v for v in strings.values() if re.match(r"^Q_\d+$", v)),
                       key=lambda x: int(x.split("_")[1]))

    # NPC references
    npc_refs = sorted(set(v for v in strings.values() if re.match(r"^NPC_\d+$", v)),
                      key=lambda x: int(x.split("_")[1]))

    # Dialog texts (long strings with punctuation)
    dialog_texts = [(k, v) for k, v in sorted(strings.items())
                    if len(v) > 20 and any(c in v for c in ".!?,;:")
                    and not v.startswith("WhizzEdit")]

    # Quest items
    qitems = sorted(set(v for v in strings.values() if v.startswith("QITEM_")))

    # Enemy types
    enemies = sorted(set(v for v in strings.values() if v.startswith("ENEMY_")))

    # Location refs
    loc_refs = sorted(set(v for v in strings.values() if v.startswith("LOC_")))

    # Build tree
    quests_f = Node("SHF_FOLDER", name=f"Quests ({len(quest_ids)})")
    for qid in quest_ids:
        quests_f.children.append(Node("SHF_QUEST", name=qid,
            props=OrderedDict({"id": qid})))

    npcs_f = Node("SHF_FOLDER", name=f"NPC References ({len(npc_refs)})")
    for npc in npc_refs:
        npcs_f.children.append(Node("QTX_NPC", name=npc,
            props=OrderedDict({"id": npc})))

    dialogs_f = Node("SHF_FOLDER", name=f"Dialog Texts ({len(dialog_texts)})")
    for obj_id, text in dialog_texts[:500]:  # Limit for performance
        preview = text[:60].replace("\n", " ").replace("\r", "")
        dialogs_f.children.append(Node("SHF_DIALOG", name=preview,
            props=OrderedDict({"obj_id": str(obj_id), "text": text})))

    groups_f = Node("SHF_FOLDER", name=f"Groups/Keywords ({len(groups)})")
    for g in groups:
        groups_f.children.append(Node("SHF_GROUP", name=g,
            props=OrderedDict({"name": g})))

    items_f = Node("SHF_FOLDER", name=f"Quest Items ({len(qitems)})")
    for qi in qitems:
        items_f.children.append(Node("NodeObject", name=qi,
            props=OrderedDict({"id": qi})))

    enemies_f = Node("SHF_FOLDER", name=f"Enemy Types ({len(enemies)})")
    for en in enemies:
        enemies_f.children.append(Node("NodeEnemy", name=en,
            props=OrderedDict({"id": en})))

    locs_f = Node("SHF_FOLDER", name=f"Locations ({len(loc_refs)})")
    for loc in loc_refs:
        locs_f.children.append(Node("QTX_LOCATION", name=loc,
            props=OrderedDict({"id": loc})))

    root.children = [quests_f, npcs_f, dialogs_f, groups_f, items_f, enemies_f, locs_f]

    # Stats in props
    root.props["strings_total"] = str(len(strings))
    root.props["quests"] = str(len(quest_ids))
    root.props["npcs"] = str(len(npc_refs))
    root.props["dialogs"] = str(len(dialog_texts))

    return root


# ============================================================
# APP
# ============================================================
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"TW1 Quest Editor v{VERSION}")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)
        self.root.configure(bg=BG)
        self.font_size = 12
        self.node_root = None
        self.xml_tree = None
        self.qtx_lines = None
        self.filepath = None
        self.file_type = None  # "idx" / "qtx" / "shf"
        self.tree_map = {}
        self.modified = False
        self._build_ui()
        # Auto-load
        for name in ("TwoWorldsQuests.idx","TwoWorldsQuests.qtx"):
            p = os.path.join(SCRIPT_DIR, name)
            if os.path.exists(p): self._load_file(p); break

    def _build_ui(self):
        top = tk.Frame(self.root, bg=BG3, height=44)
        top.pack(fill="x"); top.pack_propagate(False)
        tk.Label(top, text=f"TW1 Quest Editor v{VERSION}",
                 font=("Segoe UI",12,"bold"), bg=BG3, fg=FG).pack(side="left", padx=14)
        self.status = tk.Label(top, text="No file loaded",
                                font=("Segoe UI",9), bg=BG3, fg=FG_DIM)
        self.status.pack(side="left", padx=16)
        rf = tk.Frame(top, bg=BG3); rf.pack(side="right", padx=10)
        tk.Button(rf, text="\u2212", font=("Segoe UI",9,"bold"), width=2,
                 bg=BG2, fg=FG, relief="flat", cursor="hand2",
                 command=lambda: self._font(-1)).pack(side="left", padx=1)
        self.font_lbl = tk.Label(rf, text="12", font=("Segoe UI",9), bg=BG3, fg=FG, width=3)
        self.font_lbl.pack(side="left")
        tk.Button(rf, text="+", font=("Segoe UI",9,"bold"), width=2,
                 bg=BG2, fg=FG, relief="flat", cursor="hand2",
                 command=lambda: self._font(1)).pack(side="left", padx=1)
        # Toolbar
        bar = tk.Frame(self.root, bg=BG); bar.pack(fill="x", padx=8, pady=(5,2))
        tk.Button(bar, text="Load", font=("Segoe UI",10,"bold"),
                 bg=ACCENT, fg=FG, relief="flat", padx=14, pady=3,
                 cursor="hand2", command=self._load).pack(side="left", padx=(0,4))
        self.save_btn = tk.Button(bar, text="Save", font=("Segoe UI",10,"bold"),
                 bg=GREEN, fg=BG, relief="flat", padx=14, pady=3,
                 cursor="hand2", command=self._save)
        self.save_btn.pack(side="left", padx=(0,10))
        tk.Label(bar, text="Search:", font=("Segoe UI",10), bg=BG, fg=FG_DIM
                 ).pack(side="left", padx=(8,4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._search())
        tk.Entry(bar, textvariable=self.search_var, font=("Segoe UI",10),
                 bg=CARD_BG, fg=FG, insertbackground=FG, relief="flat", width=25
                 ).pack(side="left", ipady=4, padx=(0,6))
        self.search_lbl = tk.Label(bar, text="", font=("Segoe UI",9), bg=BG, fg=FG_DIM)
        self.search_lbl.pack(side="left")
        self.type_lbl = tk.Label(bar, text="", font=("Segoe UI",9,"bold"), bg=BG, fg=ORANGE)
        self.type_lbl.pack(side="right", padx=10)
        # Panes
        self.paned = tk.PanedWindow(self.root, orient="horizontal", bg=BG,
                                     sashwidth=4, sashrelief="flat")
        self.paned.pack(fill="both", expand=True, padx=8, pady=(2,8))
        tf = tk.Frame(self.paned, bg=TREE_BG)
        self.paned.add(tf, width=300, minsize=180)
        style = ttk.Style(); style.theme_use("clam")
        style.configure("T.Treeview", background=TREE_BG, foreground=TREE_FG,
                        fieldbackground=TREE_BG, font=("Segoe UI",11),
                        rowheight=26, borderwidth=0)
        style.map("T.Treeview", background=[("selected",BG3)],
                  foreground=[("selected",GREEN)])
        self.tree = ttk.Treeview(tf, style="T.Treeview", show="tree")
        tsb = tk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tsb.set)
        tsb.pack(side="right", fill="y"); self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.detail = tk.Frame(self.paned, bg=BG)
        self.paned.add(self.detail, minsize=400)
        self._welcome()

    def _welcome(self):
        for w in self.detail.winfo_children(): w.destroy()
        f = tk.Frame(self.detail, bg=BG); f.pack(expand=True)
        tk.Label(f, text="TW1 Quest Editor", font=("Segoe UI",18,"bold"),
                 bg=BG, fg=FG).pack(pady=(40,8))
        tk.Label(f, text=".idx (SOAP-XML) + .qtx (text) + .shf (read-only)",
                 font=("Segoe UI",11), bg=BG, fg=FG_DIM).pack()
        tk.Label(f, text="WhizzEdit still needed for compiling.",
                 font=("Segoe UI",9), bg=BG, fg=FG_DIM).pack(pady=(16,0))

    def _font(self, d):
        self.font_size = max(9, min(18, self.font_size + d))
        self.font_lbl.config(text=str(self.font_size))
        ttk.Style().configure("T.Treeview", font=("Segoe UI",self.font_size-1),
                              rowheight=max(24,self.font_size*2))
        self._on_select(None)

    # ---- LOAD / SAVE ----
    def _load(self):
        f = filedialog.askopenfilename(title="Open Quest File",
            filetypes=[("Quest files","*.idx *.qtx *.shf"),("All","*.*")],
            initialdir=SCRIPT_DIR)
        if f: self._load_file(f)

    def _load_file(self, path):
        try:
            self.status.config(text="Loading...", fg=YELLOW); self.root.update()
            ext = os.path.splitext(path)[1].lower()
            if ext == ".idx":
                self.node_root, self.xml_tree = parse_idx(path)
                self.file_type = "idx"; self.qtx_lines = None
            elif ext == ".qtx":
                self.node_root, self.qtx_lines = parse_qtx(path)
                self.file_type = "qtx"; self.xml_tree = None
            elif ext == ".shf":
                self.node_root = parse_shf(path)
                self.file_type = "shf"; self.xml_tree = None; self.qtx_lines = None
            else: raise ValueError(f"Unknown: {ext}")
            self.filepath = path; self._build_tree(); self.modified = False
            s = self._stats(self.node_root); bn = os.path.basename(path)
            info = f"{bn}  |  {s['q']}Q  {s['c']}C  {s['d']}D  {s['e']}E"
            if ext == ".shf": info += "  (read-only)"
            self.status.config(text=info, fg=GREEN)
            self.type_lbl.config(text=ext.upper(),
                                  fg=RED if ext == ".shf" else ORANGE)
            self.save_btn.config(state="normal" if ext != ".shf" else "disabled")
            self.root.title(f"TW1 Quest Editor - {bn}")
        except Exception as e:
            messagebox.showerror("Error", f"Load failed:\n{e}")
            self.status.config(text=str(e), fg=RED)
            import traceback; traceback.print_exc()

    def _stats(self, node):
        r = {"q":0,"c":0,"d":0,"e":0}
        def walk(n):
            t = n.node_type
            if t in ("NodeQuest","QTX_QUEST","SHF_QUEST"): r["q"] += 1
            elif t in ("NodeCharacter","QTX_NPC"): r["c"] += 1
            elif "Dialog" in t and "Folder" not in t: r["d"] += 1
            elif t in ("NodeEnemy",): r["e"] += 1
            for c in n.children: walk(c)
        walk(node); return r

    def _save(self):
        if not self.filepath or self.file_type == "shf": return
        bak = self.filepath + ".bak"
        try: shutil.copy2(self.filepath, bak)
        except: pass
        try:
            if self.file_type == "idx":
                self.xml_tree.write(self.filepath, encoding="utf-8", xml_declaration=False)
                with open(self.filepath, "r", encoding="utf-8") as f: c = f.read()
                with open(self.filepath, "w", encoding="utf-8-sig") as f: f.write(c)
            elif self.file_type == "qtx":
                save_qtx(self.filepath, self.node_root, self.qtx_lines)
            self.modified = False
            self.status.config(text="Saved! (.bak backup created)", fg=GREEN)
        except Exception as e:
            messagebox.showerror("Error", f"Save failed:\n{e}")

    # ---- TREE ----
    def _build_tree(self):
        self.tree.delete(*self.tree.get_children()); self.tree_map.clear()
        if not self.node_root: return
        # Only insert top-level + 1 depth, rest lazy
        for child in self.node_root.children:
            self._insert_node("", child, expand_depth=1)
        self.tree.bind("<<TreeviewOpen>>", self._on_expand)

    def _insert_node(self, parent_tid, node, expand_depth=0):
        icon = ICONS.get(node.node_type, "\u2022")
        display = node.name or node.node_type
        if "DialogText" in node.node_type:
            txt = node.props.get("text") or ""
            if txt:
                display = txt[:55].replace("\n"," ")
                if len(txt) > 55: display += "..."
        if node.node_type == "QTX_QUEST": display = node.props.get("id", node.name)
        if node.node_type in ("QTX_ACTION","QTX_FC","QTX_AOQ","QTX_REWARD","QTX_GIVER"):
            raw = node.props.get("raw", node.name)
            display = raw[:65]
            if len(raw) > 65: display += "..."
        if node.node_type == "SHF_DIALOG":
            txt = node.props.get("text") or ""
            display = txt[:60].replace("\n"," ").replace("\r","")
            if len(txt) > 60: display += "..."
        tid = self.tree.insert(parent_tid, "end", text=f"{icon}  {display}",
                                open=False)
        self.tree_map[tid] = node
        if expand_depth > 0 and node.children:
            for c in node.children:
                self._insert_node(tid, c, expand_depth - 1)
        elif node.children:
            # Placeholder so the expand arrow shows
            self.tree.insert(tid, "end", text="...", tags=("placeholder",))

    def _on_expand(self, event):
        tid = self.tree.focus()
        if not tid: return
        node = self.tree_map.get(tid)
        if not node: return
        children = self.tree.get_children(tid)
        # Check if first child is placeholder
        if len(children) == 1 and "placeholder" in self.tree.item(children[0], "tags"):
            self.tree.delete(children[0])
            for c in node.children:
                self._insert_node(tid, c, expand_depth=0)

    # ---- SEARCH ----
    def _search(self):
        q = self.search_var.get().strip().lower()
        if not q or len(q) < 2: self.search_lbl.config(text=""); return
        # Walk node tree to find matches
        hits = []
        def walk(node, path):
            hay = " ".join(filter(None, [
                node.name, node.props.get("id"), node.props.get("iid"),
                node.props.get("text"), node.props.get("notes"),
                node.props.get("create_string"), node.props.get("raw"),
                node.props.get("action_type"), node.props.get("fc_type"),
                node.props.get("npc"), node.props.get("target"),
                node.props.get("object_items"),
            ])).lower()
            if q in hay: hits.append(path + [node])
            for c in node.children:
                walk(c, path + [node])
                if len(hits) >= 100: return  # Limit
        if self.node_root:
            for c in self.node_root.children:
                walk(c, [])
                if len(hits) >= 100: break
        self.search_lbl.config(text=f"{len(hits)} found")
        if hits:
            # Ensure path to first hit is expanded in tree
            target = hits[0][-1]
            # Find or create tree item for target
            tid = self._ensure_visible(target, hits[0][:-1])
            if tid:
                self.tree.selection_set(tid)
                self.tree.see(tid)

    def _ensure_visible(self, target, ancestors):
        """Expand tree path to make target node visible, return its tid."""
        # Find tid for each ancestor, expanding as needed
        parent_tid = ""
        for anc in ancestors:
            # Find anc's tid among children of parent_tid
            found = None
            for cid in self.tree.get_children(parent_tid):
                if self.tree_map.get(cid) is anc:
                    found = cid; break
            if not found: return None
            # Expand if needed (triggers lazy load)
            children = self.tree.get_children(found)
            if len(children) == 1 and "placeholder" in self.tree.item(children[0], "tags"):
                self.tree.delete(children[0])
                for c in anc.children:
                    self._insert_node(found, c, expand_depth=0)
            self.tree.item(found, open=True)
            parent_tid = found
        # Now find target among children
        for cid in self.tree.get_children(parent_tid):
            if self.tree_map.get(cid) is target:
                return cid
        return None

    # ---- SELECT ----
    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        node = self.tree_map.get(sel[0])
        if not node: return
        self._show(node)

    def _show(self, node):
        for w in self.detail.winfo_children(): w.destroy()
        t = node.node_type
        dialogs = self._collect_dialogs(node)
        if dialogs: self._view_chat(node, dialogs)
        elif t == "NodeCharacter": self._view_character_idx(node)
        elif t == "NodeQuest": self._view_quest_idx(node)
        elif t == "QTX_NPC": self._view_npc_qtx(node)
        elif t == "QTX_LOCATION": self._view_location_qtx(node)
        elif t == "QTX_QUEST": self._view_quest_qtx(node)
        elif t in ("QTX_ACTION","QTX_FC","QTX_AOQ","QTX_REWARD","QTX_GIVER"):
            self._view_quest_sub(node)
        elif t == "SHF_DIALOG": self._view_shf_dialog(node)
        elif t == "SHF_ROOT": self._view_shf_root(node)
        else: self._view_generic(node)

    def _collect_dialogs(self, node):
        r = []
        if "DialogText" in node.node_type: r.append(node)
        for c in node.children: r.extend(self._collect_dialogs(c))
        return r

    # ============================================================
    # VIEWS
    # ============================================================
    def _view_chat(self, parent, dialogs):
        fs = self.font_size
        hdr = tk.Frame(self.detail, bg=BG3, padx=12, pady=8); hdr.pack(fill="x")
        title = parent.name or parent.props.get("iid","Dialog")
        tk.Label(hdr, text=f"\U0001f4ac  {title}",
                 font=("Segoe UI",fs+1,"bold"), bg=BG3, fg=FG).pack(anchor="w")
        sub = parent.props.get("text","")
        if sub and sub != title:
            tk.Label(hdr, text=sub, font=("Segoe UI",fs-1), bg=BG3, fg=FG_DIM).pack(anchor="w")
        tk.Label(hdr, text=f"{len(dialogs)} lines",
                 font=("Segoe UI",fs-2), bg=BG3, fg=GREEN).pack(anchor="w")
        canvas, cf = self._scrollable()
        cur_state = None
        for dnode in dialogs:
            lector = dnode.props.get("lector_type","Default")
            dtype = dnode.props.get("type") or ""
            text = dnode.props.get("text") or "(empty)"
            if dtype and dtype != cur_state:
                cur_state = dtype
                sep = tk.Frame(cf, bg=BG, pady=4); sep.pack(fill="x", padx=8)
                tk.Frame(sep, bg=FG_DIM, height=1).pack(fill="x", side="left", expand=True, pady=8)
                tk.Label(sep, text=f"  {dtype}  ", font=("Segoe UI",fs-2),
                         bg=BG, fg=YELLOW).pack(side="left")
                tk.Frame(sep, bg=FG_DIM, height=1).pack(fill="x", side="left", expand=True, pady=8)
            is_hero = lector in ("Hero","HERO")
            bg_c = CHAT_HERO if is_hero else CHAT_NPC
            brow = tk.Frame(cf, bg=BG); brow.pack(fill="x", padx=8, pady=2)
            if is_hero:
                tk.Frame(brow, bg=BG, width=50).pack(side="left", fill="y")
                bubble = tk.Frame(brow, bg=bg_c, padx=10, pady=6)
                bubble.pack(side="right", fill="x", expand=True)
                tk.Label(bubble, text="Hero", font=("Segoe UI",fs-3,"bold"),
                         bg=bg_c, fg=BLUE).pack(anchor="e")
            else:
                bubble = tk.Frame(brow, bg=bg_c, padx=10, pady=6)
                bubble.pack(side="left", fill="x", expand=True)
                tk.Frame(brow, bg=BG, width=50).pack(side="right", fill="y")
                tk.Label(bubble, text="NPC", font=("Segoe UI",fs-3,"bold"),
                         bg=bg_c, fg=GREEN).pack(anchor="w")
            editable = self.file_type != "shf"
            if editable:
                tw = tk.Text(bubble, font=("Segoe UI",fs), bg=bg_c, fg=FG,
                              wrap="word", relief="flat", insertbackground=FG,
                              padx=2, pady=2, borderwidth=0, highlightthickness=0)
                tw.insert("1.0", text)
                nl = text.count("\n") + 1 + max(0, len(text)//55)
                tw.config(height=min(10, max(1, nl)))
                tw.pack(fill="x", pady=(2,0))
                tw.bind("<KeyRelease>", lambda e, n=dnode, w=tw: self._edit_idx_text(n, w))
            else:
                tk.Label(bubble, text=text, font=("Segoe UI",fs), bg=bg_c, fg=FG,
                         wraplength=500, justify="left").pack(fill="x", pady=(2,0), anchor="w")
            parts = []
            iid = dnode.props.get("iid","")
            if iid: parts.append(f"#{iid}")
            cam = dnode.props.get("camera","")
            if cam and cam != "-1": parts.append(f"Cam:{cam}")
            if parts:
                tk.Label(bubble, text="  ".join(parts), font=("Consolas",fs-3),
                         bg=bg_c, fg=FG_DIM).pack(anchor="e" if is_hero else "w", pady=(2,0))

    def _view_character_idx(self, node):
        self._header(node, "\U0001f464 Character")
        _, frame = self._scrollable()
        prio = ["iid","name","text","marker","sector","angle","party","guild",
                "lector","create_string","exp","exp_level","remove_from_map",
                "random_stuff","notes","rumors_dialog"]
        self._show_props(frame, node, prio, editable=True)
        cs = node.props.get("create_string","")
        if cs: self._show_cs(frame, cs)

    def _view_quest_idx(self, node):
        self._header(node, "\U0001f4dc Quest")
        _, frame = self._scrollable()
        prio = ["iid","name","text","activation","group","guild",
                "min_reputation","add_to_quest_log","can_be_failed","quest_state","notes"]
        self._show_props(frame, node, prio, editable=True)
        dialogs = self._collect_dialogs(node)
        if dialogs:
            tk.Frame(frame, bg=FG_DIM, height=1).pack(fill="x", pady=(10,6), padx=8)
            tk.Label(frame, text=f"\U0001f4ac {len(dialogs)} dialog lines",
                     font=("Segoe UI",self.font_size-1), bg=BG, fg=BLUE).pack(anchor="w", padx=12)

    def _view_npc_qtx(self, node):
        self._header(node, "\U0001f464 NPC")
        _, frame = self._scrollable()
        labels = {"id":"ID","iid":"IID","marker":"Marker","sector":"Sector",
                  "angle":"Angle","quest_ref":"Quest Ref","level":"Level",
                  "party_ref":"Party Ref","size":"Size","active":"Active",
                  "create_string":"Create String","exp":"EXP",
                  "objects":"Objects","object_items":"Drop Items"}
        editable = {"sector","angle","quest_ref","level","party_ref",
                     "active","create_string","exp","objects","object_items"}
        for key, label in labels.items():
            val = node.props.get(key)
            if val is None and key in ("object_items",): continue
            if val is None: val = "(null)"
            self._labeled_row(frame, node, key, label, val, key in editable)
        cs = node.props.get("create_string","")
        if cs and cs != "(null)": self._show_cs(frame, cs)

    def _view_location_qtx(self, node):
        self._header(node, "\U0001f4cd Location")
        _, frame = self._scrollable()
        for key, label in [("id","ID"),("iid","IID"),("marker","Marker"),
                            ("sector","Sector"),("x","X"),("y","Y")]:
            val = node.props.get(key, "(null)")
            self._labeled_row(frame, node, key, label, val, False)
        if node.children:
            tk.Frame(frame, bg=FG_DIM, height=1).pack(fill="x", pady=(10,6), padx=8)
            tk.Label(frame, text=f"\U0001f464 {len(node.children)} NPCs",
                     font=("Segoe UI",self.font_size-1), bg=BG, fg=BLUE).pack(anchor="w", padx=12)

    def _view_quest_qtx(self, node):
        fs = self.font_size
        self._header(node, "\U0001f4dc Quest")
        _, frame = self._scrollable()
        for key, label in [("id","ID"),("group","Group"),("iid","IID"),
                            ("guild","Guild"),("min_rep","Min Rep"),("add_to_log","Quest Log")]:
            val = node.props.get(key, "(null)")
            ed = key in ("group","guild","min_rep","add_to_log")
            self._labeled_row(frame, node, key, label, val, ed)
        if node.children:
            tk.Frame(frame, bg=FG_DIM, height=1).pack(fill="x", pady=(10,6), padx=8)
            counts = {}
            for c in node.children:
                k = c.node_type.replace("QTX_",""); counts[k] = counts.get(k,0)+1
            colors = {"ACTION":ACCENT,"FC":BLUE,"AOQ":YELLOW,"REWARD":GREEN,"GIVER":ORANGE}
            sf = tk.Frame(frame, bg=BG); sf.pack(fill="x", padx=12, pady=(0,8))
            for k, v in counts.items():
                tk.Label(sf, text=f"{v} {k}", font=("Segoe UI",fs-1,"bold"),
                         bg=BG, fg=colors.get(k,FG_DIM)).pack(side="left", padx=(0,12))
            for child in node.children:
                raw = child.props.get("raw", child.raw_line)
                color = colors.get(child.node_type.replace("QTX_",""), FG)
                sub_f = tk.Frame(frame, bg=BG); sub_f.pack(fill="x", padx=12, pady=1)
                kw = raw.split(" ",1)[0]
                tk.Label(sub_f, text=kw, font=("Consolas",fs-1,"bold"),
                         bg=BG, fg=color, width=8, anchor="e").pack(side="left")
                var = tk.StringVar(value=raw)
                e = tk.Entry(sub_f, textvariable=var, font=("Consolas",fs-1),
                            bg=CARD_BG, fg=FG, insertbackground=FG, relief="flat")
                e.pack(side="left", fill="x", expand=True, padx=(6,0), ipady=2)
                e.bind("<KeyRelease>", lambda ev, n=child, v=var: self._edit_qtx_raw(n, v))

    def _view_quest_sub(self, node):
        kw = node.node_type.replace("QTX_","")
        icon = ICONS.get(node.node_type, "\u2022")
        self._header(node, f"{icon} {kw}")
        _, frame = self._scrollable()
        for key, val in node.props.items():
            if key == "raw" or val is None: continue
            self._labeled_row(frame, node, key, key, val, False)
        tk.Frame(frame, bg=FG_DIM, height=1).pack(fill="x", pady=(10,6), padx=8)
        tk.Label(frame, text="Raw line:", font=("Segoe UI",self.font_size-1,"bold"),
                 bg=BG, fg=YELLOW).pack(anchor="w", padx=12)
        var = tk.StringVar(value=node.props.get("raw",""))
        e = tk.Entry(frame, textvariable=var, font=("Consolas",self.font_size-1),
                    bg=CARD_BG, fg=FG, insertbackground=FG, relief="flat")
        e.pack(fill="x", padx=12, ipady=4)
        e.bind("<KeyRelease>", lambda ev, n=node, v=var: self._edit_qtx_raw(n, v))

    def _view_shf_dialog(self, node):
        fs = self.font_size
        self._header(node, "\U0001f4ad Dialog Text (read-only)")
        _, frame = self._scrollable()
        text = node.props.get("text") or ""
        obj_id = node.props.get("obj_id","")
        if obj_id:
            row = tk.Frame(frame, bg=BG); row.pack(fill="x", padx=8, pady=2)
            tk.Label(row, text="Object ID", font=("Segoe UI",fs-1,"bold"),
                     bg=BG, fg=FG_DIM, width=14, anchor="e").pack(side="left")
            tk.Label(row, text=obj_id, font=("Consolas",fs-1),
                     bg=BG, fg=FG).pack(side="left", padx=(6,0))
        if text:
            tk.Frame(frame, bg=FG_DIM, height=1).pack(fill="x", pady=(8,6), padx=8)
            txt_w = tk.Text(frame, font=("Segoe UI",fs), bg=CARD_BG, fg=FG,
                            wrap="word", relief="flat", padx=10, pady=10,
                            borderwidth=0, highlightthickness=0, state="normal")
            txt_w.insert("1.0", text)
            txt_w.config(state="disabled")
            nl = text.count("\n") + 1 + max(0, len(text)//60)
            txt_w.config(height=min(20, max(3, nl)))
            txt_w.pack(fill="x", padx=12, pady=4)

    def _view_shf_root(self, node):
        fs = self.font_size
        self._header(node, "\U0001f3ae SHF File")
        _, frame = self._scrollable()
        tk.Label(frame, text="Read-only (.NET BinaryFormatter)",
                 font=("Segoe UI",fs,"bold"), bg=BG, fg=RED).pack(anchor="w", padx=12, pady=(8,4))
        tk.Label(frame, text="Use WhizzEdit to export as .idx for full editing.",
                 font=("Segoe UI",fs-1), bg=BG, fg=FG_DIM).pack(anchor="w", padx=12)
        for key, val in node.props.items():
            if key == "info": continue
            row = tk.Frame(frame, bg=BG); row.pack(fill="x", padx=8, pady=2)
            tk.Label(row, text=key, font=("Segoe UI",fs-1,"bold"),
                     bg=BG, fg=FG_DIM, width=14, anchor="e").pack(side="left")
            tk.Label(row, text=val, font=("Consolas",fs-1),
                     bg=BG, fg=GREEN).pack(side="left", padx=(6,0))

    def _view_generic(self, node):
        icon = ICONS.get(node.node_type, "\u2022")
        label = node.node_type.replace("Node","").replace("QTX_","").replace("SHF_","")
        self._header(node, f"{icon} {label}")
        _, frame = self._scrollable()
        for k, v in node.props.items():
            if k not in HIDDEN_FIELDS and v is not None:
                ed = self.file_type != "shf"
                self._prop_row(frame, node, k, v, editable=ed)

    # ============================================================
    # SHARED UI
    # ============================================================
    def _header(self, node, prefix):
        fs = self.font_size
        h = tk.Frame(self.detail, bg=BG3, padx=12, pady=8); h.pack(fill="x")
        name = node.name or node.props.get("iid","") or node.props.get("id","")
        tk.Label(h, text=f"{prefix}:  {name}",
                 font=("Segoe UI",fs+1,"bold"), bg=BG3, fg=FG).pack(anchor="w")
        txt = node.props.get("text") or ""
        if txt and txt != name and len(txt) < 200:
            tk.Label(h, text=txt, font=("Segoe UI",fs-1), bg=BG3, fg=FG_DIM).pack(anchor="w")

    def _scrollable(self):
        canvas = tk.Canvas(self.detail, bg=BG, highlightthickness=0)
        vsb = tk.Scrollbar(self.detail, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg=BG)
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=frame, anchor="nw", tags="inn")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig("inn", width=e.width-20))
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y"); canvas.pack(side="left", fill="both", expand=True)
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        return canvas, frame

    def _labeled_row(self, parent, node, key, label, value, editable):
        fs = self.font_size
        row = tk.Frame(parent, bg=BG); row.pack(fill="x", padx=8, pady=2)
        tk.Label(row, text=label, font=("Segoe UI",fs-1,"bold"),
                 bg=BG, fg=FG_DIM, width=14, anchor="e").pack(side="left")
        if editable and self.file_type != "shf":
            var = tk.StringVar(value=str(value))
            e = tk.Entry(row, textvariable=var, font=("Consolas",fs-1),
                        bg=CARD_BG, fg=FG, insertbackground=FG, relief="flat")
            e.pack(side="left", fill="x", expand=True, padx=(6,0), ipady=3)
            e.bind("<KeyRelease>", lambda ev, n=node, k=key, v=var: self._edit_qtx_prop(n, k, v))
        else:
            tk.Label(row, text=str(value), font=("Consolas",fs-1),
                     bg=BG, fg=FG, anchor="w", wraplength=480).pack(side="left", padx=(6,0))

    def _show_props(self, frame, node, priority, editable=False):
        edit_fields = {"text","name","notes","create_string","sector","angle",
                    "party","guild","lector","activation","min_reputation",
                    "exp","exp_level","random_stuff","remove_from_map",
                    "can_be_failed","add_to_quest_log","quest_state","marker","rumors_dialog"}
        shown = set()
        for k in priority:
            v = node.props.get(k)
            if v is not None and k not in HIDDEN_FIELDS:
                self._prop_row(frame, node, k, v, editable=(editable and k in edit_fields))
                shown.add(k)
        for k, v in node.props.items():
            if k not in shown and k not in HIDDEN_FIELDS and v is not None:
                self._prop_row(frame, node, k, v, editable=(editable and k in edit_fields))

    def _prop_row(self, parent, node, key, value, editable=False):
        fs = self.font_size
        row = tk.Frame(parent, bg=BG); row.pack(fill="x", padx=8, pady=2)
        tk.Label(row, text=key, font=("Segoe UI",fs-1,"bold"),
                 bg=BG, fg=FG_DIM, width=18, anchor="e").pack(side="left")
        if editable:
            var = tk.StringVar(value=str(value))
            e = tk.Entry(row, textvariable=var, font=("Consolas",fs-1),
                        bg=CARD_BG, fg=FG, insertbackground=FG, relief="flat")
            e.pack(side="left", fill="x", expand=True, padx=(6,0), ipady=3)
            e.bind("<KeyRelease>", lambda ev, n=node, k=key, v=var: self._edit_idx_prop(n, k, v))
        else:
            tk.Label(row, text=str(value), font=("Consolas",fs-1),
                     bg=BG, fg=FG, anchor="w", wraplength=480).pack(side="left", padx=(6,0))

    def _show_cs(self, frame, cs):
        fs = self.font_size
        tk.Frame(frame, bg=FG_DIM, height=1).pack(fill="x", pady=(10,6), padx=8)
        tk.Label(frame, text="Create String:", font=("Segoe UI",fs,"bold"),
                 bg=BG, fg=YELLOW).pack(anchor="w", padx=12)
        if "#" in cs: model, equip = cs.split("#",1)
        else: model, equip = cs, ""
        m = re.match(r"(\w+)\((\d+)\)", model)
        items = [("Model", m.group(1) if m else model)]
        if m: items.append(("Level", m.group(2)))
        if equip:
            for n, p in re.findall(r"(\w+)\(([^)]+)\)", equip):
                items.append(("Equip", f"{n} ({p})"))
        for lbl, val in items:
            r = tk.Frame(frame, bg=BG); r.pack(fill="x", padx=18, pady=1)
            tk.Label(r, text=lbl, font=("Segoe UI",fs-1,"bold"),
                     bg=BG, fg=FG_DIM, width=10, anchor="e").pack(side="left")
            tk.Label(r, text=val, font=("Consolas",fs-1),
                     bg=BG, fg=GREEN).pack(side="left", padx=(6,0))

    # ============================================================
    # EDITING
    # ============================================================
    def _edit_idx_text(self, node, widget):
        new = widget.get("1.0","end-1c")
        if new != node.props.get("text") or "":
            node.props["text"] = new; self._update_xml(node, "text", new); self.modified = True
    def _edit_idx_prop(self, node, key, var):
        new = var.get()
        if new != node.props.get(key,""):
            node.props[key] = new
            self._update_xml(node, "n" if key == "name" else key, new); self.modified = True
    def _update_xml(self, node, tag, value):
        elem = node.element
        if elem is None: return
        for child in elem:
            if _strip(child.tag) == tag: child.text = value; return
    def _edit_qtx_prop(self, node, key, var):
        new = var.get()
        if new != node.props.get(key,""):
            node.props[key] = new if new != "(null)" else None; self.modified = True
    def _edit_qtx_raw(self, node, var):
        new = var.get()
        if new != node.props.get("raw",""):
            node.props["raw"] = new; node.raw_line = new; self.modified = True

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    App().run()
