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

import urwid
from xmmsclient import collections as coll
from xmmsclient.sync import XMMSError

import config
import keys
import mifl
import xmms

xs = xmms.get()

# FIXME: works like crap and it's ugly
class MarkableListBox(urwid.ListBox):
  def __init__(self, body, ch=None):
    self.__super.__init__(body)

    self._marked = {}
    if ch:
      ch.register_command(self, 'move-focus-top', lambda c, a: self.set_focus(0)),
      ch.register_command(self, 'move-focus-bottom', lambda c, a: self.set_focus_last()),
      ch.register_command(self, 'mark-and-move-up', lambda c, a: self._mark_and_move_rel(-1)),
      ch.register_command(self, 'mark-and-move-down', lambda c, a: self._mark_and_move_rel(1)),
      ch.register_command(self, 'unmark-all', lambda c, a: self.unmark_all())

      ch.register_keys(self, 'move-focus-top', keys.bindings['movement']['move-focus-top'])
      ch.register_keys(self, 'move-focus-bottom', keys.bindings['movement']['move-focus-bottom'])
      ch.register_keys(self, 'mark-and-move-up', keys.bindings['general']['mark-and-move-up'])
      ch.register_keys(self, 'mark-and-move-down', keys.bindings['general']['mark-and-move-down'])
      ch.register_keys(self, 'unmark-all', keys.bindings['general']['unmark-all'])

  def _get_marked(self):
    return self._marked

  marked = property(_get_marked)

  def set_focus_last(self):
    # FIXME: don't do anything here, let subclasses override
    if hasattr(self.body, 'set_focus_last'):
      self.body.set_focus_last()

  def toggle_focus_mark(self):
    w, pos = self.get_focus()
    if w is not None:
      key = self._get_mark_key(w, pos)
      if w.marked:
        self._unmark(key)
      else:
        self._mark(key, w)

  def unmark_all(self):
    for w in self._marked.values():
      w.marked = False
      w._update_w() # FIXME

    self._marked.clear()

  def _get_mark_key(self, w, pos):
    return pos

  def _mark(self, key, w):
    self._marked[key] = w
    w.marked = True
    w._update_w() # FIXME

  def _unmark(self, key):
    try:
      w = self._marked[key]
      w.marked = False
      w._update_w() # FIXME
      del self._marked[key]
    except KeyError:
      pass

  def _mark_and_move_rel(self, delta):
    w, pos = self.get_focus()
    if pos is not None:
      self.toggle_focus_mark()
      self.set_focus(pos+delta)


class CachedCollectionWalker(urwid.ListWalker):
  def __init__(self, collection, format, app, row_widget, show_pos_index=False):
    self.focus = 0
    self.cache = []
    self.cache_bounds = [0,0]

    self._set_collection(collection)
    self.format = format
    self.app = app
    self.row_widget = row_widget
    self.show_pos_index = show_pos_index

    self.parser = mifl.MiflParser(config.formatting[format])

  def _get_ids(self):
    return self._ids

  def _set_ids(self, ids):
    self._ids = ids
    self.ids_len = len(self._ids)
    self._clear_cache()

  ids = property(_get_ids, _set_ids)

  def _get_collection(self):
    return self._collection

  def _set_collection(self, c):
    self._collection = c

    if hasattr(c, 'ids') and c.ids:
      self._set_ids(list(c.ids))
    else:
      # XXX: get order arg also?
      self._set_ids(xs.coll_query_ids(c))
    self._clear_cache()
    self._modified()

  collection = property(_get_collection, _set_collection)

  def _in_bounds(self, n):
    return n >= self.cache_bounds[0] and n < self.cache_bounds[1]

  def _load_cache(self, pos):
    screen_rows = self.app.ui.get_cols_rows()[1]

    n = int(1.5*screen_rows)
    min_pos = max(pos - n, 0)
    max_pos = min(pos + n, self.ids_len)
    self.cache_bounds = [min_pos, max_pos]

    ids = self.ids[min_pos:max_pos]

    idl = coll.IDList()
    idl.ids += ids
    fields = self.parser[0].symbol_names()
    infos = xs.coll_query_infos(idl, fields=fields)
    infos = dict([(i['id'], i) for i in infos])

    self.cache = []
    for i, id in enumerate(ids):
      info = infos[id]
      if self.show_pos_index:
        pos_index = ('%%-%dd. ' % len(str(self.ids_len))) % (i+min_pos+1)
      else:
        pos_index = ''
      text = '%s%s' % (pos_index, self.parser[0].eval(info)[0])
      self.cache.append(self.row_widget(id, text))

  def _clear_cache(self):
    # delete the cache object and b0rk the cache_bounds so the cache will
    # be loaded the next time the playlist comes in view
    del self.cache
    self.cache = []
    self.cache_bounds = [0xDEADBEEF, -1] # -1 will always fail the boundary check

  def get_pos(self, pos):
    if pos < 0 or pos >= self.ids_len:
      return None, None

    if not self._in_bounds(pos):
      self._load_cache(pos)

    try:
      w = self.cache[pos-self.cache_bounds[0]]
      return w, pos
    except IndexError:
      return None, None

  def get_focus(self):
    return self.get_pos(self.focus)

  def set_focus(self, focus):
    if focus <= 0:
      focus = 0
    elif focus >= self.ids_len:
      focus = self.ids_len - 1

    self.focus = focus
    self._modified()

  def set_focus_last(self):
    self.set_focus(self.ids_len-1)

  def get_prev(self, pos):
    return self.get_pos(pos-1)

  def get_next(self, pos):
    return self.get_pos(pos+1)

