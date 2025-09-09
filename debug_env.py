
import sys
import os

print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")
print(f"sys.path:\n  {os.linesep.join(sys.path)}")
print(f"VIRTUAL_ENV: {os.getenv('VIRTUAL_ENV')}")
print(f"PATH: {os.getenv('PATH')}")

try:
    import pandas as pd
    print("pandas imported successfully!")
except ImportError:
    print("ERROR: pandas could NOT be imported.")