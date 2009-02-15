from distutils.core import setup
from glob import glob

setup(name='ccx2',
      version='0.1',
      description='ncurses client for xmms2',
      author='Pablo Flouret',
      author_email='pflouret@gmail.com',
      url='',
      download_url='',
      packages=['ccx2'],
      package_dir={'ccx2': 'src/ccx2'},
      scripts=['scripts/ccx2'],
      requires=['pyparsing', 'urwid'],
      data_files=[('share/ccx2', glob('share/**'))]
     )

