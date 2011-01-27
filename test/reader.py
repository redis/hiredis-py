from unittest import *
import hiredis

class ReaderTest(TestCase):
  def setUp(self):
    self.reader = hiredis.Reader()

  def reply(self):
    return self.reader.gets()

  def test_nothing(self):
    self.assertEquals(False, self.reply())

  def test_string(self):
    self.reader.feed("$5\r\nhello\r\n")
    self.assertEquals("hello", self.reply())
