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
import xmmsclient

from xmmsclient import collections as coll
from xmmsclient.sync import XMMSError

from ccx2 import mifl
from ccx2 import signals
from ccx2 import widgets
from ccx2 import xmms
from ccx2 import config

xs = xmms.get()


class PlaylistWalker(urwid.ListWalker):
  def __init__(self, pls, active_pls, app, format):
    self.focus = 0
    self.cache = []
    self.cache_bounds = (0,0)
    self.app = app
    self.format = format
    self.parser = mifl.MiflParser(config.formatting['playlist'][format])

    self.pls = pls
    self.active_pls = active_pls

    signals.connect('xmms-playlist-current-pos', self._on_xmms_playlist_current_pos)
    signals.connect('xmms-playlist-changed', self._on_xmms_playlist_changed)

    if self.pls == self.active_pls:
      try:
        self.current_pos = xs.playlist_current_pos()['position']
      except XMMSError:
        self.current_pos = -1
    else:
      self.current_pos = -1

    self.pls_ids = list(xs.coll_get(self.pls, 'Playlists').ids)
    self.pls_len = len(self.pls_ids)

  def _in_bounds(self, n):
    return n >= self.cache_bounds[0] and n < self.cache_bounds[1]

  def _load_cache(self, pos):
    screen_rows = self.app.ui.get_cols_rows()[1]

    n = int(1.5*screen_rows)
    min_pos = max(pos - n, 0)
    max_pos = min(pos + n, self.pls_len)
    self.cache_bounds = (min_pos, max_pos)

    ids = self.pls_ids[min_pos:max_pos]

    idl = coll.IDList()
    idl.ids += ids
    fields = self.parser[0].symbol_names()
    infos = xs.coll_query_infos(idl, fields=fields)
    infos = dict([(i['id'], i) for i in infos])

    self.cache = []
    for i, id in enumerate(ids):
      info = infos[id]
      pls_pos = ('%%%dd.' % len(str(self.pls_len))) % (i+min_pos+1)
      text = '%s %s' % (pls_pos, self.parser[0].eval(info)[0])
      self.cache.append(widgets.SongWidget(id, text))

  def _clear_cache(self):
    # delete the cache object and b0rk the cache_bounds so the cache will
    # be loaded the next time the playlist comes in view
    del self.cache
    self.cache_bounds = (0xDEADBEEF, -1) # -1 will always fail the boundary check

  def _on_xmms_playlist_changed(self, pls, type, id, pos, newpos):
    if pos is None:
      return

    if type == xmmsclient.PLAYLIST_CHANGED_ADD:
      self.pls_ids.append(id)
      self.pls_len += 1
    elif type == xmmsclient.PLAYLIST_CHANGED_INSERT:
      self.pls_ids.insert(pos, id)
      self.pls_len += 1
    elif type == xmmsclient.PLAYLIST_CHANGED_REMOVE:
      del self.pls_ids[pos]
      self.pls_len -= 1
      if pos == self.focus:
        self.set_focus(self.focus)
    elif type == xmmsclient.PLAYLIST_CHANGED_MOVE:
      self.pls_ids.insert(newpos, self.pls_ids.pop(pos))
    else:
      # hard reload everything just in case
      self.pls_ids = list(xs.coll_get(self.pls, 'Playlists').ids)
      self.pls_len = len(self.pls_ids)
      self._clear_cache()

    if pos >= self.cache_bounds[0] and pos < self.cache_bounds[1]:
      if pls == self.pls:
        self._load_cache(self.focus)
        signals.emit('need-redraw')
      else:
        self._clear_cache()

  def _on_xmms_playlist_current_pos(self, pls, pos):
    if pls == self.pls:
      if self._in_bounds(self.current_pos):
        self.cache[self.current_pos-self.cache_bounds[0]].unset_active()
      else:
        pass # TODO: scroll

      self.current_pos = pos
      signals.emit('need-redraw')

  def _get_at_pos(self, pos):
    if pos < 0 or pos >= self.pls_len:
      return None, None

    if not self._in_bounds(pos):
      self._load_cache(pos)

    w = self.cache[pos-self.cache_bounds[0]]

    if pos == self.current_pos:
      w.set_active()

    return w, pos

  def get_focus(self): 
    return self._get_at_pos(self.focus)
  
  def set_focus(self, focus):
    if focus <= 0:
      focus = 0
    elif focus >= self.pls_len:
      focus = self.pls_len - 1

    self.focus = focus
    self._modified()
  
  def get_prev(self, pos):
    return self._get_at_pos(pos-1)

  def get_next(self, pos):
    return self._get_at_pos(pos+1)


class Playlist(widgets.CustomKeysListBox):
  def __init__(self, app):
    keys = {}
    for action in (('move-up', 'up'),
                   ('move-down', 'down'),
                   ('page-up', 'page up'),
                   ('page-down', 'page down')):
      keys.update([(k, action[1]) for k in config.keybindings['general'][action[0]]])

    self.__super.__init__(keys, [])

    self.app = app
    self.format = 'simple'

    self._key_action = self._make_key_action_mapping()
    self._walkers = {} # pls => walker
    self.active_pls = xs.playlist_current_active()
    self.view_pls = self.active_pls

    signals.connect('xmms-playlist-loaded', self.load)
    signals.connect('xmms-playlist-changed', self._on_xmms_playlist_changed)

    self.load(self.active_pls)

  def load(self, pls, from_xmms=True):
    if pls not in self._walkers:
      self._walkers[pls] = PlaylistWalker(pls, self.active_pls, self.app, self.format)

    self._set_body(self._walkers[pls])

    if from_xmms:
      self.active_pls = pls

    self.view_pls = pls

  def _on_xmms_playlist_changed(self, pls, type, id, pos, newpos):
    try:
      if type == xmmsclient.PLAYLIST_CHANGED_REMOVE and not pos:
        del self._walkers[pls]
    except KeyError:
      pass

  def keypress(self, size, key):
    if key in self._key_action:
      self._key_action[key]()
    else:
      return self.__super.keypress(size, key)

  def _make_key_action_mapping(self):
    m = {}
    for section, action, fun in (('playlist', 'play-highlighted', self._play_highlighted),
                                 ('general', 'delete', self._delete_songs),):
      for key in config.keybindings[section][action]:
        m[key] = fun

    return m

  def _play_highlighted(self):
    pos = self.get_focus()[1]
    if pos is not None:
      xs.playlist_play(playlist=self.view_pls, pos=pos)

  def _delete_songs(self):
    pos = self.get_focus()[1]
    if pos is not None:
      xs.playlist_remove_entry(pos, self.view_pls, sync=False)

  def _set_body(self, body):
    self.body = body
    self._invalidate()

  def get_widget(self):
    return self


class PlaylistSwitcherWalker(urwid.ListWalker):
  def __init__(self):
    self.focus = 0
    self.rows = {}
    self.playlists = []
    self.nplaylists = 0

    signals.connect('xmms-collection-changed', self._on_xmms_collection_changed)
    signals.connect('xmms-playlist-loaded', self._on_xmms_playlist_loaded)
    signals.connect('xmms-playlist-changed', self._on_xmms_playlist_changed)

    self._load()

  def _load(self):
    self.playlists = [p for p in sorted(xs.playlist_list()) if p != '_active']
    self.nplaylists = len(self.playlists)
    self.cur_active = xs.playlist_current_active()

  def _reload(self):
    self.rows = {}
    self._load()
    if self.focus >= self.nplaylists:
      self.focus = self.nplaylists-1
    self._modified()

  def _on_xmms_collection_changed(self, pls, type, namespace, newname):
    if namespace == 'Playlists' and type != xmmsclient.COLLECTION_CHANGED_UPDATE:
      self._reload()
      signals.emit('need-redraw')

  def _on_xmms_playlist_loaded(self, pls):
    i = self.playlists.index(pls)
    if i in self.rows:
      self.rows[i].set_active()

    i = self.playlists.index(self.cur_active)
    if i in self.rows:
      self.rows[i].unset_active()

    self.cur_active = pls

  def _on_xmms_playlist_changed(self, pls, type, id, pos, newpos):
    if type in (xmmsclient.PLAYLIST_CHANGED_ADD,
                xmmsclient.PLAYLIST_CHANGED_MOVE,
                xmmsclient.PLAYLIST_CHANGED_REMOVE):
      self._reload()
      signals.emit('need-redraw')

  def _get_at_pos(self, pos):
    if pos < 0 or pos >= self.nplaylists:
      return None, None

    pls = self.playlists[pos]

    try:
      return self.rows[pos], pos
    except KeyError:
      self.rows[pos] = widgets.PlaylistWidget(pls)

      if pls == self.cur_active:
        self.rows[pos].set_active()

      return self.rows[pos], pos

  def get_focus(self):
    return self._get_at_pos(self.focus)

  def set_focus(self, focus):
    if focus <= 0:
      focus = 0
    elif focus >= self.nplaylists:
      focus = self.nplaylists-1
    self.focus = focus
    self._modified()

  def get_prev(self, pos):
    return self._get_at_pos(pos-1)

  def get_next(self, pos):
    return self._get_at_pos(pos+1)


class PlaylistSwitcher(widgets.CustomKeysListBox):
  def __init__(self, app):
    self.app = app

    keys = {}
    for action in (('move-up', 'up'),
                   ('move-down', 'down'),
                   ('page-up', 'page up'),
                   ('page-down', 'page down')):
      keys.update([(k, action[1]) for k in config.keybindings['general'][action[0]]])

    self.__super.__init__(keys, PlaylistSwitcherWalker())

    self._key_action = self._make_key_action_mapping()

  def _make_key_action_mapping(self):
    m = {}
    for section, action, fun in \
        (('playlist-switcher', 'load', self._load_highlighted),
         ('general', 'delete', self._delete_highlighted),
         ('playlist-switcher', 'rename', self._rename_highlighted),
         ('playlist-switcher', 'add-playlist-to-current', self._add_playlist_to_current),
         ('playlist-switcher', 'new', self._new_playlist),):
      for key in config.keybindings[section][action]:
        m[key] = fun

    return m

  def _load_highlighted(self):
    w = self.get_focus()[0]
    if w:
      xs.playlist_load(w.name, sync=False)

  def _delete_highlighted(self):
    w = self.get_focus()[0]
    if w:
      xs.playlist_remove(w.name, sync=False)

  def _rename_highlighted(self):
    w = self.get_focus()[0]
    if w:
      dialog = widgets.InputDialog('new playlist name', 55, 5)
      new_name = self.app.show_dialog(dialog)
      if new_name:
        xs.coll_rename(w.name, new_name, 'Playlists', sync=False)

  def _add_playlist_to_current(self):
    w = self.get_focus()[0]
    if w:
      # this awfulness stems from the fact that you have to use playlist_add_collection,
      # but collections in the playlist namespace don't have order, doh
      # coll2.0 should fix this mess
      idl = coll.IDList()
      cur_active = xs.playlist_current_active()
      ids_from = xs.playlist_list_entries(w.name, 'Playlists')
      ids_to = xs.playlist_list_entries(cur_active, 'Playlists')

      for id in ids_to+ids_from:
        idl.ids.append(id)

      xs.coll_save(idl, cur_active, 'Playlists')

  def _new_playlist(self):
    dialog = widgets.InputDialog('playlist name', 55, 5)
    name = self.app.show_dialog(dialog)
    if name:
      xs.playlist_create(name, sync=False)

  def keypress(self, size, key):
    if key in self._key_action:
      self._key_action[key]()
    else:
      return self.__super.keypress(size, key)

  def get_widget(self):
    return self

