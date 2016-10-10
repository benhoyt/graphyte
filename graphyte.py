"""Send data to Graphite metrics server (synchronously or on a background thread).

For example usage, see README.md.

This code is licensed under a permissive MIT license -- see LICENSE.txt.

The graphyte project lives on GitHub here:
https://github.com/Jetsetter/graphyte
"""

import atexit
import logging
try:
    import queue
except ImportError:
    import Queue as queue  # Python 2.x compatibility
import socket
import threading
import time

__all__ = ['Sender', 'init', 'send']

__version__ = '1.1'

default_sender = None
logger = logging.getLogger(__name__)


class Sender:
    def __init__(self, host, port=2003, prefix=None, timeout=5, interval=None,
                 queue_size=None, log_sends=False, protocol='tcp'):
        """Initialize a Sender instance, starting the background thread to
        send messages at given interval (in seconds) if "interval" is not
        None. Default protocol is TCP; use protocol='udp' for UDP.
        """
        self.host = host
        self.port = port
        self.prefix = prefix
        self.timeout = timeout
        self.interval = interval
        self.log_sends = log_sends
        self.protocol = protocol

        if self.interval is not None:
            if queue_size is None:
                queue_size = int(round(interval)) * 100
            self._queue = queue.Queue(maxsize=queue_size)
            self._thread = threading.Thread(target=self._thread_loop)
            self._thread.daemon = True
            self._thread.start()
            atexit.register(self.stop)

    def __del__(self):
        self.stop()

    def stop(self):
        """Tell the sender thread to finish and wait for it to stop sending
        (should be at most "timeout" seconds).
        """
        if self.interval is not None:
            self._queue.put_nowait(None)
            self._thread.join()
            self.interval = None

    def build_message(self, metric, value, timestamp):
        """Build a Graphite message to send and return it as a byte string."""
        if not metric or metric.split(None, 1)[0] != metric:
            raise ValueError('"metric" must not have whitespace in it')
        if not isinstance(value, (int, float)):
            raise TypeError('"value" must be an int or a float, not a {}'.format(
                    type(value).__name__))

        message = u'{}{} {} {}\n'.format(
            self.prefix + '.' if self.prefix else '',
            metric,
            value,
            int(round(timestamp)),
        )
        message = message.encode('utf-8')
        return message

    def send(self, metric, value, timestamp=None):
        """Send given metric and (int or float) value to Graphite host.
        Performs send on background thread if "interval" was specified when
        creating this Sender.
        """
        if timestamp is None:
            timestamp = time.time()
        message = self.build_message(metric, value, timestamp)

        if self.interval is None:
            self.send_socket(message)
        else:
            try:
                self._queue.put_nowait(message)
            except queue.Full:
                logger.error('queue full when sending {!r}'.format(message))

    def send_message(self, message):
        if self.protocol == 'tcp':
            sock = socket.create_connection((self.host, self.port), self.timeout)
            try:
                sock.send(message)
            finally:  # sockets don't support "with" statement on Python 2.x
                sock.close()
        elif self.protocol == 'udp':
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.sendto(message, (self.host, self.port))
            finally:
                sock.close()
        else:
            raise ValueError('"protocol" must be \'tcp\' or \'udp\', not {!r}'.format(self.protocol))

    def send_socket(self, message):
        """Low-level function to send message bytes to this Sender's socket.
        You should usually call send() instead of this function (unless you're
        subclassing or writing unit tests).
        """
        if self.log_sends:
            start_time = time.time()
        try:
            self.send_message(message)
        except Exception as error:
            logger.error('error sending message {!r}: {}'.format(message, error))
        else:
            if self.log_sends:
                elapsed_time = time.time() - start_time
                logger.info('sent message {!r} to {}:{} in {:.03f} seconds'.format(
                        message, self.host, self.port, elapsed_time))

    def _thread_loop(self):
        """Background thread used when Sender is in asynchronous/interval mode."""
        last_check_time = time.time()
        messages = []
        while True:
            # Get first message from queue, blocking until the next time we
            # should be sending
            time_since_last_check = time.time() - last_check_time
            time_till_next_check = max(0, self.interval - time_since_last_check)
            try:
                message = self._queue.get(timeout=time_till_next_check)
            except queue.Empty:
                pass
            else:
                if message is None:
                    # None is the signal to stop this background thread
                    break
                messages.append(message)

                # Get any other messages currently on queue without blocking,
                # paying attention to None ("stop thread" signal)
                should_stop = False
                while True:
                    try:
                        message = self._queue.get_nowait()
                    except queue.Empty:
                        break
                    if message is None:
                        should_stop = True
                        break
                    messages.append(message)
                if should_stop:
                    break

            # If it's time to send, send what we've collected
            current_time = time.time()
            if current_time - last_check_time >= self.interval:
                last_check_time = current_time
                if messages:
                    self.send_socket(b''.join(messages))
                    messages = []

        # Send any final messages before exiting thread
        if messages:
            self.send_socket(b''.join(messages))


def init(*args, **kwargs):
    """Initialize default Sender instance with given args."""
    global default_sender
    default_sender = Sender(*args, **kwargs)


def send(*args, **kwargs):
    """Send message using default Sender instance."""
    default_sender.send(*args, **kwargs)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('metric',
                        help='name of metric to send')
    parser.add_argument('value', type=float,
                        help='numeric value to send')
    parser.add_argument('-s', '--server', default='localhost',
                        help='hostname of Graphite server to send to, default %(default)s')
    parser.add_argument('-p', '--port', type=int, default=2003,
                        help='port to send message to, default %(default)d')
    parser.add_argument('-u', '--udp', action='store_true',
                        help='send via UDP instead of TCP')
    parser.add_argument('-t', '--timestamp', type=int,
                        help='Unix timestamp for message (defaults to current time)')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help="quiet mode (don't log send to stdout)")
    args = parser.parse_args()

    if not args.quiet:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    sender = Sender(args.server, port=args.port, log_sends=not args.quiet,
                    protocol='udp' if args.udp else 'tcp')
    sender.send(args.metric, args.value, timestamp=args.timestamp)
