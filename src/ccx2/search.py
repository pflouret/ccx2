import re

import urwid
import xmmsclient.collections as coll

import collutil
import commands
import config
import keys
import listbox
import mif
import signals
import widgets
import xmms


xs = xmms.get()


class SearchWalker(urwid.ListWalker):
  def __init__(self, collection, formatname):
    self.format = formatname
    self.parser = mif.FormatParser(config.formatting[formatname])
    self.widgets = {}
    self.focus = 0

    self.feeder = collutil.CollectionFeeder(collection, self.parser.fields())

  def __len__(self):
    return len(self.feeder)

  def get_pos(self, pos):
    mid = self.feeder.position_id(pos)

    if pos < 0 or mid is None:
      return None, None

    if mid not in self.widgets:
      text = self.parser.eval(self.feeder[pos])
      self.widgets[mid] = widgets.SongWidget(mid, text)

    return self.widgets[mid], pos

  def set_focus(self, focus):
    if focus <= 0:
      focus = 0
    elif focus >= len(self.feeder):
      focus = len(self.feeder) - 1

    self.focus = focus
    self._modified()

  def clear_cache(self):
    self.widgets = {}

  def set_focus_last(self): self.set_focus(len(self.feeder)-1)
  def get_focus(self): return self.get_pos(self.focus)
  def get_prev(self, pos): return self.get_pos(pos-1)
  def get_next(self, pos): return self.get_pos(pos+1)


class SearchListBox(listbox.MarkableListBox):
  def __init__(self, formatname, app):
    self.app = app
    self.format = formatname
    self.walker = SearchWalker(coll.IDList(), 'search')

    self.__super.__init__(self.walker)

  def _set_collection(self, c):
    self.walker.feeder.collection = c
    self.unmark_all()
    self._invalidate()

  collection = property(lambda self: self.walker.feeder.collection, _set_collection)

  def cmd_insert(self, args):
    if args:
      relative = False
      if args[0] in ('+', '-'):
        relative = True

      try:
        pos = int(args)
      except ValueError:
        raise commands.CommandError("valid playlist position needed")

      if relative:
        try:
          cur = xs.playlist_current_pos()['position']
          pos = cur + pos + (args[0] == '-' and 1 or 0)
        except:
          pos = None
      else:
        pos -= 1
    else:
      pos = None

    self.insert_marked(pos)

  def insert_marked(self, pos=None):
    m = self.marked_data.values()

    if not m:
      w, p = self.get_focus()

      if w is None:
        return

      m = [w.id]

    idl = coll.IDList()
    idl.ids += m
    if pos is None:
      xs.playlist_add_collection(idl, ['id'], sync=False)
    else:
      xs.playlist_insert_collection(int(pos), idl, ['id'], sync=False)

  def insert_marked_after_current(self):
    def _cb(r):
      if not r.iserror():
        v = r.value()
        if v == u'no current entry':
          self.insert_marked()
        else:
          self.insert_marked(pos=v['position']+1)
    xs.playlist_current_pos(cb=_cb, sync=False)

  def get_mark_data(self, pos, w):
    return w.id

  def keypress(self, size, key):
    k = self.__super.keypress(size, key)
    if k in ('up', 'down'):
      # don't let a focus change happen in the pile if up or down are unhandled
      return None
    return k


coll_parser_pattern_rx = re.compile(r'\(|\)|#|:|~|<|>|=|\+|OR|AND|NOT')

class Search(urwid.Pile):
  def __init__(self, app):
    self.app = app

    self.lb = SearchListBox('simple', self.app)
    self.input = widgets.InputEdit(caption='quick search: ')

    urwid.connect_signal(self.input, 'change', self._on_query_change)
    urwid.connect_signal(self.input, 'done', lambda t=None: self.cmd_cycle())
    urwid.connect_signal(self.input, 'abort', lambda t=None: self.set_focus(self.lb))
    urwid.connect_signal(self.input, 'abort', lambda: self.input.set_edit_text(''))

    self.prev_q = ''

    self.__super.__init__([('flow', urwid.AttrWrap(self.input, 'searchinput')), self.lb], 0)

  def cmd_cycle(self, args=None):
    cur = self.widget_list.index(self.focus_item)
    n = len(self.widget_list)
    i = (cur + 1) % n
    while i != cur and not self.widget_list[i].selectable():
      i = (i + 1) % n

    if i != cur and (i != 0 or len(self.lb.body) != 0):
      self.set_focus(i)

  def cmd_save(self, args):
    # TODO: playlists and playlist types/options
    args = args.strip()
    if not args:
      raise commands.CommandError, 'need some args'

    name = args
    q = self.input.edit_text
    if q and not coll_parser_pattern_rx.search(q):
      q = ' '.join(['~'+s for s in q.split()])

    try:
      c = coll.coll_parse(q)
    except ValueError:
      raise commands.CommandError, 'invalid collection'

    xs.coll_save(c, name, 'Collections', sync=False)

  def set_query(self, q):
    self.input.set_edit_text(q)
    self.input.edit_pos = len(q)

  def _on_query_change(self, q):
    def _f(sig, frame):
      caption = 'quick search: '
      qs = q
      if q:
        if coll_parser_pattern_rx.search(q):
          caption = 'pattern search: '
        else:
          qs = ' '.join(['~'+s for s in q.split()])
      else:
        self.lb.walker.clear_cache()

      try:
        self.lb.collection = coll.coll_parse(qs)
      except ValueError:
        pass

      self.input.set_caption(caption)
      signals.emit('need-redraw')

    if q != self.prev_q:
      # TODO: make a LimitCollectionFeeder to see if it helps and we can avoid the alarm
      # FIXME: crashes if press enter at the prompt before the alarm fires and 
      # FIXME: the collection is populated
      signals.alarm(0.25, _f)
    self.prev_q = q

  def get_contexts(self):
    return [self, self.lb]

