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

from ccx2 import signals
from ccx2 import widgets
from ccx2 import xmms
from ccx2.config import keybindings

xs = xmms.get()


class PlaylistWalker(urwid.ListWalker):
  def __init__(self, pls, active_pls):
    self.focus = 0
    self.rows = {}
    self.songs = []
    self.nsongs = 0

    self.pls = pls
    self.active_pls = active_pls

    signals.connect('xmms-playlist-current-pos', self._on_xmms_playlist_current_pos)

    if self.pls == self.active_pls:
      try:
        self.current_pos = xs.playlist_current_pos()['position']
      except XMMSError:
        self.current_pos = -1
    else:
      self.current_pos = -1

    self._load()

  def _load(self):
    ids = xs.playlist_list_entries(self.pls)
    songs = xs.coll_query_infos(coll.Reference(self.pls, 'Playlists'),
                                fields=['artist', 'album', 'title'])

    songs = dict([(s['id'], s) for s in songs])

    self.songs = []
    for id in ids:
      self.songs.append(songs[id])
    self.nsongs = len(self.songs)

  def _on_xmms_playlist_current_pos(self, pls, pos):
    if pls == self.pls:
      if pos in self.rows:
        self.rows[pos].set_active()
      if self.current_pos in self.rows:
        self.rows[self.current_pos].unset_active()

      self.current_pos = pos
      self._modified()

  def _get_at_pos(self, pos):
    if pos < 0 or pos >= self.nsongs:
      return None, None

    song = self.songs[pos]

    try:
      # TODO: cache only a couple of pages, not the whole playlist
      return self.rows[pos], pos
    except KeyError:
      text = '%s - %s - %s' % (song['artist'], song['album'], song['title'])
      self.rows[pos] = widgets.SongWidget(song['id'], text)
      if pos == self.current_pos:
        self.rows[pos].set_active()
      return self.rows[pos], pos
  
  def get_focus(self): 
    return self._get_at_pos(self.focus)
  
  def set_focus(self, focus):
    if focus <= 0:
      focus = 0
    elif focus >= self.nsongs:
      focus = self.nsongs-1
    self.focus = focus
    self._modified()
  
  def get_prev(self, pos):
    return self._get_at_pos(pos-1)

  def get_next(self, pos):
    return self._get_at_pos(pos+1)


class Playlist(widgets.CustomKeysListBox):
  def __init__(self):
    keys = {}
    for action in (('move-up', 'up'),
                   ('move-down', 'down'),
                   ('page-up', 'page up'),
                   ('page-down', 'page down')):
      keys.update([(k, action[1]) for k in keybindings['general'][action[0]]])

    self.__super.__init__(keys, [])

    self._key_action = self._make_key_action_mapping()
    self._walkers = {} # pls => walker
    self.active_pls = xs.playlist_current_active()
    self.view_pls = self.active_pls

    signals.connect('xmms-playlist-loaded', self.load)
    signals.connect('xmms-playlist-changed', self._on_xmms_playlist_changed)

    self.load(self.active_pls)

  def load(self, pls, from_xmms=True):
    if pls not in self._walkers:
      self._walkers[pls] = PlaylistWalker(pls, self.active_pls)

    self._set_body(self._walkers[pls])

    if from_xmms:
      self.active_pls = pls

    self.view_pls = pls

  def _on_xmms_playlist_changed(self, pls, type, id, pos):
    if type == xmmsclient.PLAYLIST_CHANGED_ADD:
      return

    try:
      focus_pos = self._walkers[pls].get_focus()[1]

      # TODO: less brute force would be cool
      del self._walkers[pls]

      if pls == self.view_pls:
        if type == xmmsclient.PLAYLIST_CHANGED_REMOVE and not pos:
          self.load(self.active_pls)
        elif type == xmmsclient.PLAYLIST_CHANGED_REMOVE:
          self.load(pls)
          if pos < focus_pos:
            focus_pos -= 1
          self._walkers[pls].set_focus(focus_pos)
    except KeyError:
      pass

    #if type == xmmsclient.PLAYLIST_CHANGED_ADD:
    #elif type == xmmsclient.PLAYLIST_CHANGED_MOVE:
    #elif type == xmmsclient.PLAYLIST_CHANGED_SORT:
    #elif type == xmmsclient.PLAYLIST_CHANGED_CLEAR:
    #elif type == xmmsclient.PLAYLIST_CHANGED_REMOVE:
    #elif type == xmmsclient.PLAYLIST_CHANGED_UPDATE:
    #elif type == xmmsclient.PLAYLIST_CHANGED_INSERT:
    #elif type == xmmsclient.PLAYLIST_CHANGED_SHUFFLE:

  def keypress(self, size, key):
    if key in self._key_action:
      self._key_action[key]()
    else:
      return self.__super.keypress(size, key)

  def _make_key_action_mapping(self):
    m = {}
    for section, action, fun in (('playlist', 'play-highlighted', self._play_highlighted),
                                 ('general', 'delete', self._delete_songs),):
      for key in keybindings[section][action]:
        m[key] = fun

    return m

  def _play_highlighted(self):
    pos = self.get_focus()[1]
    xs.playlist_play(playlist=self.view_pls, pos=pos, sync=False)

  def _delete_songs(self):
    pos = self.get_focus()[1]
    if pos:
      xs.playlist_remove_entry(pos, self.view_pls, sync=False)

  def _set_body(self, body):
    self.body = body
    self._invalidate()


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
    self.playlists = [p for p in xs.playlist_list() if p != '_active']
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

  def _on_xmms_playlist_loaded(self, pls):
    i = self.playlists.index(pls)
    if i in self.rows:
      self.rows[i].set_active()

    i = self.playlists.index(self.cur_active)
    if i in self.rows:
      self.rows[i].unset_active()

    self.cur_active = pls
    self._modified()

  def _on_xmms_playlist_changed(self, pls, type, id, pos):
    if type in (xmmsclient.PLAYLIST_CHANGED_ADD,
                xmmsclient.PLAYLIST_CHANGED_MOVE,
                xmmsclient.PLAYLIST_CHANGED_REMOVE):
      self._reload()

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
      keys.update([(k, action[1]) for k in keybindings['general'][action[0]]])

    self.__super.__init__(keys, PlaylistSwitcherWalker())

    self._key_action = self._make_key_action_mapping()

  def _make_key_action_mapping(self):
    m = {}
    for section, action, fun in \
        (('playlist-switcher', 'load', self._load_highlighted),
         ('general', 'delete', self._delete_highlighted),
         ('playlist-switcher', 'rename', self._rename_highlighted),
         ('playlist-switcher', 'new', self._new_playlist),):
      for key in keybindings[section][action]:
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

