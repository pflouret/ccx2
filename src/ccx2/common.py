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

import config
import keys
import mifl
import xmms

xs = xmms.get()

# FIXME: works like crap and it's ugly
class MarkableListBox(urwid.ListBox):
  def __init__(self, body, ch=None):
    self.__super.__init__(body)

    self._marked = {}
    if ch:
      ch.register_command(self, 'move-focus-top', lambda c, a: self.set_focus(0)),
      ch.register_command(self, 'move-focus-bottom', lambda c, a: self.set_focus_last()),
      ch.register_command(self, 'mark-and-move-up', lambda c, a: self._mark_and_move_rel(-1)),
      ch.register_command(self, 'mark-and-move-down', lambda c, a: self._mark_and_move_rel(1)),
      ch.register_command(self, 'unmark-all', lambda c, a: self.unmark_all())

      ch.register_keys(self, 'move-focus-top', keys.bindings['movement']['move-focus-top'])
      ch.register_keys(self, 'move-focus-bottom', keys.bindings['movement']['move-focus-bottom'])
      ch.register_keys(self, 'mark-and-move-up', keys.bindings['general']['mark-and-move-up'])
      ch.register_keys(self, 'mark-and-move-down', keys.bindings['general']['mark-and-move-down'])
      ch.register_keys(self, 'unmark-all', keys.bindings['general']['unmark-all'])

  def _get_marked(self):
    return self._marked

  marked = property(_get_marked)

  def set_focus_last(self):
    # FIXME: don't do anything here, let subclasses override
    if hasattr(self.body, 'set_focus_last'):
      self.body.set_focus_last()

  def toggle_focus_mark(self):
    w, pos = self.get_focus()
    if w is not None:
      key = self._get_mark_key(w, pos)
      if w.marked:
        self._unmark(key)
      else:
        self._mark(key, w)

  def unmark_all(self):
    for w in self._marked.values():
      w.marked = False
      w._update_w() # FIXME

    self._marked.clear()

  def _get_mark_key(self, w, pos):
    return pos

  def _mark(self, key, w):
    self._marked[key] = w
    w.marked = True
    w._update_w() # FIXME

  def _unmark(self, key):
    try:
      w = self._marked[key]
      w.marked = False
      w._update_w() # FIXME
      del self._marked[key]
    except KeyError:
      pass

  def _mark_and_move_rel(self, delta):
    w, pos = self.get_focus()
    if pos is not None:
      self.toggle_focus_mark()
      self.set_focus(pos+delta)

