# Copyright (c) 2008, Pablo Flouret <quuxbaz@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met: Redistributions of
# source code must retain the above copyright notice, this list of conditions and
# the following disclaimer. Redistributions in binary form must reproduce the
# above copyright notice, this list of conditions and the following disclaimer in
# the documentation and/or other materials provided with the distribution.
# Neither the name of the software nor the names of its contributors may be
# used to endorse or promote products derived from this software without specific
# prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import ConfigParser
import StringIO
import copy
import os
import re
import sys

import xmmsclient

# H: horizontal | V: vertical | D: down | U: up

UBORDER_H = u'\u2500'
UBORDER_V = u'\u2502'
UBORDER_H_D = u'\u252c'

def key_to_urwid_key(key):
  if '-' in key and key != '-':
    key = key.replace('-', ' ', 1)
  if key == 'ctrl space':
    key = '<0>'
  key = key.replace('space', ' ')
  key = key.replace('comma', ',')
  return key

_default_palette = {
    'default': ('default','default','default'),
    'focus': ('focus','black','light gray'),
    'dialog': ('dialog', 'black', 'light gray'),
    'marked': ('marked','yellow','default'),
    'marked-focus': ('marked-focus','black','brown'),
    'active': ('active','light blue', 'default'),
    'active-focus': ('active-focus','black', 'dark blue'),
    'headerbar': ('headerbar','default', 'default'),
    'status': ('status','default', 'default'),
    'searchinput': ('searchinput','yellow', 'default'),
    'message-info': ('message-info','default', 'default'),
    'message-loading': ('message-loading','default', 'default'),
    'message-error': ('message-error','light red', 'default'),
    'progress-normal': ('progress-normal', 'light gray', 'light gray'),
    'progress-complete': ('progress-complete', 'dark red', 'dark red'),
    'progress-smooth': ('progress-smooth', 'dark red', 'light gray'),
}

class Config(object):
  def __init__(self, path=None):
    if not path:
      confdir = xmmsclient.userconfdir_get()
      path = os.path.join(confdir, 'clients', 'ccx2')

      try:
        os.makedirs(path)
      except OSError:
        pass

      path = os.path.join(path, 'ccx2.conf')

      if not os.path.exists(path):
        try:
          f = open(path, 'w')
          print >> f, DEFAULT_CONFIG
          f.close()
        except:
          path = None

    self.path = path

    self.cp = ConfigParser.SafeConfigParser()

    try:
      if not self.cp.read(path):
        raise ValueError
    except:
      self.path = None
      self.cp = copy.deepcopy(default_cp)
      msg = "warning: error while reading the config file, using defaults"
      print >> sys.stderr, msg

    self.keys = {}
    self.aliases = {}
    self._palette = dict(_default_palette)
    self._formatting = {}

    self._read_keys()
    self._read_aliases()
    self._read_formatting()
    self._read_options()
    self._read_colors()

    try:
      import PIL
      self.has_pil = True
    except ImportError:
      self.has_pil = False

  palette = property(lambda self: self._palette.values())

  def format(self, key):
    try:
      f = getattr(self, 'default_%s_format' % key)
    except AttributeError:
      f = key

    try:
      return self._formatting[f]
    except KeyError:
      return ''

  def _read_keys(self):
    if not self.cp.has_section('keys'):
      return
    for cmd, keys in self.cp.items('keys'):
      keys = [key_to_urwid_key(k.strip()) for k in keys.split(',')]
      for k in keys:
        self.keys[k] = cmd
        # TODO: multiple commands to the same key (context based) ?
        # self.keys.setdefault(key_to_urwid_key(k), []).append(cmd)

  def _read_aliases(self):
    if self.cp.has_section('aliases'):
      self.aliases = dict(self.cp.items('aliases'))

  def _read_formatting(self):
    cp = self.cp.has_section('formatting') and self.cp or default_cp
    self._formatting = dict(cp.items('formatting'))

  def _read_options(self):
    rx = re.compile(r'[^a-zA-Z 0-9]')
    for k, v in self.cp.items('options'):
      if k in ('search-find-as-you-type',
               'autostart-server'):
        setattr(self, rx.sub('_', k), self.cp.getboolean('options', k))
      else:
        setattr(self, rx.sub('_', k), v)

  def _read_colors(self):
    fg_colors = ['black', 'dark red', 'dark green', 'brown', 'dark blue', 'dark magenta',
                 'dark cyan', 'light gray', 'dark gray', 'light red', 'light green', 'yellow',
                 'light blue', 'light magenta', 'light cyan', 'white', 'default']
    bg_colors = ['black', 'dark red', 'dark green', 'brown', 'dark blue', 'dark magenta',
                 'dark cyan', 'light gray', 'default']

    for key, value in self.cp.items('colors'):
      if key not in self._palette:
        continue

      sp = [v.strip() for v in value.split(',')]
      l = len(sp)
      if l == 1:
        fg, bg = sp[0], 'default'
      elif l == 2:
        fg, bg = sp
      else:
        print >> sys.stderr, 'warning: wrong color specification for %s, ignoring' % key

      if fg not in fg_colors:
        print >> sys.stderr, 'warning: bad color %s for foreground, ignoring' % fg
        continue

      if bg not in bg_colors:
        print >> sys.stderr, 'warning: bad color %s for background, ignoring' % bg
        continue

      self._palette[key] = (key, fg, bg)


DEFAULT_CONFIG = """
[options]
server-autostart = yes
search-find-as-you-type = yes
default-nowplaying-format = nowplaying
default-playlist-format = simple
default-search-format = search

[aliases]
q = quit
sa = same artist
sb = same album
s = search

[keys]
activate = enter,  ctrl-m,ctrl-j
cycle = tab
insert = a
insert +1 = w
goto playing = g
move = m
move -1 = K
move +1 = J
nav left = h
nav down = j
nav up = k
nav right = l
nav page-down = page-down,ctrl-d
nav page-up = page-up,ctrl-u
nav home = home
nav end = end
new = n
pb-prev = z
pb-toggle = x
pb-play = c
pb-stop = v
pb-next = b
quit = q
; rehash =
rename = #
rm = d,del
; same =
; save =
; search =
seek +5 = >
seek -5 = <
tab 1 = 1,f1
tab 2 = 2,f2
tab 3 = 3,f3
tab 4 = 4,f4
tab prev = [
tab next = ]
toggle ; navdn = space
navup ; toggle = ctrl-space
unmark-all = meta-space
volume +2 = +,=
volume -2 = -

[formatting]
search = [:c?:p|:a] \> :l \> [#[:partofset.]:n ][:c?:a \>] :t
simple = :a \> :t [:c?{ :p }]
nowplaying =
  :status:CR:CR
  :a:CR
  [:n. ]:t:CR
  :l[:c? (:p)][ CD:partofset]:CR
  [:d][ :g][ {:publisher}]:CR
  [#:id][ :{bitrate}bps][ :{samplerate}Hz:CR
  :CR
  \[:elapsed[/:total]\]


[colors]
# specify as foreground, background
# background can be omitted and the terminal default color will be used
#
# valid foreground colors:
# default, black, white, brown, yellow,
# dark blue, light blue, dark cyan, light cyan,
# dark gray, light gray, dark green, light green,
# dark magenta, light magenta, dark red, light red,
#
# valid background colors:
# default, black, brown, dark blue, dark cyan,
# light gray, dark green, dark magenta, dark red,

default = default,default
focus = black,light gray
focus = dark magenta,black
dialog = black,light gray
marked = yellow,default
marked-focus = black,brown
active = light blue,default
active-focus = black,dark blue
headerbar = default,default
status = default,default
searchinput = yellow,default
message-info = default,default
message-loading = default,default
message-error = light red,default
progress-normal = light gray,light gray
progress-complete = dark red,dark red
progress-smooth = dark red,light gray
"""

default_cp = ConfigParser.SafeConfigParser()
default_cp.readfp(StringIO.StringIO(DEFAULT_CONFIG))

