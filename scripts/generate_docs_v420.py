# -*- coding: utf-8 -*-
"""
Crinômetro - Script legado mantido para compatibilidade.
Redireciona para scripts/generate_docs.py (v4.4.1+).
"""
import os
import sys

_dir = os.path.dirname(os.path.abspath(__file__))
_new_script = os.path.join(_dir, "generate_docs.py")

if __name__ == "__main__":
    import runpy
    runpy.run_path(_new_script, run_name="__main__")
