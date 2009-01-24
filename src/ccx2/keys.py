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

command_mode_key = ':'

default_bindings = {
    'movement': {
        'move-focus-left': ['h', 'left'],
        'move-focus-up': ['k', 'up'],
        'move-focus-down': ['j', 'down'],
        'move-focus-right': ['l', 'right'],
        'page-up': ['ctrl u', 'page up'],
        'page-down': ['ctrl d', 'page down'],
        'move-focus-top': ['home', 'ctrl a'],
        'move-focus-bottom': ['end', 'ctrl e'],
    },
    'general': {
        'mark-and-move-down': [' '], # space
        'mark-and-move-up': ['<0>'], # ctrl space
        'unmark-all': ['meta  '], # meta space
        'return': ['enter', 'ctrl m'],
        'remove': ['d', 'delete'],
        'cancel': ['esc', 'ctrl g'],
        'quit': ['q', 'ctrl q'],
    },
    'tabs': {
        'goto-tab 1': ['1'],
        'goto-tab 2': ['2'],
        'goto-tab 3': ['3'],
        'goto-tab 4': ['4'],
        'goto-tab 5': ['5'],
        'goto-tab 6': ['6'],
        'goto-tab 7': ['7'],
        'goto-tab 8': ['8'],
        'goto-tab 9': ['9'],
        'goto-prev-tab': ['['],
        'goto-next-tab': [']'],
    },
    'text_edit': {
        'delete-word-backward': ['ctrl w', 'ctrl backspace'],
        'delete-word-forward': ['meta d', 'meta delete'],
        'move-word-backward': ['meta b'],
        'move-word-forward': ['meta f'],
        'move-char-backward': ['ctrl b'],
        'move-char-forward': ['ctrl f'],
    },
    'playback': {
        'play': ['x'],
        'play-pause-toggle': ['p', 'c'],
        'stop': ['s', 'backspace', 'v'],
        'next-track': ['>', 'b'],
        'previous-track': ['<', 'z'],
    },
    'playlist': {
        'play-focused': ['enter', 'ctrl m'],
        'move-marked-up': ['K'],
        'move-marked-down': ['J'],
    },
    'search': {
        'add-marked-to-playlist': ['a'],
        'add-marked-after-current-pos': ['w'],
    },
    'playlist-switcher': {
        'load-focused': ['enter', 'ctrl m'],
        'new': ['n'],
        'rename-focused': ['F2'],
        'add-focused-to-playlist': ['a'],
    },
    'collection-browser': {
        'navigate-in': ['l', 'right'],
        'navigate-out': ['h', 'left', 'backspace'],
        'add-to-playlist': ['a'],
    },
}

bindings = default_bindings
