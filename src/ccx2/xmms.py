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
import sys
import time
import threading

import xmmsclient
from xmmsclient import collections as coll

import signals

# TODO: better doc (rst)

# args -- id:int
signals.register('xmms-playback-current-id')

# args -- info:dict
signals.register('xmms-playback-current-info')

# args -- milliseconds:int
signals.register('xmms-playback-playtime')

# args -- status:int
#  status values:
#  xmmsclient.PLAYBACK_STATUS_PLAY
#  xmmsclient.PLAYBACK_STATUS_STOP
#  xmmsclient.PLAYBACK_STATUS_PAUSE
signals.register('xmms-playback-status')

# args -- playlist_name:string
signals.register('xmms-playlist-loaded')

# args --
# playlist_name:string
# type:int
# id:long (if present, or None)
# position:long (if present, or None)
# newposition:long (if present, or None)
#
# type values:
# xmmsclient.PLAYLIST_CHANGED_ADD
# xmmsclient.PLAYLIST_CHANGED_MOVE
# xmmsclient.PLAYLIST_CHANGED_SORT
# xmmsclient.PLAYLIST_CHANGED_CLEAR
# xmmsclient.PLAYLIST_CHANGED_REMOVE
# xmmsclient.PLAYLIST_CHANGED_UPDATE
# xmmsclient.PLAYLIST_CHANGED_INSERT
# xmmsclient.PLAYLIST_CHANGED_SHUFFLE
signals.register('xmms-playlist-changed')

# args --
# id:int
signals.register('xmms-medialib-entry-changed')

# args --
# name:string
# type:int
# namespace:string (if present, or None)
# new_name:string (if present, or None)
signals.register('xmms-collection-changed')
signals.register('xmms-configval-changed')
signals.register('xmms-mediainfo-reader-status')
signals.register('xmms-medialib-entry-added')
signals.register('xmms-playback-volume-changed')
signals.register('xmms-playlist-current-pos')

_objects = {}

def get(name='ccx2', **kwargs):
  try:
    return _objects[name]
  except KeyError:
    service = XmmsService(name=name, **kwargs)
    _objects[name] = service
    return service

class PlaybackPlaytimeTimer(threading.Thread):
  def __init__(self, seconds, xmms, fun):
    self.seconds = seconds
    self.xmms = xmms
    self.fun = fun

    threading.Thread.__init__(self)
    self.setDaemon(True)

  def run(self):
    time.sleep(self.seconds)
    self.xmms.signal_playback_playtime(self.fun)
    self.xmms.ioout()

class XmmsService(object):
  def __init__(self, path=None, name='ccx2'):
    super(XmmsService, self).__init__()
    self.xmms = xmmsclient.XMMS(name)
    self.xmms_s = xmmsclient.XMMSSync(name+'-sync')
    self.path = path or os.environ.get("XMMS_PATH", None)
    self.connected = False

    self.connect()

  def connect(self):
    def disconnect(r):
      self.connected = False

    try:
      self.xmms.connect(path=self.path, disconnect_func=disconnect)
      self.xmms_s.connect(path=self.path)
      self.connected = True
      self.connect_signals()
    except IOError:
      self.connected = False

    return self.connected

  def _callback_wrapper(self, cb):
    def _w(r):
      if r.iserror():
        return # handle error
      cb(r.value())
    return _w

  def register_callback(self, signal, cb):
    if signal == 'playback-current-id':
      self.xmms.broadcast_playback_current_id(self._callback_wrapper(cb))
    elif signal == 'playback-status':
      self.xmms.broadcast_playback_status(self._callback_wrapper(cb))
    elif signal == 'playback-playtime':
      self.xmms.signal_playback_playtime(self._callback_wrapper(cb))
    elif signal == 'playlist-current-pos':
      self.xmms.broadcast_playlist_current_pos(self._callback_wrapper(cb))
    elif signal == 'playlist-loaded':
      self.xmms.broadcast_playlist_loaded(self._callback_wrapper(cb))

    if self.xmms.want_ioout():
      self.xmms.ioout()

  def ioin(self):
    self.xmms.ioin()

  def ioout(self):
    if self.xmms.want_ioout():
      self.xmms.ioout()

  def _simple_emit_fun(self, signal_name):
    def _fun(r):
      signals.emit(signal_name, r.value())
    return _fun

  def connect_signals(self):
    self.xmms.broadcast_playback_current_id(self._on_playback_current_id)
    self.xmms.broadcast_playback_status(self._simple_emit_fun('xmms-playback-status'))
    self.xmms.broadcast_playlist_loaded(self._simple_emit_fun('xmms-playlist-loaded'))
    self.xmms.broadcast_playlist_current_pos(self._on_playlist_current_pos)
    self.xmms.broadcast_playlist_changed(self._on_playlist_changed)
    self.xmms.broadcast_collection_changed(self._on_collection_changed)
    self.xmms.broadcast_medialib_entry_changed(
        self._simple_emit_fun('xmms-medialib-entry-changed'))
    self.xmms.signal_playback_playtime(self._on_playback_playtime)

    self.ioout()

    #self.xmms.broadcast_configval_changed()
    #self.xmms.broadcast_mediainfo_reader_status()
    #self.xmms.broadcast_medialib_entry_added()
    #self.xmms.broadcast_playback_volume_changed()

  def _on_collection_changed(self, r):
    if not r.iserror():
      v = r.value()
      signals.emit('xmms-collection-changed',
                   v['name'],
                   v['type'],
                   v.get('namespace'),
                   v.get('newname'))

  def _on_playlist_current_pos(self, r):
    if not r.iserror():
      v = r.value()
      signals.emit('xmms-playlist-current-pos', v['name'], v['position'])

  def _on_playlist_changed(self, r):
    if not r.iserror():
      v = r.value()
      signals.emit('xmms-playlist-changed',
                   v['name'],
                   v['type'],
                   v.get('id'),
                   v.get('position'),
                   v.get('newposition'))

  def _medialib_get_info_cb(self, r):
    if not r.iserror() and type(r.value()) == xmmsclient.PropDict:
      signals.emit('xmms-playback-current-info', r.value())

  def _on_playback_current_id(self, r):
    id = r.value()
    signals.emit('xmms-playback-current-id', id)
    self.xmms.medialib_get_info(id, self._medialib_get_info_cb)

  def _on_playback_playtime(self, r):
    signals.emit('xmms-playback-playtime', r.value())
    PlaybackPlaytimeTimer(0.2, self.xmms, self._on_playback_playtime).start()
    return False

  def bindata_retrieve(self, hash, cb=None, sync=True):
    if sync:
      return self.xmms_s.bindata_retrieve(hash)
    else:
      self.xmms.bindata_retrieve(hash, cb)

  def coll_get(self, name, ns='Collections', cb=None, sync=True):
    if sync:
      return self.xmms_s.coll_get(name, ns)
    else:
      self.xmms.coll_get(name, ns, cb=cb)

  def coll_query_ids(self, collection, start=0, leng=0, order=None, cb=None, sync=True):
    if sync:
      try:
        r = self.xmms_s.coll_query_ids(collection, start=start, leng=leng, order=order)
        if type(r) != list:
          r = []
        return r
      except xmmsclient.XMMSError:
        return []
    else:
      self.xmms.coll_query_ids(collection, start=start, leng=leng, order=order, cb=cb)

  def coll_query_infos(self, collection, fields, start=0, leng=0,
                       order=None, cb=None, sync=True, add_id=True):
    if add_id and 'id' not in fields:
      fields = fields + ['id']

    if sync:
      try:
        r = self.xmms_s.coll_query_infos(collection, fields, start=start, leng=leng, order=order)
        if type(r) != list:
          r = []
        return r
      except xmmsclient.XMMSError:
        return []
    else:
      self.xmms.coll_query_infos(collection, fields, start=start, leng=leng, order=order, cb=cb)

  def coll_rename(self, oldname, newname, ns, cb=None, sync=True):
    if sync:
      return self.xmms_s.coll_rename(oldname, newname, ns)
    else:
      self.xmms.coll_rename(oldname, newname, ns, cb=cb)

  def coll_save(self, collection, name, ns, cb=None, sync=True):
    if sync:
      return self.xmms_s.coll_save(collection, name, ns)
    else:
      self.xmms.coll_save(collection, name, ns, cb=cb)

  def configval_get(self, key, cb=None, sync=True):
    if sync:
      return self.xmms_s.configval_get(key)
    else:
      self.xmms.configval_get(key, cb=cb)

  def configval_set(self, key, val, cb=None, sync=True):
    if sync:
      return self.xmms_s.configval_set(key, val)
    else:
      self.xmms.configval_set(key, val, cb=cb)

  def medialib_get_info(self, id, cb=None, sync=True):
    if sync:
      return self.xmms_s.medialib_get_info(id)
    else:
      return self.xmms.medialib_get_info(id, cb=cb)

  def medialib_rehash(self, mid, cb=None, sync=True):
    if sync:
      return self.xmms_s.medialib_rehash(mid)
    else:
      return self.xmms.medialib_rehash(mid, cb=cb)

  def playback_current_id(self, cb=None, sync=True):
    if sync:
      return self.xmms_s.playback_current_id()
    else:
      if cb is None:
        cb = self._on_xmms_playback_current_id
      self.xmms.playback_current_id(cb=cb)

  def playback_current_info(self, cb=None, sync=True):
    i = self.xmms_s.playback_current_id()
    if sync:
      return self.medialib_get_info(i)
    elif cb is not None:
      def _cb(r):
        if not r.iserror() and type(r.value()) == xmmsclient.PropDict:
          cb(r.value())
      self.xmms.medialib_get_info(i, cb=_cb)

  def playback_next(self, cb=None, sync=True):
    self.playlist_set_next(pos=1, relative=True, sync=True)
    if sync:
      return self.playback_tickle()
    else:
      self.playback_tickle()

  def playback_pause(self, cb=None, sync=True):
    if sync:
      return self.xmms_s.playback_pause()
    else:
      self.xmms.playback_pause(cb=cb)

  def playback_play_pause_toggle(self, cb=None, sync=True):
    def __status_cb(res):
      v = res.value()
      if v == xmmsclient.PLAYBACK_STATUS_PLAY:
        self.playback_pause(sync=False)
      else:
        self.playback_start(sync=False)
    self.playback_status(cb=__status_cb, sync=False)

  def playback_prev(self, cb=None, sync=True):
    self.playlist_set_next(pos=-1, relative=True, sync=True)
    if sync:
      return self.playback_tickle()
    else:
      self.playback_tickle(sync=True)

  def playback_seek_ms(self, ms, cb=None, sync=True):
    if sync:
      return self.xmms_s.playback_seek_ms(ms)
    else:
      self.xmms.playback_seek_ms(ms, cb=cb)

  def playback_seek_ms_rel(self, ms, cb=None, sync=True):
    if sync:
      return self.xmms_s.playback_seek_ms_rel(ms)
    else:
      self.xmms.playback_seek_ms_rel(ms, cb=cb)

  def playback_start(self, cb=None, sync=True):
    if sync:
      return self.xmms_s.playback_start()
    else:
      self.xmms.playback_start(cb=cb)

  def playback_status(self, cb=None, sync=True):
    if sync:
      return self.xmms_s.playback_status()
    else:
      self.xmms.playback_status(cb=cb)

  def playback_stop(self, cb=None, sync=True):
    if sync:
      return self.xmms_s.playback_stop()
    else:
      self.xmms.playback_stop(cb=cb)

  def playback_tickle(self, cb=None, sync=True):
    if sync:
      return self.xmms_s.playback_tickle()
    else:
      self.xmms.playback_tickle(cb=cb)

  def playback_volume_get(self, cb=None, sync=True):
    if sync:
      return self.xmms_s.playback_volume_get()
    else:
      self.xmms.playback_volume_get(cb=cb)

  def playback_volume_set(self, channel, volume, cb=None, sync=True):
    if sync:
      return self.xmms_s.playback_volume_set(channel, volume)
    else:
      self.xmms.playback_volume_set(channel, volume, cb=cb)

  def playlist_add_collection(self, coll, order, playlist=None, cb=None, sync=True):
    if sync:
      return self.xmms_s.playlist_add_collection(coll, order, playlist)
    else:
      self.xmms.playlist_add_collection(coll, order, playlist, cb=cb)

  def playlist_add_id(self, id, playlist, cb=None, sync=True):
    if sync:
      return self.xmms_s.playlist_add_id(id, playlist)
    else:
      self.xmms.playlist_add_id(id, playlist, cb=cb)

  def playlist_clear(self, playlist=None, cb=None, sync=True):
    if sync:
      return self.xmms_s.playlist_clear(playlist)
    else:
      self.xmms.playlist_clear(playlist, cb=cb)

  def playlist_create(self, playlist, cb=None, sync=True):
    if sync:
      return self.xmms_s.playlist_create(playlist)
    else:
      self.xmms.playlist_create(playlist, cb=cb)

  def playlist_current_active(self, cb=None, sync=True):
    if sync:
      return self.xmms_s.playlist_current_active()
    else:
      self.xmms.playlist_current_active(cb=cb)

  def playlist_current_pos(self, cb=None, sync=True):
    if sync:
      return self.xmms_s.playlist_current_pos()
    else:
      self.xmms.playlist_current_pos(cb=cb)

  def playlist_insert_collection(self, pos, coll, order, playlist=None, cb=None, sync=True):
    if sync:
      return self.xmms_s.playlist_insert_collection(pos, coll, order, playlist)
    else:
      self.xmms.playlist_insert_collection(pos, coll, order, playlist, cb=cb)

  def playlist_insert_id(self, pos, id, playlist=None, cb=None, sync=True):
    if sync:
      return self.xmms_s.playlist_insert_id(pos, id, playlist)
    else:
      self.xmms.playlist_insert_id(pos, id, playlist, cb=cb)

  def playlist_list(self, cb=None, sync=True):
    if sync:
      return self.xmms_s.playlist_list()
    else:
      self.xmms.playlist_list(cb=cb)

  def playlist_list_entries(self, playlist=None, cb=None, sync=True):
    if sync:
      return self.xmms_s.playlist_list_entries(playlist)
    else:
      self.xmms.playlist_list_entries(playlist, cb=cb)

  def playlist_load(self, playlist, cb=None, sync=True):
    if sync:
      return self.xmms_s.playlist_load(playlist)
    else:
      self.xmms.playlist_load(playlist, cb=cb)

  def playlist_move(self, cur_pos, new_pos, playlist=None, cb=None, sync=True):
    if sync:
      return self.xmms_s.playlist_move(cur_pos, new_pos, playlist)
    else:
      self.xmms.playlist_move(cur_pos, new_pos, playlist, cb)

  def playlist_play_pos(self, pos, relative=False):
    def __status_cb(res):
      self.playlist_set_next(pos, relative=relative, sync=False)
      self.playback_tickle(sync=False)

      if res.value() != xmmsclient.PLAYBACK_STATUS_PLAY:
        self.playback_start(sync=False)

    self.playback_status(cb=__status_cb, sync=False)

  def playlist_play(self, playlist=None, pos=0, relative=False):
    def __load_cb(res):
      if not res.iserror():
        self.playlist_play_pos(pos)

    if playlist is not None:
      self.playlist_load(playlist, __load_cb, sync=False)
    else:
      self.playlist_play_pos(pos, relative=relative)

  def playlist_remove(self, playlist, cb=None, sync=True):
    if sync:
      return self.xmms_s.playlist_remove(playlist)
    else:
      self.xmms.playlist_remove(playlist, cb=cb)

  def playlist_remove_entry(self, id, playlist=None, cb=None, sync=True):
    if sync:
      return self.xmms_s.playlist_remove_entry(id, playlist)
    else:
      self.xmms.playlist_remove_entry(id, playlist, cb=cb)

  def playlist_set_next(self, pos, relative=False, cb=None, sync=True):
    if sync:
      if relative:
        try:
          return self.xmms_s.playlist_set_next_rel(pos)
        except xmmsclient.XMMSError:
          pass
      else:
        return self.xmms_s.playlist_set_next(pos)
    else:
      if relative:
        self.xmms.playlist_set_next_rel(pos, cb=cb)
      else:
        self.xmms.playlist_set_next(pos, cb=cb)

  def playlist_shuffle(self, playlist=None, cb=None, sync=True):
    if sync:
      return self.xmms_s.playlist_shuffle(playlist)
    else:
      self.xmms.playlist_shuffle(playlist, cb=cb)


