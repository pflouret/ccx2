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

from . import urwid

from xmmsclient import collections as coll

WORD_SEPARATORS = '.,~:+][}{\\/-_;"'

class SelectableText(urwid.Text):
  def selectable(self): return True
  def keypress(self, size, key): return key


class SongWidget(SelectableText):
  def __init__(self, mid, *args, **kwargs):
    self.__super.__init__(*args, **kwargs)
    self.mid = mid

class PlaylistWidget(SelectableText):
  def __init__(self, name, *args, **kwargs):
    self.__super.__init__(name, *args, **kwargs)
    self.name = name

class LyricResultWidget(SelectableText):
  def __init__(self, title, url, *args, **kwargs):
    self.__super.__init__(title, *args, **kwargs)
    self.title, self.url = title, url


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
      if self.edit_text[p+look_delta] in WORD_SEPARATORS:
        # if separator from cursor eat all seps until not sep found
        while in_bounds(p) and self.edit_text[p+look_delta] in WORD_SEPARATORS:
          p += move_delta
      else:
        # letters, eat all until sep or white
        while in_bounds(p) and self.edit_text[p+look_delta] not in white+WORD_SEPARATORS:
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
    # XXX: un-hardcode?
    if key in ('enter', 'ctrl m', 'ctrl j'):
      self._emit('done', self.edit_text)
    elif key in ('esc', 'ctrl g'):
      self._emit('abort')
    elif key == 'ctrl w':
      self.delete_word_backward()
    elif key in ('meta d', 'meta delete'):
      self.delete_word_forward()
    elif key == 'ctrl b':
      self.edit_pos -= 1
    elif key == 'ctrl f':
      self.edit_pos += 1
    elif key == 'meta b':
      self.move_word_backward()
    elif key == 'meta f':
      self.move_word_forward()
    else:
      return self.__super.keypress(size, key)

