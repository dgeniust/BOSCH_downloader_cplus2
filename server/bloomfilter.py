import os
import math
import hashlib
import struct
import threading
import json
import base64

class URLBloomFilter:
    def __init__(self, expected_items: int = 1_000_000, false_positive_rate: float = 0.001, storage_file: str = "bloom_filter.json"):
        """
        :param storage_file: Đổi đường dẫn lưu trữ mặc định sang .json
        """
        self.n = expected_items
        self.p = false_positive_rate
        self.storage_file = storage_file
        self.lock = threading.Lock()

        # Tính toán m (bits) và k (hàm hash)
        self.m = int(- (self.n * math.log(self.p)) / (math.log(2) ** 2))
        self.k = int((self.m / self.n) * math.log(2))
        
        self.num_bytes = (self.m + 7) // 8
        self.bit_array = bytearray(self.num_bytes)

        # Đọc dữ liệu từ file JSON nếu đã tồn tại
        self.load_from_file()

    def _get_hash_indices(self, item: str):
        """Kỹ thuật Kirsch-Mitzenmacher sinh k vị trí bit từ SHA-256"""
        hash_digest = hashlib.sha256(item.encode('utf-8')).digest()
        h1, h2 = struct.unpack('<QQ', hash_digest[:16])

        for i in range(self.k):
            yield (h1 + i * h2) % self.m

    def add(self, url: str):
        with self.lock:
            for bit_index in self._get_hash_indices(url):
                byte_index = bit_index // 8
                bit_offset = bit_index % 8
                self.bit_array[byte_index] |= (1 << bit_offset)

    def contains(self, url: str) -> bool:
        with self.lock:
            for bit_index in self._get_hash_indices(url):
                byte_index = bit_index // 8
                bit_offset = bit_index % 8
                if not (self.bit_array[byte_index] & (1 << bit_offset)):
                    return False
            return True

    def __contains__(self, url: str) -> bool:
        return self.contains(url)

    def save_to_file(self):
        """Lưu toàn bộ Bloom Filter dưới dạng cấu trúc JSON"""
        with self.lock:
            # Mã hóa bytearray sang dạng chuỗi Base64 để đưa vào JSON
            b64_bit_array = base64.b64encode(self.bit_array).decode('utf-8')
            
            data = {
                "expected_items": self.n,
                "false_positive_rate": self.p,
                "total_bits": self.m,
                "hash_functions_count": self.k,
                "bit_array_base64": b64_bit_array
            }
            
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)

    def load_from_file(self):
        """Đọc và giải mã dữ liệu Bloom Filter từ file JSON"""
        if os.path.exists(self.storage_file):
            with self.lock:
                try:
                    with open(self.storage_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.n = data.get("expected_items", self.n)
                        self.p = data.get("false_positive_rate", self.p)
                        self.m = data.get("total_bits", self.m)
                        self.k = data.get("hash_functions_count", self.k)
                        
                        b64_str = data.get("bit_array_base64", "")
                        if b64_str:
                            decoded_bytes = base64.b64decode(b64_str)
                            self.bit_array = bytearray(decoded_bytes)
                except Exception as e:
                    print(f"Lỗi khi nạp file {self.storage_file}: {e}")