import argparse
import collections
import json
import logging
import signal
import threading
import time

import requests
import six
import sseclient

import pysmee


EXIT = object()
NUM_WORKERS = 5
RECONNECT_EVERY = 60 * 60  # Default is every hour
LOG = None


def decode_data(data):
    # Use OrderedDict to ensure the singature of the body matches
    json_data = json.loads(data, object_pairs_hook=collections.OrderedDict)
    body = json.dumps(json_data['body'], separators=(',', ':'))
    headers = {k: str(v) for k, v in json_data.items()
               if k not in ('query', 'body', 'host')}
    return headers, body


def send_data(where, data, do_send=True):
    headers, body = decode_data(data)
    # If it's one of my heartbeats
    logger = LOG.debug if do_send else LOG.info
    logger('Headers: %s\nBody: %s' % (headers, body))
    if do_send:
        try:
            r = requests.post(where, data=body, headers=headers)
            LOG.info('POST %s - %s' % (where, r.status_code))
        except Exception as exc:
            LOG.error('Error sending message to %s: %s' %
                      (where, exc))


class Saver(threading.Thread):
    def __init__(self, save_file):
        super(Saver, self).__init__()
        self.save_file = save_file
        if save_file:
            self.queue = six.moves.queue.Queue(maxsize=-1)
            self.start()

    def run(self):
        LOG.verbose('Saving data to %s' % self.save_file)
        with open(self.save_file, 'a+') as f:
            while True:
                data = self.queue.get(block=True)
                if data is EXIT:
                    return
                LOG.debug('Writing to disk: %s' % data)
                f.write(data)
                f.write('\n')

    def save(self, data):
        if self.save_file:
            self.queue.put(data)

    def stop_and_wait(self):
        if self.save_file:
            self.queue.put(EXIT)
            self.join()


class Worker(threading.Thread):
    queue = six.moves.queue.Queue(maxsize=-1)
    current_workers = []

    def __init__(self, source, save, url):
        super(Worker, self).__init__()
        self.source = source
        self.save = save
        self.url = url
        self.start()
        self.current_workers.append(self)

    def run(self):
        while True:
            msg = self.queue.get(block=True)
            if msg is EXIT:
                LOG.debug('%s stopping' % self.name)
                self.current_workers.remove(self)
                return

            try:
                self.process_msg(msg)
            except Exception as exc:
                LOG.error('Exception %s processing %s' % (exc, msg.event))

    def process_msg(self, msg):
        if msg.event == 'ping':
            LOG.verbose('Ping %s received' % msg.id)

        elif msg.event == 'message':
            self.save(msg.data)
            # Forward if we have url, show if not
            send_data(self.url, msg.data, do_send=bool(self.url))

        elif msg.event == 'ready':
            LOG.verbose('Connected to %s' % self.source)

        elif msg.event == 'error':
            LOG.info('Error received: %s' % msg)

        else:
            LOG.info('Unknown event %s received: %s' % (msg.event, msg))

    def stop(self):
        self.queue.put(EXIT)

    @classmethod
    def process(cls, msg):
        cls.queue.put((msg))

    @classmethod
    def stop_and_wait_all(cls):
        for worker in cls.current_workers:
            worker.stop()

        for worker in cls.current_workers:
            if worker.is_alive():
                LOG.debug('Waiting for %s to finish' % worker)
                worker.join()


class Receiver(threading.Thread):
    def __init__(self, source):
        super(Receiver, self).__init__()
        self.source = source
        self.connected = False
        self.exit = False
        self.daemon = True
        self.start()

    def run(self):
        while not self.exit:
            LOG.debug('Connecting to %s' % self.source)
            try:
                session = requests.Session()
                client = sseclient.SSEClient(self.source, session=session)

                for msg in client:
                    if self.exit:
                        self.connected = False
                        LOG.debug('Exiting')
                        return

                    self.connected = msg.event != 'close'
                    LOG.debug('Received msg: %s' %
                              msg.dump().replace('\n', '\\n'))
                    Worker.process(msg)
            except Exception as exc:
                LOG.error('Exception on receiver: %s' % exc)

    def stop(self):
        self.exit = True


class BaseParser(argparse.ArgumentParser):
    # This class is to make errors display the full help
    def error(self, message):
        self.print_help()
        print('\nerror: %s' % message)
        exit(2)


class Parser(BaseParser):
    DESCRIPTION = ("Client for smee.io's webhook payload delivery service "
                   "(v%s)" % pysmee.__version__)
    EPILOG = ("Examples:\n"
              " -Forwarding messages to a local server:\n"
              "\tpysmee forward https://smee.io/xIgtwP3rRcQWPs5e "
              "http://localhost:8010/change_hook/github\n\n"
              " -Showing messages and saving them for later:\n"
              "\tpysmee show https://smee.io/xIgtwP3rRcQWPs5e "
              "--save output.txt"
              "\n\n -Sending saved messages back to smee.io:\n"
              "\tpysmee send https://smee.io/xIgtwP3rRcQWPs5e saved.txt\n\n"
              "\n -Sending saved messages to a local server:\n"
              "\tpysmee send http://localhost:8010/change_hook/github "
              "saved.txt")

    def __add_action(self, action, help, func, is_client=True):
        parser = self.subparsers.add_parser(action, help=help)
        parser.set_defaults(target=None)
        parser.set_defaults(filename=None)
        parser.set_defaults(func=func)
        parser.add_argument('source', metavar='smee',
                            help='URL of the SMEE webhook proxy service.')
        if is_client:
            parser.add_argument('--save', dest='filename',
                                help='Name of the file to save messages')
            parser.add_argument('--reconnect', default=RECONNECT_EVERY,
                                type=int,
                                help=('Reconnect to server every N seconds. '
                                      'Default: %s' % RECONNECT_EVERY))
            parser.add_argument('--workers', default=NUM_WORKERS,
                                type=int,
                                help=('Number of reception workers. '
                                      'Default: %s' % NUM_WORKERS))
        return parser

    def __init__(self, sender, receiver):
        super(Parser, self).__init__(
            prog='pysmee',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=self.DESCRIPTION, epilog=self.EPILOG)
        self.add_argument('-v', '--verbose', action='count', default=0,
                          help='Enable verbose mode.')

        self.subparsers = self.add_subparsers(title='action',
                                              help='sub-command help',
                                              dest='action',
                                              parser_class=BaseParser)

        self.__add_action('show', 'display received messages', receiver)
        parser = self.__add_action('forward',
                                   'Forward messages to HTTP server', receiver)
        parser.add_argument('target',
                            help=('Full URL (including protocol and '
                                  'path) of the target to send messages to.'))

        parser = self.__add_action('send', 'send messages to smee from a file',
                                   sender, is_client=False)
        parser.add_argument('filename',
                            help='Name of the file with the messages')

    def parse_args(self):
        args = super(Parser, self).parse_args()
        # Python 2 doesn't support required for the suparser, so we check it
        if not args.action:
            self.error('action argument is required')
        return args


class Main(object):
    def __init__(self):
        parser = Parser(self.sender, self.receiver)
        args = parser.parse_args()
        self.set_logging(args.verbose)
        args.func(args)

    @staticmethod
    def set_logging(verbosity):
        def verbose_msg(self, message, *args, **kws):
            if self.isEnabledFor(logging.VERBOSE):
                # Yes, logger takes its '*args' as 'args'.
                self._log(logging.VERBOSE, message, args, **kws)

        global LOG

        logging.VERBOSE = 15
        LOG_LEVELS = {0: logging.INFO, 1: logging.VERBOSE}
        logging.addLevelName(logging.VERBOSE, 'VERBOSE')
        logging.Logger.verbose = verbose_msg

        level = LOG_LEVELS.get(verbosity, logging.DEBUG)
        logging.basicConfig(
            format='[%(asctime)s %(threadName)s] %(levelname)s: %(message)s',
            level=logging.DEBUG)
        LOG = logging.getLogger()
        LOG.setLevel(level)

    def get_signal_handler(self):
        def signal_handler(sig, frame):
            LOG.verbose('Stopping')
            # Receivers are daemons, no real need to wait for them to stop
            for receiver in self.receivers:
                receiver.stop()
            Worker.stop_and_wait_all()
            self.saver.stop_and_wait()
            exit(0)

        return signal_handler

    def receiver(self, args):
        if args.target:
            LOG.info('Forwarding %s to %s' % (args.source, args.target))
        else:
            LOG.info('Showing messages from %s' % args.source)

        self.saver = Saver(args.filename)
        for _ in range(args.workers):
            Worker(args.source, self.saver.save, args.target)
        LOG.debug('Started %s workers' % args.workers)
        signal.signal(signal.SIGINT, self.get_signal_handler())

        self.receivers = [Receiver(args.source)]
        while True:
            time.sleep(args.reconnect)
            LOG.debug('Replacing receiver thread')
            new_receiver = Receiver(args.source)
            self.receivers.append(new_receiver)
            while not new_receiver.connected:
                time.sleep(0.01)
            LOG.debug('Stopping old receiver thread')
            self.receivers.pop(0).stop()

    @classmethod
    def sender(cls, args):
        LOG.info('Sending contents of %s' % args.filename)
        with open(args.filename, 'r') as f:
            for i, line in enumerate(f.readlines()):
                line = line.strip()
                if line:
                    LOG.info('Sending line %s' % (i + 1))
                    LOG.debug('Line: %s' % line)
                    send_data(args.source, line)
