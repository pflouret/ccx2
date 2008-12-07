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
    return self.__super.keypress(size, self.key_mapping.get(key, key))


class SelectableText(urwid.Text):
  _selectable = True

  def __init__(self, *args, **kwargs):
    self.highlight_on_focus = 'highlight_on_focus' in kwargs and kwargs.pop('highlight_on_focus')
    self.__super.__init__(*args, **kwargs)

  def render(self, size, focus=False):
    c = self.__super.render(size, focus)
    if self.highlight_on_focus and focus:
      c = urwid.CompositeCanvas(c)
      c.fill_attr('reverse')
    return c

  def keypress(self, size, key):
    return key

class Song(SelectableText):
  def __init__(self, id, *args, **kwargs):
    self.id = id
    self.__super.__init__(*args, **kwargs)

