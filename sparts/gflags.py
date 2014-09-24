# Copyright (c) 2014, Facebook, Inc.  All rights reserved.

#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
#
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
import _sparts_gflags as _gflags
import argparse

__all__ = [
    'get_gflag',
    'set_gflag',
    'reset_gflag',
    'get_all_gflags',
    'reset_all_gflags',
    'FlagInfo',
    'add_gflags',
    'GNU_STYLE',
    'GFLAGS_STYLE',
    'MIXED_STYLE',
],

GNU_STYLE = 'GNU_STYLE'
GFLAGS_STYLE = 'GFLAGS_STYLE'
MIXED_STYLE = 'MIXED_STYLE'

def get_gflag(name):
    """Retrieve the value of a gflag"""
    return _maybe_unicode(_gflags.get_flag(_utf8_bytes(name)))

def set_gflag(name, value):
    """Set a gflag."""
    _gflags.set_flag(_utf8_bytes(name), _maybe_utf8_bytes(value))

def reset_gflag(name):
    """Reset a gflag to its default value."""
    _gflags.reset_flag(_utf8_bytes(name))


def reset_all_gflags():
    """Reset all gflags to their default values."""
    _gflags.reset_all_flags()

class FlagInfo(object):
    """Wrapper around _gflags.FlagInfo that returns unicode."""
    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        return _maybe_unicode(getattr(self._inner, name))

def get_all_gflags():
    all_flags = _gflags.get_all_flags()
    # Convert to the types we want to use
    all_flags = dict((_unicode(k), FlagInfo(v))
                     for (k, v) in all_flags.iteritems())
    return all_flags

# These are gflags that we won't import. Some are added explicitly
# (help, helpfull, helpshort, version), while others are functionality
# that we don't support.
_SPECIAL_FLAGS = frozenset((
    'help',
    'helpfull',
    'helpshort',
    'helpon',
    'helpmatch',
    'helppackage',
    'helpxml',
    'version',
    'flagfile',
    'fromenv',
    'tryfromenv',
    'undefok',
    'tab_completion_columns',
    'tab_completion_word',
))

def _hyphens(names):
    """Prepend two hyphens to all strings in names."""
    return ['--' + n for n in names]

def _parse_int32(val):
    """Parse a string as a int32 value (with range checking)."""
    val = int(val)
    if val < -(1 << 31) or val >= (1 << 31):
        raise ValueError('int32 value out of range: {}'.format(val))
    return val

def _parse_int64(val):
    """Parse a string as a int64 value (with range checking)."""
    # int actually returns a long if out of int range
    val = int(val)
    if val < -(1 << 63) or val >= (1 << 63):
        raise ValueError('int64 value out of range: {}'.format(val))
    return val

def _parse_uint64(val):
    """Parse a string as a uint64 value (with range checking)."""
    # int actually returns a long if out of int range
    val = int(val)
    if val < 0 or val >= (1 << 64):
        raise ValueError('uint64 value out of range: {}'.format(val))
    return val

_FLAG_PARSERS = {
    'string': unicode,
    'int32': _parse_int32,
    'int64': _parse_int64,
    'uint64': _parse_uint64,
    'double': float,
}

class _GFlagAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
        set_gflag(self.dest, values)

class _GFlagActionBool(argparse.Action):
    """Special action for --<bool> flags."""
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, True)
        set_gflag(self.dest, True)

class _GFlagActionNegatedBool(argparse.Action):
    """Special action for --no<bool> flags."""
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, False)
        set_gflag(self.dest, False)

def _metavar(type):
    return '<{}>'.format(type.upper())

def _default_str(dflt):
    s = repr(dflt)
    if isinstance(dflt, unicode) and s[0] == 'u':
        # Hack, don't display u'Hello', display 'Hello'
        s = s[1:]
    return s

def _names(name, style):
    """Return the list of flag names and the list of negated flag names.
       (for booleans: --foo becomes --no-foo)"""
    names = set()
    negated_names = set()
    if style == GNU_STYLE or style == MIXED_STYLE:
        hyphen_name = name.replace('_', '-')
        names.add(hyphen_name)
        negated_names.add('no-' + hyphen_name)
    if style == GFLAGS_STYLE or style == MIXED_STYLE:
        names.add(name)
        negated_names.add('no' + name)
    return list(sorted(names)), list(sorted(negated_names))

def _add_gflag(group, name, info, style):
    names, negated_names = _names(name, style)

    flag_type = info.type

    # We use current_value rather than default_value as default.
    # This is intentional; programs using gflags often set the values
    # of the flags explicitly (by assigning directly to the FLAGS_*
    # variables) before calling ParseCommandLineFlags() in order to change
    # the defaults from the ones specified where the flag was defined.
    # We aim to preserve the same behavior.
    metavar = _metavar(flag_type)
    description = '{description} (default: {default})'.format(
            default=_default_str(info.current_value),
            description=info.description)
    if flag_type == 'bool':
        # Bool is special, as we need to parse --noflying_pigs
        group.add_argument(*_hyphens(names), dest=name, nargs=0,
                           default=info.current_value, help=description,
                           action=_GFlagActionBool)
        group.add_argument(*_hyphens(negated_names), dest=name, nargs=0,
                           action=_GFlagActionNegatedBool)
    else:
        type_function = _FLAG_PARSERS[flag_type]
        group.add_argument(*_hyphens(names), type=type_function,
                           dest=name, default=info.current_value,
                           help=description, metavar=metavar,
                           action=_GFlagAction)

def add_gflags(parser, set_version=False, style=MIXED_STYLE):
    """Add gflags to an argparse.ArgumentParser parser.

    Keyword arguments:
    set_version -- set the --version flag from the gflags version string
    style -- naming style for optional arguments, one of GNU_STYLE,
             GFLAGS_STYLE, MIXED_STYLE
    """

    # Consider two gflags: 'cats' and 'flying_pigs'
    #
    # GNU style: multi-word argument names are separated by hyphens, not
    # underscores; negation uses the 'no-' prefix.
    # cats => --cats / --no-cats
    # flying_pigs => --flying-pigs / --no-flying-pigs
    #
    # GFLAGS style: multi-word argument names are separated by underscores;
    # negation uses the 'no' prefix.
    # cats => --cats / --nocats
    # flying_pigs => --flying_pigs, --noflying_pigs
    #
    # MIXED style: accept both GNU style and GFLAGS style.
    # cats => --cats / --no-cats, --nocats
    # flying_pigs => --flying-pigs, --flying_pigs /
    #                --no-flying-pigs, --noflying_pigs
    all_flags = get_all_gflags()
    all_flags = dict((k, v) for (k, v) in all_flags.iteritems()
                     if not k in _SPECIAL_FLAGS)

    # If requested, add a --version flag with the GFlags version string
    if set_version:
        version_string = _gflags.get_version_string()
        parser.add_argument(
                '--version', action='version',
                version=' '.join(('%(prog)s', _maybe_unicode(version_string))))

    # We don't support helpmatch, helppackage, helpxml, and we always
    # display the full help, even with helpshort.  --help is likely already
    # there; add it if it's not.
    help_flags = ['--helpfull', '--helpshort']
    if not parser.add_help:  # not already added
        # -h, --help go first so they show first in the output
        help_flags = ['-h', '--help'] + help_flags
    parser.add_argument(*help_flags,
                        help='show this help message and exit',
                        action='help')

    group = parser.add_argument_group('GFlags', 'GFlags from C++ code')
    for name, info in all_flags.iteritems():
        _add_gflag(group, name, info, style=style)


def _unicode(val):
    """Convert bytes to unicode (UTF-8)."""
    return val.decode('UTF-8')

def _maybe_unicode(val):
    """Convert bytes to unicode (UTF-8), leave other types unchanged."""
    return _unicode(val) if isinstance(val, str) else val 

def _utf8_bytes(val):
    """Convert unicode to bytes (UTF-8)."""
    return val.encode('UTF-8')

def _maybe_utf8_bytes(val):
    """Convert unicode to bytes (UTF-8), leave other types unchanged."""
    return _utf8_bytes(val) if isinstance(val, unicode) else val
