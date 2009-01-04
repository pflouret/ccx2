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

from ccx2 import config

class CustomKeysListBox(urwid.ListBox):
  def __init__(self, key_mapping, *args, **kwargs):
    self.key_mapping = key_mapping
    self.__super.__init__(*args, **kwargs)

  def keypress(self, size, key):
    key = self.__super.keypress(size, self.key_mapping.get(key, key))

    keys_up = config.keybindings['general']['select-and-move-up']
    keys_down = config.keybindings['general']['select-and-move-down']
    if key in keys_up + keys_down:
      focus = self.get_focus()
      delta = key in keys_down and 1 or -1
      if focus[1] is not None:
        self.set_focus(focus[1]+delta)
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
    # FIXME: this whole selected handling thing stinks badly, clean up
    keys_up = config.keybindings['general']['select-and-move-up']
    keys_down = config.keybindings['general']['select-and-move-down']
    if key in keys_up + keys_down:
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
    if self.attr != 'active':
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

class InputDialog(urwid.WidgetWrap):
  def __init__(self, title, width, height, attr=('dialog', 'body')):
    self._blank = urwid.Text('')
    self._width = width
    self._height = height
    self._attr = attr

    self._title = urwid.Padding(urwid.Text(title), 'center', width - 4)
    self._edit = urwid.Edit(wrap=urwid.CLIP)

    self._initialized = False

    self.__super.__init__(self._blank);

  def _init_w(self, body):
    w = urwid.AttrWrap(self._edit, self._attr[1])
    w = urwid.Padding(w, 'center', self._width - 4)
    w = urwid.Pile([self._title, self._blank, w])
    w = urwid.Filler(w)
    w = urwid.AttrWrap(w, self._attr[0])
    self._w = urwid.Overlay(w, body, 'center', self._width, 'middle', self._height);

    self._initialized = True

  def get_text(self):
    return self._edit.get_text()[0]

  def show(self, ui, size, body):
    if not self._initialized:
      self._init_w(body)

    keys = True

    while True:
      if keys:
        ui.draw_screen(size, self.render(size, True))
      keys = ui.get_input()

      for k in keys:
        if k == 'window resize':
          size = ui.get_cols_rows()
        elif k in config.keybindings['general']['cancel']:
          return ''
        elif k == 'enter':
          return self.get_text()
        else:
          self.keypress(size, k);

class InputEdit(urwid.Edit):
  signals = ['done', 'abort']

  def keypress(self, size, key):
    text = self.edit_text
    if key == 'enter':
      self._emit('done', self.edit_text)
    elif key in config.keybindings['general']['cancel']:
      self._emit('abort')
    else:
      return self.__super.keypress(size, key)

class CollectionListEntryWidget(SelectableText):
  def __init__(self, child_ids, *args, **kwargs):
    self.child_ids = child_ids
    self.__super.__init__(*args, **kwargs)

  def _get_child_idlist(self):
    idl = coll.IDList()
    for id in self.child_ids:
      idl.ids.append(id)
    return idl

  child_idlist = property(_get_child_idlist)

