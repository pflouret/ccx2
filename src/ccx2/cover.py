#!/usr/bin/python

from PIL import Image
import random, os, re, sys
from StringIO import StringIO

import urwid
import urwid.raw_display
import urwid.display_common

_colormap_cache = {}
redraw = False

class AlbumCoverWidget(urwid.WidgetWrap):
  def __init__(self, data=None, hash=None, maxcols=-1, halign='center', valign='middle'):
    self.maxcols = maxcols
    self.img = None
    self.dim = None
    self.hash = None

    if data:
      self.set_data(data, hash)

    self.text = urwid.Text('', wrap=urwid.ANY)
    self.filler = urwid.Filler(self.text, valign)
    self.__super.__init__(urwid.Padding(self.filler, halign))

  def set_data(self, data, hash):
    if hash != self.hash:
      self.hash = hash
      try:
        self.img = Image.open(StringIO(data))
      except IOError, e:
        self.img = None
        self.text.set_text('')
      self.dim = None
      self._invalidate()

  # TODO: check if PIL can convert an image to 8-bit colors
  def closest_color(self, rgb):
    global _colormap_cache

    n = rgb[0] << 16 | rgb[1] << 8 | rgb[2]

    if n in _colormap_cache:
      return 'h%d' % _colormap_cache[n]

    distance = 257*257*3
    match = 0

    for i, values in enumerate(urwid.display_common._COLOR_VALUES_256):
      rd, gd, bd = rgb[0] - values[0], rgb[1] - values[1], rgb[2] - values[2]
      d = rd*rd + gd*gd + bd*bd

      if d < distance:
        match = i
        distance = d

    _colormap_cache[n] = match
    return 'h%d' % match

  def get_markup(self, img):
    markup = []
    for y in range(0, img.size[1], 1):
      last = ''
      n = 0
      for x in range(0, img.size[0], 1):
        rgb = img.getpixel((x,y))
        if type(rgb) == int:
          rgb = (rgb >> 16 & 0xff, rgb >> 8 & 0xff, rgb & 0xff)

        c = self.closest_color(rgb)
        if c != last:
          if last:
            markup.append((urwid.AttrSpec(last, last), ' '*2*n))
          last = c
          n = 0
        n += 1
      if n:
        markup.append((urwid.AttrSpec(last, last), ' '*2*n))
      markup.append('\n')

    return markup[:-1]

  def scaled_dim(self, size):
    w = size[0] / 2

    if self.maxcols > 0 and size[0] > self.maxcols:
      w = self.maxcols / 2

    w = min(w, self.img.size[0])

    h = w * self.img.size[1] / self.img.size[0]

    if h > size[1]:
      h = size[1]
      w = h * self.img.size[0] / self.img.size[1]

    return w, h

  def render(self, size, focus=False):
    if self.img:
      dim = self.scaled_dim(size)
      if dim != self.dim:
        self.dim = dim
        img = self.img.resize(dim, Image.ANTIALIAS)
        self.text.set_text(self.get_markup(img))
        self._w.width = dim[0]*2
    return self._w.render(size)

  def keypress(self, size, key): return key

def get_img():
  #f = random.choice(os.listdir('bindata'))
  for f in os.listdir('/home/palbo/.config/xmms2/bindata'):
    text = Image.open(os.path.join('/home/palbo/.config/xmms2/bindata', f))
    x = WIDTH
    y = x * text.size[1] / text.size[0]
    if x < text.size[0]:
      text = text.resize((x, y), Image.ANTIALIAS)
    yield text

covers = [(f, os.path.join('/home/palbo/.config/xmms2/bindata', f)) for f in
          os.listdir('/home/palbo/.config/xmms2/bindata')]
i = random.randint(0, len(covers)-1)

def get_img_data():
  for f in os.listdir('/home/palbo/.config/xmms2/bindata'):
    yield open(os.path.join('/home/palbo/.config/xmms2/bindata', f)).read()

import threading
def main():
  global i
  palette = [
    ('header', 'black,underline', 'light gray', 'standout,underline', 'black,underline', '#88a'),
    ('panel', 'light gray', 'dark blue', '', '#ffd', '#00a'),
    ('focus', 'light gray', 'dark cyan', 'standout', '#ff8', '#806'),
    ]

  screen = urwid.raw_display.Screen()
  screen.register_palette(palette)
  #screen.set_input_timeouts(max_wait=1)

  #screen.set_terminal_properties(88)
  #screen.reset_default_terminal_palette()
  ac = AlbumCoverWidget(open(covers[i][1]).read(), covers[i][0], 80)
  w = urwid.Pile([
                  ('flow', urwid.Text('asdfas fas dfa sdf'),
                  ac
  ])
  t = urwid.Text('', align='center')
  w = urwid.Frame(w, header=t)

  import time
  def update():
    global redraw
    while True:
      t.set_text(str(time.time()))
      redraw = True
      time.sleep(1)
  th = threading.Thread(target=update)
  th.setDaemon(True)
  th.start()

  def unhandled_input(key):
    global i
    if key in ('Q','q','esc'):
      raise urwid.ExitMainLoop()
    elif key in (' ', 'backspace'):
      if key == ' ':
        i += 1
      else:
        i -= 1
      ac.set_data(open(covers[i][1]).read(), covers[i][0])
      t.set_text(covers[i][0])

  #urwid.generic_main_loop(w, screen=screen, unhandled_input=unhandled_input)
  generic_main_loop(w, screen=screen, unhandled_input=unhandled_input)

def generic_main_loop(topmost_widget, palette=[], screen=None,
  handle_mouse=True, input_filter=None, unhandled_input=None):
  def run():
    global redraw
    if handle_mouse:
      screen.set_mouse_tracking()
    size = screen.get_cols_rows()
    while True:
      canvas = topmost_widget.render(size, focus=True)
      screen.draw_screen(size, canvas)
      keys = None
      while not keys:
        keys = screen.get_input()
        if redraw:
          canvas = topmost_widget.render(size, focus=True)
          screen.draw_screen(size, canvas)
          redraw = False
      for k in keys:
        if input_filter:
          k = input_filter(k)
        else:
          k = topmost_widget.keypress(size, k)
        if k and unhandled_input:
          k = unhandled_input(k)
        if k and command_map[k] == 'redraw screen':
          screen.clear()
      
      if 'window resize' in keys:
        size = screen.get_cols_rows()
  
  if not screen:
    import raw_display
    screen = raw_display.Screen()

  if palette:
    screen.register_palette(palette)
  try:
    if screen.started:
      run()
    else:
      screen.run_wrapper(run)
  except urwid.ExitMainLoop:
    pass


if __name__ == "__main__":
  main()


