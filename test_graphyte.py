"""Unit tests for the graphyte module."""

import re
try:
    import socketserver
except ImportError:
    import SocketServer as socketserver  # Python 2.x compatibility
import time
import unittest

import graphyte


class TestSender(graphyte.Sender):
    def __init__(self, *args, **kwargs):
        graphyte.Sender.__init__(self, 'dummy_host', *args, **kwargs)
        self.messages = []

    def send_socket(self, message):
        self.messages.append(message)

    def pop_message(self):
        assert self.messages, 'no messages sent'
        return self.messages.pop(0)


class TestHandler(socketserver.BaseRequestHandler):
    messages = []

    def handle(self):
        if isinstance(self.request, tuple):
            message, sock = self.request  # UDP
        else:
            message = self.request.recv(1024)  # TCP
        self.messages.append(message)

    @classmethod
    def pop_message(cls):
        assert cls.messages, 'no messages sent'
        return cls.messages.pop(0)


class TestBuildMessage(unittest.TestCase):
    def test_no_prefix(self):
        sender = TestSender()
        self.assertEqual(sender.build_message('foo.bar', 42, 12345),
                         b'foo.bar 42 12345\n')
        self.assertEqual(sender.build_message('boo.far', 42.1, 12345.6),
                         b'boo.far 42.1 12346\n')

    def test_unicode(self):
        sender = TestSender()
        self.assertEqual(sender.build_message(u'\u201cfoo.bar\u201d', 42, 12345),
                         b'\xe2\x80\x9cfoo.bar\xe2\x80\x9d 42 12345\n')

    def test_prefix(self):
        sender = TestSender(prefix='pr.efix')
        self.assertEqual(sender.build_message('boo.far', 567, 12347),
                         b'pr.efix.boo.far 567 12347\n')

    def test_exceptions(self):
        sender = TestSender()
        with self.assertRaises(TypeError):
            sender.build_message('foo.bar', 'x', 12346)
        with self.assertRaises(ValueError):
            sender.build_message('foo bar', 42, 12346)


class TestSynchronous(unittest.TestCase):
    def test_timestamp_specified(self):
        sender = TestSender()
        sender.send('foo', 42, timestamp=12345)
        self.assertEqual(sender.pop_message(), b'foo 42 12345\n')

    def test_timestamp_generated(self):
        sender = TestSender()
        send_time = time.time()
        sender.send('foo', 42)
        match = re.match(b'^foo 42 (\\d+)\\n$', sender.pop_message())
        self.assertIsNotNone(match)
        timestamp = int(match.group(1))
        self.assertTrue(send_time - 2 <= timestamp <= send_time + 2)


class TestSendSocketTCP(unittest.TestCase):
    def setUp(self):
        self.server = socketserver.TCPServer(('127.0.0.1', 2003), TestHandler)
        self.server.timeout = 1.0

    def tearDown(self):
        self.server.server_close()

    def test_send_socket(self):
        graphyte.init('127.0.0.1')
        graphyte.send('foo', 42, timestamp=12345)
        graphyte.send('bar', 43.5, timestamp=12346)
        self.server.handle_request()
        self.server.handle_request()
        self.assertEqual(TestHandler.pop_message(), b'foo 42 12345\n')
        self.assertEqual(TestHandler.pop_message(), b'bar 43.5 12346\n')


class TestSendSocketUDP(unittest.TestCase):
    def setUp(self):
        self.server = socketserver.UDPServer(('127.0.0.1', 2003), TestHandler)
        self.server.timeout = 1.0

    def tearDown(self):
        self.server.server_close()

    def test_send_socket(self):
        graphyte.init('127.0.0.1', protocol='udp')
        graphyte.send('foo', 42, timestamp=12345)
        graphyte.send('bar', 43.5, timestamp=12346)
        self.server.handle_request()
        self.server.handle_request()
        self.assertEqual(TestHandler.pop_message(), b'foo 42 12345\n')
        self.assertEqual(TestHandler.pop_message(), b'bar 43.5 12346\n')


class TestInterval(unittest.TestCase):
    def setUp(self):
        self.sender = TestSender(interval=0.1)

    def tearDown(self):
        self.sender.stop()

    def test_stop_after_message(self):
        self.sender.send('foo', 42, timestamp=12345)
        self.sender.stop()
        self.assertEqual(self.sender.pop_message(), b'foo 42 12345\n')

    def test_stop_immediately(self):
        self.sender.stop()
        self.assertEqual(self.sender.messages, [])

    def test_send_none(self):
        time.sleep(0.2)
        self.assertEqual(self.sender.messages, [])

    def test_send_one(self):
        self.sender.send('foo', 42, timestamp=12345)
        time.sleep(0.2)
        self.assertEqual(self.sender.pop_message(), b'foo 42 12345\n')

    def test_send_multiple(self):
        self.sender.send('foo', 42, timestamp=12345)
        self.sender.send('bar', 43, timestamp=12346)
        self.sender.send('baz', 44, timestamp=12347)
        time.sleep(0.2)
        self.assertEqual(self.sender.pop_message(),
                         b'foo 42 12345\nbar 43 12346\nbaz 44 12347\n')

        self.sender.send('buz', 45, timestamp=12348)
        time.sleep(0.2)
        self.assertEqual(self.sender.pop_message(), b'buz 45 12348\n')


if __name__ == '__main__':
    unittest.main()
