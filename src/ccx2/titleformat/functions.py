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

def f_puts(parser, name, value):
  parser.context[name[0]] = unicode(value[0])
  return '', False

def f_get(parser, name):
  # TODO: default?
  try:
    v = parser.context[name]
    bool_value = v is not None
    return unicode(v), bool_value
  except KeyError:
    return '', False

def f_if(parser, *args):
  try:
    if args[0].eval(parser)[1]:
      return args[1].eval(parser)
    else:
      return args[2].eval(parser)
  except IndexError:
    return '', False

def f_if2(parser, *args):
  for arg in args:
    r = arg.eval(parser)
    if r[1]:
      return r[0], True
  return '', False

def f_left(parser, text, num):
  return text[0][:int(num[0])], text[1]

def f_right(parser, text, num):
  return text[0][-int(num):], text[1]

def f_substr(parser, text, begin, end):
  return text[0][int(begin[0]):int(end[0])], text[1]

def f_strcmp(parser, text1, text2):
  return '', text1[0] == text2[0]

def f_pad(parser, text, length, char=' '):
  return ('%s%s' % (char[0]*(int(length[0])-len(text[0])), text[0]), text[1])

