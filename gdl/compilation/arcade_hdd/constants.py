CHD_SIGNATURE = b'MComprHD'

# root of tree is file header 2(0 is the file table, and 1 is unknown)
FILE_TABLE_INDEX   = 0
UNKNOWN_FILE_INDEX = 1
ROOT_DIR_INDEX     = 2

FILE_BLOCK_TYPE_DIRECTORY = 2
FILE_BLOCK_TYPE_REGULAR   = 4

MAX_FILE_TABLE_ENTRIES = 0xFFFF # 65535 files should be plenty
MAX_FILE_SIZE = 0x10000000 # 256MB should be large enough for any potential mods

PARTITION_HEADER_SIG = int.from_bytes(b'PART', 'big')
MBR_HEADER_SIG       = 0xFEEDF00D
FILE_TABLE_SIG       = 0xF00DFACE
REGULAR_FILE_SIG     = 0xC0EDBABE
UNKNOWN_MBR_SIG      = 0xFE1DFAED
SECTOR_SIZE          = 0x200 # 512 bytes
# TODO: figure this out: https://tldp.org/HOWTO/Large-Disk-HOWTO-4.html
# https://cdn.discordapp.com/attachments/1040820763617415239/1150090764735488010/image.png
#MAX_SECTOR_COUNT     = 0xFF00000
