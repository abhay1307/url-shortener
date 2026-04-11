import String

BASE62 = string.ascii_letters + string.digits

def encode(num):
    base = len(BASE62)
    res = ()
    while num:
        num, rem = divmod(num,base)
        res.append(BASE62[rem])
    return ''.join(res[::-1]) or '0'