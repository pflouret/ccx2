import sys

from setuptools import setup
from glob import glob

sys.path.insert(0, './src')

import ccx2

setup(name='ccx2',
      version=ccx2.__version__,
      description='console client for xmms2',
      author='Pablo Flouret',
      author_email='quuxbaz@gmail.com',
      url='https://github.com/pflouret/ccx2',
      download_url='',
      packages=['ccx2'],
      package_dir={'ccx2': 'src/ccx2'},
      entry_points={
        'console_scripts': [
            'ccx2 = ccx2.__main__:main',
        ],
      },
      install_requires=[
        'Pillow',
        'simplejson',
        'urwid',
        # also Python 3 xmmsclient from https://github.com/xmms2/xmms2-devel/tree/master/src/clients/lib/python
      ],
     )

