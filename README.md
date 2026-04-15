# Deepwell: Automated Firmware Extraction Engine

An automated, database-backed firmware scraping and hoarding engine built for reverse engineering labs and vulnerability researchers.

###  Core Architecture 
* **Synchronous Evasion:** Uses Playwright/BS4 dynamically routed through a synchronous loop to stay under Cloudflare/WAF rate limits.
* **Content-Addressable Storage (CAS):** Strict SHA-256 deduplication. It only downloads a `.fw` or `.zip` if you don't already have it on disk.
* **SQLite Ledger:** Maintains a permanent record of what you have, what version it is, and where it lives on your drive.
* **Modular Handlers:** Built to be infinitely extensible. Drop a new Python function into `handlers.py`, update the JSON, and the engine handles the rest.

###  Installation

**1. Clone the repo**
```bash
git clone [https://github.com/BadChemical/Deepwell-Public.git](https://github.com/BadChemical/Deepwell-Public.git)
cd Deepwell-Public
```

**2. Nuke/Build a fresh virtual environment**
```bash
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# Linux/Mac:
source venv/bin/activate
```

**3. Install dependencies and browser binaries**
```bash
pip install -r requirements.txt
patchright install chromium
```

###  Usage

Deepwell relies on `targets.json` to know what to hunt. By default, it ships with a Proof-of-Concept handler for Bosch (targeting the CPP architectures). 

**Run a standard extraction sweep:**
```bash
python main.py
```

**Run a dry-run (Scrape only, no downloads. Great for testing new handlers):**
```bash
python main.py --dry-run
```

All extracted firmware will be automatically saved in a newly generated `./data/firmware/` directory, and logs will be written to `./logs/`. 

###  Adding Targets
Deepwell is modular. To add a new vendor:
1. Add their configuration block to `targets.json`.
2. Write a DOM-parsing function in `handlers.py` that returns a dictionary of `vendor`, `model`, `version`, `url`, and `sha256`. 
3. *Pull Requests for new enterprise handlers are welcome. I am tired of parsing HTML.*

###  Disclaimer
**For Educational and Authorized Research Purposes Only.**
This tool is designed to automate the collection of publicly available firmware for local hardware vulnerability analysis. The user is entirely responsible for ensuring their usage complies with the target vendor's Terms of Service, `robots.txt` (which can be overridden via config at your own risk), and local laws. The author assumes no liability for malicious use, accidental denial of service, or network blacklisting caused by this tool. Use responsibly.
