import tkinter as tk
from tkinter import filedialog
import zipfile
import os
import shutil
import xml.etree.ElementTree as ET
import json
from datetime import datetime

def select_slx_file(title="Choose a Simulink .slx file"):
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(title=title, filetypes=[("Simulink Model", "*.slx")])
    return path

def extract_blocks_from_slx(slx_path):
    zip_path = slx_path.replace(".slx", ".zip")
    shutil.copy(slx_path, zip_path)

    unzip_folder = "temp_unpacked"
    if os.path.exists(unzip_folder):
        shutil.rmtree(unzip_folder)
    os.makedirs(unzip_folder)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(unzip_folder)
    os.remove(zip_path)

    xml_path = os.path.join(unzip_folder, "simulink", "systems", "system_root.xml")
    if not os.path.exists(xml_path):
        raise FileNotFoundError("system_root.xml not found.")

    tree = ET.parse(xml_path)
    root_xml = tree.getroot()

    blocks = {}
    for block in root_xml.iter("Block"):
        name = block.attrib.get("Name", "Unnamed")
        block_type = block.attrib.get("BlockType")
        sid = block.attrib.get("SID")
        params = {p.attrib["Name"]: p.text for p in block.iter("P")}
        blocks[name] = {
            "BlockType": block_type,
            "SID": sid,
            "Parameters": params
        }
    return blocks

def create_baseline():
    print("📁 Select a Simulink model to create a baseline")
    slx_path = select_slx_file()
    if not slx_path:
        print("❌ No file selected.")
        return
    blocks = extract_blocks_from_slx(slx_path)
    baseline = [{"Name": name, **data} for name, data in blocks.items()]
    with open("baseline.json", "w") as f:
        json.dump(baseline, f, indent=2)
    print(f"✅ Baseline saved with {len(baseline)} blocks to baseline.json")

def compare_to_baseline():
    if not os.path.exists("baseline.json"):
        print("❌ No baseline.json found. Create a baseline first.")
        return

    print("📁 Select a Simulink model to compare to the baseline")
    slx_path = select_slx_file()
    if not slx_path:
        print("❌ No file selected.")
        return

    with open("baseline.json") as f:
        baseline_blocks = json.load(f)
    baseline_dict = {b["Name"]: b for b in baseline_blocks}

    new_blocks = extract_blocks_from_slx(slx_path)

    added, removed, changed, unchanged = [], [], [], []

    for name, new_block in new_blocks.items():
        if name not in baseline_dict:
            added.append(new_block)
        else:
            old = baseline_dict[name]
            if old["BlockType"] != new_block["BlockType"] or old["Parameters"] != new_block["Parameters"]:
                changed.append((old, new_block))
            else:
                unchanged.append(new_block)

    for name in baseline_dict:
        if name not in new_blocks:
            removed.append(baseline_dict[name])

    timestamp_file = datetime.now().strftime("%Y-%m-%d_%H-%M")
    timestamp_text = datetime.now().strftime("%Y-%m-%d at %H:%M")
    report_name = f"change_report_{timestamp_file}.md"

    with open(report_name, "w") as f:
        f.write(f"# Simulink Change Report ({timestamp_text})\n\n")

        if added:
            f.write("## ➕ Added Blocks\n")
            for b in added:
                f.write(f"- `{b['BlockType']}` block **{b['SID']}**: `{b['Parameters']}`\n")
            f.write("\n")

        if removed:
            f.write("## ❌ Removed Blocks\n")
            for b in removed:
                f.write(f"- `{b['BlockType']}` block **{b['SID']}**: `{b['Parameters']}`\n")
            f.write("\n")

        if changed:
            f.write("## 🔁 Changed Blocks\n")
            for old, new in changed:
                f.write(f"- `{old['BlockType']}` block **{old['SID']}**: parameters changed\n")
                all_keys = set(old["Parameters"].keys()).union(new["Parameters"].keys())
                for key in sorted(all_keys):
                    old_val = old["Parameters"].get(key, "<none>")
                    new_val = new["Parameters"].get(key, "<none>")
                    if old_val != new_val:
                        f.write(f"    - `{key}`: `{old_val}` → `{new_val}`\n")
            f.write("\n")

        if unchanged:
            f.write("## ✅ Unchanged Blocks\n")
            for b in unchanged:
                f.write(f"- `{b['BlockType']}` block **{b['SID']}**\n")

    print(f"📄 Change report saved as {report_name}")

# ======= MAIN MENU =======
while True:
    print("\n📊 Simulink Change Tracker")
    print("1. Create a new baseline")
    print("2. Compare to existing baseline")
    print("3. Exit")

    choice = input("Select an option (1–3): ").strip()

    if choice == "1":
        create_baseline()
    elif choice == "2":
        compare_to_baseline()
    elif choice == "3":
        print("👋 Exiting.")
        break
    else:
        print("❌ Invalid input. Please choose 1, 2, or 3.")
