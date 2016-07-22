"""Run "python setup.py install" to install graphyte."""

import os
import re
from distutils.core import setup


# Because it's best not to import the module in setup.py
with open(os.path.join(os.path.dirname(__file__), 'graphyte.py')) as f:
    for line in f:
        match = re.match(r"__version__.*'([0-9.]+)'", line)
        if match:
            version = match.group(1)
            break
    else:
        raise Exception("Couldn't find __version__ line in graphyte.py")


setup(
    name='graphyte',
    version=version,
    author='Ben Hoyt',
    author_email='benhoyt@gmail.com',
    url='https://github.com/Jetsetter/graphyte',
    license='MIT License',
    description='Python 3 compatible library to send data to a Graphite metrics server (Carbon)',
    long_description='See https://github.com/Jetsetter/graphyte for details and usage examples',
    py_modules=['graphyte'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ]
)
