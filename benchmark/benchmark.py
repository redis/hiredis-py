import sys, optparse, timeit
from functools import partial
from redis import Redis

parser = optparse.OptionParser()
parser.add_option("-n", dest="count", metavar="COUNT", default=10000)
(options, args) = parser.parse_args()

redis = Redis(host="localhost", port=6379, db=0)
commands = list()
for line in sys.stdin.readlines():
  argv = line.strip().split()
  fn = getattr(redis, argv.pop(0))
  commands.append(partial(fn, *argv))

def run():
  for fn in commands:
    fn()

timer = timeit.Timer(run)
count = int(options.count)
numops = len(commands)
print "%.2f Kops" % ((numops * count / 1000.0) / timer.timeit(number=count))

