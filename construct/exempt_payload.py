import random


def generate(strprefix, increment=0, suffix="", payload_len=0):
    r"""Generate exempt payloads.

    Args:
        strprefix (list()): the strprefix list.
        increment (int): increment for generating variable payload sizes. must be used in conjunction with increment. eg. -max -increment 10 will try the same prefix with total payload len 10, 20, ..., 100
        suffix (string): appending a fixed random payload for each probe, in hex format
        payload_len (int): length of payload to send.

    Returns:
        list: random_payload
    """
    random_payload = []
    print(strprefix, increment, suffix, payload_len)
    for line in strprefix:
        prefix = bytes.fromhex(line)
        if increment != 0:
            for i in range(increment, payload_len - 1):
                random_payload_len = i - len(prefix)
                random_payload_len = max(random_payload_len, 0)
                random_payload.append([line, prefix, random.randbytes(random_payload_len)])
        elif suffix != "":
            suffix = bytes.fromhex(suffix)
            random_payload.append([line, prefix, suffix])
        else:
            random_payload_len = payload_len - len(prefix)
            random_payload_len = max(random_payload_len, 0)
            random_payload.append([line, prefix, random.randbytes(random_payload_len)])
    return random_payload
