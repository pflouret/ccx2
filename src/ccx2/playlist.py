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

    if self.pls == self.active_pls:
      try:
        self.current_pos = xs.playlist_current_pos()['position']
      except XMMSError:
        self.current_pos = -1
    else:
      self.current_pos = -1


    signals.connect('xmms-playlist-current-pos', self._on_xmms_playlist_current_pos)

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
      self.current_pos = pos
      self._modified()

  #def _on_xmms_playlist_current_pos(self, value):
  #  if value['name'] == self.pls:
  #    self.current_pos = value['position']
  #    self._modified()

  def _get_at_pos(self, pos):
    if pos < 0 or pos >= self.nsongs:
      return None, None

    song = self.songs[pos]

    if pos == self.current_pos:
      text = u'%s - %s - %s' % (song['artist'], song['album'], song['title'])
      return urwid.AttrWrap(
          widgets.SongWidget(song['id'], text, highlight_on_focus=True),
          'current_song'), pos

    try:
      return self.rows[pos]
    except KeyError:
      text = '%s - %s - %s' % (song['artist'], song['album'], song['title'])
      self.rows[pos] = widgets.SongWidget(song['id'], text, highlight_on_focus=True), pos
      return self.rows[pos]
  
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

    self.load(self.active_pls)

  def load(self, pls, from_xmms=True):
    if pls not in self._walkers:
      self._walkers[pls] = PlaylistWalker(pls, self.active_pls)

    self._set_body(self._walkers[pls])

    if from_xmms:
      self.active_pls = pls

    self.view_pls = pls

  def keypress(self, size, key):
    if key in self._key_action:
      self._key_action[key]()
    else:
      return self.__super.keypress(size, key)

  def _make_key_action_mapping(self):
    m = {}
    for action, fun in (('play-highlighted', self._play_highlighted),):
      for key in keybindings['playlist'][action]:
        m[key] = fun

    return m

  def _play_highlighted(self):
    pos = self.get_focus()[1]
    xs.playlist_play(playlist=self.view_pls, pos=pos)

  def _set_body(self, body):
    self.body = body
    self._invalidate()

class PlaylistSwitcherWalker(urwid.ListWalker):
  def __init__(self):
    self.focus = 0
    self.rows = {}
    self.playlists = []

    signals.connect('xmms-playlist-loaded', self._on_xmms_playlist_loaded)

    self._load()

  def _load(self):
    self.playlists = [p for p in xs.playlist_list() if p != '_active']
    self.cur_active = xs.playlist_current_active()

  def _on_xmms_playlist_loaded(self, pls):
    self.cur_active = pls
    self._modified()

  def _get_at_pos(self, pos):
    if pos < 0 or pos >= len(self.playlists):
      return None, None

    pls_name = self.playlists[pos]

    if pls_name == self.cur_active:
      widget = urwid.AttrWrap(widgets.SelectableText(
          pls_name, highlight_on_focus=True), 'current_playlist')
      widget.pls_name = pls_name
      return widget, pos

    try:
      return self.rows[pos], pos
    except KeyError:
      self.rows[pos] = widgets.SelectableText(self.playlists[pos], highlight_on_focus=True)
      self.rows[pos].pls_name = pls_name
      return self.rows[pos], pos

  def get_focus(self):
    return self._get_at_pos(self.focus)

  def set_focus(self, focus):
    self.focus = focus
    self._modified()

  def get_prev(self, pos):
    return self._get_at_pos(pos-1)

  def get_next(self, pos):
    return self._get_at_pos(pos+1)

class PlaylistSwitcher(widgets.CustomKeysListBox):
  def __init__(self):
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
    for action, fun in (('load-highlighted', self._load_highlighted),
                        ('delete-highlighted', lambda: None),
                        ('new-playlist', lambda: None),
                       ):
      for key in keybindings['playlist-switcher'][action]:
        m[key] = fun

    return m

  def _load_highlighted(self):
    pls_name = self.get_focus()[0].pls_name
    xs.playlist_load(pls_name)

  def keypress(self, size, key):
    if key in self._key_action:
      self._key_action[key]()
    else:
      return self.__super.keypress(size, key)

