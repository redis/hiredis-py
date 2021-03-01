# coding=utf-8
from unittest import *
import hiredis


class ReaderTest(TestCase):
  def setUp(self):
    self.reader = hiredis.Reader()

  def reply(self):
    return self.reader.gets()

  def test_nothing(self):
    self.assertEquals(False, self.reply())

  def test_error_when_feeding_non_string(self):
    self.assertRaises(TypeError, self.reader.feed, 1)

  def test_protocol_error(self):
    self.reader.feed(b"x")
    self.assertRaises(hiredis.ProtocolError, self.reply)

  def test_protocol_error_with_custom_class(self):
    self.reader = hiredis.Reader(protocolError=RuntimeError)
    self.reader.feed(b"x")
    self.assertRaises(RuntimeError, self.reply)

  def test_protocol_error_with_custom_callable(self):
    class CustomException(Exception):
      pass

    self.reader = hiredis.Reader(protocolError=lambda e: CustomException(e))
    self.reader.feed(b"x")
    self.assertRaises(CustomException, self.reply)

  def test_fail_with_wrong_protocol_error_class(self):
    self.assertRaises(TypeError, hiredis.Reader, protocolError="wrong")

  def test_faulty_protocol_error_class(self):
    def make_error(errstr):
      1 / 0
    self.reader = hiredis.Reader(protocolError=make_error)
    self.reader.feed(b"x")
    self.assertRaises(ZeroDivisionError, self.reply)

  def test_error_string(self):
    self.reader.feed(b"-error\r\n")
    error = self.reply()

    self.assertEquals(hiredis.ReplyError, type(error))
    self.assertEquals(("error",), error.args)

  def test_error_string_with_custom_class(self):
    self.reader = hiredis.Reader(replyError=RuntimeError)
    self.reader.feed(b"-error\r\n")
    error = self.reply()

    self.assertEquals(RuntimeError, type(error))
    self.assertEquals(("error",), error.args)

  def test_error_string_with_custom_callable(self):
    class CustomException(Exception):
      pass

    self.reader = hiredis.Reader(replyError=lambda e: CustomException(e))
    self.reader.feed(b"-error\r\n")
    error = self.reply()

    self.assertEquals(CustomException, type(error))
    self.assertEquals(("error",), error.args)

  def test_error_string_with_non_utf8_chars(self):
    self.reader.feed(b"-error \xd1\r\n")
    error = self.reply()

    expected = "error \ufffd"

    self.assertEquals(hiredis.ReplyError, type(error))
    self.assertEquals((expected,), error.args)

  def test_fail_with_wrong_reply_error_class(self):
    self.assertRaises(TypeError, hiredis.Reader, replyError="wrong")

  def test_faulty_reply_error_class(self):
    def make_error(errstr):
      1 / 0

    self.reader = hiredis.Reader(replyError=make_error)
    self.reader.feed(b"-error\r\n")
    self.assertRaises(ZeroDivisionError, self.reply)

  def test_errors_in_nested_multi_bulk(self):
    self.reader.feed(b"*2\r\n-err0\r\n-err1\r\n")

    for r, error in zip(("err0", "err1"), self.reply()):
      self.assertEquals(hiredis.ReplyError, type(error))
      self.assertEquals((r,), error.args)

  def test_errors_with_non_utf8_chars_in_nested_multi_bulk(self):
    self.reader.feed(b"*2\r\n-err\xd1\r\n-err1\r\n")

    expected = "err\ufffd"

    for r, error in zip((expected, "err1"), self.reply()):
      self.assertEquals(hiredis.ReplyError, type(error))
      self.assertEquals((r,), error.args)

  def test_integer(self):
    value = 2**63-1 # Largest 64-bit signed integer
    self.reader.feed((":%d\r\n" % value).encode("ascii"))
    self.assertEquals(value, self.reply())

  def test_float(self):
    value = -99.99
    self.reader.feed(b",%f\r\n" % value)
    self.assertEqual(value, self.reply())

  def test_boolean_true(self):
    self.reader.feed(b"#t\r\n")
    self.assertTrue(self.reply())

  def test_boolean_false(self):
    self.reader.feed(b"#f\r\n")
    self.assertFalse(False, self.reply())

  def test_none(self):
    self.reader.feed(b"_\r\n")
    self.assertIsNone(self.reply())

  def test_set(self):
    self.reader.feed(b"~3\r\n+tangerine\r\n_\r\n,10.5\r\n")
    self.assertEqual({b"tangerine", None, 10.5}, self.reply())

  def test_dict(self):
    self.reader.feed(b"%2\r\n+radius\r\n,4.5\r\n+diameter\r\n:9\r\n")
    self.assertEqual({b"radius": 4.5, b"diameter": 9}, self.reply())

  def test_vector(self):
    self.reader.feed(b">4\r\n+pubsub\r\n+message\r\n+channel\r\n+message\r\n")
    self.assertEqual(
      [b"pubsub", b"message", b"channel", b"message"], self.reply()
    )

  def test_verbatim_string(self):
    value = b"text"
    self.reader.feed(b"=8\r\ntxt:%s\r\n" % value)
    self.assertEqual(value, self.reply())

  def test_status_string(self):
    self.reader.feed(b"+ok\r\n")
    self.assertEquals(b"ok", self.reply())

  def test_empty_bulk_string(self):
    self.reader.feed(b"$0\r\n\r\n")
    self.assertEquals(b"", self.reply())

  def test_bulk_string(self):
    self.reader.feed(b"$5\r\nhello\r\n")
    self.assertEquals(b"hello", self.reply())

  def test_bulk_string_without_encoding(self):
    snowman = b"\xe2\x98\x83"
    self.reader.feed(b"$3\r\n" + snowman + b"\r\n")
    self.assertEquals(snowman, self.reply())

  def test_bulk_string_with_encoding(self):
    snowman = b"\xe2\x98\x83"
    self.reader = hiredis.Reader(encoding="utf-8")
    self.reader.feed(b"$3\r\n" + snowman + b"\r\n")
    self.assertEquals(snowman.decode("utf-8"), self.reply())

  def test_decode_errors_defaults_to_strict(self):
    self.reader = hiredis.Reader(encoding="utf-8")
    self.reader.feed(b"+\x80\r\n")
    self.assertRaises(UnicodeDecodeError, self.reader.gets)

  def test_decode_error_with_ignore_errors(self):
    self.reader = hiredis.Reader(encoding="utf-8", errors="ignore")
    self.reader.feed(b"+\x80value\r\n")
    self.assertEquals("value", self.reader.gets())

  def test_decode_error_with_surrogateescape_errors(self):
    self.reader = hiredis.Reader(encoding="utf-8", errors="surrogateescape")
    self.reader.feed(b"+\x80value\r\n")
    self.assertEquals("\udc80value", self.reader.gets())

  def test_invalid_encoding(self):
    self.assertRaises(LookupError, hiredis.Reader, encoding="unknown")

  def test_invalid_encoding_error_handler(self):
    self.assertRaises(LookupError, hiredis.Reader, errors="unknown")

  def test_should_decode_false_flag_prevents_decoding(self):
    snowman = b"\xe2\x98\x83"
    self.reader = hiredis.Reader(encoding="utf-8")
    self.reader.feed(b"$3\r\n" + snowman + b"\r\n")
    self.reader.feed(b"$3\r\n" + snowman + b"\r\n")
    self.assertEquals(snowman, self.reader.gets(False))
    self.assertEquals(snowman.decode("utf-8"), self.reply())

  def test_should_decode_true_flag_decodes_as_normal(self):
    snowman = b"\xe2\x98\x83"
    self.reader = hiredis.Reader(encoding="utf-8")
    self.reader.feed(b"$3\r\n" + snowman + b"\r\n")
    self.assertEquals(snowman.decode("utf-8"), self.reader.gets(True))

  def test_set_encoding_with_different_encoding(self):
    snowman_utf8 = b"\xe2\x98\x83"
    snowman_utf16 = b"\xff\xfe\x03&"
    self.reader = hiredis.Reader(encoding="utf-8")
    self.reader.feed(b"$3\r\n" + snowman_utf8 + b"\r\n")
    self.reader.feed(b"$4\r\n" + snowman_utf16 + b"\r\n")
    self.assertEquals(snowman_utf8.decode('utf-8'), self.reader.gets())
    self.reader.set_encoding(encoding="utf-16", errors="strict")
    self.assertEquals(snowman_utf16.decode('utf-16'), self.reader.gets())

  def test_set_encoding_to_not_decode(self):
    snowman = b"\xe2\x98\x83"
    self.reader = hiredis.Reader(encoding="utf-8")
    self.reader.feed(b"$3\r\n" + snowman + b"\r\n")
    self.reader.feed(b"$3\r\n" + snowman + b"\r\n")
    self.assertEquals(snowman.decode('utf-8'), self.reader.gets())
    self.reader.set_encoding(encoding=None, errors=None)
    self.assertEquals(snowman, self.reader.gets())

  def test_set_encoding_invalid_encoding(self):
    self.reader = hiredis.Reader(encoding="utf-8")
    self.assertRaises(LookupError, self.reader.set_encoding, encoding="unknown")

  def test_set_encoding_invalid_error_handler(self):
    self.reader = hiredis.Reader(encoding="utf-8")
    self.assertRaises(LookupError, self.reader.set_encoding, encoding="utf-8", errors="unknown")

  def test_null_multi_bulk(self):
    self.reader.feed(b"*-1\r\n")
    self.assertEquals(None, self.reply())

  def test_empty_multi_bulk(self):
    self.reader.feed(b"*0\r\n")
    self.assertEquals([], self.reply())

  def test_multi_bulk(self):
    self.reader.feed(b"*2\r\n$5\r\nhello\r\n$5\r\nworld\r\n")
    self.assertEquals([b"hello", b"world"], self.reply())

  def test_nested_multi_bulk(self):
    self.reader.feed(b"*2\r\n*2\r\n$5\r\nhello\r\n$5\r\nworld\r\n$1\r\n!\r\n")
    self.assertEquals([[b"hello", b"world"], b"!"], self.reply())

  def test_nested_multi_bulk_depth(self):
    self.reader.feed(b"*1\r\n*1\r\n*1\r\n*1\r\n$1\r\n!\r\n")
    self.assertEquals([[[[b"!"]]]], self.reply())

  def test_subclassable(self):
    class TestReader(hiredis.Reader):
      def __init__(self, *args, **kwargs):
        super(TestReader, self).__init__(*args, **kwargs)

    reader = TestReader()
    reader.feed(b"+ok\r\n")
    self.assertEquals(b"ok", reader.gets())

  def test_invalid_offset(self):
    data = b"+ok\r\n"
    self.assertRaises(ValueError, self.reader.feed, data, 6)

  def test_invalid_length(self):
    data = b"+ok\r\n"
    self.assertRaises(ValueError, self.reader.feed, data, 0, 6)

  def test_ok_offset(self):
    data = b"blah+ok\r\n"
    self.reader.feed(data, 4)
    self.assertEquals(b"ok", self.reply())

  def test_ok_length(self):
    data = b"blah+ok\r\n"
    self.reader.feed(data, 4, len(data)-4)
    self.assertEquals(b"ok", self.reply())

  def test_feed_bytearray(self):
    self.reader.feed(bytearray(b"+ok\r\n"))
    self.assertEquals(b"ok", self.reply())

  def test_maxbuf(self):
    defaultmaxbuf = self.reader.getmaxbuf()
    self.reader.setmaxbuf(0)
    self.assertEquals(0, self.reader.getmaxbuf())
    self.reader.setmaxbuf(10000)
    self.assertEquals(10000, self.reader.getmaxbuf())
    self.reader.setmaxbuf(None)
    self.assertEquals(defaultmaxbuf, self.reader.getmaxbuf())
    self.assertRaises(ValueError, self.reader.setmaxbuf, -4)

  def test_len(self):
    self.assertEquals(0, self.reader.len())
    data = b"+ok\r\n"
    self.reader.feed(data)
    self.assertEquals(len(data), self.reader.len())

    # hiredis reallocates and removes unused buffer once
    # there is at least 1K of not used data.
    calls = int((1024 / len(data))) + 1
    for i in range(calls):
        self.reader.feed(data)
        self.reply()

    self.assertEquals(5, self.reader.len())

  def test_reader_has_data(self):
    self.assertEquals(False, self.reader.has_data())
    data = b"+ok\r\n"
    self.reader.feed(data)
    self.assertEquals(True, self.reader.has_data())
    self.reply()
    self.assertEquals(False, self.reader.has_data())
