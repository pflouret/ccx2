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

import common
import keys
import mifl
import signals
import widgets
import xmms

xs = xmms.get()


class PlaylistWalker(common.CachedCollectionWalker):
  def __init__(self, pls, active_pls, app, format):
    self.pls = pls
    self.active_pls = active_pls

    signals.connect('xmms-playlist-current-pos', self.on_xmms_playlist_current_pos)
    signals.connect('xmms-playlist-changed', self.on_xmms_playlist_changed)

    if self.pls == self.active_pls:
      try:
        self.current_pos = xs.playlist_current_pos()['position']
      except (XMMSError, TypeError):
        self.current_pos = -1
    else:
      self.current_pos = -1

    c = xs.coll_get(self.pls, 'Playlists')

    common.CachedCollectionWalker.__init__(self, c, format, app, widgets.SongWidget)

  def on_xmms_playlist_changed(self, pls, type, id, pos, newpos):

    if pls != self.pls:
      return

    if id is not None and type in (xmmsclient.PLAYLIST_CHANGED_ADD,
                                   xmmsclient.PLAYLIST_CHANGED_MOVE,
                                   xmmsclient.PLAYLIST_CHANGED_INSERT):
      info = xs.medialib_get_info(id)
      widget = self.row_widget(id, self.parser[0].eval(info)[0])

    # oh god...
    if type == xmmsclient.PLAYLIST_CHANGED_ADD:
      if self._in_bounds(pos):
        self.cache.append(widget)
        self.cache_bounds[1] += 1
      self.ids.append(id)
      self.ids_len += 1
    elif type == xmmsclient.PLAYLIST_CHANGED_INSERT:
      if self._in_bounds(pos):
        self.cache.insert(pos, widget)
        self.cache_bounds[1] += 1
      self.ids.insert(pos, id)
      self.ids_len += 1
    elif type == xmmsclient.PLAYLIST_CHANGED_REMOVE:
      if self._in_bounds(pos):
        del self.cache[pos - self.cache_bounds[0]]
        self.cache_bounds[1] -= 1
      del self._ids[pos]
      self.ids_len -= 1
      self.set_focus(self.focus)
    elif type == xmmsclient.PLAYLIST_CHANGED_MOVE:
      if self._in_bounds(pos):
        row = self.cache.pop(pos - self.cache_bounds[0])
      else:
        row = widget

      if self._in_bounds(newpos):
        self.cache.insert(newpos-self.cache_bounds[0], row)
      else:
        self.cache_bounds[1] -= 1
      self.ids.insert(newpos, self._ids.pop(pos))
      if self.focus == pos:
        self.set_focus(newpos)
    else:
      # hard reload everything just in case
      self.collection = xs.coll_get(self.pls, 'Playlists')
      signals.emit('need-redraw')
      return

    if pos is not None and \
       (pos <= self.cache_bounds[1] or not self.ids_len or not self.cache):
      signals.emit('need-redraw')

  def on_xmms_playlist_current_pos(self, pls, pos):
    if pls == self.pls and pos != self.current_pos and pos < self.ids_len:
      if self._in_bounds(self.current_pos):
        w = self.cache[self.current_pos - self.cache_bounds[0]]
        w.unset_active()
      else:
        pass # TODO: scroll

      self.current_pos = pos
      signals.emit('need-redraw')

  def get_pos(self, pos):
    w, p = common.CachedCollectionWalker.get_pos(self, pos)

    if w is not None and p is not None and p == self.current_pos:
      w.set_active()

    return w, p


class Playlist(common.MarkableListBox):
  def __init__(self, app):
    self.__super.__init__([], app.ch)

    self.app = app
    self.format = 'simple'

    self._walkers = {} # pls => walker
    self.active_pls = xs.playlist_current_active()
    self.view_pls = self.active_pls

    signals.connect('xmms-playlist-loaded', self.load)
    signals.connect('xmms-playlist-changed', self.on_xmms_playlist_changed)

    self.register_commands()

    self.load(self.active_pls)

  def register_commands(self):
    self.app.ch.register_command(self, 'play-focused', self.play_focus)
    self.app.ch.register_command(self, 'move-marked-up', self.move_marked_up)
    self.app.ch.register_command(self, 'move-marked-down', self.move_marked_down)
    self.app.ch.register_command(self, 'remove-marked', self.remove_marked)

    for command, k in keys.bindings['playlist'].iteritems():
      self.app.ch.register_keys(self, command, k)

    self.app.ch.register_keys(self, 'remove-marked', keys.bindings['general']['remove'])

  def load(self, pls, from_xmms=True):
    if pls not in self._walkers:
      self._walkers[pls] = PlaylistWalker(pls, self.active_pls, self.app, self.format)

    self.body = self._walkers[pls]
    self._invalidate()

    if from_xmms:
      self.active_pls = pls

    self.view_pls = pls

  def on_xmms_playlist_changed(self, pls, type, id, pos, newpos):
    try:
      if type == xmmsclient.PLAYLIST_CHANGED_REMOVE and not pos:
        del self._walkers[pls]
    except KeyError:
      pass

  def play_focus(self, context, args):
    pos = self.get_focus()[1]
    if pos is not None:
      xs.playlist_play(playlist=self.view_pls, pos=pos)

  def remove_marked(self, context, args):
    m = self.marked
    if not m:
      w, pos = self.get_focus()
      if pos is None:
        return
      m = [self._get_mark_key(w, pos)]

    for w, pos in sorted(m, key=lambda e: e[1], reverse=True):
      xs.playlist_remove_entry(pos, self.view_pls, sync=False)

    self.unmark_all()

  def get_contexts(self):
    return [self]

  def move_marked_up(self, context, args):
    # TODO: will have to do this locally and then sync up, or do it synchronous while
    # TODO: turning off the signal, the performance for just receiving the signals is awful
    m = list(self.marked)
    if not m:
      m = [self._get_mark_key(*self.get_focus())]

    m.sort(key=lambda e: e[1])
    p = 0
    while m and m[0][1] == p:
      m.pop(0)
      p += 1

    if not m:
      return

    for w, pos in m:
      xs.playlist_move(pos, pos - 1, sync=False)
      if self.marked:
        self._unmark((w, pos))
        self._mark((w, pos-1), w)

  def move_marked_down(self, context, args):
    m = list(self.marked)
    if not m:
      m = [self._get_mark_key(*self.get_focus())]

    m.sort(key=lambda e: e[1], reverse=True)
    p = self.body.ids_len - 1
    while m and m[0][1] == p:
      m.pop(0)
      p -= 1

    if not m:
      return

    for w, pos in m:
      xs.playlist_move(pos, pos + 1, sync=False)
      if self.marked:
        self._unmark((w, pos))
        self._mark((w, pos+1), w)

  def _get_mark_key(self, w, pos):
    return (w, pos)


class PlaylistSwitcherWalker(urwid.ListWalker):
  def __init__(self):
    self.focus = 0
    self.rows = {}
    self.playlists = []
    self.nplaylists = 0

    signals.connect('xmms-collection-changed', self.on_xmms_collection_changed)
    signals.connect('xmms-playlist-loaded', self.on_xmms_playlist_loaded)
    signals.connect('xmms-playlist-changed', self.on_xmms_playlist_changed)

    self._load()

  def _load(self):
    self.playlists = [p for p in sorted(xs.playlist_list()) if not p.startswith('_')]
    self.nplaylists = len(self.playlists)
    self.cur_active = xs.playlist_current_active()

  def _reload(self):
    self.rows = {}
    self._load()
    if self.focus >= self.nplaylists:
      self.focus = self.nplaylists-1
    self._modified()

  def get_pos(self, pos):
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
    return self.get_pos(self.focus)

  def set_focus(self, focus):
    if focus <= 0:
      focus = 0
    elif focus >= self.nplaylists:
      focus = self.nplaylists-1
    self.focus = focus
    self._modified()

  def get_prev(self, pos):
    return self.get_pos(pos-1)

  def get_next(self, pos):
    return self.get_pos(pos+1)

  def on_xmms_collection_changed(self, pls, type, namespace, newname):
    if namespace == 'Playlists' and type != xmmsclient.COLLECTION_CHANGED_UPDATE:
      self._reload()
      signals.emit('need-redraw')

  def on_xmms_playlist_loaded(self, pls):
    i = self.playlists.index(pls)
    if i in self.rows:
      self.rows[i].set_active()

    i = self.playlists.index(self.cur_active)
    if i in self.rows:
      self.rows[i].unset_active()

    self.cur_active = pls
    signals.emit('need-redraw')

  def on_xmms_playlist_changed(self, pls, type, id, pos, newpos):
    if pos is None and \
       type in (xmmsclient.PLAYLIST_CHANGED_ADD,
                xmmsclient.PLAYLIST_CHANGED_MOVE,
                xmmsclient.PLAYLIST_CHANGED_REMOVE):
      self._reload()
      signals.emit('need-redraw')


class PlaylistSwitcher(common.MarkableListBox):
  def __init__(self, app):
    self.__super.__init__(PlaylistSwitcherWalker(), app.ch)

    self.app = app
    self.register_commands()

  def register_commands(self):
    self.app.ch.register_command(self, 'load-focused', self.load_focused)
    self.app.ch.register_command(self, 'remove-focused', self.remove_marked)
    self.app.ch.register_command(self, 'rename-focused', self.rename_focused)
    self.app.ch.register_command(self, 'add-focused-to-playlist', self.add_to_current)
    self.app.ch.register_command(self, 'new', self.new_playlist)

    for command, k in keys.bindings['playlist-switcher'].iteritems():
      self.app.ch.register_keys(self, command, k)

    self.app.ch.register_keys(self, 'remove-focused', keys.bindings['general']['remove'])

  def load_focused(self, context=None, args=None):
    w = self.get_focus()[0]
    if w:
      xs.playlist_load(w.name, sync=False)

  def remove_marked(self, context=None, args=None):
    w = self.get_focus()[0]
    if w:
      xs.playlist_remove(w.name, sync=False)

  def rename_focused(self, context=None, args=None):
    w = self.get_focus()[0]
    if w:
      dialog = widgets.InputDialog('new playlist name', 55, 5)
      new_name = self.app.show_dialog(dialog)
      if new_name:
        xs.coll_rename(w.name, new_name, 'Playlists', sync=False)

  def add_to_current(self, context=None, args=None):
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

  def new_playlist(self, context=None, args=None):
    dialog = widgets.InputDialog('playlist name', 55, 5)
    name = self.app.show_dialog(dialog)
    if name:
      xs.playlist_create(name, sync=False)

  def get_contexts(self):
    return [self]
