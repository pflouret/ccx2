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

from ccx2.titleformat.functions import *

__all__ = ['register_function', 'TitleformatParser', 'eval', 'ScriptError', 'ParseError',
           'EndOfFile', 'SyntaxError', 'UnknownFunction']

# TODO: make a parser that's not completely ugly

class ScriptError(Exception): pass
class ParseError(ScriptError): pass
class EndOfFile(ParseError): pass
class SyntaxError(ParseError): pass
class UnknownFunction(ScriptError): pass

_functions = {}

def register_function(f, name=None, eval_args=True):
  if not name:
    name = f.__name__
  _functions[name] = (f, eval_args)

register_function(f_if, name='if', eval_args=False)
register_function(f_if2, name='if2', eval_args=False)
register_function(f_left, name='left')
register_function(f_right, name='right')
register_function(f_substr, name='substr')
register_function(f_strcmp, name='strcmp')
register_function(f_puts, name='puts')
register_function(f_get, name='get')
register_function(f_pad, name='pad')

class Text(unicode):
  def eval(self, parser):
    return self, False

class Var(object):
  def __init__(self, name, default=u''):
    self.name = name
    self._default = default

  def eval(self, parser):
    try:
      v = parser.context[self.name]
      bool_value = v is not None
      if not bool_value:
        raise ValueError()
    except (KeyError, ValueError):
      v = self._default
      bool_value = False
    return unicode(v), bool_value

class Expr(object):
  def __init__(self, *args):
    self.exprs = args and list(args) or []
    self.has_branches = False

  def add(self, expr):
    self.exprs.append(expr)

  def eval(self, parser):
    result = u''
    bool_value = False
    for e in self.exprs:
      v, b = e.eval(parser)
      bool_value = bool_value or b
      result = result + v
    return result, bool_value

class Cond(object):
  def __init__(self, exprs):
    self.exprs = exprs

  def add(self, expr):
    self.exprs.append(expr)

  def eval(self, parser):
    result = u''
    bool_value = False
    for e in self.exprs:
      v, b = e.eval(parser)
      bool_value = bool_value or b
      result = result + v
    if bool_value:
      return result, bool_value
    return u'', bool_value

class Function(object):
  def __init__(self, name, args):
    self.name = name
    self.args = args

  def eval(self, parser):
    try:
      function, eval_args = _functions[self.name]
    except KeyError:
      raise UnknownFunction("Unknown function '%s'" % self.name)
    if eval_args:
      args = [arg.eval(parser) for arg in self.args]
    else:
      args = self.args
    return function(parser, *args)

def isidentif(ch):
  return ch.isalnum() or ch in '_ '

# TODO: add 'no braches' option
# TODO: add aliases for vars (album artist, track artist, etc)
# TODO: parameter for strict mode, don't raise exceptions if false
class TitleformatParser(object):
  def __init__(self, text):
    self._text = text
    self._pos = 0
    self._px = self._x = 1
    self._py = self._y = 1
    self._line = 0
    self._parse()

  def __raise_eof(self):
    raise EndOfFile(
      "Unexpected end of script at position %d, line %d" %
        (self._x, self._y))

  def __raise_char(self, ch):
    raise SyntaxError(
      "Unexpected character '%s' at position %d, line %d"  %
        (ch, self._x, self._y))

  def _read(self):
    try:
      ch = self._text[self._pos]
    except IndexError:
      return None
    else:
      self._pos += 1
      self._px = self._x
      self._py = self._y
      if ch == '\n':
        self._line = self._pos
        self._x = 1
        self._y += 1
      else:
        self._x += 1
    return ch

  def _unread(self):
    self._pos -= 1
    self._x = self._px
    self._y = self._py

  def _parse_var(self, top):
    begin = self._pos
    while True:
      ch = self._read()
      if ch == '%':
        return Var(self._text[begin:self._pos-1], default=top and '?' or '')
      elif ch is None:
        self.__raise_eof()
      elif not isidentif(ch):
        self.__raise_char(ch)

  def _parse_text(self, top, cond, literal):
    text = []
    while True:
      ch = self._read()
      if literal:
        if ch == "'" or ch is None:
          break
      else:
        if ch == "'":
          self._unread()
          break
        elif ch is None:
          break
        elif (not top and not cond and ch == '(') or (not top and cond and ch == '['):
          self.__raise_char(ch)
        elif ch in '$%[|' or (not top and not cond and ch in ',)') or \
             (not top and cond and ch == ']'):
          self._unread()
          break
      text.append(ch)

    return Text("".join(text))

  def _parse_arguments(self, cond=False):
    results = []
    while True:
      result, ch = self._parse_expr(False, cond=cond)
      results.append(result)
      if (not cond and ch == ')') or (cond and ch == ']'):
        return results

  def _parse_function(self):
    start = self._pos
    while True:
      ch = self._read()
      if ch == '(':
        name = self._text[start:self._pos-1]
        if name not in _functions:
          raise UnknownFunction("Unknown function '%s'" % name)
        return Function(name, self._parse_arguments())
      elif ch is None:
        self.__raise_eof()
      elif not isidentif(ch):
        self.__raise_char(ch)

  def _parse_cond(self):
    exprs = self._parse_arguments(cond=True)
    return Cond(exprs)

  def _parse_expr(self, top, cond=False):
    expr = Expr()
    while True:
      ch = self._read()
      if ch is None:
        if top:
          break
        else:
          self.__raise_eof()
      elif (not top and not cond and ch in ',)') or (not top and cond and ch == ']'):
        break
      elif ch == '|':
        expr.add(Text(u'\0'))
        expr.has_branches = True
      elif ch == '[':
        expr.add(self._parse_cond())
      elif ch == '$':
        expr.add(self._parse_function())
      elif ch == '%':
        expr.add(self._parse_var(top))
      else:
        if ch != "'":
          self._unread()
        expr.add(self._parse_text(top, cond, literal=ch=="'"))
    return (expr, ch)

  def _parse(self):
    self._parsed_expr = self._parse_expr(True)[0]

  def get_field_names(self, level=None):
    if level is None:
      queue = list(self._parsed_expr.exprs)
    else:
      toplevel = self._parsed_expr.exprs
      split = []
      prev = 0
      for i,e in enumerate(toplevel):
        if e == u'\0':
          split.append(toplevel[prev:i])
          prev = i+1
      split.append(toplevel[prev:])

      try:
        queue = split[level]
      except IndexError:
        queue = []

    names = []

    while queue:
      e = queue.pop(0)
      t = type(e)
      if t == Var:
        names.append(e.name)
      elif t in [Expr, Cond]:
        queue = e.exprs + queue
      elif t == Function:
        queue = e.args + queue

    return names

  def eval(self, context):
    self.context = context
    res = self._parsed_expr.eval(self)[0]
    return res.find(u'\0') >= 0 and res.split(u'\0') or res

def eval(format, context, level=0):
  return TitleformatParser(format).eval(context, level)
