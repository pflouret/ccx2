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

class CustomKeysListBox(urwid.ListBox):
  def __init__(self, key_mapping, *args, **kwargs):
    self.key_mapping = key_mapping
    self.__super.__init__(*args, **kwargs)

  def keypress(self, size, key):
    key = self.__super.keypress(size, self.key_mapping.get(key, key))

    if key in (' ', '<0>'):
      focus = self.get_focus()
      delta = key == ' ' and 1 or -1
      if focus[1] is not None:
        self.change_focus(size, focus[1]+delta)
    return key


class SelectableText(urwid.WidgetWrap):
  def __init__(self,
               text,
               attr='body',
               focus_attr='focus',
               sel_attr='selected',
               sel_focus_attr='selected-focus'):
    self.attr = attr
    self.focus_attr = focus_attr
    self.sel_attr = sel_attr
    self.sel_focus_attr = sel_focus_attr

    self.selected = False
    w = urwid.AttrWrap(urwid.Text(text), None)
    self.__super.__init__(w)
    self.update_w()

  def selectable(self):
    return True

  def update_w(self):
    if self.selected:
      self._w.attr = self.sel_attr
      self._w.focus_attr = self.sel_focus_attr
    else:
      self._w.attr = self.attr
      self._w.focus_attr = self.focus_attr

  def keypress(self, size, key):
    if key in (' ', '<0>'):
      self.selected = not self.selected
      self.update_w()

    return key

class SongWidget(SelectableText):
  def __init__(self, id, *args, **kwargs):
    self.id = id
    self.__super.__init__(*args, **kwargs)
    self._old_attr = self.attr
    self._old_focus_attr = self.focus_attr

  def set_active(self):
    self._old_attr = self.attr
    self._old_focus_attr = self.focus_attr
    self.attr = 'active'
    self.focus_attr = 'active-focus'
    self.update_w()

  def unset_active(self):
    self.attr = self._old_attr
    self.focus_attr = self._old_focus_attr
    self.update_w()

# TODO: refactor
class PlaylistWidget(SelectableText):
  def __init__(self, name, *args, **kwargs):
    self.name = name
    self.__super.__init__(name, *args, **kwargs)
    self._old_attr = self.attr
    self._old_focus_attr = self.focus_attr

  def set_active(self):
    self._old_attr = self.attr
    self._old_focus_attr = self.focus_attr
    self.attr = 'active'
    self.focus_attr = 'active-focus'
    self.update_w()

  def unset_active(self):
    self.attr = self._old_attr
    self.focus_attr = self._old_focus_attr
    self.update_w()

