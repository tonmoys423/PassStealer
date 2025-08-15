import base64
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import unpad

# AES Key (from the original script)
AES_KEY = base64.b64decode("WjJuKOjI7EXLwDe9xezW7sgS46vHcSp5U+BHgbZzpmQ=")


def decrypt_file(encrypted_file, output_file):
    with open(encrypted_file, 'rb') as f:
        data = f.read()

    # Extract IV (first 16 bytes)
    iv = data[:16]
    ciphertext = data[16:]

    # Decrypt
    cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)

    with open(output_file, 'wb') as f:
        f.write(decrypted)


# Usage:
decrypt_file("edge.xlsx.enc", "edge_decrypted.xlsx")