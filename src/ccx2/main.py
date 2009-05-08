#!/usr/bin/env python

# Copyright (c) 2008-2009 Pablo Flouret <quuxbaz@gmail.com>
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

import curses
import os
import select
import signal
import sys
import time
import warnings

warnings.filterwarnings('ignore', category=DeprecationWarning)
import urwid
import urwid.curses_display
import urwid.raw_display
warnings.filterwarnings('default', category=DeprecationWarning)

import xmmsclient
import xmmsclient.collections as coll

import commands
import config
import containers
import help
import lyrics
import mif
import nowplaying
import playlist
import search
import signals
import util
import widgets
import xmms


class HeaderBar(urwid.WidgetWrap):
  status_desc = {xmmsclient.PLAYBACK_STATUS_PLAY: 'PLAYING',
                 xmmsclient.PLAYBACK_STATUS_STOP: 'STOPPED',
                 xmmsclient.PLAYBACK_STATUS_PAUSE: 'PAUSED '}

  def __init__(self, app):
    self.app = app
    self.xs = xmms.get()
    self.info = {}
    self.ctx = {}
    self.time = 0
    self.status = self.xs.playback_status()
    self.parser = mif.FormatParser(self.app.config.format('header'))

    self.text = urwid.Text('')
    self.__super.__init__(self.text)

    signals.connect('xmms-playback-status', self.on_xmms_playback_status)
    signals.connect('xmms-playback-current-info', self.on_xmms_playback_current_info)
    signals.connect('xmms-playback-playtime', self.on_xmms_playback_playtime)

    self.xs.playback_current_info(self.on_xmms_playback_current_info, sync=False)

  def _update(self):
    self.ctx['status'] = HeaderBar.status_desc[self.status]
    self.ctx['elapsed'] = util.humanize_time(self.time)
    if 'duration' in self.info:
      self.ctx['total'] = util.humanize_time(self.info['duration'])

    self.text.set_text(self.parser.eval(self.ctx))
    self._invalidate()
    signals.emit('need-redraw')

  def on_xmms_playback_playtime(self, milli):
    if self.time/1000 != milli/1000:
      self.time = milli
      self._update()

  def on_xmms_playback_status(self, status):
    self.status = status
    self._update()

  def on_xmms_playback_current_info(self, info):
    self.info = info
    self.ctx = dict(zip((k[1] for k in self.info), self.info.values()))
    self._update()


signals.register('show-message')
signals.register('clear-message')

class StatusArea(urwid.Pile):
  def __init__(self):
    self.status = urwid.AttrWrap(urwid.Text(''), 'status')
    self._empty = urwid.Text('')
    self.last_type = None

    self.__super.__init__([self.status, self._empty], 1)

    signals.connect('show-message', self.set_message)
    signals.connect('clear-message', lambda: self.clear_message(clear_loading=True))

  def _restore(self, *args, **kwargs):
    self.widget_list[1] = self._empty
    self.set_focus(1)
    self._invalidate()

  def set_message(self, msg, type='info'):
    self.last_type = type
    attr = 'message-'+type
    self.status.set_text((attr, msg))
    signals.emit('need-redraw')

  def clear_message(self, clear_loading=False):
    if clear_loading or self.last_type != 'loading':
      self.status.set_text('')
      signals.emit('need-redraw')

  def show_prompt(self, caption=':', done_cb=[], abort_cb=[], change_cb=[]):
    input = widgets.InputEdit(caption=caption)

    done_cb.insert(0, self._restore)
    abort_cb.insert(0, self._restore)

    for name, cbs in (('done', done_cb), ('abort', abort_cb), ('change', change_cb)):
      for cb in cbs:
        urwid.connect_signal(input, name, cb)

    self.widget_list[1] = input
    self.set_focus(1)
    self._invalidate()


signals.register('need-redraw')
signals.register('window-resized')

class Ccx2(object):
  context_name = 'main'

  def __init__(self, config_path=None):
    self.xs = xmms.get()
    self.config = config.Config(config_path)
    self.cm = commands.CommandManager(self.config)
    self.colors = 8
    self.show_key = False
    self._pipe = os.pipe()

    self.need_redraw = True

    def _need_redraw(): self.need_redraw = True
    signals.connect('need-redraw', _need_redraw)

    if not self.xs.connected:
      if self.config.autostart_server:
        os.system('xmms2-launcher')
      if not self.xs.connect():
        print >> sys.stderr, "error: couldn't connect to server"
        sys.exit(0)

  def run(self):
    self.setup_ui()

    try:
      self.ui.run_wrapper(self.main_loop)
    except KeyboardInterrupt:
      sys.exit(0)

  def setup_ui(self):
    self.ui = urwid.curses_display.Screen()
    self.ui.register_palette(self.config.palette)
    self.ui.set_input_timeouts(max_wait=0)

    try:
      curses.setupterm()
      self.colors = curses.tigetnum('colors')
    except:
      pass

    pview = urwid.Columns([('weight', 1, playlist.PlaylistSwitcher(self)),
                           ('fixed', 1, urwid.SolidFill(u'\u2502')),
                           ('weight', 5, playlist.Playlist(self))],
                          dividechars=1, focus_column=2)

    show_cover = self.config.show_cover and self.colors == 256 and self.config.has_pil

    tabs = [('help', help.Help(self)),
            ('now playing', nowplaying.NowPlaying(self, show_cover=show_cover)),
            ('playlist', pview),
            ('search', search.Search(self))]

    if self.config.show_lyrics:
      tabs.append(('lyrics', lyrics.Lyrics(self)))

    if show_cover:
      i = len(self.ui.curses_pairs)
      for j in range(16,256):
        self.ui.curses_pairs.append((j,j))
        self.ui.palette['h%d'%j] = (j+i-16, 0, 0)

    focus_tab = self.xs.playback_status() == xmmsclient.PLAYBACK_STATUS_PLAY and 1 or 2

    self.tabcontainer = containers.TabContainer(self, tabs, focus_tab=focus_tab)
    self.headerbar = HeaderBar(self)
    self.statusarea = StatusArea()
    self.view = urwid.Frame(self.tabcontainer, header=self.headerbar, footer=self.statusarea)

  def notify(self):
    os.write(self._pipe[1], '\0')

  def redraw(self):
    canvas = self.view.render(self.size, focus=1)
    self.ui.draw_screen(self.size, canvas)
    self.need_redraw = False

  def main_loop(self):
    self.size = self.ui.get_cols_rows()

    xmmsfd = self.xs.xmms.get_fd()
    stdinfd = sys.stdin.fileno()

    while True:
      if self.need_redraw:
        self.redraw()

      input_keys = None

      w = self.xs.xmms.want_ioout() and [xmmsfd] or []

      try:
        (i, o, e) = select.select([xmmsfd, stdinfd, self._pipe[0]], w, [])
      except select.error:
        i = [xmmsfd, stdinfd]

      if not self.xs.connected:
        print >> sys.stderr, "disconnected from server"
        sys.exit(0) # TODO

      for fd in i:
        if fd == xmmsfd:
          self.xs.ioin()
        elif fd == stdinfd:
          input_keys = self.ui.get_input()
        elif fd == self._pipe[0]:
          os.read(self._pipe[0], 1)

      if o and o[0] == xmmsfd:
        self.xs.ioout()

      if not input_keys:
        continue

      self.statusarea.clear_message()

      for k in input_keys:
        if self.show_key:
          signals.emit('show-message', 'key: %s' % config.urwid_key_to_key(k))
          self.show_key = False
          continue
        try:
          if k == 'window resize':
            self.size = self.ui.get_cols_rows()
            signals.emit('window-resized', self.size)
          elif self.view.keypress(self.size, k) is None:
            continue
          elif self.cm.run_key(k, self.view.body.get_contexts() + [self]):
            continue
          elif k == ':':
            self.show_command_prompt()
          else:
            signals.emit('show-message', "unbound key: %s" % k, 'error')
        except commands.CommandError, e:
          signals.emit('show-message', "command error: %s" % e, 'error')

  def show_dialog(self, dialog):
    return dialog.show(self.ui, self.size, self.view)

  def show_prompt(self, caption, done_cb=[], abort_cb=[], change_cb=[]):
    def _restore(*args):
      self.view.set_focus('body')

    if type(done_cb) != list: done_cb = [done_cb]
    if type(abort_cb) != list: abort_cb = [abort_cb]
    if type(change_cb) != list: change_cb = [change_cb]
    done_cb.insert(0, _restore)
    abort_cb.insert(0, _restore)

    self.statusarea.show_prompt(caption, done_cb=done_cb, abort_cb=abort_cb, change_cb=change_cb)
    self.view.set_focus('footer')

  def show_command_prompt(self):
    contexts = self.view.body.get_contexts() + [self]

    def _restore(*args):
      self.view.set_focus('body')

    def _run(widget, text):
      try:
        self.cm.run_command(text, contexts)
      except commands.CommandError, e:
        signals.emit('show-message', "command error: %s" % e, 'error')

    self.statusarea.show_prompt(done_cb=[_restore, _run], abort_cb=[_restore])

    self.view.set_focus('footer')

  # FIXME
  def show_dialog(self, dialog):
    self.view.body = dialog
    def r(w): self.view.body = self.tabcontainer
    urwid.connect_signal(dialog, 'closed', r)

  def search(self, query=None):
    self.tabcontainer.load_tab_by_name('search')
    if query:
      search = self.tabcontainer.get_current()
      search.set_query(query)

  def cmd_clear(self, args): self.xs.playlist_clear(sync=False)
  def cmd_pb_play(self, args): self.xs.playback_start(sync=False)
  def cmd_pb_toggle(self, args): self.xs.playback_play_pause_toggle(sync=False)
  def cmd_pb_stop(self, args): self.xs.playback_stop(sync=False)
  def cmd_pb_next(self, args): self.xs.playback_next(sync=False)
  def cmd_pb_prev(self, args): self.xs.playback_prev(sync=False)
  def cmd_quit(self, args): sys.exit(0)
  def cmd_search(self, args): self.search(args)
  def cmd_shuffle(self, args): self.xs.playlist_shuffle(args or None, sync=False)
  def cmd_slow_as_hell(self, args): signals.emit('show-message', 'Indeed!')

  def cmd_info(self, args):
    info = self.xs.playback_current_info()
    self.show_dialog(containers.InfoDialog(self, info, self.view.body))

  def cmd_keycode(self, args):
    signals.emit('show-message', "Press any key to see the config compatible keycode")
    self.show_key = True

  def cmd_nav(self, args):
    map = {'page-up': 'page up', 'page-down': 'page down'}

    if args not in ('left', 'down', 'up', 'right', 'page-up', 'page-down', 'home', 'end'):
      raise commands.CommandError('wrong navigation direction')

    self.view.keypress(self.size, map.get(args, args))

  def cmd_rehash(self, args):
    try:
      c = coll.coll_parse(args)
    except ValueError:
      raise commands.CommandError, 'bad pattern'

    ids = self.xs.coll_query_ids(c)

    for i in ids:
      self.xs.medialib_rehash(i, sync=False)

  def cmd_seek(self, args):
    if args:
      relative = args[0] in ('+', '-')

      try:
        mult = 1
        seconds = 0
        for p in reversed(args.split(':')):
          seconds += int(p)*mult
          mult *= 60
        # FIXME: check for a valid time spec, laziness is my name
      except ValueError:
        raise commands.CommandError, "bad seconds value"

      if relative:
        self.xs.playback_seek_ms_rel(seconds*1000, sync=False)
      else:
        self.xs.playback_seek_ms(seconds*1000, sync=False)

  def cmd_volume(self, args):
    cur = self.xs.playback_volume_get()

    if isinstance(cur, basestring):
      signals.emit('show-message', "volume: "+cur)
      return

    if args:
      relative = args[0] in ('+', '-')

      try:
        volume = int(args)
      except ValueError:
        raise commands.CommandError, "wrong volume value"

      for c in cur:
        if relative:
          cur[c] = cur[c] + volume
        else:
          cur[c] = volume
        self.xs.playback_volume_set(c, cur[c])

    s = "volume: " + ' '.join("%s:%d" % (c, v) for c, v in cur.iteritems())
    signals.emit('show-message', s)


if __name__ == '__main__':
  Ccx2().run()

