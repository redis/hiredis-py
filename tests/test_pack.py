import hiredis


def test_basic():
    cmd = ('HSET', 'foo', 'key', 'value1', b'key_b', b'bytes str', 'key_mv',
           memoryview(b'bytes str'), b'key_i', 67, 'key_f', 3.14159265359)
    expected_packed = b'*12\r\n$4\r\nHSET\r\n$3\r\nfoo\r\n$3\r\nkey\r\n$6\r\nvalue1\r\n$5\r\nkey_b\r\n$9\r\nbytes str\r\n$6\r\nkey_mv\r\n$9\r\nbytes str\r\n$5\r\nkey_i\r\n$2\r\n67\r\n$5\r\nkey_f\r\n$13\r\n3.14159265359\r\n'
    packed_cmd = hiredis.pack_command(cmd)
    assert packed_cmd == expected_packed


def test_spaces_in_cmd():
    cmd = ('COMMAND', 'GETKEYS', 'EVAL',
           'return {KEYS[1],KEYS[2],ARGV[1],ARGV[2]}', 2, 'key1', 'key2', 'first', 'second')
    expected_packed = b'*9\r\n$7\r\nCOMMAND\r\n$7\r\nGETKEYS\r\n$4\r\nEVAL\r\n$40\r\nreturn {KEYS[1],KEYS[2],ARGV[1],ARGV[2]}\r\n$1\r\n2\r\n$4\r\nkey1\r\n$4\r\nkey2\r\n$5\r\nfirst\r\n$6\r\nsecond\r\n'
    packed_cmd = hiredis.pack_command(cmd)
    assert packed_cmd == expected_packed


def test_null_chars():
    cmd = ('SET', 'a', bytes(b'\xaa\x00\xffU'))
    expected_packed = b'*3\r\n$3\r\nSET\r\n$1\r\na\r\n$4\r\n\xaa\x00\xffU\r\n'
    packed_cmd = hiredis.pack_command(cmd)
    assert packed_cmd == expected_packed
