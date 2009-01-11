import urwid
import xmmsclient.collections as coll

import common
import signals
import widgets

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
      signals.emit('need-redraw-non-urgent')

    # TODO: make a CachedLimitedCollectionWalker to see if it helps and we can avoid the alarm 
    signals.alarm(0.1, _f)

  def get_input_widget(self):
    return self.w

class SearchListBox(common.ActionsListBox):
  def __init__(self, format, app):
    self.__super.__init__(SearchWalker(format, app))
    self.app = app

  def keypress(self, size, key):
    if key == '/':
      # FIXME: hack
      self.app.show_input(self.body.get_input_widget())
    else:
      return self.__super.keypress(size, key)
