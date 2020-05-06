#!/usr/bin/env python3
import json
import os
import glob
import urllib.request
import shutil

script_dir = os.path.dirname(os.path.realpath(__file__))
karrot_dir = os.path.join(script_dir, 'karrot')
plantsharing_dir = os.path.join(script_dir, 'plantsharing')
result_dir = os.path.join(script_dir, 'result')

assert os.path.isdir(karrot_dir), "Please create {}".format(result_dir)
assert os.path.isdir(plantsharing_dir), "Please create {}".format(result_dir)
assert os.path.isdir(result_dir), "Please create {}".format(result_dir)

def merge_content(base_content, head_content):
    merged_content = {}
    # merge
    merged_content.update(base_content)
    merged_content.update(head_content)
    return merged_content

def get_file(file_name):
    this_url = "https://raw.githubusercontent.com/yunity/karrot-frontend/master/src/locales/{}".format(file_name)
    result_file = os.path.join(karrot_dir, file_name)

    with urllib.request.urlopen(this_url) as response, open(result_file, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
    return True

def merge_file(base_file):
    # requirements
    file_name = os.path.basename(base_file)
    head_file = os.path.join(plantsharing_dir, file_name)
    result_file = os.path.join(result_dir, file_name)
    if not os.path.isfile(head_file):
        print("Warning: {} does not exist, copying {}".format(head_file, base_file))
        head_file = base_file
    # open
    with open(base_file, 'r') as base_fh:
        base_content = json.load(base_fh)
    with open(head_file, 'r') as head_fh:
        head_content = json.load(head_fh)
    merged_content = merge_content(base_content, head_content)
    with open(result_file, 'w') as result_fh:
        json.dump(merged_content, result_fh)
    return True


UPDATE_LANG_CODES = ['de', 'en']

def main():

    for lang_code in UPDATE_LANG_CODES:
        file_name = "locale-{}.json".format(lang_code)
        print("Updating {}".format(file_name))
        get_file(file_name)

    for base_file in glob.glob(os.path.join(karrot_dir, 'locale-*.json')):
        print("Merging {}".format(base_file))
        merge_file(base_file)

if __name__ == "__main__":
    main()

