import gc
import platform

import hiredis
import pytest

@pytest.fixture()
def reader():
  return hiredis.Reader()

# def reply():
#   return reader.gets()

def test_nothing(reader):
  assert not reader.gets()

def test_error_when_feeding_non_string(reader):
  with pytest.raises(TypeError):
    reader.feed(1)

def test_protocol_error(reader):
  reader.feed(b"x")
  with pytest.raises(hiredis.ProtocolError):
    reader.gets()

def test_protocol_error_with_custom_class():
  r = hiredis.Reader(protocolError=RuntimeError)
  r.feed(b"x")
  with pytest.raises(RuntimeError):
    r.gets()

def test_protocol_error_with_custom_callable():
  
  class CustomException(Exception):
    pass

  r = hiredis.Reader(protocolError=lambda e: CustomException(e))
  r.feed(b"x")
  with pytest.raises(CustomException):
    r.gets()

def test_fail_with_wrong_protocol_error_class():
  with pytest.raises(TypeError):
    hiredis.Reader(protocolError="wrong")

def test_faulty_protocol_error_class():
  def make_error(errstr):
    1 / 0
  r = hiredis.Reader(protocolError=make_error)
  r.feed(b"x")
  with pytest.raises(ZeroDivisionError):
    r.gets()

def test_error_string(reader):
  reader.feed(b"-error\r\n")
  error = reader.gets()

  assert isinstance(error, hiredis.ReplyError)
  assert ("error", ) == error.args

def test_error_string_with_custom_class():
  r = hiredis.Reader(replyError=RuntimeError)
  r.feed(b"-error\r\n")
  error = r.gets()

  assert isinstance(error, RuntimeError)
  assert ("error", ) == error.args

def test_error_string_with_custom_callable():
  class CustomException(Exception):
    pass

  r= hiredis.Reader(replyError=lambda e: CustomException(e))
  r.feed(b"-error\r\n")
  error = r.gets()

  assert isinstance(error, CustomException)
  assert ("error", ) == error.args

def test_error_string_with_non_utf8_chars(reader):
  reader.feed(b"-error \xd1\r\n")
  error = reader.gets()

  expected = "error \ufffd"

  assert isinstance(error, hiredis.ReplyError)
  assert (expected,) == error.args

def test_fail_with_wrong_reply_error_class():
  with pytest.raises(TypeError):
    hiredis.Reader(replyError="wrong")

def test_faulty_reply_error_class():
  def make_error(errstr):
    1 / 0

  r= hiredis.Reader(replyError=make_error)
  r.feed(b"-error\r\n")
  with pytest.raises(ZeroDivisionError):
    r.gets()

def test_errors_in_nested_multi_bulk(reader):
  reader.feed(b"*2\r\n-err0\r\n-err1\r\n")

  for r, error in zip(("err0", "err1"), reader.gets()):
    assert isinstance(error, hiredis.ReplyError)
    assert (r,) == error.args

def test_errors_with_non_utf8_chars_in_nested_multi_bulk(reader):
  reader.feed(b"*2\r\n-err\xd1\r\n-err1\r\n")

  expected = "err\ufffd"

  for r, error in zip((expected, "err1"), reader.gets()):
    assert isinstance(error, hiredis.ReplyError)
    assert (r,) == error.args

def test_integer(reader):
  value = 2**63-1 # Largest 64-bit signed integer
  reader.feed((":%d\r\n" % value).encode("ascii"))
  assert value == reader.gets()

def test_float(reader):
  value = -99.99
  reader.feed(b",%f\r\n" % value)
  assert value == reader.gets()

def test_boolean_true(reader):
  reader.feed(b"#t\r\n")
  assert reader.gets()

def test_boolean_false(reader):
  reader.feed(b"#f\r\n")
  assert not reader.gets()

def test_none(reader):
  reader.feed(b"_\r\n")
  assert reader.gets() is None

def test_set(reader):
  reader.feed(b"~3\r\n+tangerine\r\n_\r\n,10.5\r\n")
  assert [b"tangerine", None, 10.5] == reader.gets()

def test_set_with_nested_dict(reader):
  reader.feed(b"~2\r\n+tangerine\r\n%1\r\n+a\r\n:1\r\n")
  assert [b"tangerine", {b"a": 1}] == reader.gets()

def test_dict(reader):
  reader.feed(b"%2\r\n+radius\r\n,4.5\r\n+diameter\r\n:9\r\n")
  assert {b"radius": 4.5, b"diameter": 9} == reader.gets()

@pytest.mark.limit_memory("50 KB")
def test_dict_memory_leaks(reader):
  data = (
    b"%5\r\n"
    b"+radius\r\n,4.5\r\n"
    b"+diameter\r\n:9\r\n"
    b"+nested_map\r\n"
    b"%2\r\n"
    b"+key1\r\n+value1\r\n"
    b"+key2\r\n:42\r\n"
    b"+nested_array\r\n"
    b"*2\r\n"
    b"+item1\r\n"
    b"+item2\r\n"
    b"+nested_set\r\n"
    b"~2\r\n"
    b"+element1\r\n"
    b"+element2\r\n"
  )
  for i in range(10000):
    reader.feed(data)
    res = reader.gets()
    assert {
             b"radius": 4.5,
             b"diameter": 9,
             b"nested_map": {b"key1": b"value1", b"key2": 42},
             b"nested_array": [b"item1", b"item2"],
             b"nested_set": [b"element1", b"element2"],
           } == res

def test_dict_with_unhashable_key(reader):
    reader.feed(
      b"%1\r\n"
      b"%1\r\n+key1\r\n+value1\r\n"
      b":9\r\n"
    )
    with pytest.raises(TypeError):
      reader.gets()

def test_dict_repeated_key_not_last(reader):
  """A repeated key keeps its position, so the last value wins and no
  placeholder leaks into the result. Compared as items() because dict equality
  ignores order, and order is precisely what the old scheme disturbed."""
  reader.feed(b"%3\r\n+a\r\n:1\r\n+b\r\n:2\r\n+a\r\n:3\r\n")
  assert [(b"a", 3), (b"b", 2)] == list(reader.gets().items())

def test_dict_repeated_key_interleaved(reader):
  reader.feed(b"%4\r\n+a\r\n:1\r\n+b\r\n:2\r\n+a\r\n:3\r\n+b\r\n:4\r\n")
  assert [(b"a", 3), (b"b", 4)] == list(reader.gets().items())

def test_dict_hash_equal_keys(reader):
  """0 and False are distinct on the wire but the same dict key."""
  reader.feed(b"%3\r\n:0\r\n+x\r\n+k\r\n+y\r\n#f\r\n+z\r\n")
  assert [(0, b"z"), (b"k", b"y")] == list(reader.gets().items())

def test_dict_split_between_key_and_value(reader):
  """A key is buffered until its value arrives, possibly several feeds later."""
  reader.feed(b"%2\r\n+radius\r\n")
  assert not reader.gets()
  reader.feed(b",4.5\r\n+diameter\r\n")
  assert not reader.gets()
  reader.feed(b":9\r\n")
  assert {b"radius": 4.5, b"diameter": 9} == reader.gets()

def test_dict_protocol_error_after_key(reader):
  # "!" is an unrecognised type byte, which aborts the parse. Error replies
  # start with "-" and parse fine, so they would not abort anything.
  reader.feed(b"%2\r\n+radius\r\n,4.5\r\n+diameter\r\n!bogus\r\n")
  with pytest.raises(hiredis.ProtocolError):
    reader.gets()

@pytest.mark.skipif(platform.python_implementation() != "CPython",
                    reason="gc.get_referents() only reports tp_traverse on CPython")
def test_dict_pending_key_is_traversed(reader):
  """A key waiting for its value is a reference the reader owns.

  It has to be reported to the GC, or a cycle running through a buffered key
  would never be collected. This is also what makes the release below
  observable.
  """
  reader.feed(b"%1\r\n$3\r\nabc\r\n")
  assert not reader.gets()
  assert b"abc" in gc.get_referents(reader)

@pytest.mark.skipif(platform.python_implementation() != "CPython",
                    reason="gc.get_referents() only reports tp_traverse on CPython")
def test_dict_protocol_error_releases_pending_key(reader):
  """A reply aborted between a key and its value must release the buffered key.

  The reader is unusable afterwards either way (hiredis latches the error), so
  what matters is that the key it was holding is dropped rather than pinned for
  the lifetime of the reader. Checked with the reader still alive, so this
  covers the release in gets() and not the one in dealloc.
  """
  reader.feed(b"%1\r\n$3\r\nabc\r\n!bogus\r\n")
  with pytest.raises(hiredis.ProtocolError):
    reader.gets()
  assert b"abc" not in gc.get_referents(reader)

def _nested_unhashable_keys(depth=12):
  """A reply that holds a deep stack of buffered keys.

  A map in key position is parented, and so buffered, when its header is read
  rather than when it completes, so every level but the outermost is on the
  stack while the next one is parsed. The innermost map takes "+a" / ":1"; each
  of the remaining maps needs one value, hence depth - 1 of them.
  """
  return b"%1\r\n" * depth + b"+a\r\n:1\r\n" + b":2\r\n" * (depth - 1)

def test_dict_deeply_nested_unhashable_keys(reader):
  """Maps in key position nest without bound; unwinding must stay clean."""
  reader.feed(_nested_unhashable_keys())
  with pytest.raises(TypeError):
    reader.gets()

@pytest.mark.skipif(platform.python_implementation() != "CPython",
                    reason="gc.get_referents() only reports tp_traverse on CPython")
def test_dict_deeply_nested_unhashable_keys_release(reader):
  """The abort has to unwind the whole stack, not just the pair it failed on.

  At depth 12 ten maps are still buffered when the failing pair is inserted, so
  this is the case where releasing only the key in hand would strand the rest.
  """
  reader.feed(_nested_unhashable_keys())
  with pytest.raises(TypeError):
    reader.gets()
  assert not [obj for obj in gc.get_referents(reader) if isinstance(obj, dict)]

def test_dict_reused_reader(reader):
  """Consecutive maps on one reader must not leak state between replies, and a
  key must stay buffered across a gets() that reports not-enough-data."""
  for i in range(3):
    reader.feed(b"%%2\r\n+k\r\n:%d" % i)
    assert not reader.gets()               # "k" buffered, its value incomplete
    reader.feed(b"\r\n+j\r\n")
    assert not reader.gets()               # "j" buffered too
    reader.feed(b":%d\r\n" % (i * 10))
    assert {b"k": i, b"j": i * 10} == reader.gets()

def test_vector(reader):  
  reader.feed(b">4\r\n+pubsub\r\n+message\r\n+channel\r\n+message\r\n")
  result = reader.gets()
  assert isinstance(result, hiredis.PushNotification)
  assert [b"pubsub", b"message", b"channel", b"message"] == result

@pytest.mark.skipif(platform.python_implementation() != "CPython",
                    reason="requires CPython reference counting")
def test_push_notification_releases_backing_list(reader):
  # The list a notification is sized from is only borrowed by PyList_SetSlice,
  # so not releasing it strands one list per notification received.
  payload = b">4\r\n+pubsub\r\n+message\r\n+channel\r\n+message\r\n"
  iterations = 512

  def live_lists():
    return sum(1 for obj in gc.get_objects() if type(obj) is list)

  for _ in range(8):
    reader.feed(payload)
    reader.gets()
  gc.collect()
  before = live_lists()

  for _ in range(iterations):
    reader.feed(payload)
    reader.gets()
  gc.collect()

  # Leaking strands exactly one list per iteration, so the bug reads as a delta
  # of 512 where a fixed build measures 0. The bound is left far above 0 only so
  # that allocations elsewhere in the run cannot make this flaky.
  assert live_lists() - before < iterations // 8

def test_verbatim_string(reader):
  value = b"text"
  reader.feed(b"=8\r\ntxt:%s\r\n" % value)
  assert value == reader.gets()

def test_status_string(reader):
  reader.feed(b"+ok\r\n")
  assert b"ok" == reader.gets()

def test_empty_bulk_string(reader):
  reader.feed(b"$0\r\n\r\n")
  assert b"" == reader.gets()

def test_bulk_string(reader):
  reader.feed(b"$5\r\nhello\r\n")
  assert b"hello" == reader.gets()

def test_bulk_string_without_encoding(reader):
  snowman = b"\xe2\x98\x83"
  reader.feed(b"$3\r\n" + snowman + b"\r\n")
  assert snowman == reader.gets()

def test_bulk_string_with_encoding():
  snowman = b"\xe2\x98\x83"
  r= hiredis.Reader(encoding="utf-8")
  r.feed(b"$3\r\n" + snowman + b"\r\n")
  assert snowman.decode("utf-8") == r.gets()

def test_decode_errors_defaults_to_strict():
  r= hiredis.Reader(encoding="utf-8")
  r.feed(b"+\x80\r\n")
  with pytest.raises(UnicodeDecodeError):
    r.gets()

def test_decode_error_with_ignore_errors():
  r= hiredis.Reader(encoding="utf-8", errors="ignore")
  r.feed(b"+\x80value\r\n")
  assert "value" == r.gets()

def test_decode_error_with_surrogateescape_errors():
  r= hiredis.Reader(encoding="utf-8", errors="surrogateescape")
  r.feed(b"+\x80value\r\n")
  assert "\udc80value" == r.gets()

def test_invalid_encoding():
  with pytest.raises(LookupError):
    hiredis.Reader(encoding="unknown")

def test_should_decode_false_flag_prevents_decoding():
  snowman = b"\xe2\x98\x83"
  r = hiredis.Reader(encoding="utf-8")
  r.feed(b"$3\r\n" + snowman + b"\r\n")
  r.feed(b"$3\r\n" + snowman + b"\r\n")
  assert snowman == r.gets(False)
  assert snowman.decode() == r.gets()

def test_should_decode_true_flag_decodes_as_normal():
  snowman = b"\xe2\x98\x83"
  r= hiredis.Reader(encoding="utf-8")
  r.feed(b"$3\r\n" + snowman + b"\r\n")
  assert snowman.decode() == r.gets(True)

def test_set_encoding_with_different_encoding():
  snowman_utf8 = b"\xe2\x98\x83"
  snowman_utf16 = b"\xff\xfe\x03&"
  r= hiredis.Reader(encoding="utf-8")
  r.feed(b"$3\r\n" + snowman_utf8 + b"\r\n")
  r.feed(b"$4\r\n" + snowman_utf16 + b"\r\n")
  assert snowman_utf8.decode() == r.gets()
  r.set_encoding(encoding="utf-16", errors="strict")
  assert snowman_utf16.decode('utf-16') == r.gets()

def test_set_encoding_to_not_decode():
  snowman = b"\xe2\x98\x83"
  r= hiredis.Reader(encoding="utf-8")
  r.feed(b"$3\r\n" + snowman + b"\r\n")
  r.feed(b"$3\r\n" + snowman + b"\r\n")
  assert snowman.decode() == r.gets()
  r.set_encoding(encoding=None, errors=None)
  assert snowman == r.gets()

def test_set_encoding_invalid_encoding():
  r= hiredis.Reader(encoding="utf-8")
  with pytest.raises(LookupError):
    r.set_encoding("unknown")

def test_set_encoding_invalid_error_handler():
  r = hiredis.Reader(encoding="utf-8")
  with pytest.raises(LookupError):
    r.set_encoding(encoding="utf-8", errors="unknown")

def test_null_multi_bulk(reader):
  reader.feed(b"*-1\r\n")
  assert reader.gets() is None

def test_empty_multi_bulk(reader):
  reader.feed(b"*0\r\n")
  assert reader.gets() == []

def test_multi_bulk(reader):
  reader.feed(b"*2\r\n$5\r\nhello\r\n$5\r\nworld\r\n")
  assert [b"hello", b"world"] == reader.gets()

def test_nested_multi_bulk(reader):
  reader.feed(b"*2\r\n*2\r\n$5\r\nhello\r\n$5\r\nworld\r\n$1\r\n!\r\n")
  assert [[b"hello", b"world"], b"!"] == reader.gets()

def test_nested_multi_bulk_depth(reader):
  reader.feed(b"*1\r\n*1\r\n*1\r\n*1\r\n$1\r\n!\r\n")
  assert [[[[b"!"]]]] == reader.gets()

def test_subclassable(reader):
  
  class TestReader(hiredis.Reader):
    pass

  reader = TestReader()
  reader.feed(b"+ok\r\n")
  assert b"ok" == reader.gets()

def test_invalid_offset(reader):
  data = b"+ok\r\n"
  with pytest.raises(ValueError):
    reader.feed(data, 6)

def test_invalid_length(reader):
  data = b"+ok\r\n"
  with pytest.raises(ValueError):
    reader.feed(data, 0, 6)

def test_ok_offset(reader):
  data = b"blah+ok\r\n"
  reader.feed(data, 4)
  assert b"ok" == reader.gets()

def test_ok_length(reader):
  data = b"blah+ok\r\n"
  reader.feed(data, 4, len(data)-4)
  assert b"ok" == reader.gets()

def test_feed_bytearray(reader):
  reader.feed(bytearray(b"+ok\r\n"))
  assert b"ok" == reader.gets()

def test_maxbuf(reader):
  defaultmaxbuf = reader.getmaxbuf()
  reader.setmaxbuf(0)
  assert 0 == reader.getmaxbuf()
  reader.setmaxbuf(10000)
  assert 10000 == reader.getmaxbuf()
  reader.setmaxbuf(None)
  assert defaultmaxbuf == reader.getmaxbuf()
  with pytest.raises(ValueError):
    reader.setmaxbuf(-4)

def test_len(reader):
  assert reader.len() == 0
  data = b"+ok\r\n"
  reader.feed(data)
  assert reader.len() == len(data)

  # hiredis reallocates and removes unused buffer once
  # there is at least 1K of not used data.
  calls = int((1024 / len(data))) + 1
  for i in range(calls):
      reader.feed(data)
      reader.gets()

  assert reader.len() == 5

def test_reader_has_data(reader):
  assert reader.has_data() is False
  data = b"+ok\r\n"
  reader.feed(data)
  assert reader.has_data()
  reader.gets()
  assert reader.has_data() is False

def test_custom_not_enough_data():
  r = hiredis.Reader(notEnoughData=Ellipsis)
  assert r.gets() == Ellipsis
