from Crypto.Hash import SHAKE128

# From RSA_OAEP.py
k0 = 8
k1 = 128

def RSA_OAEP_Enc(m, e, N, R):
    k = N.bit_length() - 2
    m0k1 = m << k1
    shake = SHAKE128.new(R.to_bytes(k0 // 8, byteorder='big'))
    GR = shake.read((k - k0) // 8)
    m0k1GR = m0k1 ^ int.from_bytes(GR, byteorder='big')
    shake = SHAKE128.new(m0k1GR.to_bytes((m0k1GR.bit_length() + 7) // 8, byteorder='big'))
    Hm0k1GR = shake.read(k0 // 8)
    RHm0k1GR = R ^ int.from_bytes(Hm0k1GR, byteorder='big')
    m_ = (m0k1GR << k0) + RHm0k1GR
    c = pow(m_, e, N)
    return c

# Given values
c_target = int(
    "26586528191085700304892966616578618499776424404883002833837118394209420591517"
)
N = int(
    "55850725815335016174494660798604100471935688135865226598547191801194445724183"
)
e = 65537

def find_pin():
    for m in range(0, 10000):           # 4-digit PIN (0000–9999)
        for R in range(2**(k0-1), 2**k0):  # R is 8-bit, but chosen in [128, 255]
            if RSA_OAEP_Enc(m, e, N, R) == c_target:
                return m, R
    return None, None

if __name__ == "__main__":
    pin, R = find_pin()
    if pin is None:
        print("No matching PIN found.") # For me to check if not found
    else:  # Correct result
        print("Found PIN (as integer):", pin)
        print("Found PIN (4-digit):", f"{pin:04d}")
        print("Corresponding R:", R)
