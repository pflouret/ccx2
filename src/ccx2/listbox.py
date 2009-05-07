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

import urwid

from xmmsclient import collections as coll

import commands
import signals
import xmms

BADROWSMSG = "Widget %s at position %s within listbox calculated %d rows but rendered %d!"
BADFOCUSROWSMSG = "Focus widget %s at position %s within listbox " \
                  "calculated %d rows but rendered %d!"
BADCURSORMSG = "Focus Widget %s at position %s within listbox calculated cursor " \
               "coords %s but rendered cursor coords %s!"

class AttrListBox(urwid.ListBox):
  """A listbox with rows that can have attributes."""

  def __init__(self, body, attr=None, focus_attr=None, focus_str=None, row_attrs=None):
    self.__super.__init__(body)

    self.attr = attr
    self.focus_attr = focus_attr
    self.focus_str = focus_str
    self.row_attrs = row_attrs is not None and row_attrs or {}

    self._bottom_pos = None
    self._top_pos = None
    self._focus_pos = None

  def get_row_attr(self, pos):
    return self.row_attrs.get(pos, [(self.attr, 0)])[-1][0]

  def set_row_attr(self, pos, attr, priority=0):
    self.row_attrs[pos] = [(attr, priority)]

  def add_row_attr(self, pos, attr, priority=0):
    self.row_attrs.setdefault(pos, []).append((attr, priority))
    self.row_attrs[pos].sort(key=lambda e: e[1])

  def remove_row_attr(self, pos, attr):
    try:
      for a in self.row_attrs[pos]:
        if a[0] == attr:
          self.row_attrs[pos].remove(a)
          break
      if not self.row_attrs[pos]:
        del self.row_attrs[pos]
    except KeyError:
      pass

  def clear_attrs(self):
    self.row_attrs = {}

  def render(self, size, focus=False ):
    """Render listbox and return canvas. """
    (maxcol, maxrow) = size

    middle, top, bottom = self.calculate_visible((maxcol, maxrow), focus=focus)

    if middle is None:
      return urwid.SolidCanvas(" ", maxcol, maxrow)
    
    _ignore, focus_widget, focus_pos, focus_rows, cursor = middle
    trim_top, fill_above = top
    trim_bottom, fill_below = bottom

    if bottom[1]:
      self._bottom_pos = bottom[1][-1][1]
    else:
      self._bottom_pos = None
    if top[1]:
      self._top_pos = top[1][-1][1]
    else:
      self._top_pos = None
    self._focus_pos = focus_pos

    combinelist = []
    rows = 0
    fill_above.reverse() # fill_above is in bottom-up order

    for widget,w_pos,w_rows in fill_above:
      canvas = widget.render((maxcol,))
      attr = self.get_row_attr(w_pos)
      if attr:
        canvas = urwid.CompositeCanvas(canvas)
        canvas.fill_attr(attr)

      if w_rows != canvas.rows():
        raise urwid.ListBoxError, BADROWSMSG % (`widget`,`w_pos`,w_rows, canvas.rows())
      rows += w_rows
      combinelist.append((canvas, w_pos, False))
    
    focus_canvas = focus_widget.render((maxcol,), focus=focus)

    focus_attr = None
    if focus_pos in self.row_attrs:
      focus_attr = self.get_row_attr(focus_pos)
      if focus and self.focus_str:
        focus_attr += self.focus_str
    elif focus:
      focus_attr = self.focus_attr

    if focus_attr:
      focus_canvas = urwid.CompositeCanvas(focus_canvas)
      focus_canvas.fill_attr(focus_attr)

    if focus_canvas.rows() != focus_rows:
      raise ListBoxError, BADFOCUSROWSMSG % (`focus_widget`, `focus_pos`,
                                             focus_rows, focus_canvas.rows())
    c_cursor = focus_canvas.cursor
    if cursor != c_cursor:
      raise urwid.ListBoxError, BADCURSORMSG % (`focus_widget`,`focus_pos`,`cursor`,`c_cursor`)
      
    rows += focus_rows
    combinelist.append((focus_canvas, focus_pos, True))
    
    for widget,w_pos,w_rows in fill_below:
      canvas = widget.render((maxcol,))
      attr = self.get_row_attr(w_pos)
      if attr:
        canvas = urwid.CompositeCanvas(canvas)
        canvas.fill_attr(attr)
      if w_rows != canvas.rows():
        raise urwid.ListBoxError, BADROWSMSG  % (`widget`,`w_pos`,w_rows, canvas.rows())
      rows += w_rows
      combinelist.append((canvas, w_pos, False))
    
    final_canvas = urwid.CanvasCombine(combinelist)
    
    if trim_top:	
      final_canvas.trim(trim_top)
      rows -= trim_top
    if trim_bottom:	
      final_canvas.trim_end(trim_bottom)
      rows -= trim_bottom
    
    assert rows <= maxrow
    
    if rows < maxrow:
      bottom_pos = focus_pos
      if fill_below:
        bottom_pos = fill_below[-1][1]
      assert trim_bottom==0 and self.body.get_next(bottom_pos) == (None,None)
      final_canvas.pad_trim_top_bottom(0, maxrow - rows)

    return final_canvas

  def keypress(self, size, key):
    return self.__super.keypress(size, key)

class MarkableListBox(AttrListBox):
  def __init__(self, body):
    self._marked_data = {}

    self.__super.__init__(body, focus_attr='focus', focus_str='-focus')

  marked_data = property(lambda self: self._marked_data)

  def get_mark_data(self, pos, w):
    return pos

  def set_focus_last(self):
    # FIXME: don't do anything here, let subclasses override
    if hasattr(self.body, 'set_focus_last'):
      self.body.set_focus_last()

  def toggle_mark(self, pos, data):
    if pos >= 0 and pos < len(self.body):
      if pos in self._marked_data:
        del self._marked_data[pos]
        self.remove_row_attr(pos, 'marked')
      else:
        self._marked_data[pos] = data
        self.add_row_attr(pos, 'marked', 100)

  def unmark_all(self):
    self._marked_data.clear()
    for pos in self.row_attrs.keys():
      self.remove_row_attr(pos, 'marked')
    self._invalidate()

  def cmd_nav(self, args):
    if args == 'home':
      self.set_focus(0)
    elif args == 'end':
      self.set_focus_last()
    else:
      return commands.CONTINUE_RUNNING_COMMANDS

  def cmd_toggle(self, args):
    if args:
      try:
        pos = int(args)
        if pos < 0 or pos >= len(self.body):
          raise ValueError
      except ValueError:
        raise commands.CommandError("valid playlist position required")
    else:
      w, pos = self.get_focus()

    if pos is not None:
      self.toggle_mark(pos, self.get_mark_data(pos, w))

  def cmd_unmark_all(self, args):
    self.unmark_all()


class SongListBox(MarkableListBox):
  def __init__(self, app, body):
    self.xs = xmms.get()
    self.app = app
    self.__super.__init__(body)

  def cmd_same(self, args):
    fields = args.split()
    w, p = self.get_focus()
    if w is not None:
      info = self.xs.medialib_get_info(w.mid)
      q = ' AND '.join('%s:"%s"' % (f, info[f]) for f in fields if info.get(f))
      if q:
        self.app.search(q)
      else:
        pass # TODO: error message

  def cmd_insert(self, args):
    pos = None
    field = None
    if args:
      args = [a.strip() for a in args.split()]
      relative = False

      if args[0][0] in ('+', '-'):
        relative = True

      try:
        pos = int(args[0])
      except ValueError:
        field = args[0]

      if len(args) > 1:
        field = args[1]

      if pos:
        if relative:
          try:
            cur = self.xs.playlist_current_pos()['position']
            pos = cur + pos + (args[0][0] == '-' and 1 or 0)
          except:
            pos = None
        else:
          pos -= 1

      if field:
        self.insert_by_field(field, pos)
        return

    self.insert_marked(pos)

  def insert_by_field(self, field, pos=None):
    w, p = self.get_focus()

    if w is None:
      return

    info = self.xs.medialib_get_info(w.mid)
    if field not in info:
      raise commands.CommandError("the song doesn't have a value for '%s'" % field)

    c = coll.Equals(field=field, value=info[field].encode('utf-8'))

    if pos is None:
      self.xs.playlist_add_collection(c, ['id'], sync=False)
    else:
      self.xs.playlist_insert_collection(int(pos), c, ['id'], sync=False)

    pos_s = pos is not None and "at position %d" % (pos+1) or ''
    msg = 'added songs matching %s="%s" to playlist %s' % (field, info[field], pos_s)
    signals.emit('show-message', msg)

  def insert_marked(self, pos=None):
    m = self.marked_data.values()

    if not m:
      w, p = self.get_focus()

      if w is None:
        return

      m = [w.mid]

    idl = coll.IDList()
    idl.ids += m
    if pos is None:
      self.xs.playlist_add_collection(idl, ['id'], sync=False)
    else:
      self.xs.playlist_insert_collection(int(pos), idl, ['id'], sync=False)

    n = len(idl.ids)
    pos_s = pos is not None and "at position %d" % (pos+1) or ''
    msg = "added %d song%s to playlist %s" % (n, n > 1 and 's' or '', pos_s)
    signals.emit('show-message', msg)

  def insert_marked_after_current(self):
    def _cb(r):
      if not r.iserror():
        v = r.value()
        if v == u'no current entry':
          self.insert_marked()
        else:
          self.insert_marked(pos=v['position']+1)
    self.xs.playlist_current_pos(cb=_cb, sync=False)

  def get_mark_data(self, pos, w):
    return w.mid

