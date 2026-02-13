#!/usr/bin/env python3
"""TW1 LAN Viewer v1.1 — View Two Worlds 1 language files (.lan)
Full format: Translation Entries + Alias Entries + Quest Entries (dialog trees)"""
import struct, os, sys, re, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import OrderedDict

# Theme
BG = "#1e1e2e"; BG2 = "#252536"; BG3 = "#2a2a3d"; BG4 = "#32324a"
FG = "#e0e0e0"; FG_DIM = "#888899"; GREEN = "#50fa7b"; BLUE = "#6272a4"
ORANGE = "#ffb86c"; RED = "#ff5555"; CYAN = "#8be9fd"; PINK = "#ff79c6"
YELLOW = "#f1fa8c"; PURPLE = "#bd93f9"

CATEGORIES = OrderedDict([
    ("DQ_",       ("Dialogs",      "\U0001f4ac", CYAN)),
    ("Q_",        ("Quests",       "\U0001f4dc", GREEN)),
    ("NPCName",   ("NPC Names",    "\U0001f464", ORANGE)),
    ("NPC_",      ("NPC Refs",     "\U0001f465", ORANGE)),
    ("RUMORS_",   ("Rumors",       "\U0001f4e2", YELLOW)),
    ("TALK_",     ("Casual Talks", "\U0001f5e3", BLUE)),
    ("EVENT_",    ("Events",       "\u26a1",     RED)),
    ("CUTSCENE_", ("Cutscenes",    "\U0001f3ac", PINK)),
    ("Citizen_",  ("Citizens",     "\U0001f3d8", FG_DIM)),
    ("Guard_",    ("Guards",       "\U0001f6e1", FG_DIM)),
    ("QITEM_",    ("Quest Items",  "\U0001f4e6", PURPLE)),
    ("ING_",      ("Ingredients",  "\U0001f9ea", PURPLE)),
    ("WP_",       ("Weapons",      "\u2694",     RED)),
    ("AR_",       ("Armor",        "\U0001f6e1", BLUE)),
    ("Tip_",      ("Tips",         "\U0001f4a1", YELLOW)),
    ("Net_",      ("Network",      "\U0001f310", FG_DIM)),
    ("Skill",     ("Skills",       "\u2728",     CYAN)),
])

# ============================================================
# LAN PARSER — Full Format (BugLord spec)
# ============================================================
def _read_dstr(data, pos):
    sl = struct.unpack_from("<I", data, pos)[0]; pos += 4
    s = data[pos:pos+sl].decode("ascii", errors="replace"); pos += sl
    return s, pos

def _read_dstr2(data, pos):
    sl = struct.unpack_from("<I", data, pos)[0]; pos += 4
    s = data[pos:pos+sl*2].decode("utf-16-le", errors="replace"); pos += sl*2
    return s, pos

def _read_arr_pad_int32(data, pos):
    count = struct.unpack_from("<I", data, pos)[0]; pos += 4
    pos += 4  # padding
    vals = []
    for _ in range(count):
        vals.append(struct.unpack_from("<i", data, pos)[0]); pos += 4
    return vals, pos

def parse_lan(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
    if data[:4] != b"LAN\x00":
        raise ValueError("Not a valid LAN file (missing LAN\\0 header)")
    version = struct.unpack_from("<I", data, 4)[0]
    pos = 8
    tr_count = struct.unpack_from("<I", data, pos)[0]; pos += 4
    translations = OrderedDict()
    for _ in range(tr_count):
        key, pos = _read_dstr(data, pos)
        val, pos = _read_dstr2(data, pos)
        clean = key[9:] if key.startswith("translate") else key
        translations[clean] = val
    aliases = OrderedDict()
    if pos < len(data) - 4:
        try:
            al_count = struct.unpack_from("<I", data, pos)[0]; pos += 4
            for _ in range(al_count):
                akey, pos = _read_dstr(data, pos)
                aval, pos = _read_dstr(data, pos)
                ck = akey[9:] if akey.startswith("translate") else akey
                cv = aval[9:] if aval.startswith("translate") else aval
                aliases[ck] = cv
        except Exception:
            pass
    quests = OrderedDict()
    if pos < len(data) - 4:
        try:
            q_count = struct.unpack_from("<I", data, pos)[0]; pos += 4
            for _ in range(q_count):
                qid, pos = _read_dstr(data, pos)
                qid_clean = qid[9:] if qid.startswith("translate") else qid
                dialog_count = struct.unpack_from("<I", data, pos)[0]; pos += 4
                pos += 4
                dialogs = []
                for _ in range(dialog_count):
                    lector = struct.unpack_from("<i", data, pos)[0]; pos += 4
                    trans_id, pos = _read_dstr(data, pos)
                    sound_cue, pos = _read_dstr(data, pos)
                    next_dlgs, pos = _read_arr_pad_int32(data, pos)
                    flags = struct.unpack_from("<I", data, pos)[0]; pos += 4
                    cam_angles, pos = _read_arr_pad_int32(data, pos)
                    anim1 = struct.unpack_from("<I", data, pos)[0]; pos += 4
                    anim2 = struct.unpack_from("<I", data, pos)[0]; pos += 4
                    tid_clean = trans_id[9:] if trans_id.startswith("translate") else trans_id
                    dialogs.append({"lector": lector, "trans_id": tid_clean,
                        "sound_cue": sound_cue, "next": next_dlgs,
                        "flags": flags, "cam_angles": cam_angles,
                        "anim1": anim1, "anim2": anim2})
                quests[qid_clean] = dialogs
        except Exception:
            pass
    return version, translations, aliases, quests

def categorize(entries):
    cats = OrderedDict()
    for li in CATEGORIES.values(): cats[li[0]] = []
    cats["Other"] = []
    for key, val in entries.items():
        placed = False
        for prefix, (label, _, _) in CATEGORIES.items():
            if key.startswith(prefix):
                cats[label].append((key, val)); placed = True; break
        if not placed:
            cats["Other"].append((key, val))
    return OrderedDict((k, v) for k, v in cats.items() if v)

def subcategorize_dialogs(items):
    groups = OrderedDict()
    for key, val in items:
        m = re.match(r"^DQ_(\d+)", key)
        qid = f"Q_{m.group(1)}" if m else "Unknown"
        if qid not in groups: groups[qid] = []
        groups[qid].append((key, val))
    return groups

def subcategorize_quests(items):
    groups = OrderedDict()
    for key, val in items:
        m = re.match(r"^Q_(\d+)", key)
        qid = f"Q_{m.group(1)}" if m else key
        if qid not in groups: groups[qid] = []
        groups[qid].append((key, val))
    return groups

# ============================================================
# APP
# ============================================================
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TW1 LAN Viewer v1.1")
        self.root.geometry("1200x750")
        self.root.configure(bg=BG)
        self.root.minsize(800, 500)
        self.font_size = 12
        self.translations = OrderedDict()
        self.aliases = OrderedDict()
        self.quests = OrderedDict()
        self.categories = OrderedDict()
        self.tree_map = {}
        self.compare_translations = None
        self.filepath = None; self.compare_path = None
        self._build_ui(); self._auto_load(); self.root.mainloop()

    def _build_ui(self):
        tb = tk.Frame(self.root, bg=BG2, padx=8, pady=6); tb.pack(fill="x")
        tk.Label(tb, text="TW1 LAN Viewer v1.1", font=("Segoe UI", 12, "bold"),
                 bg=BG2, fg=GREEN).pack(side="left")
        self.status_lbl = tk.Label(tb, text="", font=("Segoe UI", 9), bg=BG2, fg=ORANGE)
        self.status_lbl.pack(side="left", padx=12)
        tk.Button(tb, text="+", width=2, bg=BG3, fg=FG,
                  command=lambda: self._resize(1)).pack(side="right")
        self.fs_lbl = tk.Label(tb, text="12", bg=BG2, fg=FG, font=("Segoe UI", 10))
        self.fs_lbl.pack(side="right", padx=2)
        tk.Button(tb, text="-", width=2, bg=BG3, fg=FG,
                  command=lambda: self._resize(-1)).pack(side="right")
        tk.Button(tb, text="Compare", bg=BG4, fg=CYAN, font=("Segoe UI", 10),
                  bd=0, padx=10, command=self._load_compare).pack(side="right", padx=4)
        tk.Button(tb, text="Load", bg=RED, fg="#fff", font=("Segoe UI", 10, "bold"),
                  bd=0, padx=12, command=self._load_file).pack(side="right", padx=4)
        sb = tk.Frame(self.root, bg=BG2, padx=8, pady=4); sb.pack(fill="x")
        tk.Label(sb, text="Search:", bg=BG2, fg=FG_DIM, font=("Segoe UI", 10)).pack(side="left")
        self.search_var = tk.StringVar()
        se = tk.Entry(sb, textvariable=self.search_var, bg=BG3, fg=FG,
                      insertbackground=FG, font=("Segoe UI", 11), bd=0)
        se.pack(side="left", fill="x", expand=True, padx=6)
        se.bind("<Return>", lambda e: self._search())
        self.search_lbl = tk.Label(sb, text="", bg=BG2, fg=GREEN, font=("Segoe UI", 9))
        self.search_lbl.pack(side="right")
        pw = tk.PanedWindow(self.root, orient="horizontal", bg=BG, sashwidth=4, sashrelief="flat")
        pw.pack(fill="both", expand=True)
        left = tk.Frame(pw, bg=BG); pw.add(left, width=380)
        style = ttk.Style(); style.theme_use("clam")
        style.configure("Dark.Treeview", background=BG, foreground=FG,
                         fieldbackground=BG, font=("Segoe UI", 11), rowheight=26)
        style.map("Dark.Treeview", background=[("selected", BG4)],
                  foreground=[("selected", GREEN)])
        self.tree = ttk.Treeview(left, style="Dark.Treeview", show="tree")
        scr = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scr.set)
        scr.pack(side="right", fill="y"); self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<<TreeviewOpen>>", self._on_expand)
        right = tk.Frame(pw, bg=BG); pw.add(right)
        self.detail = tk.Frame(right, bg=BG); self.detail.pack(fill="both", expand=True)
        self._show_welcome()

    def _resize(self, d):
        self.font_size = max(8, min(20, self.font_size + d))
        self.fs_lbl.config(text=str(self.font_size))
        ttk.Style().configure("Dark.Treeview", font=("Segoe UI", self.font_size-1),
                               rowheight=max(22, self.font_size*2))

    def _auto_load(self):
        d = os.path.dirname(os.path.abspath(__file__))
        for f in os.listdir(d):
            if f.lower().endswith(".lan") and "quest" in f.lower():
                self._do_load(os.path.join(d, f)); return
        for f in os.listdir(d):
            if f.lower().endswith(".lan"):
                self._do_load(os.path.join(d, f)); return

    def _load_file(self):
        p = filedialog.askopenfilename(title="Open LAN file",
            filetypes=[("LAN files", "*.lan"), ("All", "*.*")])
        if p: self._do_load(p)

    def _load_compare(self):
        p = filedialog.askopenfilename(title="Compare LAN file",
            filetypes=[("LAN files", "*.lan"), ("All", "*.*")])
        if not p: return
        try:
            _, tr, _, _ = parse_lan(p)
            self.compare_translations = tr; self.compare_path = p
            self.status_lbl.config(text=self.status_lbl.cget("text") +
                f"  |  \u2194 {os.path.basename(p)}")
        except Exception as e:
            messagebox.showerror("Error", f"Compare failed:\n{e}")

    def _do_load(self, path):
        try:
            self.root.title("TW1 LAN Viewer v1.1 \u2014 Loading...")
            self.root.update()
            ver, tr, al, qu = parse_lan(path)
            self.translations = tr; self.aliases = al; self.quests = qu
            self.filepath = path; self.categories = categorize(tr)
            self._build_tree()
            name = os.path.basename(path)
            td = sum(len(d) for d in qu.values())
            self.root.title(f"TW1 LAN Viewer v1.1 \u2014 {name}")
            parts = [f"v{ver}", f"{len(tr):,} texts", f"{len(al)} aliases",
                     f"{len(qu)} quests", f"{td:,} dialog nodes"]
            self.status_lbl.config(text="  |  ".join(parts))
            self._show_stats()
        except Exception as e:
            messagebox.showerror("Error", f"Load failed:\n{e}")

    # ---- TREE ----
    def _build_tree(self):
        self.tree.delete(*self.tree.get_children()); self.tree_map.clear()
        for cat_name, items in self.categories.items():
            icon = "\U0001f4c1"
            for prefix, (label, ic, _) in CATEGORIES.items():
                if label == cat_name: icon = ic; break
            tid = self.tree.insert("", "end",
                text=f"{icon}  {cat_name}  ({len(items):,})", open=False)
            self.tree_map[tid] = ("__cat__", cat_name)
            if cat_name == "Dialogs":
                groups = subcategorize_dialogs(items)
                for qid, gitems in groups.items():
                    qname = self.translations.get(qid, "")
                    label = f"{qid}: {qname}" if qname else qid
                    stid = self.tree.insert(tid, "end",
                        text=f"\U0001f4dc  {label}  ({len(gitems)})", open=False)
                    self.tree_map[stid] = ("__dq_group__", gitems)
                    if gitems: self.tree.insert(stid, "end", text="...", tags=("placeholder",))
            elif cat_name == "Quests":
                groups = subcategorize_quests(items)
                for qid, gitems in groups.items():
                    qname = ""
                    for k, v in gitems:
                        if "_" not in k[2:]: qname = v; break
                    label = f"{qid}: {qname}" if qname else qid
                    stid = self.tree.insert(tid, "end", text=f"\U0001f4dc  {label}", open=False)
                    self.tree_map[stid] = ("__q_group__", gitems)
                    if len(gitems) > 1: self.tree.insert(stid, "end", text="...", tags=("placeholder",))
            else:
                if items: self.tree.insert(tid, "end", text="...", tags=("placeholder",))
        if self.aliases:
            tid = self.tree.insert("", "end",
                text=f"\U0001f517  Aliases  ({len(self.aliases)})", open=False)
            self.tree_map[tid] = ("__aliases__", None)
            self.tree.insert(tid, "end", text="...", tags=("placeholder",))
        if self.quests:
            td = sum(len(d) for d in self.quests.values())
            tid = self.tree.insert("", "end",
                text=f"\U0001f3ad  Dialog Trees  ({len(self.quests)} quests, {td:,} nodes)", open=False)
            self.tree_map[tid] = ("__quest_trees__", None)
            for qid, dialogs in self.quests.items():
                qname = self.translations.get(qid.replace("DQ_", "Q_"), "")
                label = f"{qid}: {qname}" if qname else qid
                stid = self.tree.insert(tid, "end",
                    text=f"\U0001f4ac  {label}  ({len(dialogs)} nodes)", open=False)
                self.tree_map[stid] = ("__quest_tree__", (qid, dialogs))
                if dialogs: self.tree.insert(stid, "end", text="...", tags=("placeholder",))

    def _on_expand(self, event):
        try:
            tid = self.tree.focus()
            if not tid: return
            ch = self.tree.get_children(tid)
            if len(ch) != 1: return
            if "placeholder" not in self.tree.item(ch[0], "tags"): return
            self.tree.delete(ch[0])
            info = self.tree_map.get(tid)
            if not info: return
            kind, data = info
            if kind == "__cat__":
                for key, val in self.categories.get(data, []):
                    p = val[:70].replace("\n", " ")
                    ctid = self.tree.insert(tid, "end", text=f"  {key}:  {p}")
                    self.tree_map[ctid] = ("__entry__", (key, val))
            elif kind == "__dq_group__":
                for key, val in data:
                    p = val[:60].replace("\n", " ")
                    ctid = self.tree.insert(tid, "end", text=f"  {p}")
                    self.tree_map[ctid] = ("__entry__", (key, val))
            elif kind == "__q_group__":
                for key, val in data:
                    s = key.split("_", 2)[-1] if "_" in key[2:] else ""
                    s = re.sub(r"^\d+_?", "", s) or "Name"
                    p = val[:60].replace("\n", " ")
                    ctid = self.tree.insert(tid, "end", text=f"  [{s}] {p}")
                    self.tree_map[ctid] = ("__entry__", (key, val))
            elif kind == "__aliases__":
                for akey, aval in self.aliases.items():
                    ctid = self.tree.insert(tid, "end", text=f"  {akey}  \u2192  {aval}")
                    self.tree_map[ctid] = ("__alias__", (akey, aval))
            elif kind == "__quest_tree__":
                qid, dialogs = data
                for i, d in enumerate(dialogs):
                    text = self.translations.get(d["trans_id"], "")
                    preview = text[:55].replace("\n", " ") if text else f"[{d['trans_id']}]"
                    speaker = "Hero" if d["lector"] == 1 else f"NPC#{d['lector']}"
                    ctid = self.tree.insert(tid, "end", text=f"  [{i}] {speaker}: {preview}")
                    self.tree_map[ctid] = ("__dialog_node__", (qid, i, d))
        except Exception as e:
            print(f"Expand error: {e}")

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        info = self.tree_map.get(sel[0])
        if not info: return
        try:
            kind, data = info
            if kind == "__cat__": self._show_category(data)
            elif kind == "__dq_group__": self._show_dialog_group(data)
            elif kind == "__q_group__": self._show_quest_group(data)
            elif kind == "__entry__": self._show_entry(*data)
            elif kind == "__alias__": self._show_alias(*data)
            elif kind == "__aliases__": self._show_aliases_overview()
            elif kind == "__quest_trees__": self._show_quest_trees_overview()
            elif kind == "__quest_tree__": self._show_quest_tree(*data)
            elif kind == "__dialog_node__": self._show_dialog_node(*data)
        except Exception as e:
            print(f"View error: {e}"); import traceback; traceback.print_exc()

    # ---- SHARED UI ----
    def _clear(self):
        for w in self.detail.winfo_children(): w.destroy()

    def _scrollable(self):
        canvas = tk.Canvas(self.detail, bg=BG, highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(self.detail, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg=BG)
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); canvas.pack(fill="both", expand=True)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))
        return canvas, frame

    # ---- VIEWS ----
    def _show_welcome(self):
        self._clear()
        fs = self.font_size
        f = tk.Frame(self.detail, bg=BG); f.pack(expand=True)
        tk.Label(f, text="TW1 LAN Viewer", font=("Segoe UI", fs+6, "bold"),
                 bg=BG, fg=FG).pack(pady=(40, 8))
        tk.Label(f, text="Two Worlds 1 Language File Viewer",
                 font=("Segoe UI", fs), bg=BG, fg=FG_DIM).pack()
        tk.Label(f, text="Texts + Aliases + Dialog Trees",
                 font=("Segoe UI", fs-1), bg=BG, fg=CYAN).pack(pady=(4, 20))
        tk.Label(f, text="Load a .lan file or place this script next to one.",
                 font=("Segoe UI", fs-1), bg=BG, fg=FG_DIM).pack()

    def _show_stats(self):
        self._clear()
        fs = self.font_size; _, frame = self._scrollable()
        tk.Label(frame, text="\U0001f4ca  Statistics", font=("Segoe UI", fs+3, "bold"),
                 bg=BG, fg=FG).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Label(frame, text=os.path.basename(self.filepath),
                 font=("Segoe UI", fs), bg=BG, fg=FG_DIM).pack(anchor="w", padx=16)
        td = sum(len(d) for d in self.quests.values())
        sf = tk.Frame(frame, bg=BG); sf.pack(anchor="w", padx=16, pady=(8, 4))
        for lb, vl, cl in [("Texts", f"{len(self.translations):,}", GREEN),
                            ("Aliases", str(len(self.aliases)), BLUE),
                            ("Quests", str(len(self.quests)), ORANGE),
                            ("Dialog Nodes", f"{td:,}", CYAN)]:
            tk.Label(sf, text=f"{lb}: ", font=("Segoe UI", fs-1), bg=BG, fg=FG_DIM).pack(side="left")
            tk.Label(sf, text=vl, font=("Segoe UI", fs-1, "bold"), bg=BG, fg=cl).pack(side="left", padx=(0, 16))
        tk.Frame(frame, bg=FG_DIM, height=1).pack(fill="x", padx=16, pady=8)
        tk.Label(frame, text="Text Categories:", font=("Segoe UI", fs, "bold"),
                 bg=BG, fg=FG).pack(anchor="w", padx=16, pady=(0, 4))
        mx = max((len(v) for v in self.categories.values()), default=1)
        for cn, items in self.categories.items():
            color = FG_DIM
            for prefix, (label, _, c) in CATEGORIES.items():
                if label == cn: color = c; break
            row = tk.Frame(frame, bg=BG); row.pack(fill="x", padx=16, pady=2)
            tk.Label(row, text=cn, font=("Segoe UI", fs-1), bg=BG, fg=FG, width=16, anchor="e").pack(side="left")
            bw = max(4, int(300 * len(items) / mx))
            bar = tk.Frame(row, bg=color, height=18, width=bw)
            bar.pack(side="left", padx=(8, 4)); bar.pack_propagate(False)
            tk.Label(row, text=f"{len(items):,}", font=("Segoe UI", fs-1, "bold"),
                     bg=BG, fg=color).pack(side="left")
        if self.quests:
            tk.Frame(frame, bg=FG_DIM, height=1).pack(fill="x", padx=16, pady=8)
            tk.Label(frame, text="Dialog Tree Stats:", font=("Segoe UI", fs, "bold"),
                     bg=BG, fg=FG).pack(anchor="w", padx=16, pady=(0, 4))
            lectors = set()
            cues = 0
            for dlgs in self.quests.values():
                for d in dlgs:
                    lectors.add(d["lector"])
                    if d["sound_cue"]: cues += 1
            hero = sum(1 for dlgs in self.quests.values() for d in dlgs if d["lector"] == 1)
            npc = td - hero
            tk.Label(frame, text=f"{len(lectors)} speakers  |  Hero: {hero:,}  |  NPC: {npc:,}  |  {cues:,} sound cues",
                     font=("Segoe UI", fs-1), bg=BG, fg=CYAN).pack(anchor="w", padx=16)

    def _show_category(self, cat_name):
        self._clear(); fs = self.font_size
        items = self.categories.get(cat_name, [])
        color = FG_DIM
        for prefix, (label, _, c) in CATEGORIES.items():
            if label == cat_name: color = c; break
        hdr = tk.Frame(self.detail, bg=BG3, padx=12, pady=8); hdr.pack(fill="x")
        tk.Label(hdr, text=cat_name, font=("Segoe UI", fs+2, "bold"), bg=BG3, fg=color).pack(anchor="w")
        tk.Label(hdr, text=f"{len(items):,} entries", font=("Segoe UI", fs-1), bg=BG3, fg=FG_DIM).pack(anchor="w")
        _, frame = self._scrollable()
        for i, (key, val) in enumerate(items[:200]):
            bg = BG2 if i % 2 == 0 else BG
            row = tk.Frame(frame, bg=bg); row.pack(fill="x", padx=8, pady=1)
            tk.Label(row, text=key, font=("Consolas", fs-2), bg=bg, fg=ORANGE, width=30, anchor="w").pack(side="left", padx=4)
            tk.Label(row, text=val[:100].replace("\n", " \u21b5 "), font=("Segoe UI", fs-1),
                     bg=bg, fg=FG, anchor="w").pack(side="left", fill="x", expand=True)
        if len(items) > 200:
            tk.Label(frame, text=f"... +{len(items)-200} more", font=("Segoe UI", fs-1), bg=BG, fg=FG_DIM).pack(pady=8)

    def _show_dialog_group(self, items):
        self._clear(); fs = self.font_size
        if not items: return
        m = re.match(r"^DQ_(\d+)", items[0][0])
        qid = f"Q_{m.group(1)}" if m else "?"
        qname = self.translations.get(qid, "")
        hdr = tk.Frame(self.detail, bg=BG3, padx=12, pady=8); hdr.pack(fill="x")
        tk.Label(hdr, text=f"\U0001f4ac  {qid}: {qname}" if qname else f"\U0001f4ac  {qid}",
                 font=("Segoe UI", fs+1, "bold"), bg=BG3, fg=CYAN).pack(anchor="w")
        tk.Label(hdr, text=f"{len(items)} text entries", font=("Segoe UI", fs-1), bg=BG3, fg=FG_DIM).pack(anchor="w")
        _, frame = self._scrollable()
        for key, val in items:
            sp = key.split(".", 1)[1] if "." in key else ""
            is_hero = any(s in sp for s in ["CLOSE", "QC", "QNS", "QS"])
            bgc = "#1a3a1a" if is_hero else BG3
            fgc = GREEN if is_hero else FG
            speaker = "Hero" if is_hero else "NPC"
            padl, padr = (80, 12) if is_hero else (12, 80)
            bubble = tk.Frame(frame, bg=bgc, padx=10, pady=6)
            bubble.pack(fill="x", padx=(padl, padr), pady=2)
            tk.Label(bubble, text=f"{speaker}  \u2022  {key}", font=("Consolas", fs-3), bg=bgc, fg=FG_DIM).pack(anchor="w")
            tk.Label(bubble, text=val, font=("Segoe UI", fs), bg=bgc, fg=fgc,
                     wraplength=600, justify="left", anchor="w").pack(anchor="w", pady=(2, 0))

    def _show_quest_group(self, items):
        self._clear(); fs = self.font_size
        if not items: return
        qname = ""
        for k, v in items:
            if "_" not in k[2:]: qname = v; break
        m = re.match(r"^Q_(\d+)", items[0][0])
        qid = f"Q_{m.group(1)}" if m else "?"
        hdr = tk.Frame(self.detail, bg=BG3, padx=12, pady=8); hdr.pack(fill="x")
        tk.Label(hdr, text=f"\U0001f4dc  {qid}: {qname}" if qname else f"\U0001f4dc  {qid}",
                 font=("Segoe UI", fs+1, "bold"), bg=BG3, fg=GREEN).pack(anchor="w")
        _, frame = self._scrollable()
        sfx = {"": "Quest Name", "QTD": "Description (Take)", "QSD": "Description (Solve)", "QCD": "Description (Close)"}
        for key, val in items:
            s = key.split("_", 2)[-1] if "_" in key[2:] else ""
            s = re.sub(r"^\d+_?", "", s) or ""
            label = sfx.get(s, s or "Name")
            row = tk.Frame(frame, bg=BG2, padx=10, pady=6); row.pack(fill="x", padx=12, pady=3)
            tk.Label(row, text=label, font=("Segoe UI", fs-1, "bold"), bg=BG2, fg=ORANGE).pack(anchor="w")
            tk.Label(row, text=val, font=("Segoe UI", fs), bg=BG2, fg=FG,
                     wraplength=650, justify="left", anchor="w").pack(anchor="w", pady=(2, 0))

    def _show_entry(self, key, val):
        self._clear(); fs = self.font_size
        hdr = tk.Frame(self.detail, bg=BG3, padx=12, pady=8); hdr.pack(fill="x")
        tk.Label(hdr, text=key, font=("Consolas", fs, "bold"), bg=BG3, fg=ORANGE).pack(anchor="w")
        _, frame = self._scrollable()
        tf = tk.Frame(frame, bg=BG2, padx=12, pady=10); tf.pack(fill="x", padx=12, pady=(12, 4))
        tk.Label(tf, text="Value:", font=("Segoe UI", fs-1, "bold"), bg=BG2, fg=FG_DIM).pack(anchor="w")
        txt = tk.Text(tf, font=("Segoe UI", fs), bg=BG2, fg=FG, wrap="word",
                      height=max(3, val.count("\n")+2), bd=0, highlightthickness=0)
        txt.insert("1.0", val); txt.config(state="disabled"); txt.pack(fill="x", pady=(4, 0))
        for akey, aval in self.aliases.items():
            if akey == key or aval == key:
                af = tk.Frame(frame, bg=BG3, padx=12, pady=6); af.pack(fill="x", padx=12, pady=4)
                tk.Label(af, text=f"\U0001f517  Alias: {akey} \u2192 {aval}",
                         font=("Consolas", fs-2), bg=BG3, fg=BLUE).pack(anchor="w")
        if self.compare_translations:
            cv = self.compare_translations.get(key)
            cf = tk.Frame(frame, bg=BG3, padx=12, pady=10); cf.pack(fill="x", padx=12, pady=4)
            if cv is None:
                tk.Label(cf, text="\u274c  Not in comparison", font=("Segoe UI", fs-1), bg=BG3, fg=RED).pack(anchor="w")
            elif cv == val:
                tk.Label(cf, text="\u2705  Identical", font=("Segoe UI", fs-1), bg=BG3, fg=GREEN).pack(anchor="w")
            else:
                tk.Label(cf, text="\U0001f504  Different:", font=("Segoe UI", fs-1, "bold"), bg=BG3, fg=YELLOW).pack(anchor="w")
                ct = tk.Text(cf, font=("Segoe UI", fs), bg=BG3, fg=YELLOW, wrap="word",
                             height=max(2, cv.count("\n")+2), bd=0, highlightthickness=0)
                ct.insert("1.0", cv); ct.config(state="disabled"); ct.pack(fill="x", pady=(4, 0))
        tk.Label(frame, text=f"Key: translate{key}  |  {len(val)} chars  |  {len(val.split())} words",
                 font=("Consolas", fs-2), bg=BG, fg=FG_DIM).pack(anchor="w", padx=16, pady=8)

    def _show_alias(self, akey, aval):
        self._clear(); fs = self.font_size
        hdr = tk.Frame(self.detail, bg=BG3, padx=12, pady=8); hdr.pack(fill="x")
        tk.Label(hdr, text="\U0001f517  Alias", font=("Segoe UI", fs+1, "bold"), bg=BG3, fg=BLUE).pack(anchor="w")
        _, frame = self._scrollable()
        for label, k, color in [("From:", akey, ORANGE), ("To:", aval, GREEN)]:
            row = tk.Frame(frame, bg=BG2, padx=12, pady=8); row.pack(fill="x", padx=12, pady=4)
            tk.Label(row, text=label, font=("Segoe UI", fs-1, "bold"), bg=BG2, fg=FG_DIM).pack(anchor="w")
            tk.Label(row, text=k, font=("Consolas", fs), bg=BG2, fg=color).pack(anchor="w")
            val = self.translations.get(k, "(no text)")
            tk.Label(row, text=val, font=("Segoe UI", fs-1), bg=BG2, fg=FG,
                     wraplength=600, justify="left").pack(anchor="w", pady=(4, 0))
        tk.Label(frame, text="Alias = same dialog text reused in a different quest state",
                 font=("Segoe UI", fs-2), bg=BG, fg=FG_DIM).pack(pady=8)

    def _show_aliases_overview(self):
        self._clear(); fs = self.font_size
        hdr = tk.Frame(self.detail, bg=BG3, padx=12, pady=8); hdr.pack(fill="x")
        tk.Label(hdr, text=f"\U0001f517  Aliases ({len(self.aliases)})",
                 font=("Segoe UI", fs+2, "bold"), bg=BG3, fg=BLUE).pack(anchor="w")
        tk.Label(hdr, text="Dialog text reuse \u2014 same line in different quest states",
                 font=("Segoe UI", fs-1), bg=BG3, fg=FG_DIM).pack(anchor="w")
        _, frame = self._scrollable()
        for i, (akey, aval) in enumerate(self.aliases.items()):
            bg = BG2 if i % 2 == 0 else BG
            row = tk.Frame(frame, bg=bg); row.pack(fill="x", padx=8, pady=1)
            tk.Label(row, text=akey, font=("Consolas", fs-2), bg=bg, fg=ORANGE, anchor="w").pack(side="left", padx=4)
            tk.Label(row, text="\u2192", font=("Segoe UI", fs-1), bg=bg, fg=BLUE).pack(side="left", padx=4)
            tk.Label(row, text=aval, font=("Consolas", fs-2), bg=bg, fg=GREEN, anchor="w").pack(side="left", padx=4)

    def _show_quest_trees_overview(self):
        self._clear(); fs = self.font_size
        td = sum(len(d) for d in self.quests.values())
        hdr = tk.Frame(self.detail, bg=BG3, padx=12, pady=8); hdr.pack(fill="x")
        tk.Label(hdr, text="\U0001f3ad  Dialog Trees", font=("Segoe UI", fs+2, "bold"), bg=BG3, fg=PINK).pack(anchor="w")
        tk.Label(hdr, text=f"{len(self.quests)} quests with {td:,} dialog nodes",
                 font=("Segoe UI", fs-1), bg=BG3, fg=FG_DIM).pack(anchor="w")
        tk.Label(hdr, text="Speakers, sound cues, branching, cameras, animations",
                 font=("Segoe UI", fs-2), bg=BG3, fg=CYAN).pack(anchor="w")
        _, frame = self._scrollable()
        sq = sorted(self.quests.items(), key=lambda x: len(x[1]), reverse=True)
        tk.Label(frame, text="Top 30 by dialog count:", font=("Segoe UI", fs, "bold"),
                 bg=BG, fg=FG).pack(anchor="w", padx=16, pady=(12, 4))
        mx = len(sq[0][1]) if sq else 1
        for qid, dlgs in sq[:30]:
            qname = self.translations.get(qid.replace("DQ_", "Q_"), "")
            row = tk.Frame(frame, bg=BG); row.pack(fill="x", padx=16, pady=1)
            tk.Label(row, text=qid, font=("Consolas", fs-2), bg=BG, fg=ORANGE, width=12, anchor="e").pack(side="left")
            bw = max(4, int(250 * len(dlgs) / mx))
            bar = tk.Frame(row, bg=CYAN, height=16, width=bw)
            bar.pack(side="left", padx=(8, 4)); bar.pack_propagate(False)
            tk.Label(row, text=str(len(dlgs)), font=("Segoe UI", fs-2, "bold"), bg=BG, fg=CYAN).pack(side="left", padx=(0, 8))
            if qname:
                tk.Label(row, text=qname[:40], font=("Segoe UI", fs-2), bg=BG, fg=FG_DIM).pack(side="left")

    def _show_quest_tree(self, qid, dialogs):
        self._clear(); fs = self.font_size
        qname = self.translations.get(qid.replace("DQ_", "Q_"), "")
        hdr = tk.Frame(self.detail, bg=BG3, padx=12, pady=8); hdr.pack(fill="x")
        title = f"\U0001f3ad  {qid}: {qname}" if qname else f"\U0001f3ad  {qid}"
        tk.Label(hdr, text=title, font=("Segoe UI", fs+1, "bold"), bg=BG3, fg=PINK).pack(anchor="w")
        lectors = set(d["lector"] for d in dialogs)
        cues = sum(1 for d in dialogs if d["sound_cue"])
        tk.Label(hdr, text=f"{len(dialogs)} nodes  |  {len(lectors)} speakers  |  {cues} sound cues",
                 font=("Segoe UI", fs-1), bg=BG3, fg=FG_DIM).pack(anchor="w")
        _, frame = self._scrollable()
        for i, d in enumerate(dialogs):
            text = self.translations.get(d["trans_id"], "")
            is_hero = d["lector"] == 1
            bgc = "#1a3a1a" if is_hero else BG3
            fgc = GREEN if is_hero else FG
            speaker = "Hero" if is_hero else f"Lector #{d['lector']}"
            padl, padr = (80, 12) if is_hero else (12, 80)
            bubble = tk.Frame(frame, bg=bgc, padx=10, pady=6)
            bubble.pack(fill="x", padx=(padl, padr), pady=2)
            meta = [f"[{i}] {speaker}"]
            if d["sound_cue"]: meta.append(f"\U0001f50a {d['sound_cue']}")
            tk.Label(bubble, text="  ".join(meta), font=("Consolas", fs-3), bg=bgc, fg=FG_DIM).pack(anchor="w")
            display = text if text else f"[{d['trans_id']}]"
            tk.Label(bubble, text=display, font=("Segoe UI", fs), bg=bgc, fg=fgc,
                     wraplength=600, justify="left", anchor="w").pack(anchor="w", pady=(2, 0))
            m2 = []
            if d["next"]: m2.append(f"Next: {d['next']}")
            if d["flags"]: m2.append(f"Flags: 0x{d['flags']:04x}")
            if d["cam_angles"]: m2.append(f"Cam: {d['cam_angles']}")
            if d["anim1"]: m2.append(f"Anim: {d['anim1']}")
            if m2:
                tk.Label(bubble, text="  |  ".join(m2), font=("Consolas", fs-3), bg=bgc, fg=FG_DIM).pack(anchor="w", pady=(2, 0))

    def _show_dialog_node(self, qid, idx, d):
        self._clear(); fs = self.font_size
        text = self.translations.get(d["trans_id"], "(no text)")
        is_hero = d["lector"] == 1
        hdr = tk.Frame(self.detail, bg=BG3, padx=12, pady=8); hdr.pack(fill="x")
        speaker = "Hero" if is_hero else f"Lector #{d['lector']}"
        tk.Label(hdr, text=f"\U0001f399  Dialog Node [{idx}]  \u2014  {speaker}",
                 font=("Segoe UI", fs+1, "bold"), bg=BG3, fg=GREEN if is_hero else FG).pack(anchor="w")
        tk.Label(hdr, text=f"Quest: {qid}", font=("Segoe UI", fs-1), bg=BG3, fg=FG_DIM).pack(anchor="w")
        _, frame = self._scrollable()
        tf = tk.Frame(frame, bg="#1a3a1a" if is_hero else BG2, padx=14, pady=12)
        tf.pack(fill="x", padx=12, pady=(12, 4))
        tk.Label(tf, text=text, font=("Segoe UI", fs+1), bg=tf.cget("bg"),
                 fg=GREEN if is_hero else FG, wraplength=650, justify="left", anchor="w").pack(anchor="w")
        props = [
            ("Translation ID", d["trans_id"], ORANGE),
            ("Sound Cue", d["sound_cue"] or "(none)", CYAN if d["sound_cue"] else FG_DIM),
            ("Lector/Speaker", f"{d['lector']}  {'(Hero)' if is_hero else ''}", FG),
            ("Next Dialogs", str(d["next"]) if d["next"] else "(end)", BLUE),
            ("Flags", f"0x{d['flags']:08x}", FG),
            ("Camera Angles", str(d["cam_angles"]) if d["cam_angles"] else "(default)", FG),
            ("Animation 1", str(d["anim1"]), FG),
            ("Animation 2", str(d["anim2"]), FG),
        ]
        for label, val, color in props:
            row = tk.Frame(frame, bg=BG); row.pack(fill="x", padx=16, pady=2)
            tk.Label(row, text=f"{label}:", font=("Segoe UI", fs-1), bg=BG, fg=FG_DIM, width=18, anchor="e").pack(side="left")
            tk.Label(row, text=val, font=("Consolas", fs-1), bg=BG, fg=color).pack(side="left", padx=8)
        if d["next"]:
            tk.Frame(frame, bg=FG_DIM, height=1).pack(fill="x", padx=16, pady=8)
            tk.Label(frame, text="Linked dialog(s):", font=("Segoe UI", fs-1, "bold"), bg=BG, fg=BLUE).pack(anchor="w", padx=16)
            dialogs = self.quests.get(qid, [])
            for ni in d["next"]:
                if 0 <= ni < len(dialogs):
                    nd = dialogs[ni]
                    nt = self.translations.get(nd["trans_id"], "")
                    ns = "Hero" if nd["lector"] == 1 else f"Lector #{nd['lector']}"
                    preview = nt[:80].replace("\n", " ") if nt else f"[{nd['trans_id']}]"
                    nf = tk.Frame(frame, bg=BG2, padx=10, pady=4); nf.pack(fill="x", padx=20, pady=2)
                    tk.Label(nf, text=f"\u2192 [{ni}] {ns}: {preview}",
                             font=("Segoe UI", fs-1), bg=BG2, fg=CYAN).pack(anchor="w")

    # ---- SEARCH ----
    def _search(self):
        q = self.search_var.get().strip().lower()
        if not q or len(q) < 2: self.search_lbl.config(text=""); return
        hits = []
        for key, val in self.translations.items():
            if q in key.lower() or q in val.lower():
                hits.append((key, val))
            if len(hits) >= 200: break
        self.search_lbl.config(text=f"{len(hits)} found")
        if not hits: return
        self._clear(); fs = self.font_size
        hdr = tk.Frame(self.detail, bg=BG3, padx=12, pady=8); hdr.pack(fill="x")
        tk.Label(hdr, text=f"\U0001f50d  \"{q}\"", font=("Segoe UI", fs+1, "bold"), bg=BG3, fg=FG).pack(anchor="w")
        tk.Label(hdr, text=f"{len(hits)} results", font=("Segoe UI", fs-1), bg=BG3, fg=FG_DIM).pack(anchor="w")
        _, frame = self._scrollable()
        for i, (key, val) in enumerate(hits[:200]):
            bg = BG2 if i % 2 == 0 else BG
            row = tk.Frame(frame, bg=bg, padx=10, pady=4); row.pack(fill="x", padx=4, pady=1)
            tk.Label(row, text=key, font=("Consolas", fs-2), bg=bg, fg=ORANGE).pack(anchor="w")
            tk.Label(row, text=val[:200].replace("\n", " \u21b5 "), font=("Segoe UI", fs-1), bg=bg, fg=FG,
                     wraplength=700, justify="left", anchor="w").pack(anchor="w")

if __name__ == "__main__":
    App()
