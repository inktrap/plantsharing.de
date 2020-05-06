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

def get_file(lang_code):
    file_name = "locale-{}.json".format(lang_code)
    print("Updating {}".format(file_name))
    this_url = "https://raw.githubusercontent.com/yunity/karrot-frontend/master/src/locales/{}".format(file_name)
    result_file = os.path.join(karrot_dir, file_name)

    with urllib.request.urlopen(this_url) as response, open(result_file, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
    return True

def traverse_dict(base_content, head_content, keep, branch_func, leaf_func):
    # only keep the differences in head_file
    # print(head_content)
    for k,v in head_content.items():
        # everything is either a string or a dict
        if isinstance(v, str):
            # if this function is true, keep the head value v
            if leaf_func(base_content, k, v):
                keep[k] = v
        if isinstance(v, dict):
            new_dict = traverse_dict(base_content[k], v, {}, branch_func, leaf_func)
            if branch_func(new_dict):
                keep[k] = new_dict
    return keep

def keep_diff(base_file, head_file, diff_file):

    def _diff_content_f(base_content, k, v):
        if k not in base_content:
            return False
        return base_content[k] != v

    def _branch_func(new_dict):
        # only append non-empty dicts
        return len(new_dict) > 0

    print("Writing diff to {}".format(diff_file))
    with open(base_file, 'r') as base_fh:
        base_content = json.load(base_fh)
    with open(head_file, 'r') as head_fh:
        head_content = json.load(head_fh)
    diffed_content = traverse_dict(base_content, head_content, {}, _branch_func, _diff_content_f)
    with open(diff_file, 'w') as result_fh:
        json.dump(diffed_content, result_fh, indent=4)
    return True

def merge_file(base_file, head_file, file_name):
    print("Merging {}".format(base_file))

    def _merge_overwrite_f(base_content, k, v):
        return True

    def _branch_func(new_dict):
        # overwrite everything that is defined
        return True

    # requirements
    result_file = os.path.join(result_dir, file_name)
    if not os.path.isfile(head_file):
        print("Warning: {} does not exist, copying {}".format(head_file, base_file))
        head_file = base_file
    # open
    with open(base_file, 'r') as base_fh:
        base_content = json.load(base_fh)
    with open(head_file, 'r') as head_fh:
        head_content = json.load(head_fh)
    # merge the already existing base_content with the new head_content
    merged_content = traverse_dict(base_content, head_content, base_content, _branch_func, _merge_overwrite_f)
    with open(result_file, 'w') as result_fh:
        json.dump(merged_content, result_fh, indent=4)
    return True


UPDATE_LANG_CODES = ['de', 'en']

def main():

    for lang_code in UPDATE_LANG_CODES:
        get_file(lang_code)

    for base_file in glob.glob(os.path.join(karrot_dir, 'locale-*.json')):
        file_name = os.path.basename(base_file)
        diff_file = os.path.join(plantsharing_dir, "diff-" + file_name)
        # TODO: add option to merge diff file over head_file?
        # keep diff needs to run initially, also it's a nice overview of your changes
        head_file = os.path.join(plantsharing_dir, file_name)
        # create the difference between the base file and the head file
        keep_diff(base_file, head_file, diff_file)
        # overwrite the base file with the diff
        merge_file(base_file, diff_file, file_name)

if __name__ == "__main__":
    main()

