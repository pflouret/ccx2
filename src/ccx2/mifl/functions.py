
def f_and(context, *args):
  for e in args:
    v, b = e.eval(context)
    if not b:
      break
  else:
    return v, True
  return u'', False

def f_cat(context, *args):
  acc = []
  result_bool = False
  for v, b in args:
    acc.append(unicode(v))
    result_bool = result_bool or b

  return u''.join(acc), result_bool

def f_equal(context, *args):
  acc = True
  for i in range(len(args)-1):
    acc = acc and (args[i][0] == args[i+1][0])

  return u'', acc

def f_if(context, *args):
  try:
    s, b = args[0].eval(context)
    if b:
      return args[1].eval(context)
    else:
      return args[2].eval(context)
  except IndexError:
    return u'', False

def f_left(context, text, num):
  s, b = text
  try:
    return s[:int(num[0])], b
  except ValueError:
    return u'', False

def f_minus(context, *args):
  if not args:
    return u'', False

  acc = args[0][0]
  for v, b in args[1:]:
    acc -= v

  if not acc:
    acc = u''
  else:
    acc = unicode(acc)
  return acc, bool(acc)

def f_not(context, arg):
  return u'', not arg[1]

def f_or(context, *args):
  for e in args:
    v, b = e.eval(context)
    if b:
      break
  else:
    return u'', False
  return v, True

def f_plus(context, *args):
  s = sum([a[0] for a in args])
  if not s:
    s = u''
  else:
    s = unicode(s)
  return s, bool(s)

def f_set(context, symbol, value):
  try:
    context[symbol.symbol] = value.eval(context)[0]
  except AttributeError:
    pass
  return u'', False

