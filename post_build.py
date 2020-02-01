#!/usr/local/bin/python3
import os
import shutil

root_folder = os.path.join(os.path.dirname(__file__), 'dist/Maestral.app/Contents/macOS')

items_to_remove = [
]

print('Removing unneeded modules...')


for path in items_to_remove:
    full_path = os.path.join(root_folder, path)
    if os.path.isfile(full_path):
        os.remove(full_path)
    elif os.path.isdir(full_path):
        shutil.rmtree(full_path)

print('Done.')
