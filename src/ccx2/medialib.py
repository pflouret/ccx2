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

from ccx2 import mifl
from ccx2 import signals
from ccx2 import widgets
from ccx2 import xmms
from ccx2.config import keybindings

xs = xmms.get()

# TODO: move to config
_formats = {'default': "$if2(%performer%,%artist%)|['['%date%']' ]%album%|[CD%partofset%|]%title%"}
_formats = {'default':
            '(or :performer :artist) > :album > (if :partofset (cat "CD" :partofset)) > :title'}

class FormattedSongListWalker(urwid.ListWalker):
  def __init__(self, parser, collection, level=0):
    self.focus = 0
    self.rows = {}
    self.collection = collection
    self._parser = parser
    self._level = level
    self.skipped_levels = 0

    self.formatted_data = []
    self.nformated_data = 0
    self.ids = {}

    self._load()

  def _load(self):
    for e in self._parser[self._level:]:
      data = xs.coll_query_infos(self.collection, fields=e.symbol_names())
      formatted_data = []
      self.ids = {}
      for d in data:
        import sys
        v, b = e.eval(d)
        #print >> sys.stderr, v
        if b:
          formatted_data.append(v)
        self.ids.setdefault(v, []).append(d['id'])
      if formatted_data:
        break
      self.skipped_levels += 1
    else:
      self.ids = {}
      return

    self.formatted_data = list(sorted(self.ids))
    self.nformated_data = len(self.formatted_data)

  def _get_at_pos(self, pos):
    if pos < 0 or pos >= self.nformated_data:
      return None, None

    try:
      # TODO: cache only a couple of pages, not the whole list
      return self.rows[pos], pos
    except KeyError:
      d = self.formatted_data[pos]
      #text = type(d) == list and d[0] or d
      self.rows[pos] = widgets.SelectableText(d)
      return self.rows[pos], pos

  def get_focus(self):
    return self._get_at_pos(self.focus)

  def set_focus(self, focus):
    if focus <= 0:
      focus = 0
    elif focus >= self.nformated_data:
      focus = self.nformated_data-1
    self.focus = focus
    self._modified()

  def get_prev(self, pos):
    return self._get_at_pos(pos-1)

  def get_next(self, pos):
    return self._get_at_pos(pos+1)


class MediaLib(widgets.CustomKeysListBox):
  def __init__(self):
    keys = {}
    for action in (('move-up', 'up'),
                   ('move-down', 'down'),
                   ('page-up', 'page up'),
                   ('page-down', 'page down')):
      keys.update([(k, action[1]) for k in keybindings['general'][action[0]]])

    self.__super.__init__(keys, [])
    self._walkers = {} # formatname => path => walker
    self._levels = {} # formatname => level
    self._positions = {} # formatname => level => position
    self._parsers = {}

    self._cur_format = 'default'
    self._parsers['default'] = mifl.MiflParser(_formats['default'])

    self.load()

  # TODO: split this up and clean up the signature which is confusing
  def load(self, collection=coll.Universe(), format=None, direction=None):
    if not format:
      format = self._cur_format

    if format not in self._parsers:
      self._parsers[format] = mifl.MiflParser(_formats[format])

    self._cur_format = format

    if direction not in (None, 'in', 'out'):
      raise ValueError("direction must be one of None, 'in' or 'out'")

    _widget, focus = self.body.get_focus()

    if direction is None or focus is None or format not in self._levels:
      target_level = 0
      self._levels[format] = target_level
      self._positions.setdefault(format, {})[target_level] = 0
      path = ()
    elif direction == 'in':
      cur_level = self._levels[format]
      self._positions[format][cur_level] = focus

      target_level = cur_level + 1

      if target_level >= len(self._parsers[format]) - self.body.skipped_levels: # FIXME: ugly
        return

      try:
        focus = self._positions[format][target_level]
      except:
        focus = 0

      path = tuple([self._positions[format][l] for l in range(target_level)])

    elif direction == 'out':
      cur_level = self._levels[format]
      self._positions[format][cur_level] = focus

      target_level = cur_level - 1

      if target_level < 0:
        return

      path = tuple([self._positions[format][l] for l in range(target_level)])
      focus = self._positions[format][target_level]

    self._levels[format] = target_level

    try:
      w = self._walkers[format][path]
      self._set_body(w)
      self.body.set_focus(focus)
    except KeyError:
      w = FormattedSongListWalker(self._parsers[format], collection, target_level)
      self._walkers.setdefault(format, {})[path] = w
      self._set_body(w)

  def keypress(self, size, key):
    if key in ['l', 'enter']:
      _w, pos = self.body.get_focus()

      # TODO: this shouldn't be here
      ids = self.body.ids[self.body.formatted_data[pos]]
      if ids:
        idl = coll.IDList()
        for id in ids:
          idl.ids.append(id)

        self.load(idl, direction='in')
    elif key in ['h', 'backspace']:
      self.load(direction='out')
    else:
      return self.__super.keypress(size, key)

  def _set_body(self, body):
    self.body = body
    self._invalidate()

