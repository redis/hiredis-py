import glob, os.path, sys

# Add path to hiredis.so load path
path = glob.glob("build/lib*/hiredis/*.so")[0]
sys.path.insert(0, os.path.dirname(path))

from unittest import *
import reader

def tests():
  suite = TestSuite()
  suite.addTest(makeSuite(reader.ReaderTest))
  return suite
