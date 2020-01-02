import sys
import os


sys.path.insert(1, '..')
env_files = [
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '../test.env')]

for file in env_files:
    with open(file, 'r') as f:
        for line in f.readlines():
            if '=' in line:
                k, v = line.split('=')
                os.environ[k] = v
