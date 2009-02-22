from distutils.core import setup
from glob import glob

setup(name='ccx2',
      version='0.1',
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

