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

def traverse_dict(base_content, head_content, keep, cond_func):
    # only keep the differences in head_file
    # print(head_content)
    for k,v in head_content.items():
        if k not in base_content:
            continue
        # everything is either a string or a dict
        if isinstance(v, str):
            # if this function is true, keep the head value v
            if cond_func(base_content, k, v):
                keep[k] = v
        if isinstance(v, dict):
            new_dict = traverse_dict(base_content[k], v, {}, cond_func)
            # only append non-empty dicts
            if len(new_dict) > 0:
                keep[k] = new_dict
    return keep

def keep_diff(base_file, head_file, diff_file):

    def _diff_content_f(base_content, k, v):
        return base_content[k] != v

    print("Writing diff to {}".format(diff_file))
    with open(base_file, 'r') as base_fh:
        base_content = json.load(base_fh)
    with open(head_file, 'r') as head_fh:
        head_content = json.load(head_fh)
    diffed_content = traverse_dict(base_content, head_content, {}, _diff_content_f)
    with open(diff_file, 'w') as result_fh:
        json.dump(diffed_content, result_fh, indent=4)
    return True

#def merge_content(base_content, head_content):
#    # merge
#    merged_content.update(base_content)
#    merged_content.update(head_content)
#    return merged_content


def merge_file(base_file, head_file, file_name):
    print("Merging {}".format(base_file))

    def _merge_overwrite_f(base_content, k, v):
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
    # merged_content = merge_content(base_content, head_content)
    merged_content = traverse_dict(base_content, head_content, {}, _merge_overwrite_f)
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
        ## keep diff only needs to run initially. simply change the diff from then on.
        # head_file = os.path.join(plantsharing_dir, file_name)
        # keep_diff(base_file, head_file, diff_file)
        merge_file(base_file, diff_file, file_name)

if __name__ == "__main__":
    main()

