# Copyright 2014 ARM Limited
#
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.

# standard library modules, , ,
from __future__ import print_function
import re
import logging
import os

# colorama, BSD 3-Clause license, cross-platform terminal colours, pip install colorama
import colorama

# settings, , load and save settings, internal
from yotta.lib import settings
# Target, , represents an installed target, internal
from yotta.lib import target
# Component, , represents an installed component, internal
from yotta.lib import component
# fsutils, , misc filesystem utils, internal
from yotta.lib import fsutils

# OK this is a pretty terrible validation regex... should find a proper module
# to do this
Target_RE = re.compile('^('+
    '[a-z]+[a-z0-9+-]*,?('+
        '[a-zA-Z0-9-]+/[a-zA-Z0-9-]+' +'|'+ '([a-zA-Z0-9_-]*@)?[a-zA-Z0-9_+-]+://.*' + '|' + '[a-z0-9.-]*'+
    ')?'+
')$')


def addOptions(parser):
    parser.add_argument('set_target', default=None, nargs='?',
        help='set the build target to this (targetname[,versionspec_or_url])'
    )
    parser.add_argument('-g', '--global', dest='save_global',
        default=False, action='store_true',
        help='set globally (in the per-user settings) instead of locally to this directory'
    )
    parser.add_argument('-n', '--no-install', dest='no_install',
        default=False, action='store_true',
        help='do not immediately download the target description'
    )


def displayCurrentTarget(args):
    if not args.plain:
        DIM    = colorama.Style.DIM       #pylint: disable=no-member
        BRIGHT = colorama.Style.BRIGHT    #pylint: disable=no-member
        GREEN  = colorama.Fore.GREEN      #pylint: disable=no-member
        RED    = colorama.Fore.RED        #pylint: disable=no-member
        RESET  = colorama.Style.RESET_ALL #pylint: disable=no-member
    else:
        DIM = BRIGHT = GREEN = RED = RESET = u''

    line = u''

    c = component.Component(os.getcwd())
    if c.isApplication():
        app_path = c.path
    else:
        app_path = None

    derived_target, errors = target.getDerivedTarget(
        args.target, c.targetsPath(), application_dir=app_path, install_missing=False
    )
    for error in errors:
        logging.error(error)

    if derived_target is None:
        line = BRIGHT + RED + args.target + u' missing' + RESET
    else:
        for t in derived_target.hierarchy:
            if len(line):
                line += '\n'
            if t:
                line += t.getName() + DIM + u' ' + str(t.getVersion()) + RESET
                if t.installedLinked():
                    line += GREEN + BRIGHT + u' -> ' + RESET + GREEN + fsutils.realpath(t.path)
            else:
                line += BRIGHT + RED + t.getName() + DIM + u' ' + str(t.getVersion()) + BRIGHT + u' missing'
            line += RESET
        base_spec = t.baseTargetSpec()
        if base_spec:
            # if the last target in the hierarchy has a base spec, then the
            # hierarchy is incomplete:
            line += '\n' + BRIGHT + RED + base_spec.name + u' ' + base_spec.versionReq() + u' missing'

    if u'unicode' in str(type(line)):
        # python 2.7
        print(line.encode('utf-8'))
    else:
        print(line)
    return len(errors)


def execCommand(args, following_args):
    if args.set_target is None:
        return displayCurrentTarget(args)
    else:
        if not Target_RE.match(args.set_target):
            logging.error('Invalid target: "%s"' % args.set_target)#, targets must be one of:
            #
            #    a valid name (lowercase letters, numbers, and hyphen)
            #    a github ref (owner/project)
            #    a valid url
            #
            #Note that to use a local directory as a target you can use
            #
            #    # in the directory containing the target package:
            #    yotta link target
            #
            #    # then in the directory of the application to use the target:
            #    yotta link target {targetname}
            #    yotta target {targetname}
            #
            #''')
            return 1
        else:
            if args.set_target.find(',') == -1:
                t = args.set_target + ',*'
            else:
                t = args.set_target
            settings.setProperty('build', 'target', t, not args.save_global)
            settings.setProperty('build', 'targetSetExplicitly', True, not args.save_global)
            if not args.no_install:
                # if we have a module in the current directory, try to make sure
                # this target is installed
                c = component.Component(os.getcwd())
                if c:
                    target, errors = c.satisfyTarget(t)
                    for err in errors:
                        logging.error(err)
                    if len(errors):
                        logging.error('NOTE: use "yotta link-target" to test a locally modified target prior to publishing.')
                        return 1
            return 0
