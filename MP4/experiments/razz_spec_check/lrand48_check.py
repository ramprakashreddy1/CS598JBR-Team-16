# Verify that the razz_simulation test expectations come from POSIX srand48(3)/lrand48().
A, C, M = 0x5DEECE66D, 0xB, 1 << 48
def srand48(seed): return ((seed & 0xFFFFFFFF) << 16) | 0x330E
def lrand48(x):
    x = (A * x + C) % M
    return x, x >> 17          # lrand48 returns the high 31 bits
names = []
for s in ["Spade","Heart","Diamond","Club"]:
    for r in ["Ace","2","3","4","5","6","7","8","9","10","J","Q","K"]:
        names.append(s+r)
expected = [1001,1012,1032,911,1000,987,1026,978,971,964,942,968,1033,962,1011,939,975,1052,1028,1002,992,1054,1004,1045,993,984,1023,960,993,1058,998,971,1018,1025,1042,1045,983,1018,999,995,1024,999,968,1024,986,1015,1036,1015,966,973,982,1018]
seed3_order = ["Heart9","SpadeAce","Heart10","Club2","Diamond6","HeartQ","Diamond2","Diamond9"]
# dealing order from a fresh 52-card deck: idx = lrand48() % remaining; pick idx-th remaining card
x = srand48(3); deck = list(range(52)); order = []
for _ in range(8):
    x, v = lrand48(x); i = v % len(deck); order.append(names[deck.pop(i)])
print("first 8 deals from seed 3 :", order)
print("matches SEED3 order       :", order == seed3_order)
def counts(start):
    x = srand48(3)
    for _ in range(start): x, _ = lrand48(x)
    c = [0]*52
    for _ in range(52000):
        x, v = lrand48(x); c[v % 52] += 1
    return c
print("stream from 0 == expected  :", counts(0) == expected)
for off in (1, 8, 13, 50, 58, 59, 63):
    print(f"stream from {off:3d} == expected:", counts(off) == expected)
