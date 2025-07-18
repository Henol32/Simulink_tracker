# 🔍 Simulink Change Tracker

This Python tool lets you compare `.slx` Simulink models and automatically generate a Markdown report that highlights:
- ✅ Unchanged blocks
- ➕ Added blocks
- ❌ Removed blocks
- 🔁 Blocks with changed parameters

It's perfect for keeping track of model iterations during development.

---

## 📦 Requirements

To run this tool, you need:

### ✅ Python 3.9+ installed

Check with:
```bash
python3 --version

**### ✅ tkinter (for file browsing)**
On Windows and macOS, tkinter is usually included.

On Linux, install it using:

```bash
sudo apt install python3-tk

---------------------------------------------------------------------------------------------------------------------

🛠️ How to Use
1. Download the script
  Clone the repo or download simulink_tracker.py to your computer.

2. Run the script
  python3 simulink_tracker.py

3. Choose an option from the menu:
  📊 Simulink Change Tracker
  1. Create a new baseline
  2. Compare to existing baseline
  3. Exit

📁 What It Does
Option 1 extracts all blocks from your .slx and saves them in baseline.json.

Option 2 lets you pick another .slx file, compares it to the baseline, and writes a Markdown report like:

change_report_2025-07-16_15-22.md

Option 3 Exits the code


