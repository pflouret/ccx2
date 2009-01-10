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
import mifl
import xmms

xs = xmms.get()

class ActionsListBox(urwid.ListBox):
  def __init__(self, *args, **kwargs):
    self._movement_keys = {}
    for action in (('move-up', 'up'),
                   ('move-down', 'down'),
                   ('page-up', 'page up'),
                   ('page-down', 'page down')):
      self._movement_keys.update(
          [(k, action[1]) for k in config.keybindings['general'][action[0]]])

    self._action_map = {}
    self._actions = [('general', 'move-top', lambda: self.set_focus(0)),
                     ('general', 'move-bottom', lambda: self.body.set_focus_last()),
                     ('general', 'select-and-move-up', lambda: self.focus_rel(-1)),
                     ('general', 'select-and-move-down', lambda: self.focus_rel(1))]

    if 'actions' in kwargs:
      self._actions.extend(kwargs.pop('actions'))

    self._setup_actions()

    self.__super.__init__(*args, **kwargs)

  def _get_actions(self):
    return self._actions

  def _set_actions(self, actions):
    self._actions.extend(actions)
    self._setup_actions()

  actions = property(_get_actions, _set_actions)

  def _setup_actions(self):
    for section, action, fun in self._actions:
      for key in config.keybindings[section][action]:
        self._action_map[key] = fun

  def focus_rel(self, delta):
    w, pos = self.get_focus()

    if pos is not None:
      self.set_focus(pos+delta)

  def keypress(self, size, key):
    key = self.__super.keypress(size, self._movement_keys.get(key, key))

    if key in self._action_map:
      self._action_map[key]()
    else:
      return key


class CachedCollectionWalker(urwid.ListWalker):
  def __init__(self, collection, format, app, row_widget, show_pos_index=False):
    self.focus = 0
    self.cache = []
    self.cache_bounds = (0,0)

    self._set_collection(collection)
    self.format = format
    self.app = app
    self.row_widget = row_widget
    self.show_pos_index = show_pos_index

    self.parser = mifl.MiflParser(config.formatting['playlist'][format])

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

    if type(c) == coll.IDList:
      self._set_ids(list(c.ids))
    else:
      # XXX: get order arg also?
      self._set_ids(xs.coll_query_ids(c))

  collection = property(_get_collection, _set_collection)

  def _in_bounds(self, n):
    return n >= self.cache_bounds[0] and n < self.cache_bounds[1]

  def _load_cache(self, pos):
    screen_rows = self.app.ui.get_cols_rows()[1]

    n = int(1.5*screen_rows)
    min_pos = max(pos - n, 0)
    max_pos = min(pos + n, self.ids_len)
    self.cache_bounds = (min_pos, max_pos)

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
        pos_index = ('%%%dd. ' % len(str(self.ids_len))) % (i+min_pos+1)
      else:
        pos_index = ''
      text = '%s%s' % (pos_index, self.parser[0].eval(info)[0])
      self.cache.append(self.row_widget(id, text))

  def _clear_cache(self):
    # delete the cache object and b0rk the cache_bounds so the cache will
    # be loaded the next time the playlist comes in view
    if hasattr(self, 'cache'):
      del self.cache
      self.cache_bounds = (0xDEADBEEF, -1) # -1 will always fail the boundary check

  def get_pos(self, pos):
    if pos < 0 or pos >= self.ids_len:
      return None, None

    if not self._in_bounds(pos):
      self._load_cache(pos)

    w = self.cache[pos-self.cache_bounds[0]]

    return w, pos

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

