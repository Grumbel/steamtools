#!/usr/bin/env python3

# Copyright (c) 2012-2014 Ian Munsie <darkstarsword@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys
import struct
import binascii
from io import BytesIO


def pr_unknown(data, print_unknown):
    if print_unknown:
        decoded = struct.unpack('%dB' % len(data), data)
        print('[? ' + ' '.join(['%.2X' % x for x in decoded]) + ' ?]', file=sys.stderr)


def pr_unexpected(data, expected, note=''):
    l = len(data)
    expected_bytes = [int(expected[i:i + 2], 16) for i in range(0, l * 2, 2)]
    decoded = struct.unpack('%dB' % len(data), data)
    if decoded != tuple(expected_bytes):
        print('WARNING: %sExpected [%s], got [%s]' % (note,
                                                      ' '.join(['%.2X' % x for x in expected_bytes]),
                                                      ' '.join(['%.2X' % x for x in decoded])))
        return 1
    return 0


def decode_compressed_int(f):
    val = bytes = 0
    while True:
        byte = struct.unpack('B', f.read(1))[0]
        val |= (byte & 0x7f) << (bytes * 7)
        bytes += 1
        if (byte & 0x80) == 0:
            return val


def _decode_entry(f):
    pr_unexpected(f.read(1), '0A')
    filename_len = decode_compressed_int(f)
    return f.read(filename_len)


class DepotChunk(object):

    def __init__(self, sha):
        self.sha = sha

    def __str__(self):
        return '%.10i:%.10i  %s (%#.8x %i)' % (self.off, self.off + self.len, self.sha, self.unk1, self.unk2)

    def __lt__(self, other):
        return self.off < other.off


class DepotHash(list):

    def __str__(self):
        return '\n\t\t'.join(map(str, ['           %10i  %s (%s)' % (self.filesize, self.sha, self.filetype)] + sorted(self)))


def dump_hash(f, filename):
    return binascii.hexlify(f.read())


def decode_hash(f, filename):
    import hashlib

    # It looks like there are bytes describing the data that follows, so
    # it's possible that the order may not need to be as strict as this.
    # If an assert fails in the future I may need to refactor this to allow
    # for more flexible ordering (or another edge case has been found).

    ret = DepotHash()

    assert(f.read(1) == b'\x10')

    ret.filesize = decode_compressed_int(f)

    assert(f.read(1) == b'\x18')

    filetype = {
        b'\x00': 'file',
        b'\x01': 'config file',
        b'\x02': 'unidentified file type 0x02 (gam?)',
        b'\x04': 'unidentified file type 0x04 (vpk?)',
        b'\x08': 'unidentified file type 0x08',  # Hydrophobia: Prophecy seems to have this flag set for lots of files
        b'\x20': 'unidentified file type 0x20 (setup?)',  # The Ship uses this for DXSETUP.exe
        b'\x40': 'directory',
        b'\x80': 'post install script',
        b'\xa0': 'post install executable (?)',  # Serious Sam 3 uses this for Sam3.exe and Sam3_Unrestricted.exe
    }[f.read(1)]

    if filetype == 'directory':
        assert(ret.filesize == 0)
    elif filetype.startswith('post install'):
        filetype += ' flags: %s' % binascii.hexlify(f.read(1))

    ret.filetype = filetype

    assert(f.read(2) == b'\x22\x14')  # 0x22 = name hash, 0x14 = sizeof(sha1)

    # sha1 of the filename in lower case using \ as a path separator
    name_hash = binascii.hexlify(f.read(20))
    assert(hashlib.sha1(filename.lower()).hexdigest() == name_hash.decode('ascii'))

    assert(f.read(2) == b'\x2a\x14')  # 0x2a = full hash, 0x14 = sizeof(sha1)

    # For directories and empty files this is just all 0s, for non-empty
    # files this is a sha1 of the whole file:
    ret.sha = binascii.hexlify(f.read(20))

    while True:
        t = f.read(1)
        if t == b'':
            break
        assert(t == b'\x32')
        chunk_len = decode_compressed_int(f)
        chunk = BytesIO(f.read(chunk_len))
        assert(chunk.read(2) == b'\x0a\x14')  # 0x0a = chunk hash, 0x14 = sizeof(sha1)

        chunk_sha = binascii.hexlify(chunk.read(20))

        chunk_meta = DepotChunk(chunk_sha)
        while True:
            type = chunk.read(1)
            if type == b'':
                break

            type = {
                b'\x18': 'off',
                b'\x20': 'len',

                # Seems to be an identifier - chunks sharing
                # sha1s have matching unk1 fields, even between
                # different files (at least within a deopt):
                b'\x15': 'unk1',

                # Whereas this can be repeated on differing
                # chunks. Appears to usually be of a similar
                # value to the len field, but not (ever?)
                # exact - can be greater or smaller.
                # Sometimes much smaller:
                b'\x28': 'unk2',

            }[type]  # .get(type, 'UNKNOWN TYPE %s' % binascii.hexlify(type))

            if type == 'unk1':
                # FIXME: Format string is a guess, I don't know
                # what this field is, nor what endian it is in.
                # It doesn't seem to be encoded the same way
                # other integers are in these files.
                (val,) = struct.unpack('<I', chunk.read(4))
            else:
                val = decode_compressed_int(chunk)

            setattr(chunk_meta, type, val)

        ret.append(chunk_meta)
    return ret


def decode_entry(f):
    total_len = decode_compressed_int(f)
    data = BytesIO(f.read(total_len))
    filename = _decode_entry(data)
    try:
        h = decode_hash(data, filename)
        # h = dump_hash(data, filename)
    except:
        h = 'ERROR DECODING HASH'
        raise
    return (filename, h)


def dump_remaining_data(f):
    print('Remaining undecoded data:', file=sys.stderr)
    try:
        while True:
            for i in range(2):
                for j in range(8):
                    print('%.2X' % struct.unpack('B', f.read(1))[0], end=' ', file=sys.stderr)
                print('', end=' ', file=sys.stderr)
            print(file=sys.stderr)
    except:
        print(file=sys.stderr)
        return


def decode_depotcache(filename, print_unknown=False):
    with open(filename, 'rb') as f:
        pr_unexpected(f.read(4), 'D017F671', "Unexpected magic value: ")
        pr_unknown(f.read(3), print_unknown)
        pr_unexpected(f.read(1), '00')
        while True:
            byte = struct.unpack('B', f.read(1))[0]
            if byte == 0x0a:
                yield decode_entry(f)
            elif byte == 0xbe:
                if print_unknown:
                    print('0xBE FOUND, ENDING', file=sys.stderr)
                    dump_remaining_data(f)
                return
            else:
                print('WARNING: UNKNOWN TYPE 0x%.2X' % byte)


def main():
    for filename in sys.argv[1:]:
        print('Decoding %s...' % filename, file=sys.stderr)
        for entry in decode_depotcache(filename, True):
            print('%s\n\t\t%s' % entry)
        print(file=sys.stderr)

if __name__ == '__main__':
    main()

# EOF #
