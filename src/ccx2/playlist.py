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

import collutil
import config
import keys
import listbox
import mifl
import signals
import widgets
import xmms

xs = xmms.get()


class PlaylistWalker(urwid.ListWalker):
  def __init__(self, pls, app, format):
    self.pls = pls
    self.format = format
    self.parser = mifl.MiflParser(config.formatting[format])
    self.widgets = {}
    self.focus = 0

    self.feeder = collutil.PlaylistFeeder(self.pls, self.parser[0].symbol_names())

    try:
      self.current_pos = int(self.feeder.collection.attributes.get('position', -1))
    except ValueError:
      self.current_pos = -1

    signals.connect('xmms-playlist-current-pos', self.on_xmms_playlist_current_pos)
    signals.connect('xmms-playlist-changed', self.on_xmms_playlist_changed)

  def __len__(self):
    return len(self.feeder)

  def on_xmms_playlist_changed(self, pls, type, id, pos, newpos):
    if pls != self.pls:
      return

    self.set_focus(self.focus)
    signals.emit('need-redraw')

  def on_xmms_playlist_current_pos(self, pls, pos):
    if pls == self.pls and pos != self.current_pos:
      self.current_pos = pos
      signals.emit('need-redraw')

  def get_pos(self, pos):
    mid = self.feeder.position_id(pos)

    if pos < 0 or mid is None:
      return None, None

    if mid not in self.widgets:
      text = self.parser[0].eval(self.feeder[pos])[0]
      self.widgets[mid] = widgets.SongWidget(mid, text)

    w = self.widgets[mid]

    return w, pos

  def set_focus(self, focus):
    if focus <= 0:
      focus = 0
    elif focus >= len(self.feeder):
      focus = len(self.feeder) - 1

    self.focus = focus
    self._modified()

  def set_focus_last(self): self.set_focus(len(self.feeder)-1)
  def get_focus(self): return self.get_pos(self.focus)
  def get_prev(self, pos): return self.get_pos(pos-1)
  def get_next(self, pos): return self.get_pos(pos+1)


class Playlist(listbox.MarkableListBox):
  def __init__(self, app):
    self.__super.__init__([], app.ch)
    self.body.current_pos = -1 # filthy filthy

    self.app = app
    self.format = 'simple'

    self._walkers = {} # pls => walker
    self.active_pls = xs.playlist_current_active()
    self.view_pls = self.active_pls

    signals.connect('xmms-playlist-loaded', self.load)
    signals.connect('xmms-playlist-changed', self.on_xmms_playlist_changed)
    signals.connect('xmms-playlist-current-pos', self.on_xmms_playlist_current_pos)

    self.register_commands()

    self.load(self.active_pls)

  def register_commands(self):
    self.app.ch.register_command(self, 'play-focused', self.play_focus)
    self.app.ch.register_command(self, 'move-marked-up', self.move_marked_up)
    self.app.ch.register_command(self, 'move-marked-down', self.move_marked_down)
    self.app.ch.register_command(self, 'remove-marked', self.remove_marked)
    self.app.ch.register_command(self, 'search-same', self.search_same)
    self.app.ch.register_command(self, 'sa', 'search-same album') # XXX: alias
    self.app.ch.register_command(self, 'sar', 'search-same artist') # XXX: alias

    for command, k in keys.bindings['playlist'].iteritems():
      self.app.ch.register_keys(self, command, k)

    self.app.ch.register_keys(self, 'remove-marked', keys.bindings['general']['remove'])

  def load(self, pls, from_xmms=True):
    if pls not in self._walkers:
      self._walkers[pls] = PlaylistWalker(pls, self.app, self.format)

    self._set_active_attr(self.body.current_pos, self._walkers[pls].current_pos)
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

  def on_xmms_playlist_current_pos(self, pls, pos):
    self._set_active_attr(self.body.current_pos, pos)

  def play_focus(self, context, args):
    pos = self.get_focus()[1]
    if pos is not None:
      xs.playlist_play(playlist=self.view_pls, pos=pos)

  def remove_marked(self, context, args):
    m = self.marked_data
    if not m:
      w, pos = self.get_focus()
      if pos is None:
        return
      m = {pos: self.get_mark_data(pos, w)}

    for pos, w in sorted(m.items(), key=lambda e: e[0], reverse=True):
      xs.playlist_remove_entry(pos, self.view_pls, sync=False)

    self.unmark_all()

  def move_marked_up(self, context, args):
    m = self.marked_data.items()
    if not m:
      w, pos = self.get_focus()
      if pos is None:
        return
      m = [(pos, self.get_mark_data(pos, w))]

    m.sort(key=lambda e: e[0])
    p = 0
    while m and m[0][0] == p:
      m.pop(0)
      p += 1

    if not m:
      return

    for pos, mid in m:
      xs.playlist_move(pos, pos - 1, sync=False)
      if not self.marked_data: # moving only the focused song
        self.set_focus(pos-1)
      else:
        self.toggle_mark(pos, mid)
        self.toggle_mark(pos-1, mid)
        # TODO: scroll if moving past last row in view

  def move_marked_down(self, context, args):
    m = self.marked_data.items()
    if not m:
      w, pos = self.get_focus()
      if pos is None:
        return
      m = [(pos, self.get_mark_data(pos, w))]

    m.sort(key=lambda e: e[0], reverse=True)
    p = len(self.body) - 1
    while m and m[0][0] == p:
      m.pop(0)
      p -= 1

    if not m:
      return

    for pos, mid in m:
      xs.playlist_move(pos, pos + 1, sync=False)
      if not self.marked_data: # moving only the focused song
        self.set_focus(pos+1)
      else:
        self.toggle_mark(pos, mid)
        self.toggle_mark(pos+1, mid)
        # TODO: scroll if moving past last row in view

  def search_same(self, context, args):
    fields = args.split()
    w, p = self.get_focus()
    if w is not None:
      info = xs.medialib_get_info(w.id)
      q = ' AND '.join('%s:"%s"' % (f, info[f]) for f in fields if info.get(f))
      if q:
        self.app.search(q)
      else:
        pass # TODO: error message

  def get_mark_data(self, pos, w):
    return w.id

  def get_contexts(self):
    return [self]

  def _set_active_attr(self, prevpos, newpos):
    if prevpos != -1:
      self.remove_row_attr(prevpos, 'active')

    if newpos != -1:
      self.add_row_attr(newpos, 'active')


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

  def __len__(self):
    return self.nplaylists

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

    if pos not in self.rows:
      self.rows[pos] = widgets.PlaylistWidget(pls)

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
    self.cur_active = pls

  def on_xmms_playlist_changed(self, pls, type, id, pos, newpos):
    if pos is None and \
       type in (xmmsclient.PLAYLIST_CHANGED_ADD,
                xmmsclient.PLAYLIST_CHANGED_MOVE,
                xmmsclient.PLAYLIST_CHANGED_REMOVE):
      self._reload()
      signals.emit('need-redraw')


class PlaylistSwitcher(listbox.MarkableListBox):
  def __init__(self, app):
    self.__super.__init__(PlaylistSwitcherWalker(), app.ch)

    self.app = app
    self.register_commands()
    self.cur_active = xs.playlist_current_active()
    self._set_active_attr(None, self.cur_active)

    signals.connect('xmms-playlist-loaded', self.on_xmms_playlist_loaded)

  def register_commands(self):
    self.app.ch.register_command(self, 'load-focused', self.load_focused)
    self.app.ch.register_command(self, 'remove-focused', self.remove_marked)
    self.app.ch.register_command(self, 'rename-focused', self.rename_focused)
    self.app.ch.register_command(self, 'add-focused-to-playlist', self.add_to_current)
    self.app.ch.register_command(self, 'new', self.new_playlist)

    for command, k in keys.bindings['playlist-switcher'].iteritems():
      self.app.ch.register_keys(self, command, k)

    self.app.ch.register_keys(self, 'remove-focused', keys.bindings['general']['remove'])

  def on_xmms_playlist_loaded(self, pls):
    self._set_active_attr(self.cur_active, pls)
    self.cur_active = pls
    self._invalidate()
    signals.emit('need-redraw')

  def _set_active_attr(self, prevpls, newpls):
    try:
      if prevpls:
        prevpos = self.body.playlists.index(prevpls)
      newpos = self.body.playlists.index(newpls)
    except ValueError:
      return # shouldn't happen

    if prevpls:
      self.remove_row_attr(prevpos, 'active')

    if newpls:
      self.add_row_attr(newpos, 'active')

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

