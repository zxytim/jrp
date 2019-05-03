import argparse
from jrp import config
from redis import StrictRedis
from multiprocessing import Process
from setproctitle import setproctitle

import time

import rq
from rq.queue import FailedQueue


def start_worker(worker):
    setproctitle('rq-worker:{}'.format(worker.name))
    worker.work()


class Task:
    def init_parser(self, parser):
        pass

    def run(self, args):
        pass



def parse_queue_config(config):
    """
    :param config: a list of string of format "<name>:<quantity>"
    """
    rst = []
    for conf in config:
        name, count = conf.split(':')
        count = int(count)
        rst.append((name, count))
    return rst


class RQWorker(Task):
    def init_parser(self, parser):
        parser.add_argument(
            'config', nargs='+', help='name:quantity')

    def run(self, args):
        redis = StrictRedis(config.REDIS_HOST, config.REDIS_PORT)
        workers = []

        queue_config = parse_queue_config(args.config)
        with rq.Connection(redis):
            for name, count in queue_config:
                queue = rq.Queue(name)

                for i in range(count):
                    w = rq.Worker([queue], name='{}:{}'.format(name, i))
                    workers.append(w)

        procs = [
            Process(target=start_worker, args=(w, )) for w in workers
        ]
        for p in procs:
            p.start()

        for p in procs:
            p.join()


class RQFailureRecover(Task):
    def init_parser(self, parser):
        parser.add_argument(
            'queue_names', nargs='+', help='one name at a time')

    def run(self, args):
        redis = StrictRedis(config.REDIS_HOST, config.REDIS_PORT)

        names = args.queue_names
        fq = FailedQueue(connection=redis)

        def check_fjob(fjob):
            if fjob.origin not in names:
                return False

            # XXX: Damn... Should change to another database soon
            if isinstance(fjob.exc_info, str):
                permitted_errors = [
                    'sqlite3.OperationalError: database is locked',
                    'rq.timeouts.JobTimeoutException: Task exceeded maximum timeout value',
                    'pdftotext',
                    'not pdf, but `text/xml`',
                ]
                for s in permitted_errors:
                    if s in fjob.exc_info:
                        return True

            return False

        while True:
            count = 0

            fjobs = fq.get_jobs()
            for fjob in fjobs:
                if check_fjob(fjob):
                    fq.requeue(fjob.id)
                    count += 1

            print('{} failed jobs: {} requeued, {} remains'.format(
                len(fjobs), count, len(fjobs) - count)
            )
            time.sleep(60)


def main():
    parser = argparse.ArgumentParser()

    tasks = [
        ('rq-worker', RQWorker()),
        ('rq-failure-recover', RQFailureRecover()),
    ]

    subparsers = parser.add_subparsers(
        dest='task', required=True)

    for name, task in tasks:
        subp = subparsers.add_parser(name)
        task.init_parser(subp)
        subp.set_defaults(func=task.run)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
