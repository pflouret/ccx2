import re

import urwid
import xmmsclient.collections as coll

import common
import keys
import signals
import widgets
import xmms


xs = xmms.get()

class SearchListBox(common.MarkableListBox):
  def __init__(self, format, app):
    self.app = app
    walker = common.CachedCollectionWalker(coll.IDList(), 'search', app, widgets.SongWidget)

    self.__super.__init__(walker, app.ch)

    self.register_commands()

  def register_commands(self):
    self.app.ch.register_command(self, 'add-marked-to-playlist', self.add_marked_to_playlist),
    self.app.ch.register_command(
        self, 'add-marked-after-current-pos', self.add_marked_after_current_pos)

    for command, k in keys.bindings['search'].iteritems():
      self.app.ch.register_keys(self, command, k)

  def _get_mark_key(self, w, pos):
    return w.id

  def add_marked_to_playlist(self, context=None, args=None, insert_in_pos=None):
    m = list(self.marked)

    if not m:
      w, pos = self.get_focus()

      if w is None:
        return

      m = [self._get_mark_key(w, pos)]

    idl = coll.IDList()
    idl.ids += m
    if insert_in_pos is None:
      xs.playlist_add_collection(idl, ['id'], sync=False)
    else:
      xs.playlist_insert_collection(int(insert_in_pos), idl, ['-id'], sync=False)

  def add_marked_after_current_pos(self, context=None, args=None, ):
    def _cb(r):
      if not r.iserror():
        v = r.value()
        if v == u'no current entry':
          self.add_marked_to_playlist()
        else:
          self.add_marked_to_playlist(insert_in_pos=v['position']+1)
    xs.playlist_current_pos(cb=_cb, sync=False)

  def get_contexts(self):
    return [self]

  def keypress(self, size, key):
    if key == '/':
      self.unmark_all()
      # FIXME: hack
      self.app.show_prompt(self.body.get_input_widget())
    else:
      return self.__super.keypress(size, key)

coll_parser_pattern_rx = re.compile(r'\(|\)|#|:|~|<|>|=|\+|OR|AND|NOT')

class Search(urwid.Pile):
  def __init__(self, app):
    self.app = app

    self.lb = SearchListBox('simple', self.app)
    self.input = widgets.InputEdit(caption='  quick search: ')

    focus_lb = lambda t=None: self.set_focus(self.lb)
    urwid.connect_signal(self.input, 'change', self._on_query_change)
    urwid.connect_signal(self.input, 'done', focus_lb)
    urwid.connect_signal(self.input, 'abort', focus_lb)
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

    if i != cur:
      self.set_focus(i)

  def _on_query_change(self, q):
    def _f(sig, frame):
      caption = '  quick search: '
      qs = q
      if q:
        if coll_parser_pattern_rx.search(q):
          caption = 'pattern search: '
        else:
          qs = ' '.join(['~'+s for s in q.split()])

      try:
        self.lb.body.collection = coll.coll_parse(qs)
      except ValueError:
        pass

      self.input.set_caption(caption)
      signals.emit('need-redraw')

    if q != self.prev_q:
      # TODO: make a CachedLimitedCollectionWalker to see if it helps and we can avoid the alarm
      signals.alarm(0.25, _f)
      self.prev_q = q

  def get_contexts(self):
    return [self] + self.lb.get_contexts()

