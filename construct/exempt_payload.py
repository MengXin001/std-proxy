import random


def generate(strprefix, increment=0, suffix="", payloadLen=0):
    r"""Generate exempt payloads.

    Args:
        strprefix (list()): the strprefix list.
        increment (int): increment for generating variable payload sizes. must be used in conjunction with increment. eg. -max -increment 10 will try the same prefix with total payload len 10, 20, ..., 100
        suffix (string): appending a fixed random payload for each probe, in hex format
        payloadLen (int): length of payload to send.

    Returns:
        list: randomPayload
    """
    randomPayload = list()
    print(strprefix, increment, suffix, payloadLen)
    for line in strprefix:
        prefix = bytes.fromhex(line)
        if increment != 0:
            for i in range(increment, payloadLen - 1):
                randomPayloadLen = i - len(prefix)
                if randomPayloadLen < 0:
                    randomPayloadLen = 0
                randomPayload.append([line, prefix, random.randbytes(randomPayloadLen)])
        elif suffix != "":
            suffix = bytes.fromhex(suffix)
            randomPayload.append([line, prefix, suffix])
        else:
            randomPayloadLen = payloadLen - len(prefix)
            if randomPayloadLen < 0:
                randomPayloadLen = 0
            randomPayload.append([line, prefix, random.randbytes(randomPayloadLen)])
    return randomPayload
