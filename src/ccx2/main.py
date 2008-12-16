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

import sys

import urwid
import urwid.curses_display

from ccx2 import bars
from ccx2 import medialib
from ccx2 import playlist
from ccx2 import signals
from ccx2 import xmms

from ccx2.config import keybindings

xs = xmms.get()

class GlobalCommandsHandler(object):
  def __init__(self):
    self._key_action = {}

    for action, fun in (('play', lambda: xs.playback_start(sync=False)),
                        ('play-pause-toggle', lambda: xs.playback_play_pause_toggle(sync=False)),
                        ('stop', lambda: xs.playback_stop(sync=False)),
                        ('next-track', lambda: xs.playback_next(sync=False)),
                        ('previous-track', lambda: xs.playback_prev(sync=False)),
                       ):
      for key in keybindings['playback'][action]:
        self._key_action[key] = fun

  def keypress(self, size, key):
    if key in self._key_action:
      self._key_action[key]()
    else:
      return key

class Ccx2(object):
  palette = [
    ('body','default','default', 'standout'),
    ('dialog', 'black', 'light gray'),
    ('selected','yellow','default', 'standout'),
    ('selected-focus','yellow','dark green', 'standout'),
    ('focus','black','dark green', 'standout'),
    ('active','dark red', 'default'),
    ('active-focus','dark red', 'dark green'),
    ('statusbar','light gray', 'default'),
    ('headerbar','dark cyan', 'default'),
    ]
    
  def __init__(self):
    self.gch = GlobalCommandsHandler()
    self.playlist = playlist.Playlist()
    self.switcher = playlist.PlaylistSwitcher(self)
    self.medialib = None
    self.statusbar = bars.StatusBar()
    self.headerbar = bars.HeaderBar()
    self.view = urwid.Frame(self.playlist, header=self.headerbar, footer=self.statusbar)

    signals.connect('xmms-have-ioin', self.redraw)

  def main(self):
    self.ui = urwid.curses_display.Screen()
    self.ui.register_palette(self.palette)
    self.ui.set_input_timeouts(max_wait=0.1)
    self.ui.run_wrapper(self.run)

  def show_dialog(self, dialog):
    return dialog.show(self.ui, self.size, self.view)

  def redraw(self):
    canvas = self.view.render(self.size, focus=1)
    self.ui.draw_screen(self.size, canvas)

  def run(self):
    self.size = self.ui.get_cols_rows()

    while 1:
      self.redraw()

      keys = None
      while not keys:
        keys = self.ui.get_input()
        # FIXME: put these in a thread
        xs.ioout()
        xs.ioin()

      for k in keys:
        if k == 'window resize':
          self.size = self.ui.get_cols_rows()
        elif k in keybindings['general']['goto-playlist']:
          self.view.body = self.playlist
        elif k in keybindings['general']['goto-playlist-switcher']:
          self.view.body = self.switcher
        elif k in keybindings['general']['goto-medialib']:
          if not self.medialib:
            self.medialib = medialib.MediaLib()
          self.view.body = self.medialib
        elif k in keybindings['general']['quit']:
          return
        elif self.view.keypress(self.size, k) is None:
          continue
        elif self.gch.keypress(self.size, k) is None:
          continue

if __name__ == '__main__':
  Ccx2().main()

