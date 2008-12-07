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

from ccx2 import widgets
from ccx2 import xmms
from ccx2.config import keybindings

xs = xmms.get()

class PlaylistWalker(urwid.ListWalker):
  def __init__(self):
    self.focus = 0
    self.rows = {}
    self.songs = []

    self.current = xs.playlist_current_active(sync=True)
    self.current_pos = xs.playlist_current_pos(sync=True)['position']
    xs.register_callback('playlist-current-pos', self._on_xmms_playlist_current_pos)

    self.load()

  def load(self, pls_name=None):
    if pls_name is None:
      pls_name = xs.playlist_current_active(sync=True)
    ids = xs.playlist_list_entries(pls_name, sync=True)
    songs = xs.coll_query_infos(coll.Reference(pls_name, 'Playlists'),
                                fields=['artist', 'album', 'title'],
                                sync=True)
    songs = dict([(s['id'], s) for s in songs])

    self.songs = []
    for id in ids:
      self.songs.append(songs[id])

  def _on_xmms_playlist_current_pos(self, value):
    if value['name'] == self.current:
      self.current_pos = value['position']
      self._modified()

  def _get_at_pos(self, pos):
    if pos < 0 or pos >= len(self.songs):
      return None, None

    song = self.songs[pos]

    if pos == self.current_pos:
      text = u'%s - %s - %s' % (song['artist'], song['album'], song['title'])
      return urwid.AttrWrap(
          widgets.Song(song['id'], text, highlight_on_focus=True),
          'current_song'), pos

    try:
      return self.rows[pos]
    except KeyError:
      text = '%s - %s - %s' % (song['artist'], song['album'], song['title'])
      self.rows[pos] = widgets.Song(song['id'], text, highlight_on_focus=True), pos
      return self.rows[pos]
  
  def get_focus(self): 
    return self._get_at_pos(self.focus)
  
  def set_focus(self, focus):
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
    self.__super.__init__(keys, PlaylistWalker())

    self._key_action = self._make_key_action_mapping()

  def _make_key_action_mapping(self):
    m = {}
    for action, fun in (('play-highlighted', self._play_highlighted),):
      for key in keybindings['playlist'][action]:
        m[key] = fun

    return m

  def _play_highlighted(self):
    pos = self.get_focus()[1]
    xs.playlist_play_pos(pos)

  def keypress(self, size, key):
    if key in self._key_action:
      self._key_action[key]()
    else:
      return self.__super.keypress(size, key)

