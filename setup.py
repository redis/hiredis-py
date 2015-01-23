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

# To link the extension with the C library, distutils passes the "-lLIBRARY"
# option to the linker. This makes it go through its library search path. If it
# finds a shared object of the specified library in one of the system-wide
# library paths, it will dynamically link it.
#
# We want the linker to statically link the version of hiredis that is included
# with hiredis-py. However, the linker may pick up the shared library version
# of hiredis, if it is available through one of the system-wide library paths.
# To prevent this from happening, we use an obfuscated library name such that
# the only version the linker will be able to find is the right version.
#
# This is a terrible hack, but patching distutils to do the right thing for all
# supported Python versions is worse...
#
# Also see: https://github.com/pietern/hiredis-py/issues/15
lib = ("hiredis_for_hiredis_py", {
  "sources": ["vendor/hiredis/%s.c" % src for src in ("read", "sds")]})

ext = Extension("hiredis.hiredis",
  sources=glob.glob("src/*.c"),
  include_dirs=["vendor"])

setup(
  name="hiredis",
  version=version(),
  description="Python wrapper for hiredis",
  url="https://github.com/redis/hiredis-py",
  author="Pieter Noordhuis",
  author_email="pcnoordhuis@gmail.com",
  keywords=["Redis"],
  license="BSD",
  packages=["hiredis"],
  libraries=[lib],
  ext_modules=[ext],

  # Override "install_lib" command
  cmdclass={ "install_lib": install_lib },

  classifiers=[
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: MacOS',
    'Operating System :: POSIX',
    'Programming Language :: C',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.2',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: Implementation :: CPython',
    'Topic :: Software Development',
  ],
)
