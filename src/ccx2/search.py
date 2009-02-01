import re

import urwid
import xmmsclient.collections as coll

import collutil
import config
import keys
import listbox
import mifl
import signals
import widgets
import xmms


xs = xmms.get()


class SearchWalker(urwid.ListWalker):
  def __init__(self, collection, format):
    self.format = format
    self.parser = mifl.MiflParser(config.formatting[format])
    self.widgets = {}
    self.focus = 0

    self.feeder = collutil.CollectionFeeder(collection, self.parser[0].symbol_names())

  def __len__(self):
    return len(self.feeder)

  def get_pos(self, pos):
    mid = self.feeder.position_id(pos)

    if pos < 0 or mid is None:
      return None, None

    if mid not in self.widgets:
      text = self.parser[0].eval(self.feeder[pos])[0]
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
  def __init__(self, format, app):
    self.app = app
    self.format = format
    self.parser = mifl.MiflParser(config.formatting[format])
    self.walker = SearchWalker(coll.IDList(), 'search')

    self.__super.__init__(self.walker, self.app.ch)

    self.register_commands()

  def _set_collection(self, c):
    self.walker.feeder.collection = c
    self.unmark_all()
    self._invalidate()

  collection = property(lambda self: self.walker.feeder.collection, _set_collection)

  def register_commands(self):
    self.app.ch.register_command(self, 'add-marked-to-playlist', self.add_marked_to_playlist),
    self.app.ch.register_command(
        self, 'add-marked-after-current-pos', self.add_marked_after_current_pos)

    for command, k in keys.bindings['search'].iteritems():
      self.app.ch.register_keys(self, command, k)

  def add_marked_to_playlist(self, context=None, args=None, insert_in_pos=None):
    m = self.marked_data.values()

    if not m:
      w, pos = self.get_focus()

      if w is None:
        return

      m = [w.id]

    idl = coll.IDList()
    idl.ids += m
    if insert_in_pos is None:
      xs.playlist_add_collection(idl, ['id'], sync=False)
    else:
      xs.playlist_insert_collection(int(insert_in_pos), idl, ['-id'], sync=False)

  def add_marked_after_current_pos(self, context=None, args=None):
    def _cb(r):
      if not r.iserror():
        v = r.value()
        if v == u'no current entry':
          self.add_marked_to_playlist()
        else:
          self.add_marked_to_playlist(insert_in_pos=v['position']+1)
    xs.playlist_current_pos(cb=_cb, sync=False)

  def get_mark_data(self, pos, w):
    return w.id

  def keypress(self, size, key):
    k = self.__super.keypress(size, key)
    if k in keys.bindings['movement']['move-focus-up'] + \
            keys.bindings['movement']['move-focus-down']:
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
    urwid.connect_signal(self.input, 'done', lambda t=None: self.cycle_focus())
    urwid.connect_signal(self.input, 'abort', lambda t=None: self.set_focus(self.lb))
    urwid.connect_signal(self.input, 'abort', lambda: self.input.set_edit_text(''))

    self.prev_q = ''

    self.__super.__init__([self.lb, ('flow', self.input)], 1)

    self.app.ch.register_command(self, 'switch-focus', lambda c, a: self.cycle_focus())
    self.app.ch.register_keys(self, 'switch-focus', ['tab'])

  def cycle_focus(self):
    cur = self.widget_list.index(self.focus_item)
    n = len(self.widget_list)
    i = (cur + 1) % n
    while i != cur and not self.widget_list[i].selectable():
      i = (i + 1) % n

    if i != cur and (i != 0 or len(self.lb.body) != 0):
      self.set_focus(i)

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

