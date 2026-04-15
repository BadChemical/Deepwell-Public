
import sqlite3
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_FILE = os.path.join(DATA_DIR, 'deepwell.db')

def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS firmware_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor TEXT NOT NULL,
            model TEXT NOT NULL,
            version TEXT NOT NULL,
            download_url TEXT NOT NULL,
            sha256 TEXT UNIQUE,
            file_path TEXT,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')



    conn.commit()
    conn.close()
    print("[*] [Database] Schema ready.")

def save_firmware_data(extracted_data):
    
    if not extracted_data:
        print("[-] [Database] No data to save.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    new_records = 0

    for item in extracted_data:
        try:
           
            cursor.execute('''
                INSERT OR IGNORE INTO firmware_archive 
                (vendor, model, version, download_url, sha256)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                item['vendor'], 
                item['model'], 
                item['version'], 
                item['url'], 
                item['sha256']
            ))
            
    
            if cursor.rowcount == 1:
                new_records += 1
                
        except Exception as e:
            print(f"[!] [Database] Error saving {item['model']}: {e}")

    conn.commit()  
    conn.close()
    print(f"[+] [Database] Sweep complete: Added {new_records} NEW firmware records to the archive.")

def get_undownloaded():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, vendor, model, version, download_url, sha256
        FROM firmware_archive
        WHERE file_path IS NULL
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_file_path(firmware_id, file_path):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE firmware_archive 
        SET file_path = ? 
        WHERE id = ?
    ''', (file_path, firmware_id))
    conn.commit()
    conn.close()
    print(f'[+] [Database] file_path updated for ID {firmware_id}')


    
    
