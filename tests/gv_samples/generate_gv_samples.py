#!/usr/bin/env python

from __future__ import with_statement

import logging

import sys
sys.path.append("/usr/lib/dialcentral")
sys.path.append("../../src")

import gv_backend


def main():
	username = sys.argv[1]
	password = sys.argv[2]
	gv_backend.grab_debug_info(username, password)


if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)
	main()
