import bcrypt

# Replace with your actual admin password
password = 'admin1'
hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

print(f"Hashed Password: {hashed_password}")

