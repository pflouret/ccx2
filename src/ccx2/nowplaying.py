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

import time

import urwid
import urwid.display_common
import xmmsclient

from . import commands
from . import containers
from . import mif
from . import signals
from . import util
from . import widgets
from . import xmms

try:
  from PIL import Image
  try:
    from io import StringIO
  except ImportError:
    from io import StringIO
except ImportError:
  pass


class NowPlaying(urwid.WidgetWrap):
  def __init__(self, app, show_cover=True, formatname='nowplaying'):
    self.xs = xmms.get()
    self.app = app
    self.show_cover = show_cover
    self.format = formatname
    self.parser = mif.FormatParser(self.app.config.format(formatname))
    self.ctx = self.info = {}
    self.cur_hash = None
    self.status = self.xs.playback_status()
    self.time = 0

    self.progress = urwid.ProgressBar('progress-normal', 'progress-complete', 0, 100,
                                      'progress-smooth')
    self.song = urwid.Text('', align='right')
    if self.show_cover:
      self.cover = AlbumCoverWidget(maxcols=65, align='center', valign='top')
      cover_w = self.cover
    else:
      cover_w = urwid.SolidFill(' ')

    fill = urwid.SolidFill(' ')
    w = urwid.Columns([('fixed', 1, fill),
                       cover_w,
                       ('fixed', 2, fill),
                       urwid.Filler(urwid.Pile([('flow', self.song),
                                                ('fixed', 1, urwid.SolidFill(' ')),
                                                ('flow', self.progress)]), 'top'),
                       ('fixed', 1, fill),
                      ])

    self.__super.__init__(w)

    signals.connect('xmms-playback-status', self.on_xmms_playback_status)
    signals.connect('xmms-playback-current-info', self.on_xmms_playback_current_info)
    signals.connect('xmms-playback-playtime', self.on_xmms_playback_playtime)
    self.xs.playback_current_info(self.on_xmms_playback_current_info, sync=False)

  def update(self):
    status_desc = {xmmsclient.PLAYBACK_STATUS_PLAY: 'PLAYING',
                   xmmsclient.PLAYBACK_STATUS_STOP: 'STOPPED',
                   xmmsclient.PLAYBACK_STATUS_PAUSE: 'PAUSED '}

    self.ctx['status'] = status_desc[self.status]
    self.ctx['elapsed'] = util.humanize_time(self.time)
    if 'duration' in self.info:
      self.ctx['total'] = util.humanize_time(self.info['duration'])
      self.progress.set_completion(float(self.time) / self.info['duration'] * 100)

    self.song.set_text(self.parser.eval(self.ctx))

  def on_xmms_playback_playtime(self, milli):
    if self.show_cover and not self.cur_hash:
      self.cover.reset()

    if self.time/1000 != milli/1000:
      self.time = milli
      self.update()

  def on_xmms_playback_status(self, status):
    self.status = status
    self.update()

  def on_xmms_playback_current_info(self, info):
    self.info = info
    self.ctx = dict(list(zip((k[1] for k in self.info), list(self.info.values()))))
    if self.show_cover:
      if 'picture_front' in self.info:
        # TODO: cache the picture to disk (or open directly from disk if local?)
        hash = self.info['picture_front']
        if hash != self.cur_hash:
          self.xs.bindata_retrieve(hash, cb=self._set_cover_cb, sync=False)
          self.cur_hash = hash
      else:
        self.cover.reset()
        self.cur_hash = None
    self.update()

  def _set_cover_cb(self, r):
    if not r.iserror():
      self.cover.set_data(r.value())
      self._invalidate()

  def cmd_same(self, args):
    fields = args.split()
    if 'id' in self.info:
      q = ' AND '.join('%s:"%s"' % (f, self.info[f]) for f in fields if self.info.get(f))
      if q:
        self.app.search(q)
      else:
        pass # TODO: error message

  def get_contexts(self):
    return [self]

_colormap_cache = {}

class AlbumCoverWidget(urwid.WidgetWrap):
  def __init__(self, data=None, maxcols=-1, align='center', valign='middle'):
    self.maxcols = maxcols
    self.img = None
    self.dim = None
    self.step = 0
    self.cheesy_last_animated = 0

    if data:
      self.set_data(data)

    self.text = urwid.Text('', wrap=urwid.ANY)
    self.filler = urwid.Filler(self.text, valign)
    self.padding = urwid.Padding(self.filler, align)
    self.__super.__init__(self.filler)

  def reset(self):
    self.dim = None
    self.img = None
    self.text.set_text('')
    self._w = self.filler
    self._invalidate()

  def set_data(self, data):
    try:
      self.img = Image.open(StringIO(data))
      if self.img.mode == 'P':
        self.img = self.img.convert('RGB')

      self.dim = None
      self.text.align = 'left'
      self._w = self.padding
    except IOError as e:
      self.reset()
    self._invalidate()

  def closest_color(self, rgb):
    global _colormap_cache

    n = rgb[0] << 16 | rgb[1] << 8 | rgb[2]

    if n in _colormap_cache:
      return _colormap_cache[n]

    distance = 257*257*3
    match = 0

    colors = urwid.display_common._COLOR_VALUES_256[16:]
    indexes = list(range(16,256))
    for i, values in zip(indexes, colors):
      rd, gd, bd = rgb[0] - values[0], rgb[1] - values[1], rgb[2] - values[2]
      d = rd*rd + gd*gd + bd*bd

      if d < distance:
        match = i
        distance = d

    _colormap_cache[n] = match
    return match

  def get_markup(self, img):
    markup = []
    for y in range(0, img.size[1], 1):
      last = ''
      n = 0
      for x in range(0, img.size[0], 1):
        rgb = img.getpixel((x,y))
        if type(rgb) == int:
          rgb = (rgb >> 16 & 0xff, rgb >> 8 & 0xff, rgb & 0xff)

        c = self.closest_color(rgb)
        if c != last:
          if last:
            #markup.append((urwid.AttrSpec(last, last), ' '*n))
            markup.append(('h%d'%last, ' '*n))
          last = c
          n = 0
        n += 1
      if n:
        #markup.append((urwid.AttrSpec(last, last), ' '*n))
        markup.append(('h%d'%last, ' '*n))
      markup.append('\n')

    return markup[:-1]

  def scaled_dim(self, size):
    w = size[0]

    if self.maxcols > 0 and size[0] > self.maxcols:
      w = self.maxcols

    w = min(w, self.img.size[0])

    h = (w/2) * self.img.size[1] / self.img.size[0]

    if len(size) > 1 and h > size[1]:
      h = size[1]
      w = (h * self.img.size[0] / self.img.size[1])*2

    return w, h

  def render(self, size, focus=False):
    if self.img:
      dim = self.scaled_dim(size)
      if dim != self.dim:
        self.dim = dim
        img = self.img.resize(dim, Image.ANTIALIAS)
        self.text.set_text(self.get_markup(img))
        self._w.width = dim[0]
    return self._w.render(size)


