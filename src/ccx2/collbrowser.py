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
            """(or :performer :artist)
               > :album
               > (if :partofset (cat "CD" :partofset))
               > (pad :tracknr "2" "0"). (if (not (= :artist :performer)) (cat :artist " - ")):title'}
            """}

class CollectionListWalker(urwid.ListWalker):
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
        v, b = e.eval(d)
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
      self.rows[pos] = widgets.CollectionListEntryWidget(self.ids[d], d)
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


class CollectionBrowser(widgets.CustomKeysListBox):
  def __init__(self, format):
    keys = {}
    for action in (('move-up', 'up'),
                   ('move-down', 'down'),
                   ('page-up', 'page up'),
                   ('page-down', 'page down')):
      keys.update([(k, action[1]) for k in keybindings['general'][action[0]]])

    self.__super.__init__(keys, [])

    self.format = format

    self.walkers = {} # path => walker
    self.level = 0
    self.positions = {} # level => position

    self.parser = mifl.MiflParser(_formats['default'])

    self._key_action = self._make_key_action_mapping()

    self.load()

  def _make_key_action_mapping(self):
    m = {}
    for section, action, fun in \
        (('collection-browser', 'navigate-in', self.go_in),
         ('collection-browser', 'navigate-out', self.go_out),):
      for key in keybindings[section][action]:
        m[key] = fun
    return m

  def _set_walker(self, path, collection=None):
    # TODO: go_out() should pass a collection and not require the walker to be cached
    assert(path in self.walkers or collection)

    if path in self.walkers:
      w = self.walkers[path]
    else:
      w = CollectionListWalker(self.parser, collection, self.level)
      self.walkers[path] = w
    self._set_body(w)

  def go_in(self):
    widget, focus = self.body.get_focus()

    self.positions[self.level] = focus
    target_level = self.level + 1

    if target_level >= len(self.parser) - self.body.skipped_levels: # FIXME: ugly
      return

    path = tuple([self.positions[l] for l in range(target_level)])
    self.level = target_level

    self._set_walker(path, widget.child_idlist)

  def go_out(self):
    target_level = self.level - 1

    if target_level < 0:
      return

    path = tuple([self.positions[l] for l in range(target_level)])
    self.level = target_level

    self._set_walker(path)

  def load(self, collection=coll.Universe()):
    self.level = 0
    self.positions[0] = 0
    self._set_walker((), collection) # must be an empty tuple!

  def keypress(self, size, key):
    if key in self._key_action:
      self._key_action[key]()
    else:
      return self.__super.keypress(size, key)

  def _set_body(self, body):
    self.body = body
    self._invalidate()


class CollectionBrowserManager(object):
  def __init__(self):
    self.cur_format = 'default'
    self.browsers = {}

  def get_browser(self, format=None):
    if format is not None:
      self.cur_format = format

    if self.cur_format in self.browsers:
      browser = self.browsers[self.cur_format]
    else:
      browser = CollectionBrowser(_formats[self.cur_format])
      self.browsers[self.cur_format] = browser

    return browser

