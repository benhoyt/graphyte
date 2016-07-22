# graphyte

graphyte is a small Python library that sends data to a Graphite metrics
server (Carbon). We wrote it because the existing
[graphitesend](https://github.com/daniellawrence/graphitesend) library didn't
support Python 3, and it also required gevent for asyncronous use. graphyte
is compatible with Python 3.4+ as well as Python 2.7, and uses the standard
library's `threading` module for asynchronous use.

Using graphyte is simple -- just call `init()` to initialize the default
sender and then `send()` to send a message. For example, to send
`system.sync.foo.bar 42 {timestamp}\n` to graphite.example.com:2003
synchronously:

```python
import graphyte
graphyte.init('graphite.example.com', prefix='system.sync')
graphyte.send('foo.bar', 42)
```

If you want to send asynchronously on a background thread (for example, in a
web server context), just specify a send interval. For example, this will
setup a background thread to send every 10 seconds:

```python
graphyte.init('graphite.example.com', prefix='system.async', interval=10)
graphyte.send('foo.bar', 42)
```

For more advanced usage, for example if you want to send to multiple servers
or if you want to subclass `Sender`, you can instantiate instances of `Sender`
directly. For example, to instantiate two senders sending to different servers
(one synchronous, one using a background thread with send interval 10 seconds),
use something like the following:

```python
sender1 = graphyte.Sender('graphite1.example.com', prefix='system.one')
sender2 = graphyte.Sender('graphite2.example.com', prefix='system.two', interval=10)
sender1.send('foo.bar1', 42)
sender2.send('foo.bar2', 43)
```

Or, to customize how messages are logged or sent to the socket, subclass
`Sender` and override `send_socket`:

```python
class CustomSender(graphyte.Sender):
    def send_socket(self, message):
        print('Sending bytes in some custom way: {!r}'.format(message))
```

Socket sending errors are logged using the Python logging system (using logger
name "graphyte"). If the sender is initialized with `log_sends=True`, all
sends are logged at the INFO level.

You can also use graphyte to send metrics directly from the command line:

    python -m graphyte foo.bar 42

There are command line arguments to specify the server and port and other
configuration. Type `python -m graphyte --help` for help.

Read the code in [graphyte.py](https://github.com/Jetsetter/graphyte/blob/master/graphyte.py)
for more details -- it's pretty small!

graphyte was written by [Ben Hoyt](http://benhoyt.com/) for
[Jetsetter](http://www.jetsetter.com/) and is licensed with a permissive MIT
license (see
[LICENSE.txt](https://github.com/Jetsetter/graphyte/blob/master/LICENSE.txt)).
