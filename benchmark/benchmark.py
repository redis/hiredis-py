#!/usr/bin/env python

import sys, optparse, timeit
from functools import partial
from redis import Redis

import gevent
from gevent import monkey
from gevent.coros import Semaphore
monkey.patch_socket()

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

def start_clients(clients):
  [sem.release() for _ in range(len(clients))]
  gevent.joinall(clients)

start = partial(start_clients, [gevent.spawn(create_client) for _ in range(options.clients)])
time = timeit.timeit(start, number=1)
print "%.2f Kops" % ((len(commands) * count / 1000.0) / time)
