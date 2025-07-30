import tkinter as tk
from tkinter import filedialog
import zipfile, os, shutil, xml.etree.ElementTree as ET, json, re, glob
from datetime import datetime

print("LOADED:", __file__)


# ── helper: copy thumbnail out of a .slx ──────────────────
def extract_thumbnail(slx_path: str, out_png: str) -> bool:
    """
    Copy the first PNG stored under *metadata/* inside the .slx.
    Works for …/thumbnail.png or …/preview.png anywhere in the archive.
    Returns True if an image was extracted.
    """
    with zipfile.ZipFile(slx_path) as zf:
        candidates = [
            name for name in zf.namelist()
            if "metadata/" in name.lower()          # ← no leading slash
            and name.lower().endswith(".png")
            and ("thumb" in name.lower() or "preview" in name.lower())
        ]

        if not candidates:
            return False                            # model has no preview

        data = zf.read(candidates[0])               # grab the first match

    with open(out_png, "wb") as fp:
        fp.write(data)
    return True

def new_run_dir(prefix):
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    path = f"{prefix}{ts}"
    os.makedirs(path, exist_ok=True)
    return path          # absolute or relative is fine



# ── hide purely graphical parameters in the report ───────
IGNORED_PARMS = {"Position", "ZOrder", "SampleTime",
                 "Floating", "ContentPreviewEnabled", "ScopeSpecificationString"}

def cleaned(params: dict) -> dict:
    """Return copy without visual-only keys."""
    return {k: v for k, v in params.items() if k not in IGNORED_PARMS}

# ── tiny GUI file-picker ─────────────────────────────────
def select_slx_file(title="Choose a Simulink .slx file"):
    root = tk.Tk(); root.withdraw()
    return filedialog.askopenfilename(title=title,
                                      filetypes=[("Simulink Model", "*.slx")])

# ── extract every block & connection ─────────────────────
def extract_blocks_and_lines_from_slx(slx_path):
    zip_path = slx_path.replace(".slx", ".zip")
    shutil.copy(slx_path, zip_path)

    work = "temp_unpacked"
    if os.path.exists(work): shutil.rmtree(work)
    os.makedirs(work)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(work)
    os.remove(zip_path)

    root_dir = os.path.join(work, "simulink", "systems")
    root_xml = os.path.join(root_dir, "system_root.xml")
    if not os.path.exists(root_xml):
        raise FileNotFoundError("system_root.xml not found")

    blocks, lines, sid_to_path = {}, [], {}

    # ---- helpers ---------------------------------------------------------
    def walk_blocks(elem, prefix=""):
        for blk in elem.findall("./Block") + elem.findall("./Blocks/Block"):
            name  = blk.get("Name", "Unnamed")
            btype = blk.get("BlockType")
            sid   = str(blk.get("SID"))
            path  = f"{prefix}/{name}" if prefix else name
            sid_to_path[sid] = path
            params = {p.get("Name"): p.text for p in blk.iter("P")}
            blocks[path] = {"BlockType": btype, "SID": sid, "Parameters": params}
            inner = blk.find("System")
            if inner is not None:
                walk_blocks(inner, path)

    def harvest_lines(elem):
        for ln in elem.findall("./Line") + elem.findall("./Lines/Line"):
            # --- source ----------------------------------------------------
            src = ln.find("Src")
            if src is None:                                  # old P-style
                s_txt = next((p.text for p in ln.findall("P")
                               if p.get("Name") == "Src"), "")
                if "#" not in s_txt or ":" not in s_txt:
                    continue
                src_sid, src_port = s_txt.split("#")[0], s_txt.split(":")[1]
                dst_nodes = [p for p in ln.findall("P") if p.get("Name") == "Dst"]
            else:                                            # new style
                src_sid, src_port = src.get("Block"), src.get("Port")
                dst_nodes = ln.findall("Dst")

            # --- destinations ---------------------------------------------
            for dst in dst_nodes:
                if dst.tag == "Dst":                         # new style
                    dst_sid, dst_port = dst.get("Block"), dst.get("Port")
                else:                                        # old P-style
                    txt = dst.text or ""
                    if "#" not in txt or ":" not in txt:
                        continue
                    dst_sid, dst_port = txt.split("#")[0], txt.split(":")[1]

                lines.append({
                    "SrcBlock": sid_to_path.get(src_sid, f"[Unknown SID {src_sid}]"),
                    "SrcPort":  src_port,
                    "DstBlock": sid_to_path.get(dst_sid, f"[Unknown SID {dst_sid}]"),
                    "DstPort":  dst_port,
                })

    # ---- root & every subsystem xml -------------------------------------
    root_tree = ET.parse(root_xml)
    walk_blocks(root_tree.getroot()); harvest_lines(root_tree.getroot())

    for fpath in glob.glob(os.path.join(root_dir, "**", "system_*.xml"),
                           recursive=True):
        if fpath.endswith("system_root.xml"): continue
        fname     = os.path.basename(fpath)
        sys_elem  = ET.parse(fpath).getroot()

        parent_sid = (sys_elem.get("ParentSID") or sys_elem.get("BlockSID") or
                      sys_elem.get("Parent")    or sys_elem.get("ParentBlockSID") or
                      sys_elem.get("SID"))
        if str(parent_sid) not in sid_to_path:
            m = re.search(r"system_(\d+)", fname)
            if m: parent_sid = m.group(1)

        walk_blocks(sys_elem, sid_to_path.get(str(parent_sid), ""))
        harvest_lines(sys_elem)

    return blocks, lines, work

## ── baseline creator ------------------------------------------------------
def create_baseline():
    ## print("DEBUG cwd =", os.getcwd())
    run_dir = new_run_dir("baseline_")
   ## print("DEBUG made", run_dir, "exists?", os.path.exists(run_dir))

    print("📁 Select a Simulink model to create a baseline")
    slx = select_slx_file();  print()
    if not slx:
        return

    # unpack & analyse
    blocks, lines, temp_dir = extract_blocks_and_lines_from_slx(slx)

    # ---------- root-level artefacts (needed later by compare)
    with open("baseline.json", "w") as fp:
        json.dump({"blocks": [{"Name": n, **d} for n, d in blocks.items()],
                   "lines": lines}, fp, indent=2)

    thumb_src = os.path.join(temp_dir, "metadata", "thumbnail.png")
    if os.path.exists(thumb_src):
        shutil.copy(thumb_src, "baseline_thumb.png")

    # ---------- history folder for this run
    run_dir = new_run_dir("baseline_")            # e.g. baseline_2025-07-29_15-31
    if os.path.exists(thumb_src):
        shutil.copy(thumb_src,
                    os.path.join(run_dir, "baseline_thumb.png"))
    with open(os.path.join(run_dir, "baseline.json"), "w") as fp:
        json.dump({"blocks": [{"Name": n, **d} for n, d in blocks.items()],
                   "lines": lines}, fp, indent=2)

    print(f"✅ Baseline saved — {len(blocks)} blocks, {len(lines)} wires\n"
          f"   Root          : baseline.json  (+ baseline_thumb.png)\n"
          f"   History folder: {run_dir}/")
    
# ── baseline comparer ------------------------------------------------------
def compare_to_baseline():
    if not os.path.exists("baseline.json"):
        print("❌ baseline.json not found – run option 1 first."); return

    print("📁 Select the model to compare to the baseline")
    slx = select_slx_file(); print()
    if not slx:
        return

    # new run folder (e.g. report_2025-07-29_14-22)
    run_dir = new_run_dir("report_")

    # ------------------------------------------------ thumbnail handling
    # copy baseline thumbnail into run folder (if we have one)
    if os.path.exists("baseline_thumb.png"):
        shutil.copy("baseline_thumb.png",
                    os.path.join(run_dir, "baseline_thumb.png"))

    # extract blocks + wires and get the temp-unpacked path
    new_blocks, new_lines, temp_dir = extract_blocks_and_lines_from_slx(slx)

    # copy new thumbnail from the temp folder
    src = os.path.join(temp_dir, "metadata", "thumbnail.png")
    if os.path.exists(src):
        shutil.copy(src, os.path.join(run_dir, "new_thumb.png"))

    # ------------------------------------------------ load baseline data
    with open("baseline.json") as fp:
        base = json.load(fp)
    base_blocks = {b["Name"]: b for b in base["blocks"]}
    base_lines  = base["lines"]

    # ------------------------------------------------ diff (unchanged code)
    added, removed, changed, unchanged = [], [], [], []
    for name, nb in new_blocks.items():
        if name not in base_blocks:
            added.append({**nb, "Name": name})
        else:
            ob = base_blocks[name]
            if ob["BlockType"] != nb["BlockType"] or ob["Parameters"] != nb["Parameters"]:
                changed.append((ob, {**nb, "Name": name}))
            else:
                unchanged.append({**nb, "Name": name})
    for name in base_blocks:
        if name not in new_blocks:
            removed.append(base_blocks[name])

    new_set  = {json.dumps(l, sort_keys=True) for l in new_lines}
    base_set = {json.dumps(l, sort_keys=True) for l in base_lines}
    added_raw   = [json.loads(x) for x in new_set - base_set]
    removed_raw = [json.loads(x) for x in base_set - new_set]

    modified, still_added, still_removed = [], [], []
    for rem in removed_raw:
        match = next((ad for ad in added_raw
                      if ad["SrcBlock"] == rem["SrcBlock"] and
                         ad["SrcPort"] == rem["SrcPort"]), None)
        if match:
            modified.append((rem, match)); added_raw.remove(match)
        else:
            still_removed.append(rem)
    still_added = added_raw

    # ------------------------------------------------ write report
    report_path = os.path.join(
        run_dir,
        f"change_report_{datetime.now():%Y-%m-%d_%H-%M}.md"
    )
    with open(report_path, "w") as f:
        f.write("> **Tip:** open this file in a Markdown viewer "
            "(e.g. VS Code: **Ctrl+Shift+V** / right-click → *Open Preview*) "
            "to see the images below.\n\n")
        f.write(f"# Simulink Change Report ({datetime.now():%Y-%m-%d at %H:%M})\n\n")

        # thumbnails (only if both copies exist in *this* folder)
        if (os.path.exists(os.path.join(run_dir, "baseline_thumb.png")) and
            os.path.exists(os.path.join(run_dir, "new_thumb.png"))):
            f.write("## 📷 Model thumbnails\n\n")
            f.write("| Baseline | New |\n|----------|-----|\n")
            f.write("| ![baseline](baseline_thumb.png) | "
                    "![new](new_thumb.png) |\n\n")

        # ---- Added blocks
        if added:
            f.write("## ➕ Added Blocks\n")
            for b in added:
                kept = cleaned(b["Parameters"])
                line = f"- `{b['BlockType']}` **{b['Name']}** (SID {b['SID']})"
                if kept: line += f": `{kept}`"
                f.write(line + "\n")
            f.write("\n")

        # ---- Removed blocks
        if removed:
            f.write("## ❌ Removed Blocks\n")
            for b in removed:
                kept = cleaned(b["Parameters"])
                line = f"- `{b['BlockType']}` **{b['Name']}** (SID {b['SID']})"
                if kept: line += f": `{kept}`"
                f.write(line + "\n")
            f.write("\n")

        # ---- Changed blocks
        if changed:
            f.write("## 🔁 Changed Blocks\n")
            for old, new in changed:
                f.write(f"- `{old['BlockType']}` **{old['Name']}** "
                        f"(SID {old['SID']}) changed:\n")
                old_p = cleaned(old["Parameters"]); new_p = cleaned(new["Parameters"])
                for k in sorted(set(old_p)|set(new_p)):
                    if old_p.get(k) != new_p.get(k):
                        f.write(f"    - `{k}`: `{old_p.get(k,'<none>')}` → "
                                f"`{new_p.get(k,'<none>')}`\n")
            f.write("\n")

        # ---- Connection diff
        if still_added or still_removed or modified:
            f.write("## 🔀 Connection Changes\n")
            if still_added:
                f.write("### ➕ Added Lines\n")
                for l in still_added:
                    f.write(f"- `{l['SrcBlock']}` (Port {l['SrcPort']}) "
                    f"→ `{l['DstBlock']}` (Port {l['DstPort']})\n")
            if still_removed:
                f.write("### ❌ Removed Lines\n")
                for l in still_removed:
                     f.write(f"- `{l['SrcBlock']}` (Port {l['SrcPort']}) "
                     f"→ `{l['DstBlock']}` (Port {l['DstPort']})\n")
            if modified:
                f.write("### 🔁 Modified Lines\n")
                for o,n in modified:
                    f.write(f"- Src `{o['SrcBlock']}` Port {o['SrcPort']}:\n"
                            f"    - Old dst → `{o['DstBlock']}` Port {o['DstPort']}\n"
                            f"    - New dst → `{n['DstBlock']}` Port {n['DstPort']}\n")
            f.write("\n")

        # ---- Unchanged
        if unchanged:
            f.write("## ✅ Unchanged Blocks\n")
            for b in unchanged:
                kept = cleaned(b["Parameters"])
                line = f"- `{b['BlockType']}` **{b['Name']}** (SID {b['SID']})"
                if kept: line += f": `{kept}`"
                f.write(line + "\n")

    print(f"📄 Report (and images) saved in →  {run_dir}/")


# ── CLI menu ─────────────────────────────────────────
if __name__ == "__main__":
    while True:
        print("\n📊 Simulink Change Tracker")
        print("1. Create a new baseline")
        print("2. Compare to existing baseline")
        print("3. Exit")
        try:
            choice = input("Select an option (1–3): ").strip()
        except KeyboardInterrupt:
            print("\n🔄  Restarting menu…"); continue
        except EOFError:
            print("\n👋 Exiting."); break

        if choice == "1":
            create_baseline()
        elif choice == "2":
            compare_to_baseline()
        elif choice == "3":
            print("👋 Exiting."); break
        else:
            print("❌ Invalid input. Please choose 1, 2, or 3.")
