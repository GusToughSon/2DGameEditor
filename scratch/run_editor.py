import sys
import os
import runpy

# Reorder sys.path to prioritize system site-packages over the local workspace directory
# so that the system-wide Pillow is used rather than the local Python 3.14 PIL binaries.
cwd = os.path.abspath('.')
sys.path = [p for p in sys.path if p != '' and os.path.abspath(p) != cwd]
sys.path.append(cwd)

if __name__ == '__main__':
    runpy.run_path('GameEditor.py', run_name='__main__')
