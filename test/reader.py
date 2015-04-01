# coding=utf-8
from unittest import *
import hiredis
import sys

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

  def test_fail_with_wrong_reply_error_class(self):
    self.assertRaises(TypeError, hiredis.Reader, replyError="wrong")

  def test_errors_in_nested_multi_bulk(self):
    self.reader.feed(b"*2\r\n-err0\r\n-err1\r\n")

    for r, error in zip(("err0", "err1"), self.reply()):
      self.assertEquals(hiredis.ReplyError, type(error))
      self.assertEquals((r,), error.args)

  def test_integer(self):
    value = 2**63-1 # Largest 64-bit signed integer
    self.reader.feed((":%d\r\n" % value).encode("ascii"))
    self.assertEquals(value, self.reply())

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

  def test_bulk_string_with_other_encoding(self):
    snowman = b"\xe2\x98\x83"
    self.reader = hiredis.Reader(encoding="utf-32")
    self.reader.feed(b"$3\r\n" + snowman + b"\r\n")
    self.assertEquals(snowman, self.reply())

  def test_bulk_string_with_invalid_encoding(self):
    self.reader = hiredis.Reader(encoding="unknown")
    self.reader.feed(b"$5\r\nhello\r\n")
    self.assertRaises(LookupError, self.reply)

  def test_null_multi_bulk(self):
    self.reader.feed(b"*-1\r\n")
    self.assertEquals(None, self.reply())

  def test_empty_multi_bulk(self):
    self.reader.feed(b"*0\r\n")
    self.assertEquals([], self.reply())

  def test_multi_bulk(self):
    self.reader.feed(b"*2\r\n$5\r\nhello\r\n$5\r\nworld\r\n")
    self.assertEquals([b"hello", b"world"], self.reply())

  def test_multi_bulk_with_invalid_encoding_and_partial_reply(self):
    self.reader = hiredis.Reader(encoding="unknown")
    self.reader.feed(b"*2\r\n$5\r\nhello\r\n")
    self.assertEquals(False, self.reply())
    self.reader.feed(b":1\r\n")
    self.assertRaises(LookupError, self.reply)

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
    if sys.hexversion >= 0x02060000:
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
