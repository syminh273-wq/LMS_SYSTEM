import time
import os
import uuid

def uuid7():
    """
    Generate a UUIDv7 (sortable by time).
    Ref: https://uuid7.com/
    """
    # posix timestamp in milliseconds
    ms = int(time.time() * 1000)
    
    # 48-bit timestamp
    # 4-bit version (7)
    # 12-bit sequence/rand
    # 2-bit variant (2)
    # 62-bit rand
    
    # Simple implementation:
    # 48 bits: ms timestamp
    # 4 bits: version (0x7)
    # 12 bits: random
    # 2 bits: variant (0x2)
    # 62 bits: random
    
    rand_bytes = os.urandom(10)
    
    # Construct bytes
    b = bytearray()
    # Timestamp 48 bits
    b.extend(ms.to_bytes(6, 'big'))
    # Random + Version (7)
    # The first 4 bits of the 7th byte are the version
    b.append((0x70 | (rand_bytes[0] & 0x0F)))
    b.append(rand_bytes[1])
    # Variant (2) + Random
    # The first 2 bits of the 9th byte are the variant
    b.append((0x80 | (rand_bytes[2] & 0x3F)))
    b.extend(rand_bytes[3:])
    
    return uuid.UUID(bytes=bytes(b))
