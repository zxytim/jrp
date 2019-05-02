import rq
import argparse
from jrp import config
from redis import StrictRedis
from multiprocessing import Process


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config', nargs='+',
                        help='name:quantity')
    args = parser.parse_args() 

    redis = StrictRedis(config.REDIS_HOST, config.REDIS_PORT)
    workers = []
    with rq.Connection(redis):
        for conf in args.config:
            name, count = conf.split(':')
            count = int(count)
            queue = rq.Queue(name)

            for i in range(count):
                w = rq.Worker([queue], name='{}:{}'.format(name, i))
                workers.append(w)

    procs = [
        Process(target=w.work) for w in workers
    ]
    for p in procs:
        p.start()

    for p in procs:
        p.join()


if __name__ == '__main__':
    main()
