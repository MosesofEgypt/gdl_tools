import hashlib
import os
import struct

CACHE_HEADER_SIG = b"G3DCache"
CACHE_HEADER_VER = 0xDB0B0001
CACHE_CHECKSUM_ALGORITHM = "md5"

CACHE_FLAG_EXTRACTED = 1 << 0

CACHE_HEADER_STRUCT = struct.Struct('<8s II 4s H 10s 16s')
# 48 bytes
#   signature
#   version
#   flags
#   cache_type
#   cache_type_version
#   checksum_algorithm
#   source_asset_checksum

DIGEST_CHUNK_SIZE = 256*1024 # 256KB

def get_asset_checksum(filepath=None, rawdata=None,
                       algorithm=CACHE_CHECKSUM_ALGORITHM):
    digester = hashlib.new(algorithm)
    if filepath:
        with open(filepath, "rb") as f:
            data = True
            while data:
                data = f.read(DIGEST_CHUNK_SIZE)
                digester.update(data)
    elif rawdata is not None:
        digester.update(rawdata)
    else:
        raise ValueError("No asset data to read.")

    return digester.digest()


def verify_source_asset_checksum(
        asset_filepath=None, asset_rawdata=None, cache_rawdata=None
        ):
    asset_cache = AssetCache()
    asset_cache.parse(cache_rawdata)
    asset_checksum = get_asset_checksum(
        filepath=asset_filepath, rawdata=asset_rawdata,
        algorithm=asset_cache.checksum_algorithm
        )

    return asset_cache.source_asset_checksum == asset_checksum


def verify_source_file_asset_checksum(asset_filepath, cache_filepath):
    with open(cache_filepath, "rb") as f:
        return verify_source_asset_checksum(
            asset_filepath=asset_filepath, cache_rawdata=f
            )


class AssetCache:
    version                 = CACHE_HEADER_VER
    cache_type              = ''
    cache_type_version      = 0
    checksum_algorithm      = CACHE_CHECKSUM_ALGORITHM
    source_asset_checksum   = b''
    expected_cache_type_versions = frozenset()

    is_extracted            = False

    _sub_classes            = {}

    def serialize_to_file(self, filepath):
        rawdata = self.serialize()
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(rawdata)

    @classmethod
    def get_cache_class_from_cache_type(cls, cache_type):
        cache_class = cls._sub_classes.get(cache_type)
        if cache_class:
            return cache_class

        raise ValueError(f"Unknown asset type '{cache_type}'")

    @classmethod
    def get_cache_class(cls, rawdata):
        asset_cache = AssetCache()
        start = rawdata.tell()
        try:
            asset_cache.parse(rawdata)
            return cls.get_cache_class_from_cache_type(asset_cache.cache_type)
        finally:
            rawdata.seek(start)

    def parse(self, rawdata):
        if not rawdata:
            raise ValueError("No header data to read.")

        sig, ver, flags, cache_type, cache_type_ver, algo, checksum = \
             CACHE_HEADER_STRUCT.unpack(rawdata.read(CACHE_HEADER_STRUCT.size))
        cache_type          = cache_type.strip(b'\x00').decode("latin-1")
        checksum_algorithm  = algo.strip(b'\x00').decode("latin-1")

        if sig != CACHE_HEADER_SIG:
            raise ValueError("File does not appear to be a G3DCache file.")
        elif ver != CACHE_HEADER_VER:
            raise ValueError(f"Unknown G3DCache file version: {ver}")

        cache_key = (cache_type, cache_type_ver)
        allowed = set(self.expected_cache_type_versions)
        if allowed:
            allowed.add((self.cache_type, self.cache_type_version))
            if cache_key not in allowed:
                raise ValueError(
                    f"Unexpected cache type or version {cache_key} for {type(self)}."
                    "Must be one of: " + (", ".join(str(v) for v in sorted(allowed)))
                    )

        self.version               = ver
        self.is_extracted          = bool(flags & CACHE_FLAG_EXTRACTED)
        self.cache_type            = cache_type
        self.cache_type_version    = cache_type_ver
        self.checksum_algorithm    = checksum_algorithm
        self.source_asset_checksum = checksum

    def serialize(self):
        if len(self.cache_type) > 4:
            raise ValueError(
                f"Asset type '{cache_type}' is too long to be stored in cache file."
                )

        flags = (
            (CACHE_FLAG_EXTRACTED * bool(self.is_extracted))
            )

        header_data = CACHE_HEADER_STRUCT.pack(
            CACHE_HEADER_SIG, self.version, flags,
            self.cache_type.encode("latin-1"),
            self.cache_type_version,
            self.checksum_algorithm.encode("latin-1"),
            self.source_asset_checksum
            )

        return header_data

    def parse_from_file(filepath):
        rawdata = get_readable_rawdata(filepath, rawdata)
        try:
            with open(filepath, "rb") as f:
                self.parse(f)
        finally:
            if hasattr(rawdata, "close"):
                rawdata.close()
