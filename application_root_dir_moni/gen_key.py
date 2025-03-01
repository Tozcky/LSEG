from cryptography.fernet import Fernet

# Generate a new valid encryption key
new_key = Fernet.generate_key().decode()

print("New ENCRYPTION_KEY:", new_key)