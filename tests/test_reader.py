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

def test_vector(reader):
  reader.feed(b">4\r\n+pubsub\r\n+message\r\n+channel\r\n+message\r\n")
  assert [b"pubsub", b"message", b"channel", b"message"] == reader.gets()

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
