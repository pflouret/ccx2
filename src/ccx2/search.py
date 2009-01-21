import urwid
import xmmsclient.collections as coll

import common
import signals
import widgets
import xmms

xs = xmms.get()


import re

coll_parser_pattern_rx = re.compile(r'\(|\)|#|:|~|<|>|=|\+|OR|AND|NOT')

class SearchWalker(common.CachedCollectionWalker):
  def __init__(self, format, app, query=''):
    self.empty_coll = coll.IDList()
    self.prev_q = ''

    common.CachedCollectionWalker.__init__(
        self, self.empty_coll, 'search', app, widgets.SongWidget)

    self.w = widgets.InputEdit(caption='  quick search: ')

    urwid.connect_signal(self.w, 'change', self._on_query_change)

    self._on_query_change(query)

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
        self.collection = coll.coll_parse(qs)
      except ValueError:
        pass

      self.w.set_caption(caption)
      self._modified()
      signals.emit('need-redraw')

    if q != self.prev_q:
      # TODO: make a CachedLimitedCollectionWalker to see if it helps and we can avoid the alarm 
      signals.alarm(0.25, _f)
      self.prev_q = q

  def get_input_widget(self):
    return self.w

class SearchListBox(common.ActionsListBox):
  def __init__(self, format, app):
    actions = [('search', 'add-marked-to-playlist', self.add_marked_to_playlist),
               ('search', 'add-marked-after-current-pos', self.add_marked_after_current_pos)]
    self.__super.__init__(SearchWalker(format, app), actions=actions)
    self.app = app

  def _get_mark_key(self, w, pos):
    return w.id

  def add_marked_to_playlist(self, insert_in_pos=None):
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
      xs.playlist_insert_collection(int(insert_in_pos), idl, ['id'], sync=False)

  def add_marked_after_current_pos(self):
    def _cb(r):
      if not r.iserror():
        v = r.value()
        if v == u'no current entry':
          self.add_marked_to_playlist()
        else:
          self.add_marked_to_playlist(v['position']+1)
    xs.playlist_current_pos(cb=_cb, sync=False)

  def keypress(self, size, key):
    if key == '/':
      self.unmark_all()
      # FIXME: hack
      self.app.show_input(self.body.get_input_widget())
    else:
      return self.__super.keypress(size, key)
