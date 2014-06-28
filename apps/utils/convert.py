# -*- coding: utf-8 -*-

def pack_bigint(i):
    b = bytearray()
    while i:
        b.append(i & 0xFF)
        i >>= 8
    return b
 

def unpack_bigint(b):
    b = bytearray(b)     # in case you're passing in a bytes/str
    return sum((1 << (bi * 8)) * bb for (bi, bb) in enumerate(b))
