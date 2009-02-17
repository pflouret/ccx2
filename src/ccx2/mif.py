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

__all__ = ['FormatParser']

_field_aliases = {'a': 'artist',
                  'l': 'album',
                  't': 'title',
                  'n': 'tracknr',
                  'd': 'date',
                  'g': 'genre',
                  'u': 'url',
                  'c': 'compilation',
                  'p': 'performer'}

_special_fields = {'CR': ('\n', False)}

class FormatParser(list):
  def __init__(self, text):
    self._text = text
    self._fieldlist = None
    self._pos = 0
    self._px = self._x = 1
    self._py = self._y = 1
    self._line = 0
    self._reserved = ':[]|>?'

    super(FormatParser, self).__init__([])

    self._parse()

  def fields(self):
    if self._fieldlist is not None:
      return self._fieldlist

    self._fieldlist = []
    for e in self:
      self._fieldlist.extend(e.fields())

    return self._fieldlist

  def eval(self, ctx):
    return u' '.join(level.eval(ctx)[0] for level in self)

  def _peek(self):
    try:
      return self._text[self._pos]
    except IndexError:
      return None

  def _read(self):
    try:
      ch = self._text[self._pos]
    except IndexError:
      return ''

    self._pos += 1
    self._px = self._x
    self._py = self._y
    if ch == '\n':
      self._line = self._pos
      self._x = 1
      self._y += 1
      ch = ' '
    else:
      self._x += 1

    return ch

  def _unread(self):
    self._pos -= 1
    self._x = self._px
    self._y = self._py

  def _parse_field(self):
    ch = firstch = self._read()

    if ch == '{':
      ch = self._read()

    start = self._pos-1

    while ch and (ch.isalnum() or ch in '-_'):
      ch = self._read()

    end = None
    if ch == '}' and firstch == '{':
      end = self._pos - 1
    elif ch:
      self._unread()

    if end is None:
      end = self._pos

    return Field(self._text[start:end])

  def _parse_text(self):
    text = []

    while True:
      ch = self._read()

      if not ch or ch in self._reserved:
        if ch:
          self._unread()
        break

      if ch == '\\':
        ch = self._read()

      text.append(ch)

    s = ''.join(text)
    return s and Text(s) or None

  def _parse_cond(self):
    question_exprs = None
    got_pipe = False
    args = []
    exprs = []
    while True:
      ch = self._read()

      if ch == '?' and not question_exprs and not got_pipe:
        question_exprs = exprs
        exprs = []
        continue # swallow the '?'
      elif not ch or ch in '|]':
        args.append(exprs)
        exprs = []
        if ch != '|': # not ch or ch == ']'
          break
        else:
          got_pipe = True
          continue # swallow the '|'

      e = self._parse_expr(ch)
      if e:
        exprs.append(e)

    return Cond(question_exprs, args)

  def _parse_expr(self, ch):
    if ch == ':':
      return self._parse_field()
    elif ch == '[':
      return self._parse_cond()
    elif ch in self._reserved: # reserved ch in non-interesting context
      return Text(ch)
    else:
      self._unread()
      return self._parse_text()

  def _parse(self):
    level = Level()

    while True:
      ch = self._read()
      if not ch or ch == '>':
        self.append(level)
        level = Level()
        if not ch: break
        continue
      e = self._parse_expr(ch)
      if e:
        level.append(e)

class Text(object):
  def __init__(self, s):
    self.s = unicode(s)

  def fields(self): return []
  def eval(self, ctx): return self.s, False
  def __str__(self): return u'Text(%r)' % self.s
  def __repr__(self): return str(self)

class Field(object):
  def __init__(self, name):
    self.name = name

  def fields(self):
    if self.name in _special_fields:
      return []
    else:
      return [_field_aliases.get(self.name, self.name)]

  def eval(self, ctx):
    v, b = None, None
    if self.name in ctx:
      v = ctx[self.name]
    elif self.name in _field_aliases and _field_aliases[self.name] in ctx:
      v = ctx[_field_aliases[self.name]]
    elif self.name in _special_fields:
      v, b = _special_fields[self.name]

    if b is None: b = v is not None
    if v is None: v = u''

    return unicode(v), b

  def __str__(self): return u'Field(%s)' % self.name
  def __repr__(self): return str(self)

class CondPart(object):
  def __init__(self, exprs):
    self.exprs = exprs

  def fields(self):
    fields = []
    for e in self.exprs:
      fields.extend(e.fields())
    return fields

  def eval(self, ctx):
    acc = []
    bools = False
    for e in self.exprs:
      v, b = e.eval(ctx)
      acc.append(v)
      bools = bools or b

    return u''.join(acc), bools

  def __str__(self): return u'CondPart(%r)' % self.exprs
  def __repr__(self): return str(self)

class Cond(object):
  def __init__(self, question_exprs, exprs):
    self.got_question = bool(question_exprs)

    if question_exprs:
      exprs = [question_exprs] + exprs

    self.parts = [CondPart(e) for e in exprs]
    self.fieldlist = None

  def fields(self):
    if self.fieldlist is not None:
      return self.fieldlist

    self.fieldlist = []
    for part in self.parts:
      self.fieldlist.extend(part.fields())
    return self.fieldlist

  def eval(self, ctx):
    if self.got_question:
      b = self.parts[0].eval(ctx)[1]
      try:
        return self.parts[b and 1 or 2].eval(ctx)[0], True
      except IndexError:
        pass
    else:
      for part in self.parts:
        v, b = part.eval(ctx)
        if b:
          return v, b

    return u'', False

  def __str__(self): return u'Cond(%r)' % self.parts
  def __repr__(self): return str(self)

class Level(list):
  def __init__(self, exprs=[]):
    self.fieldlist = None
    super(Level, self).__init__(exprs)

  def fields(self):
    if self.fieldlist is not None:
      return self.fieldlist

    self.fieldlist = []
    for e in self:
      self.fieldlist.extend(e.fields())

    return self.fieldlist

  def eval(self, ctx):
    acc = []
    bools = False
    for e in self:
      v, b = e.eval(ctx)
      acc.append(v)
      bools = bools or b

    return u''.join(acc).strip(), bools

  def __str__(self): return u'Level(%r)' % list(self)
  def __repr__(self): return str(self)

