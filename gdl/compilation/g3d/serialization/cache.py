import hashlib
import mmap
import struct

CACHE_HEADER_SIG = b"G3DCache"
CACHE_HEADER_VER = 0xDB0B0001
CACHE_CHECKSUM_ALGORITHM = "md5"

CACHE_FLAG_EXTRACTED = 1 << 0

CACHE_HEADER_STRUCT = struct.Struct('<8s II 4s H 10s 16s')
#   signature
#   version
#   flags
#   cache_type
#   cache_type_version
#   checksum_algorithm
#   source_asset_checksum

DIGEST_CHUNK_SIZE = 256*1024 # 256KB


def get_asset_checksum(filepath=None, rawdata=None,
                       algo=CACHE_CHECKSUM_ALGORITHM):
    digester = hashlib.new(algo)
    if filepath:
        with open(filepath, "rb") as f:
            data = True
            while data:
                data = data.read(DIGEST_CHUNK_SIZE)
                digester.update(data)
    elif rawdata is not None:
        digester.update(rawdata)
    else:
        raise ValueError("No asset data to read.")

    return digester.digest()


def parse_cache_header(rawdata):
    if not rawdata:
        raise ValueError("No header data to read.")

    sig, ver, flags, cache_type, cache_type_ver, algo, checksum = \
         CACHE_HEADER_STRUCT.unpack(rawdata.read(CACHE_HEADER_STRUCT.size))
    if sig != CACHE_HEADER_SIG:
        raise ValueError("File does not appear to be a G3DCache file.")
    elif ver != CACHE_HEADER_VER:
        raise ValueError(f"Unknown G3DCache file version: {ver}")

    algo = algo.decode("latin-1")
    return dict(
        version=ver,
        flags=flags,
        cache_type=cache_type,
        cache_type_version=cache_type_ver,
        checksum_algorithm=algo,
        checksum=checksum
        )


def serialize_cache_header(cache_type, cache_type_version, *,
                           flags=0, checksum=b''):
    if len(cache_type) > 4:
        raise ValueError(
            f"Asset type '{cache_type}' is too long to be stored in cache file."
            )

    header_data = CACHE_HEADER_STRUCT.pack(
        CACHE_HEADER_SIG, CACHE_HEADER_VER, flags, cache_type, cache_type_version,
        CACHE_CHECKSUM_ALGORITHM.encode("latin-1"), checksum
        )

    return header_data


def verify_source_asset_checksum(
        asset_filepath=None, asset_rawdata=None, cache_rawdata=None
        ):
    header = read_cache_header(cache_rawdata)
    asset_checksum = get_asset_checksum(
        filepath=asset_filepath, rawdata=asset_rawdata,
        algo=header["checksum_algorithm"]
        )

    return asset_checksum == header["checksum"]


def verify_source_file_asset_checksum(asset_filepath, cache_filepath):
    with open(cache_filepath, "rb") as f:
        return verify_source_asset_checksum(
            asset_filepath=asset_filepath, cache_rawdata=f
            )
    

def get_readable_rawdata(filepath=None, rawdata=None):
    if filepath:
        with open(filepath, "rb"):
            rawdata = mmap.mmap(f.fileno(), 0, access='rb')
    elif not rawdata:
        raise ValueError("No cache data or file to read.")

    return rawdata
