#!/usr/bin/env python

import sys, optparse, timeit
from functools import partial
from redis import Redis

import gevent
from gevent import monkey
from gevent.coros import Semaphore
monkey.patch_all()

parser = optparse.OptionParser()
parser.add_option("-n", dest="count", metavar="COUNT", type="int", default=10000)
parser.add_option("-c", dest="clients", metavar="CLIENTS", type="int", default=1),
(options, args) = parser.parse_args()

commands = list()
for line in sys.stdin.readlines():
  argv = line.strip().split()
  commands.append((argv[0], argv[1:]))

sem = Semaphore(0)
count = options.count
todo = count

def create_client():
  global todo
  redis = Redis(host="localhost", port=6379, db=0)

  sem.acquire()
  while todo > 0:
    todo -= 1
    for (cmd, args) in commands:
      getattr(redis, cmd)(*args)

def run(clients):
  [sem.release() for _ in range(len(clients))]

  # Time how long it takes for all greenlets to finish
  join = partial(gevent.joinall, clients)
  time = timeit.timeit(join, number=1)
  print "%.2f Kops" % ((len(commands) * count / 1000.0) / time)

# Let clients connect, and kickstart benchmark a little later
clients = [gevent.spawn(create_client) for _ in range(options.clients)]
let = gevent.spawn(run, clients)
gevent.joinall([let])
