import os
from typing import Dict, Tuple
import json
from io import BytesIO

APK_SIG_BLOCK_MAGIC_HI = 0x3234206b636f6c42 #LITTLE_ENDIAN, High
APK_SIG_BLOCK_MAGIC_LO = 0x20676953204b5041 # LITTLE_ENDIAN, Low
APK_SIG_BLOCK_MIN_SIZE = 32

APK_SIGNATURE_SCHEME_V2_BLOCK_ID = 0x7109871a

APK_CHANNEL_BLOCK_ID = 0x71777777


ZIP_EOCD_REC_MIN_SIZE = 22
ZIP_EOCD_REC_SIG = 0x06054b50
UINT16_MAX_VALUE = 0xffff
ZIP_EOCD_COMMENT_LENGTH_FIELD_OFFSET = 20

DEFAULT_CHARSET = "UTF-8"
ENDIAN = 'little'


def get_file_size(f: BytesIO) -> int:
    current = f.tell()
    try:
        f.seek(0, os.SEEK_END)
        return f.tell()
    finally:
        f.seek(current, os.SEEK_SET)


def get_zip_archive_comment_size(f: BytesIO) -> int:
    f_size = get_file_size(f)
    if f_size < ZIP_EOCD_REC_MIN_SIZE:
        raise Exception("APK too small for ZIP End of Central Directory (EOCD) record")

    max_comment_size = min(f_size - ZIP_EOCD_REC_MIN_SIZE, UINT16_MAX_VALUE)
    eocd_with_empty_comment_start_position = f_size - ZIP_EOCD_REC_MIN_SIZE

    for expected_size in range(0, max_comment_size + 1):
        start = eocd_with_empty_comment_start_position - expected_size
        f.seek(start, os.SEEK_SET)
        buf = f.read(4)
        if int.from_bytes(buf, ENDIAN) == ZIP_EOCD_REC_SIG:
            f.seek(start + ZIP_EOCD_COMMENT_LENGTH_FIELD_OFFSET, os.SEEK_SET)
            buf = f.read(2)
            size = int.from_bytes(buf, ENDIAN)
            if size == expected_size:
                return size

    raise Exception("ZIP End of Central Directory (EOCD) record not found")


def get_zip_archive_central_dir_start_offset(f: BytesIO, comment_size: int) -> int:
    f_size = get_file_size(f)
    f.seek(f_size - comment_size - 6, os.SEEK_SET)
    buf = f.read(4)
    return int.from_bytes(buf, ENDIAN)


def read_apk_sig_block(f: BytesIO, central_dir_offset: int) -> Tuple:
    if central_dir_offset < APK_SIG_BLOCK_MIN_SIZE:
        raise Exception("APK too small for APK Signing Block. ZIP Central Directory offset: {}".format(central_dir_offset))
    
    '''
     Read the magic and offset in file from the footer section of the block:
     * uint64:   size of block
     * 16 bytes: magic
    '''
    f.seek(central_dir_offset - 24, os.SEEK_SET)
    buf = f.read(24)

    if int.from_bytes(buf[8:8+8], ENDIAN) != APK_SIG_BLOCK_MAGIC_LO \
            or int.from_bytes(buf[16:16+8], ENDIAN) != APK_SIG_BLOCK_MAGIC_HI:
        raise Exception("No APK Signing Block before ZIP Central Directory")

    # Read and compare size fields
    sig_block_size_in_footer = int.from_bytes(buf[0:8], ENDIAN)
    if sig_block_size_in_footer < 24 or sig_block_size_in_footer > 0x7fffffff -8:
        raise Exception("APK Signing Block size out of range: {}".format(sig_block_size_in_footer))
    
    total_size = sig_block_size_in_footer + 8
    sig_block_offset = central_dir_offset - total_size
    if sig_block_offset < 0 :
        raise Exception( "APK Signing Block offset out of range: {}".format(sig_block_offset))
    
    f.seek(sig_block_offset, os.SEEK_SET)
    sig_block = f.read(total_size)
    sig_block_size_in_header = int.from_bytes(sig_block[0:8], ENDIAN)
    if sig_block_size_in_header != sig_block_size_in_footer:
        raise Exception("APK Signing Block sizes in header and footer do not match: {} vs {}".format(sig_block_size_in_header, sig_block_size_in_footer))
    
    return sig_block, sig_block_offset



'''
FORMAT:
OFFSET       DATA TYPE  DESCRIPTION
* @+0  bytes uint64:    size in bytes (excluding this field)
* @+8  bytes pairs
* @-24 bytes uint64:    size in bytes (same as the one above)
* @-16 bytes uint128:   magic
'''
def read_apk_sig_block_id_values(sig_block: bytes) -> Dict:
    id_values = {}
    start, end = 8, len(sig_block) - 24
    if end < start:
        raise Exception("end < start: {} < {}".format(end, start))

    entries = sig_block[start:end]
    
    cnt = 0
    pos, size = 0, len(entries)
    while size > pos:
        cnt += 1
        if size - pos < 8:
            raise Exception("Insufficient data to read size of APK Signing Block entry #}{".format(cnt))

        current_entry_value_size = int.from_bytes(entries[pos:pos+8], ENDIAN)
        pos += 8
        
        if current_entry_value_size < 4 or current_entry_value_size > 0x7fffffff:
            raise Exception("APK Signing Block entry #{} size out of range: {}".format(cnt, current_entry_value_size))

        next = pos + current_entry_value_size
        if current_entry_value_size > size - pos:
            raise Exception("APK Signing Block entry #{} size out of range: {}, available: ".format(cnt, current_entry_value_size, size - pos))
        
        _id = int.from_bytes(entries[pos:pos + 4], ENDIAN)
        pos += 4
        id_values[_id] = entries[pos:pos + current_entry_value_size - 4]
        pos = next

    return id_values


def write_apk_sig_id_values(f: BytesIO, id_values: Dict[int, bytes]) -> int:
    # 24 = 8(size of block in bytes—same as the very first field (uint64)) + 16 (magic “APK Sig Block 42” (16 bytes))
    bytes_write = 24
    for _, value in id_values.items():
        # 12 = 8(uint64-length-prefixed) + 4 (ID (uint32))
        bytes_write += 12 + len(value)
    f.write(bytes_write.to_bytes(8, ENDIAN))

    for id, value in id_values.items():
        # Long.BYTES - Integer.BYTES
        value_bytes = len(value) + (8 - 4)
        f.write(value_bytes.to_bytes(8, ENDIAN))
        f.write(id.to_bytes(4, ENDIAN))
        f.write(value)

    f.write(bytes_write.to_bytes(8, ENDIAN))
    f.write(APK_SIG_BLOCK_MAGIC_LO.to_bytes(8, ENDIAN))
    f.write(APK_SIG_BLOCK_MAGIC_HI.to_bytes(8, ENDIAN))

    return bytes_write


def build_channel(f: BytesIO, channel: str):
    f_size = get_file_size(f)
    comment_size = get_zip_archive_comment_size(f)
    central_dir_offset = get_zip_archive_central_dir_start_offset(f, comment_size)
    sig_block, sig_block_offset = read_apk_sig_block(f, central_dir_offset)
    sig_id_values = read_apk_sig_block_id_values(sig_block)

    if sig_id_values is None or not APK_SIGNATURE_SCHEME_V2_BLOCK_ID in sig_id_values:
        raise Exception("No APK Signature Scheme v2 block in APK Signing Block")
    
    sig_id_values.update({APK_CHANNEL_BLOCK_ID:  json.dumps({'channel': channel}).encode(DEFAULT_CHARSET)})

    f.seek(central_dir_offset, os.SEEK_SET)
    central_dir_bytes = f.read(f_size - central_dir_offset)


    f.seek(sig_block_offset, os.SEEK_SET)
    size_writes = write_apk_sig_id_values(f, sig_id_values)

    f.write(central_dir_bytes)
    current_file_size = f.tell()
    f.truncate()

    '''
    update CentralDir Offset
    End of central directory record (EOCD)
    Offset     Bytes     Description[23]
    0            4       End of central directory signature = 0x06054b50
    4            2       Number of this disk
    6            2       Disk where central directory starts
    8            2       Number of central directory records on this disk
    10           2       Total number of central directory records
    12           4       Size of central directory (bytes)
    16           4       Offset of start of central directory, relative to start of archive
    20           2       Comment length (n)
    22           n       Comment
    '''
    f.seek(current_file_size - comment_size - 6, os.SEEK_SET)

    # 6 = 2(Comment length) + 4 (Offset of start of central directory, relative to start of archive)
    # 8 = size of block in bytes (excluding this field) (uint64)
    eocd_mrk = central_dir_offset + size_writes + 8 - (central_dir_offset - sig_block_offset)
    f.write(eocd_mrk.to_bytes(4, ENDIAN))
    f.seek(0, os.SEEK_SET)