import glob, os.path, sys

version = sys.version.split(" ")[0]
majorminor = version[0:3]

from unittest import *
from . import reader

def tests():
  suite = TestSuite()
  suite.addTest(makeSuite(reader.ReaderTest))
  return suite
