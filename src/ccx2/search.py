import urwid
import xmmsclient.collections as coll

import common
import signals
import widgets
import xmms

xs = xmms.get()


class SearchWalker(common.CachedCollectionWalker):
  def __init__(self, format, app, query=''):
    self.empty_coll = coll.IDList()
    common.CachedCollectionWalker.__init__(
        self, self.empty_coll, 'search', app, widgets.SongWidget)

    self.w = widgets.InputEdit(caption='pattern search: ')
    urwid.connect_signal(self.w, 'change', self._on_query_change)

    self._on_query_change(query)

  def _on_query_change(self, q):
    def _f(sig, frame):
      try:
        self.collection = coll.coll_parse(q)
      except ValueError:
        self.collection = self.empty_coll

      self._modified()
      signals.emit('need-redraw')

    # TODO: make a CachedLimitedCollectionWalker to see if it helps and we can avoid the alarm 
    signals.alarm(0.1, _f)

  def get_input_widget(self):
    return self.w

class SearchListBox(common.ActionsListBox):
  def __init__(self, format, app):
    actions = [('search', 'add-marked-to-playlist', self.add_marked_to_playlist)]
    self.__super.__init__(SearchWalker(format, app), actions=actions)
    self.app = app

  def _get_mark_key(self, w, pos):
    return w.id

  def add_marked_to_playlist(self):
    m = list(self.marked)

    if not m:
      w, pos = self.get_focus()

      if w is None:
        return

      m = [self._get_mark_key(w, pos)]

    idl = coll.IDList()
    idl.ids += m
    xs.playlist_add_collection(idl, ['id'], sync=False)

  def keypress(self, size, key):
    if key == '/':
      self.unmark_all()
      # FIXME: hack
      self.app.show_input(self.body.get_input_widget())
    else:
      return self.__super.keypress(size, key)
