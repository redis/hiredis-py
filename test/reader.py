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

  def test_integer(self):
    value = 2**63-1 # Largest 64-bit signed integer
    self.reader.feed(":%d\r\n" % value)
    self.assertEquals(value, self.reply())

  def test_status_string(self):
    self.reader.feed("+ok\r\n")
    self.assertEquals("ok", self.reply())

  def test_empty_bulk_string(self):
    self.reader.feed("$0\r\n\r\n")
    self.assertEquals("", self.reply())

  def test_bulk_string(self):
    self.reader.feed("$5\r\nhello\r\n")
    self.assertEquals("hello", self.reply())

  def test_null_multi_bulk(self):
    self.reader.feed("*-1\r\n")
    self.assertEquals(None, self.reply())

  def test_empty_multi_bulk(self):
    self.reader.feed("*0\r\n")
    self.assertEquals([], self.reply())

  def test_multi_bulk(self):
    self.reader.feed("*2\r\n$5\r\nhello\r\n$5\r\nworld\r\n")
    self.assertEquals(["hello", "world"], self.reply())

  def test_nested_multi_bulk(self):
    self.reader.feed("*2\r\n*2\r\n$5\r\nhello\r\n$5\r\nworld\r\n$1\r\n!\r\n")
    self.assertEquals([["hello", "world"], "!"], self.reply())
