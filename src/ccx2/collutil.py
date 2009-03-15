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

import xmmsclient
from xmmsclient import collections as coll

import signals
import xmms


class CollectionFeeder(object):
  def __init__(self, collection, fields, size=100):
    super(CollectionFeeder, self).__init__()

    self.xs = xmms.get()
    self._collection = collection
    self.fields = fields
    self.infos = {}
    self.size = size
    self.window = [0, 0]
    self.ids = None
    self.len = 0

    self.reload_ids()

    signals.connect('xmms-medialib-entry-changed', self.on_medialib_entry_changed)

  def __getitem__(self, position):
    if not self._in_window(position):
      self._move_window(position)

    try:
      return self.infos[self.ids[position]]
    except KeyError:
      raise IndexError

  def __len__(self):
    return self.len

  def _set_collection(self, collection):
    self._collection = collection
    self.reload_ids()
    self.reset_window()
    self.infos = {}

  collection = property(lambda self: self._collection, _set_collection)

  def position_id(self, position):
    try:
      return self.ids[position]
    except IndexError:
      return None

  def id_positions(self, mid):
    return [i for i,m in enumerate(self.ids) if m == mid]

  def reload_ids(self):
    if hasattr(self.collection, 'ids') and self.collection.ids:
      self.ids = list(self.collection.ids)
    else:
      self.ids = self.xs.coll_query_ids(self.collection)

    self.len = len(self.ids)
    self.reset_window()

  def reset_window(self):
    self.window = [0, 0]

  def _in_window(self, n, inclusive=False):
    return n >= self.window[0] and n < self.window[1] + (inclusive and 1 or 0)

  def _move_window(self, center):
    new_window = [max(center-self.size/2, 0), min(center+self.size/2, self.len)]

    #overlap = (max(self.window[0], new_window[0]), min(self.window[1], new_window[1]))
    #if overlap[1] - overlap[0] > 0:
    #  self.infos = dict((i, self.infos[i]) for i in self.ids[overlap[0]:overlap[1]])
    #  left = min(self.window[0], new_window[0])
    #  right = max(self.window[1], new_window[1])
    #else:
    #  self.infos = {}
    #  req_ids = self.ids[new_window[0]:new_window[1]]

    c = coll.IDList()
    c.ids += self.ids[new_window[0]:new_window[1]]
    for info in self.xs.coll_query_infos(c, self.fields):
      self.infos[info['id']] = info

    self.window = new_window

  def on_medialib_entry_changed(self, mid):
    if mid in self.infos:
      self.infos[mid] = self.xs.medialib_get_info(mid)


class PlaylistFeeder(CollectionFeeder):
  def __init__(self, pls_name, fields, size=100):
    self.xs = xmms.get()
    self.name = pls_name

    c = self.xs.coll_get(pls_name, 'Playlists')
    super(PlaylistFeeder, self).__init__(c, fields, size)

    signals.connect('xmms-playlist-changed', self._on_playlist_changed)

  def _on_playlist_changed(self, pls, type, mid, pos, newpos):
    if pls != self.name:
      return

    if type == xmmsclient.PLAYLIST_CHANGED_ADD:
      if self._in_window(pos, inclusive=True):
        self.window[1] += 1
        if mid not in self.infos:
          self.infos[mid] = self.xs.medialib_get_info(mid)
      self.ids.append(mid)
      self.len += 1
    elif type == xmmsclient.PLAYLIST_CHANGED_INSERT:
      if self._in_window(pos):
        self.window[1] += 1
        if mid not in self.infos:
          self.infos[mid] = self.xs.medialib_get_info(mid)
      self.ids.insert(pos, mid)
      self.len += 1
    elif type == xmmsclient.PLAYLIST_CHANGED_REMOVE:
      if self._in_window(pos):
        self.window[1] -= 1
      del self.ids[pos]
      self.len -= 1
    elif type == xmmsclient.PLAYLIST_CHANGED_MOVE:
      self.ids.insert(newpos, self.ids.pop(pos))
    elif type == xmmsclient.PLAYLIST_CHANGED_CLEAR:
      self.window = [0, 0]
      self.infos = {}
      self.ids = []
      self.len = 0
    else:
      self.window = [0, 0]
      self.reload_ids()

