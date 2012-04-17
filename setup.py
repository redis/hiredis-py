#!/usr/bin/env python
from distutils.core import setup, Extension
from distutils.command import install_lib as _install_lib
import sys, imp, os, glob

def version():
  module = imp.load_source("hiredis.version", "hiredis/version.py")
  return module.__version__

# Patch "install_lib" command to run build_clib before build_ext
# to properly work with easy_install.
# See: http://bugs.python.org/issue5243
class install_lib(_install_lib.install_lib):
  def build(self):
    if not self.skip_build:
      if self.distribution.has_pure_modules():
        self.run_command('build_py')
        if self.distribution.has_c_libraries():
          self.run_command('build_clib')
        if self.distribution.has_ext_modules():
          self.run_command('build_ext')

lib = ("hiredis", {
  "sources": ["vendor/hiredis/%s.c" % src for src in ("hiredis", "net", "sds")],
  "include_dirs": ["vendor/hiredis"]})

ext = Extension("hiredis.hiredis",
  sources=glob.glob("src/*.c"),
  include_dirs=["src", "vendor"],
  libraries=["hiredis"])

setup(
  name="hiredis",
  version=version(),
  description="Python extension that wraps hiredis",
  url="https://github.com/pietern/hiredis-py",
  author="Pieter Noordhuis",
  author_email="pcnoordhuis@gmail.com",
  keywords=["Redis"],
  license="BSD",
  packages=["hiredis"],
  libraries=[lib],
  ext_modules=[ext],

  # Override "install_lib" command
  cmdclass={ "install_lib": install_lib },
)
