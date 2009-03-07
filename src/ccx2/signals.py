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

# quick and dirty signals
# FIXME: the quick and dirty part

import signal

_signals = {}

def register(name):
  if name in _signals:
    # TODO: warn only
    raise ValueError("Signal with name %r already registered" % name)
  _signals[name] = []

def connect(name, callback):
  try:
    _signals[name].append(callback)
  except KeyError:
    raise NameError("No signal named %r" % name)

def disconnect(name, callback):
  try:
    _signals[name].remove(callback)
  except KeyError:
    pass

def emit(name, *args):
  if name not in _signals:
    raise NameError("No signal named %r" % name)

  for callback in _signals[name]:
    callback(*args)

def _alarm_available(t, f):
  def _f(sig, frame):
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    f(sig, frame)
  signal.signal(signal.SIGALRM, _f)
  signal.setitimer(signal.ITIMER_REAL, t)

def _alarm_not_available(t, f):
  f(signal.SIGALRM, None)

if hasattr(signal, 'setitimer'):
  alarm = _alarm_available
else:
  alarm = _alarm_not_available

