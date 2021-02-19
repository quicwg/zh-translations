#!/usr/bin/env python3

import sys
import argparse
import html
import os

parser = argparse.ArgumentParser(description="Lint markdown drafts.")
parser.add_argument("files", metavar="file", nargs="+", help="Files to lint")
parser.add_argument("-l", dest="maxLineLength", default=180)
parser.add_argument("-f", dest="maxFigureLineLength", default=66)

args = parser.parse_args()

foundError = False

for inputfile in args.files:
    insideFigure = False
    beforeAbstract = True
    zh_file_name = "-zh.".join(inputfile.split('.'))
    with open(zh_file_name, mode='w') as f:
        with open(inputfile, mode="rt", newline=None, encoding="utf-8") as draft:
            lines = draft.readlines()

            for line in lines:
                line = html.unescape(line.rstrip("\r\n"))
                f.write(line+"\n")

    os.remove(inputfile)
    os.rename(zh_file_name, inputfile)

sys.exit(1 if foundError else 0)
