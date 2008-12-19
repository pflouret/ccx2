from pyparsing import OneOrMore, CharsNotIn, Combine, Forward, Group
from pyparsing import ParserElement, Optional, Suppress,  White, Word, ZeroOrMore
from pyparsing import alphanums, dblQuotedString, oneOf, printables, removeQuotes

from ccx2.mifl.functions import *

g_functions = {}

def register_function(f, name=None, eval_args=True):
  if not name:
    name = f.__name__
  g_functions[name] = (f, eval_args)

register_function(f_and, name='and', eval_args=False)
register_function(f_cat, name='cat')
register_function(f_equal, name='=')
register_function(f_if, name='if', eval_args=False)
register_function(f_left, name='left')
register_function(f_minus, name='-')
register_function(f_not, name='not')
register_function(f_or, name='or', eval_args=False)
register_function(f_pad, name='pad')
register_function(f_plus, name='+')
register_function(f_set, name='set', eval_args=False)

def remove_duplicates(l):
  # quick and dirty
  acc = []
  for e in l:
    if e not in acc:
      acc.append(e)
  return acc

# TODO: Text always has a True bool value for now, consider making a convenient [cond]
# TODO: construct to not pollute the code too much with "and", "or" and "if" functions.
# TODO: In such case Text should always return False within conds.
class Text(ParserElement):
  def __init__(self, text, *args, **kwargs):
    self.text = unicode(text)

    ParserElement.__init__(self, *args, **kwargs)
    self.name = 'Text(%r)' % self.text

  def symbol_names(self):
    return []

  def eval(self, context):
    if not self.text.strip():
      return u'', False
    else:
      return self.text, True

class Symbol(ParserElement):
  def __init__(self, symbol, *args, **kwargs):
    self.symbol = symbol
    self.default = kwargs.pop('default', u'')

    ParserElement.__init__(self, *args, **kwargs)
    self.name = 'Symbol(%r)' % self.symbol

  def symbol_names(self):
    return [self.symbol]

  def eval(self, context):
    if self.symbol in context:
      s = context[self.symbol]
      b = bool(s)
      if b:
        return unicode(s), b

    return self.default, False

class Function(ParserElement):
  def __init__(self, tokens, *args, **kwargs):
    self.f_name = tokens[0]
    self.args = tokens[1:]

    ParserElement.__init__(self, *args, **kwargs)
    self.name = 'Function:  (%s %r)' % (self.f_name, self.args)

  def symbol_names(self):
    symbols = []
    for e in self.args:
      vals = e.symbol_names()
      if vals:
        symbols.extend(vals)
    return remove_duplicates(symbols)

  def eval(self, context):
    if self.f_name in g_functions:
      f, eval_args = g_functions[self.f_name]
      if eval_args:
        args = [a.eval(context) for a in self.args]
      else:
        args = self.args
      return f(context, *args)

    return u'', False

class Branch(ParserElement):
  def __init__(self, exprs, *args, **kwargs):
    self.exprs = exprs.asList()

    ParserElement.__init__(self, *args, **kwargs)
    self.name = 'Branch(%r)' % self.exprs

  def symbol_names(self):
    symbols = []
    for e in self.exprs:
      vals = e.symbol_names()
      if vals:
        symbols.extend(vals)
    return remove_duplicates(symbols)

  def eval(self, context):
    vals = []
    bool_val = False
    for e in self.exprs:
      v, b = e.eval(context)
      vals.append(v)
      bool_val = bool_val or b

    return ''.join(vals), bool_val


class MiflParser(list):
  def __init__(self, formatstr):

    self.formatstr = formatstr
    self.parser = self._make_parser()

    try:
      exprs = self.parser.parseString(self.formatstr).asList()
    except:
      # TODO: informative error or whatever
      exprs = []

    list.__init__(self, exprs)

  def _make_parser(self):
    punct = "!#$%&*+,-./;<=>?@[\\]^_`{|}~"
    lparen, rparen = Suppress('('), Suppress(')')
    white = ZeroOrMore(White('\r\n').suppress()|White()).suppress()
    function_name = Word(alphanums + punct)

    symbol = Combine(Suppress(':') + Word(alphanums))
    string = dblQuotedString
    atom = (string | symbol)
    sexp = Forward()

    string = string.setParseAction(removeQuotes)
    string = string.addParseAction(lambda s,l,t: Text(t[0]))
    symbol = symbol.setParseAction(lambda s,l,t: Symbol(t[0]))
    sexp.setParseAction(lambda s,l,t: Function(t[0]))

    sexp << Group(lparen + function_name + ZeroOrMore(atom^sexp) + rparen)

    branch = (Optional(White()) + Suppress('>') + Optional(White())).suppress()
    escaped_char = (Suppress('\\') + oneOf(' '.join(printables)))
    text = (escaped_char | OneOrMore(CharsNotIn(':()>"\\\'\n\r')).setWhitespaceChars('\n\r'))
    text = text.setParseAction(lambda s,l,t: Text(t[0]))
    sexptop = (white + sexp + white)

    branch_level = OneOrMore(
        symbol.copy().setWhitespaceChars('\n\r') ^
        sexptop ^
        text)
    branch_level = branch_level.setParseAction(lambda s,l,t: Branch(t))

    top = ZeroOrMore(branch_level ^ branch)

    return top

  def eval_all(self, context):
    vals = []
    for e in self.exprs:
      v, b = e.eval(context)
      if b:
        vals.append(v)
    return ''.join(vals)

