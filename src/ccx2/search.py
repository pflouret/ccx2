import urwid
import xmmsclient.collections as coll

import common
import signals
import widgets

class SearchWalker(common.CachedCollectionWalker):
  def __init__(self, format, app):
    self.query = ''
    self.empty_coll = coll.IDList()
    common.CachedCollectionWalker.__init__(self, self.empty_coll, format, app, widgets.SongWidget)

  def _on_query_change(self, q):
    if q:
      try:
        self.collection = coll.coll_parse(q)
      except ValueError:
        self.collection = self.empty_coll
    else:
      self.collection = self.empty_coll

    self.query = q
    self._modified()
    signals.emit('need-redraw-non-urgent')

  def get_input_widget(self):
    w = widgets.InputEdit(caption='pattern search: ')
    urwid.connect_signal(w, 'change', self._on_query_change)
    return w

class SearchListBox(common.ActionsListBox):
  def __init__(self, format, app):
    self.__super.__init__(SearchWalker(format, app))
    self.app = app

