from distutils.core import setup, Extension
import sys, os, glob

# Compile hiredis as static library when setup.py is used directly. (I'm aware
# this is a big hack, but I don't how this is done properly with disttools).
if __name__ == "__main__":
  # Initialize submodule when not present
  if not os.path.isdir("vendor/hiredis"):
    os.system("git submodule update --init")
  cwd = os.getcwd()
  os.chdir("vendor/hiredis")

  # Python shipped with OSX needs all architectures to be compiled
  if sys.platform == "darwin":
    os.putenv("OBJARCH","-arch ppc -arch i386 -arch x86_64")

  os.system("make static")
  os.chdir(cwd)

ext = Extension("hiredis.hiredis",
  sources=glob.glob("src/*.c"),
  include_dirs=["src", "vendor"],
  library_dirs=["vendor/hiredis"],
  libraries=["hiredis"])

setup(
    name="hiredis",
    version="0.0.1",
    description="Python extension that wraps hiredis",
    url="https://github.com/pietern/hiredis-py",
    author="Pieter Noordhuis",
    author_email="pcnoordhuis@gmail.com",
    keywords=["Redis"],
    license="BSD",
    packages=["hiredis"],
    ext_modules=[ext])
