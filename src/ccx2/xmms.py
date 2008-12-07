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

import time
import threading

import xmmsclient
from xmmsclient import collections as coll

_objects = {}

def get(name='ccx2', **kwargs):
  try:
    return _objects[name]
  except KeyError:
    service = XmmsService(name=name, **kwargs)
    _objects[name] = service
    return service

class PlaybackPlaytimeTimer(threading.Thread):
  def __init__(self, seconds, callback):
    self.seconds = seconds
    self.callback = callback
    threading.Thread.__init__(self)
    self.setDaemon(True)

  def run(self):
    while True:
      self.callback()
      time.sleep(self.seconds)

class XmmsService(object):
  def __init__(self, path=None, name='ccx2'):
    super(XmmsService, self).__init__()
    self.xmms = xmmsclient.XMMS(name)
    self.xmms_s = xmmsclient.XMMSSync(name+'-sync')
    self.xmms.connect()
    self.xmms_s.connect()

    self.create_signals()

    self.have_ioin = False

  def _callback_wrapper(self, cb):
    def _w(r):
      self.have_ioin = True # shit ugly, ugh
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
    self.have_ioin = False
    self.xmms.ioin()

  def ioout(self):
    if self.xmms.want_ioout():
      self.xmms.ioout()

  def create_signals(self):
    pass
    # TODO: handle errors
    #self.xmms.broadcast_playback_current_id(self._on_xmms_playback_current_id)
    #self.xmms.broadcast_playback_status(lambda res: self.emit('xmms-playback-status', res.value()))
    #self.xmms.broadcast_playlist_loaded( lambda res: self.emit('xmms-playlist-loaded', res.value()))
    #self.xmms.broadcast_playlist_changed(
    #    lambda res: self.emit('xmms-playlist-changed', res.value()))
    #self.xmms.broadcast_collection_changed()
    #self.xmms.broadcast_configval_changed()
    #self.xmms.broadcast_mediainfo_reader_status()
    #self.xmms.broadcast_medialib_entry_added()
    #self.xmms.broadcast_medialib_entry_changed()
    #self.xmms.broadcast_playback_volume_changed()
    #self.xmms.broadcast_playlist_current_pos()

  def _on_xmms_playback_playtime(self, res=None):
    if res:
      # came from the xmms2 signal
      self.emit('xmms-playback-playtime', res.value())
    else:
      # came from gobject.timeout, reinstate the signal
      self.xmms.signal_playback_playtime(self._on_xmms_playback_playtime)
    return True

  def _on_xmms_playback_current_id(self, res):
    id = res.value()
    self.emit('xmms-playback-current-id', id)
    self.xmms.medialib_get_info(
        id,
        lambda res: self.emit('xmms-playback-current-info', res.value()))

  def bindata_retrieve(self, hash, cb=None, sync=True):
    if sync:
      return self.xmms_s.bindata_retrieve(hash)
    else:
      self.xmms.bindata_retrieve(hash, cb)

  def coll_query_infos(self, collection, fields, cb=None, sync=True):
    if 'id' not in fields:
      fields = fields + ['id']

    if sync:
      return self.xmms_s.coll_query_infos(collection, fields)
    else:
      self.xmms.coll_query_infos(collection, fields, cb=cb)

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

  def playback_current_id(self, cb=None, sync=True):
    if sync:
      return self.xmms_s.playback_current_id()
    else:
      if cb is None:
        cb = self._on_xmms_playback_current_id
      self.xmms.playback_current_id(cb=cb)

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

  def playlist_add_id(self, id, playlist, cb=None, sync=True):
    if sync:
      return self.xmms_s.playlist_add_id(id, playlist)
    else:
      self.xmms.playlist_add_id(id, playlist, cb=cb)

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

  def playlist_play_pos(self, pos, relative=False):
    def __status_cb(res):
      if res.value() != xmmsclient.PLAYBACK_STATUS_PLAY:
        self.playback_start(sync=False)

      self.playlist_set_next(pos, relative=relative, sync=False)
      self.playback_tickle(sync=False)
    self.playback_status(cb=__status_cb, sync=False)

  def playlist_play(self, playlist=None, pos=0, relative=False):
    def __load_cb(res):
      if res.iserror():
        print >> sys.stderr, res.get_error()
        return
      # TODO: relative makes sense?
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

  def playlist_set_next(self, pos, relative=False, cb=None, sync=True):
    if sync:
      if relative:
        return self.xmms_s.playlist_set_next_rel(pos)
      else:
        return self.xmms_s.playlist_set_next(pos)
    else:
      if relative:
        self.xmms.playlist_set_next_rel(pos, cb=cb)
      else:
        self.xmms.playlist_set_next(pos, cb=cb)

