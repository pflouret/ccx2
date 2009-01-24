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

import config
import keys

class MarkableText(urwid.WidgetWrap):
  def __init__(self,
               text,
               attr='default',
               focus_attr='focus',
               mark_attr='marked',
               mark_focus_attr='marked-focus',
               marked=False):

    self._attr = attr
    self._focus_attr = focus_attr
    self._mark_attr = mark_attr
    self._mark_focus_attr = mark_focus_attr
    self.marked = marked

    w = urwid.AttrWrap(urwid.Text(text), None)
    self.__super.__init__(w)

    self._update_w()

  def _set_attr(self, attr_name, value):
    setattr(self, attr_name, value)
    self._update_w()

  attr = property(lambda self: self._attr,
                  lambda self, v: self._set_attr('_attr', v))
  focus_attr = property(lambda self: self._focus_attr,
                        lambda self, v: self._set_attr('_focus_attr', v))
  mark_attr = property(lambda self: self._mark_attr,
                       lambda self, v: self._set_attr('_mark_attr', v))
  mark_focus_attr = property(lambda self: self._mark_focus_attr,
                             lambda self, v: self._set_attr('_mark_focus_attr', v))

  def selectable(self):
    return True

  def toggle_marked(self):
    self.marked = not self.marked
    self._update_w()

  def keypress(self, size, key):
    return key

  def _update_w(self):
    if self.marked:
      self._w.attr = self.mark_attr
      self._w.focus_attr = self.mark_focus_attr
    else:
      self._w.attr = self.attr
      self._w.focus_attr = self.focus_attr


class SongWidget(MarkableText):
  def __init__(self, id, *args, **kwargs):
    self.__super.__init__(*args, **kwargs)

    self.id = id
    self._old_attr = self.attr
    self._old_focus_attr = self.focus_attr

  def set_active(self):
    if self.attr != 'active':
      self._old_attr = self.attr
      self._old_focus_attr = self.focus_attr
      self.attr = 'active'
      self.focus_attr = 'active-focus'

  def unset_active(self):
    self.attr = self._old_attr
    self.focus_attr = self._old_focus_attr


# TODO: refactor
class PlaylistWidget(MarkableText):
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

  def unset_active(self):
    self.attr = self._old_attr
    self.focus_attr = self._old_focus_attr


class InputDialog(urwid.WidgetWrap):
  def __init__(self, title, width, height, attr=('dialog', 'default')):
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

    input_keys = True

    while True:
      if input_keys:
        ui.draw_screen(size, self.render(size, True))
      input_keys = ui.get_input()

      for k in input_keys:
        if k == 'window resize':
          size = ui.get_cols_rows()
        elif k in keys.bindings['general']['cancel']:
          return ''
        elif k == 'enter':
          return self.get_text()
        else:
          self.keypress(size, k);

class InputEdit(urwid.Edit):
  signals = ['done', 'abort']
  BACK = 1
  FORWARD = 2

  def _find_word_pos(self, dir):
    assert dir in (self.BACK, self.FORWARD)
    white = ' \t'

    tlen = len(self.edit_text)

    if dir == self.BACK:
      look_delta = move_delta = -1
      in_bounds = lambda p: p > 0
    else:
      look_delta = 0
      move_delta = 1
      in_bounds = lambda p: p <= tlen-1

    p = self.edit_pos

    if not in_bounds(p):
      return p

    # eat all whitespace from cursor
    if self.edit_text[p+look_delta] in white:
      while in_bounds(p) and self.edit_text[p+look_delta] in white:
        p += move_delta

    if in_bounds(p):
      if self.edit_text[p+look_delta] in config.word_separators:
        # if separator from cursor eat all seps until not sep found
        while in_bounds(p) and self.edit_text[p+look_delta] in config.word_separators:
          p += move_delta
      else:
        # letters, eat all until sep or white
        while in_bounds(p) and self.edit_text[p+look_delta] not in white+config.word_separators:
          p += move_delta

    return p

  def _delete_word(self, dir):
    start = self.edit_pos
    p = self._find_word_pos(dir)
    self.highlight = dir == self.BACK and (p, start) or (start, p)
    self._delete_highlighted()

  def delete_word_forward(self):
    self._delete_word(self.FORWARD)

  def delete_word_backward(self):
    self._delete_word(self.BACK)

  def move_word_forward(self):
    self.edit_pos = self._find_word_pos(self.FORWARD)

  def move_word_backward(self):
    self.edit_pos = self._find_word_pos(self.BACK)

  def keypress(self, size, key):
    text = self.edit_text
    if key in keys.bindings['general']['return']:
      self._emit('done', self.edit_text)
    elif key in keys.bindings['general']['cancel']:
      self._emit('abort')
    elif key in keys.bindings['text_edit']['delete-word-backward']:
      self.delete_word_backward()
    elif key in keys.bindings['text_edit']['delete-word-forward']:
      self.delete_word_forward()
    elif key in keys.bindings['text_edit']['move-char-backward']:
      self.edit_pos -= 1
    elif key in keys.bindings['text_edit']['move-char-forward']:
      self.edit_pos += 1
    elif key in keys.bindings['text_edit']['move-word-backward']:
      self.move_word_backward()
    elif key in keys.bindings['text_edit']['move-word-forward']:
      self.move_word_forward()
    else:
      return self.__super.keypress(size, key)

class CollectionListEntryWidget(MarkableText):
  def __init__(self, child_ids, *args, **kwargs):
    self.child_ids = child_ids
    self.__super.__init__(*args, **kwargs)

  def _get_child_idlist(self):
    idl = coll.IDList()
    for id in self.child_ids:
      idl.ids.append(id)
    return idl

  child_idlist = property(_get_child_idlist)

