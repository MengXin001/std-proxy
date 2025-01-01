import logging
import re

logging.basicConfig(level=logging.DEBUG, format="%(message)s")


class SSHAnalyzer:
    def __init__(self):
        self.client_buffer = bytearray()
        self.server_buffer = bytearray()
        self.client_done = False
        self.server_done = False
        self.client_map = {}
        self.server_map = {}

    def feed(self, reverse, data):
        if reverse:
            self.server_buffer.extend(data)
            return self._parse_server_exchange_line()
        else:
            self.client_buffer.extend(data)
            return self._parse_client_exchange_line()

    def _parse_exchange_line(self, buffer):
        line_end = buffer.find(b"\r\n")
        if line_end == -1:
            return False, None

        line = buffer[:line_end]
        buffer = buffer[line_end + 2 :]

        parts = line.split(b" ", 1)

        if len(parts) < 1 or len(parts) > 2:
            return False, None

        match = re.search(
            r"SSH-(\d+\.\d+)-([^\r\n]+)", parts[0].decode("utf-8", errors="ignore")
        )
        if match:
            protocol_version = match.group()
            software_version = parts[1].decode() if len(parts) == 2 else ""

            return True, {"protocol": protocol_version, "software": software_version}
        else:
            return False, None

    def _parse_client_exchange_line(self):
        parsed, result = self._parse_exchange_line(self.client_buffer)
        if parsed:
            self.client_map = result
            logging.info(f"Client Protocol: {self.client_map}")
            self.client_buffer.clear()
            self.client_done = True
        return parsed

    def _parse_server_exchange_line(self):
        parsed, result = self._parse_exchange_line(self.server_buffer)
        if parsed:
            self.server_map = result
            logging.info(f"Server Protocol: {self.server_map}")
            self.server_buffer.clear()
            self.server_done = True
        return parsed

    def get_stream_info(self):
        return {
            "client_protocol": self.client_map,
            "server_protocol": self.server_map,
            "client_done": self.client_done,
            "server_done": self.server_done,
            "client_buffer": self.client_buffer.decode(errors="ignore"),
            "server_buffer": self.server_buffer.decode(errors="ignore"),
        }


if __name__ == "__main__":
    analyzer = SSHAnalyzer()
    client_data = "a841f4311b76e45f0117f759080045000052cd0240004006e939c0a80173c0a801a60016c3e8327b92fe479a5bad501801f6d12e00005353482d322e302d4f70656e5353485f382e397031205562756e74752d337562756e7475302e31300d0a"
    analyzer.feed(reverse=False, data=bytes.fromhex(client_data))
    result = analyzer.get_stream_info()
    print(result)

    '''
    {'client_protocol': {'protocol': 'SSH-2.0-OpenSSH_8.9p1', 'software': 'Ubuntu-3ubuntu0.10'}, 'server_protocol': {}, 'client_done': True, 'server_done': False, 'client_buffer': '', 'server_buffer': ''}
    '''