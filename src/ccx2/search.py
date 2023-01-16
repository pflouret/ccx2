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

import os
import re
import threading
import time

from . import urwid
import xmmsclient.collections as coll

from . import collutil
from . import config
from . import commands
from . import listbox
from . import mif
from . import signals
from . import widgets
from . import xmms


class SearchWalker(urwid.ListWalker):
  def __init__(self, collection, format):
    self.format = format
    self.parser = mif.FormatParser(format)
    self.widgets = {}
    self.focus = 0

    self.feeder = collutil.CollectionFeeder(collection, self.parser.fields())

    signals.connect('xmms-medialib-entry-changed', self.on_medialib_entry_changed)

  def __len__(self):
    return len(self.feeder)

  def get_pos(self, pos):
    mid = self.feeder.position_id(pos)

    if pos < 0 or mid is None:
      return None, None

    if mid not in self.widgets:
      text = self.parser.eval(self.feeder[pos])
      self.widgets[mid] = widgets.SongWidget(mid, text)

    return self.widgets[mid], pos

  def set_focus(self, focus):
    if focus <= 0:
      focus = 0
    elif focus >= len(self.feeder):
      focus = len(self.feeder) - 1

    self.focus = focus
    self._modified()

  def clear_cache(self):
    self.widgets = {}

  def set_focus_last(self): self.set_focus(len(self.feeder)-1)
  def get_focus(self): return self.get_pos(self.focus)
  def get_prev(self, pos): return self.get_pos(pos-1)
  def get_next(self, pos): return self.get_pos(pos+1)

  def on_medialib_entry_changed(self, mid):
    if mid in self.widgets:
      del self.widgets[mid]


class SearchListBox(listbox.SongListBox):
  def __init__(self, formatname, app):
    self.format = formatname
    self.walker = SearchWalker(coll.IDList(), app.config.format('search'))

    self.__super.__init__(app, self.walker)

  def _set_collection(self, c):
    self.walker.feeder.collection = c
    self.unmark_all()
    self._invalidate()

  collection = property(lambda self: self.walker.feeder.collection, _set_collection)

  def keypress(self, size, key):
    k = self.__super.keypress(size, key)
    if k in ('up', 'down'):
      # don't let a focus change happen in the pile if up or down are unhandled
      return None
    return k


coll_parser_pattern_rx = re.compile(r'\(|\)|#|:|~|<|>|=|\+|OR|AND|NOT')

class Search(urwid.Pile):
  context_name = 'search'

  def __init__(self, app):
    self.xs = xmms.get()
    self.app = app

    self.lb = SearchListBox('simple', self.app)
    self.input = widgets.InputEdit(caption='quick search: ')

    if self.app.config.search_find_as_you_type:
      urwid.connect_signal(self.input, 'change', self._on_query_change)
    urwid.connect_signal(self.input, 'done', self._on_done)
    urwid.connect_signal(self.input, 'abort', lambda w: self.set_focus(self.lb))
    urwid.connect_signal(self.input, 'abort', lambda w: self.input.set_edit_text(''))

    self.prev_q = ''

    self.lock = threading.RLock()
    self._timer = None

    self.__super.__init__([('flow', urwid.AttrWrap(self.input, 'searchinput')), self.lb], 0)

  def cmd_cycle(self, args=None):
    cur = self.widget_list.index(self.focus_item)
    n = len(self.widget_list)
    i = (cur + 1) % n
    while i != cur and not self.widget_list[i].selectable():
      i = (i + 1) % n

    #if i != cur and (i != 0 or len(self.lb.body) != 0):
    self.set_focus(i)

  def cmd_save(self, args):
    # TODO: playlists and playlist types/options
    args = args.strip()
    if not args:
      raise commands.CommandError('need some args')

    name = args
    q = self.input.edit_text
    if q and not coll_parser_pattern_rx.search(q):
      q = ' '.join(['~'+s for s in q.split()])

    try:
      c = coll.coll_parse(q)
    except ValueError:
      raise commands.CommandError('invalid collection')

    self.xs.coll_save(c, name, 'Collections', sync=False)
    signals.emit('show-message',
                 "saved collection %s with pattern %s" % (name, q))

  def set_query(self, q):
    self.set_focus(0)
    self.input.set_edit_text(q)
    self.input.edit_pos = len(q)
    self.input.keypress(self.app.size, 'enter')

  def update_caption(self, q):
    caption = 'quick search: '
    if q and coll_parser_pattern_rx.search(q):
      caption = 'pattern search: '
    self.input.set_caption(caption)

  def process_query(self, q):
    try:
      self.lock.acquire()
      caption = 'quick search: '
      if q:
        if coll_parser_pattern_rx.search(q):
          caption = 'pattern search: '
        else:
          q = ' '.join(['~'+s for s in q.split()])
      else:
        self.lb.walker.clear_cache()

      try:
        self.lb.collection = coll.coll_parse(q)
      except ValueError:
        signals.emit('show-message', "bad pattern", 'error')

      self.input.set_caption(caption)
      signals.emit('need-redraw')
      self.app.notify()
    finally:
      self.lock.release()

  def _on_done(self, widget, q):
    if not self.app.config.search_find_as_you_type:
      self.process_query(q)
    else:
      self.update_caption(q)
    self.cmd_cycle()
    self._invalidate()

  def _on_query_change(self, widget, q):
    if self.app.config.search_find_as_you_type:
      if q != self.prev_q:
        if self._timer:
          self._timer.cancel()
        self._timer = threading.Timer(0.25, lambda: self.process_query(q))
        self._timer.start()
    self.prev_q = q

  def get_contexts(self):
    return [self, self.lb]

  def keypress(self, size, key):
    # XXX: huge ugly hack
    key = self.__super.keypress(size, key)
    if key and key in ('esc', 'ctrl g'):
      self.app.tabcontainer.load_previous_tab()
    else:
      return key


