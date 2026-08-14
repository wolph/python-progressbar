"""Parallel execution with progress bars.

Private implementation package behind the public ``progressbar.map`` /
``imap`` / ``amap`` / ``run`` / ``Pool`` family. The package is private
(underscored) because the public surface includes a ``parallel``
*decorator* exported as ``progressbar.parallel`` -- a public
``progressbar/parallel.py`` module would clobber that attribute on
``import progressbar.parallel``.

Public names are re-exported lazily from ``progressbar/__init__.py``.
"""
