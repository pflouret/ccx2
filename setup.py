import sys

from distutils.core import setup
from glob import glob

sys.path.insert(0, './src')

import ccx2

setup(name='ccx2',
      version=ccx2.__version__,
      description='console client for xmms2',
      author='Pablo Flouret',
      author_email='quuxbaz@gmail.com',
      url='http://github.com/palbo/ccx2',
      download_url='',
      packages=['ccx2', 'ccx2.urwid'],
      package_dir={'ccx2': 'src/ccx2',
                   'ccx2.urwid': 'src/ccx2/urwid'},
      scripts=['scripts/ccx2'],
      requires=[],
     )

