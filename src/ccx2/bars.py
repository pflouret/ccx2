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

import signals
import xmms

xs = xmms.get()

class StatusBar(urwid.WidgetWrap):
  def __init__(self):
    self.__super.__init__(urwid.AttrWrap(urwid.Text(''), 'statusbar'))
    signals.connect('xmms-playback-playtime', self._on_xmms_playback_playtime)

  def _humanize_time(self, milli, str_output=True):
    sec, milli = divmod(milli, 1000)
    min, sec = divmod(sec, 60)
    hours, min = divmod(min, 60)
    if str_output:
      return '%s%02d:%02d' % (hours and '%02d:' % hours or '', min, sec)
    else:
      hours, min, sec

  def _on_xmms_playback_playtime(self, milli):
    self._w.set_text(self._humanize_time(milli))
    signals.emit('need-redraw')

class HeaderBar(urwid.WidgetWrap):
  status_desc = {xmmsclient.PLAYBACK_STATUS_PLAY: 'playing',
                 xmmsclient.PLAYBACK_STATUS_STOP: 'stopped',
                 xmmsclient.PLAYBACK_STATUS_PAUSE: 'paused'}

  def __init__(self):
    self.__super.__init__(urwid.AttrWrap(urwid.Text(''), 'headerbar'))
    self._info = {}
    self._status = xs.playback_status()
    self._make_text()

    signals.connect('xmms-playback-status', self._on_xmms_playback_status)
    signals.connect('xmms-playback-current-info', self._on_xmms_playback_current_info)

  def _make_text(self):
    status = HeaderBar.status_desc[self._status]
    text = u'%s | %s - %s' % (status, self._info.get('artist', ''), self._info.get('title', ''))
    self._w.set_text(text)

  def _on_xmms_playback_status(self, status):
    self._status = status
    self._make_text()
    self._invalidate()
    signals.emit('need-redraw')

  def _on_xmms_playback_current_info(self, info):
    self._info = info
    self._make_text()
    self._invalidate()
    signals.emit('need-redraw')

