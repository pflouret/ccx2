#!/usr/bin/env python

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

import signal
import sys
import time

import urwid
import urwid.curses_display
import xmmsclient

import commands
import keys
import playlist
import search
import signals
import containers
import widgets
import xmms


xs = xmms.get()

class HeaderBar(urwid.WidgetWrap):
  status_desc = {xmmsclient.PLAYBACK_STATUS_PLAY: 'PLAYING',
                 xmmsclient.PLAYBACK_STATUS_STOP: 'STOPPED',
                 xmmsclient.PLAYBACK_STATUS_PAUSE: 'PAUSED '}

  def __init__(self):
    self.__super.__init__(urwid.AttrWrap(urwid.Text(''), 'headerbar'))
    self.info = {}
    self.time = 0
    self.status = xs.playback_status()
    self._make_text()

    signals.connect('xmms-playback-status', self.on_xmms_playback_status)
    signals.connect('xmms-playback-current-info', self.on_xmms_playback_current_info)
    signals.connect('xmms-playback-playtime', self.on_xmms_playback_playtime)

    curid = xs.playback_current_id()
    xs.medialib_get_info(
        curid, cb=lambda r: self.on_xmms_playback_current_info(r.value()), sync=False)

  def _humanize_time(self, milli, str_output=True):
    sec, milli = divmod(milli, 1000)
    min, sec = divmod(sec, 60)
    hours, min = divmod(min, 60)
    if str_output:
      return '%s%02d:%02d' % (hours and '%02d:' % hours or '', min, sec)
    else:
      hours, min, sec

  def _make_text(self):
    status = HeaderBar.status_desc[self.status]
    c = self.info.get('compilation')
    p = self.info.get('performer')
    a = self.info.get('artist')
    t = self.info.get('title')
    text = status
    if p or a or t or t:
      text += ' | '
    if p or a: text += p or a
    if t: text += ' - ' + t
    if c: text += ' - ' + a
    if self.time: text += ' [' + self._humanize_time(self.time) + ']'

    self._w.set_text(text)

  def on_xmms_playback_playtime(self, milli):
    if self.time/1000 != milli/1000:
      self.time = milli
      self._make_text()
      self._invalidate()
      signals.emit('need-redraw')

  def on_xmms_playback_status(self, status):
    self.status = status
    self._make_text()
    self._invalidate()
    signals.emit('need-redraw')

  def on_xmms_playback_current_info(self, info):
    if type(info) == xmmsclient.PropDict:
      self.info = info
      self._make_text()
      self._invalidate()
      signals.emit('need-redraw')

signals.register('need-redraw')
signals.register('need-redraw-non-urgent')

class Ccx2(object):
  # default black white brown yellow
  # light/dark: red green blue magenta cyan gray
  palette = [
    ('default','default','default'),
    ('focus','black','light gray'),
    ('dialog', 'black', 'light gray'),
    ('marked','yellow','default'),
    ('marked-focus','black','brown'),
    ('active','light blue', 'default'),
    ('active-focus','black', 'dark blue'),
    ('headerbar','default', 'default')]

  def __init__(self):
    self.ch = commands.CommandHandler()

    pview = urwid.Columns([('weight', 1, playlist.PlaylistSwitcher(self)),
                           ('fixed', 1, urwid.SolidFill(u'\u2502')),
                           ('weight', 5, playlist.Playlist(self))],
                          dividechars=1, focus_column=2)
    tabs = [('help', urwid.ListBox([urwid.Text('yeah right')])),
            ('playlist', pview),
            ('search', search.Search(self))]

    self.tabcontainer = containers.TabContainer(self, tabs)
    self.headerbar = HeaderBar()
    self.view = urwid.Frame(self.tabcontainer, header=self.headerbar)

    self.need_redraw = False

    def _need_redraw(): self.need_redraw = True
    signals.connect('need-redraw', _need_redraw)

    self.register_commands()

  def register_commands(self):
    self.ch.register_command(self, 'play', lambda c, a: xs.playback_start(sync=False))
    self.ch.register_command(self, 'play-pause-toggle',
                             lambda c, a: xs.playback_play_pause_toggle(sync=False)),
    self.ch.register_command(self, 'stop', lambda c, a: xs.playback_stop(sync=False)),
    self.ch.register_command(self, 'next-track', lambda c, a: xs.playback_next(sync=False)),
    self.ch.register_command(self, 'previous-track', lambda c, a: xs.playback_prev(sync=False)),

    self.ch.register_command(self, 'quit', lambda c, a: sys.exit(0))
    self.ch.register_command(self, 'q', 'quit') # XXX: alias

    self.ch.register_command(self, 'search', lambda c, a: self.search(a))

    for command, k in keys.bindings['playback'].iteritems():
      self.ch.register_keys(self, command, k)

    self.ch.register_keys(self, 'quit', keys.bindings['general']['quit'])
    self.ch.register_keys(self, 'search', ['/'])

    # change default urwid command map
    for action in (('move-focus-up', 'cursor up'),
                   ('move-focus-down', 'cursor down'),
                   ('move-focus-right', 'cursor right'),
                   ('move-focus-left', 'cursor left'),
                   ('page-up', 'cursor page up'),
                   ('page-down', 'cursor page down'),
                   ('move-focus-top', 'cursor max left'),
                   ('move-focus-bottom', 'cursor max right')):
      for k in keys.bindings['movement'][action[0]]:
        urwid.command_map[k] = action[1]


  def main(self):
    self.ui = urwid.curses_display.Screen()
    self.ui.register_palette(self.palette)
    self.ui.set_input_timeouts(max_wait=0)
    self.ui.run_wrapper(self.run)

  def show_dialog(self, dialog):
    return dialog.show(self.ui, self.size, self.view)

  def show_prompt(self, widget):
    def _restore(*args):
      self.view.footer = None
      self.view.set_focus('body')

    urwid.connect_signal(widget, 'done', _restore)
    urwid.connect_signal(widget, 'abort', _restore)

    self.view.footer = widget
    self.view.set_focus('footer')

  def search(self, query=None):
    self.tabcontainer.load_tab_by_name('search')
    if query:
      search = self.tabcontainer.get_current()
      search.set_query(query)

  def redraw(self):
    canvas = self.view.render(self.size, focus=1)
    self.ui.draw_screen(self.size, canvas)
    self.need_redraw = False

  def run(self):
    self.size = self.ui.get_cols_rows()

    while 1:
      self.redraw()

      input_keys = None
      while not input_keys:
        input_keys = self.ui.get_input()
        xs.ioout()
        xs.ioin()
        if self.need_redraw:
          self.redraw()
        time.sleep(0.01)

      for k in input_keys:
        if k == 'window resize':
          self.size = self.ui.get_cols_rows()
        elif self.view.keypress(self.size, k) is None:
          continue
        elif k == keys.command_mode_key:
          contexts = self.view.body.get_contexts() + [self]
          self.show_prompt(self.ch.get_command_prompt(contexts))
        elif self.ch.run_key(self.view.body.get_contexts() + [self], k):
          continue
        # TODO: else show unbound key msg

if __name__ == '__main__':
  Ccx2().main()

