from RSA_Oracle_client import RSA_Oracle_Get, RSA_Oracle_Query, RSA_Oracle_Checker, modinv

my_id =32812

# Step 1: get ciphertext C, modulus N, exponent e
C, N, e = RSA_Oracle_Get()

# Step 2: choose multiplier x
x = 2

# Step 3: compute modified ciphertext C' = C * x^e mod N
C_prime = (C * pow(x, e, N)) % N

# Step 4: query oracle with C' (must NOT equal original C)
m_prime = RSA_Oracle_Query(C_prime)

# Step 5: compute modular inverse of x
x_inv = modinv(x, N)

# Step 6: compute original plaintext m = m' * x^{-1} mod N
m_int = (m_prime * x_inv) % N

# Step 7: convert integer to UTF-8 string
m_bytes = m_int.to_bytes((m_int.bit_length() + 7)//8, 'big')
m_str = m_bytes.decode()

print("Recovered plaintext message:")
print(m_str)

# Step 8: Check with the server
RSA_Oracle_Checker(m_str)
