# 🔍 Simulink Change Tracker

Compare two `*.slx` models and get a tidy Markdown report showing

|   | Section | What you’ll see |
|---|---------|-----------------|
| ✅ | **Unchanged Blocks** | blocks whose type & parameters are identical |
| ➕ | **Added Blocks** | blocks present only in the new model |
| ❌ | **Removed Blocks** | blocks missing from the new model |
| 🔁 | **Changed Blocks** | same block, parameters changed |
| 🔀 | **Connection Changes** | new / removed / modified lines |
| 📷 | **Model thumbnails** | side-by-side screenshots (if Simulink saved one) |

Each run is archived in its own timestamped folder, so you keep a history of all comparisons.


## 📦 Requirements

| Needed | Check dependency | 
|----|------------|
| Python **3.9+** | `python3 --version` |
| Tk file-dialog (`tkinter`) | Windows/macOS: included<br>Ubuntu / Debian:<br>`sudo apt install python3-tk`<br>Fedora:<br>`sudo dnf install python3-tkinter` |

No third-party Python packages required.

## 🛠️ How to Use

**1. Download the script**

Clone the repo or download simulink_tracker.py to your computer.

**2. Run the script**
  ```bash
  python3 simulink_tracker.py
  ```

**3. Choose an option from the menu:**
  ```bash
  📊 Simulink Change Tracker
  1. Create a new baseline
  2. Compare to existing baseline
  3. Exit
  ```

### 📁 What It Does

**Option 1** extracts all blocks from your .slx and saves them in baseline.json.

**Option 2** lets you pick another .slx file, compares it to the baseline, and writes a Markdown report like:

change_report_2025-07-16_15-22.md

**Option 3** Exits the code


## ⚙️ Configuration
**Ignored parameters**
Cosmetic fields such as "Position" and the huge
"ScopeSpecificationString" are skipped.
Edit IGNORED_PARMS near the top of simulink_tracker.py to tweak.

**Run-folder location**
new_run_dir() creates folders next to the script; change the base path if
you want them elsewhere.

## Viewing the report
**Tip:** open the .md file in a Markdown viewer to see tables & images.

VS Code: press Ctrl + Shift + V or right-click → Open Preview

GitHub/GitLab: just click the file in the repo

## 📝 Example output 
# Simulink Change Report (2025-07-29 at 16:07)

## 📷 Model thumbnails

| Baseline | New |
|----------|-----|
| ![baseline](baseline_thumb.png) | ![new](new_thumb.png) |

## ➕ Added Blocks
- `Constant` **Subsystem/Constant1** (SID 5): `{'Value': '3'}`

## 🔁 Changed Blocks
- `Constant` **Constant** (SID 2) changed:
    - `Value`: `3` → `14`

## 🔀 Connection Changes
### ➕ Added Lines
- `Constant1` (Port 1) → `Product` (Port 3)

### 🔁 Modified Lines
- `Product` (Port 1): `Scope2` → `Scope`

