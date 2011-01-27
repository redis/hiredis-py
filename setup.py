from distutils.core import setup, Extension

hiredis = Extension("hiredis",
  sources=["src/hiredis.c", "src/reader.c"],
  include_dirs=["src", "vendor"],
  library_dirs=["vendor/hiredis"],
  extra_link_args=["-lhiredis"])

setup(name="hiredis", version="0.0.1", ext_modules=[hiredis])

