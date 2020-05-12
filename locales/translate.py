#!/usr/bin/env python3
import json
import os
import glob
import urllib.request
import shutil

import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "-i",
    "--init-diff",
    action="store_true",
    default=False,
    dest="init_diff",
    help="init diff from weblate/locale-en.json keys and create weblate files from karrot",
)

parser.add_argument(
    "-e",
    "--edit-diff",
    action="store_true",
    default=False,
    dest="edit_diff",
    help="get diff from project and karrot and (re-)create weblate files",
)

parser.add_argument(
    "-m",
    "--merge-diff",
    action="store_true",
    default=False,
    dest="merge_diff",
    help="merge diff from weblate over karrot and (re-)create project files",
)


parser.add_argument(
    "-k",
    "--update-karrot",
    action="store_true",
    default=False,
    dest="update_karrot",
    help="pull new karrot locale versions from github",
)

parser.add_argument(
    "-p",
    "--update-project",
    action="store_true",
    default=False,
    dest="update_project",
    help="pull new project locale versions from weblate",
)

args = parser.parse_args()

script_dir = os.path.dirname(os.path.realpath(__file__))
karrot_dir = os.path.join(script_dir, 'karrot')
weblate_dir = os.path.join(script_dir, 'weblate')
project_dir = os.path.join(script_dir, 'plantsharing')

assert os.path.isdir(karrot_dir), "Please create {}".format(karrot_dir)
assert os.path.isdir(project_dir), "Please create {}".format(project_dir)
assert os.path.isdir(weblate_dir), "Please create {}".format(weblate_dir)


def get_file(lang_code, this_url, out_dir):
    file_name = "locale-{}.json".format(lang_code)
    print("Updating {}".format(_get_printname(file_name)))
    this_url = this_url.format(file_name)
    result_file = os.path.join(out_dir, file_name)

    with urllib.request.urlopen(this_url) as response:
        if response.status == 404:
            print("404: file does not exist. Continueing.")
            return True
        with open(result_file, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
    return True


def filter_dict(base_content, head_content, keep, branch_func, leaf_func, keep_content=False):
    # only keep the differences in head_file
    # print(head_content)
    for k,v in head_content.items():
        # everything is either a string or a dict
        if isinstance(v, str):
            # if this function is true, keep the head value v
            if leaf_func(base_content, k, v):
                keep[k] = v
        if isinstance(v, dict):
            # subdictionaries are empty and only the values of header_dict are added
            new_dict = filter_dict(base_content[k], v, {}, branch_func, leaf_func, keep_content)
            if branch_func(new_dict):
                keep[k] = new_dict
    return keep


def merge_dict(base_content, head_content, keep, branch_func, leaf_func):
    for k,v in head_content.items():
        # everything is either a string or a dict
        if isinstance(v, str):
            # if this function is true, keep the head value v
            if leaf_func(base_content, k, v):
                keep[k] = v
        if isinstance(v, dict):
            new_dict = filter_dict(base_content[k], v, base_content[k], branch_func, leaf_func)
            if branch_func(new_dict):
                keep[k] = new_dict
    return keep

def rewrite_dict(this_dict, keep, branch_func, leaf_func):
    for k,v in this_dict.items():
        # everything is either a string or a dict
        if isinstance(v, str):
            # rewrite the leaf based on leaf_func
            keep[k] = leaf_func(this_dict, k, v)
        if isinstance(v, dict):
            # rewrite the branch based on branch_func
            # and recurse
            keep[k] = rewrite_dict(branch_func(v), v, branch_func, leaf_func)
    return keep


def make_suggestions(base_content, head_content, init_dict, keep):
    # traverse the keys in init_dict and check wether
    for k,v in init_dict.items():
        if isinstance(v, str):
            if k in head_content:
                # a value exists in head_file (the diff), if yes, take it
                keep[k] = head_content[k]
            elif k in base_content:
                # if not, check wether one exists in base_content
                keep[k] = base_content[k]
            else:
                # just keep the existing value from init_dict (empty string)
                keep[k] = v
        if isinstance(v, dict):
            if k in base_content:
                this_base_content = base_content[k]
            else:
                this_base_content = {}
            if k in head_content:
                this_head_content = head_content[k]
            else:
                this_head_content = {}
            # if the dict doesn't exist in base nor head content, we won't go down that path
            # instead we'll simply use the initial dict to get a full tree
            keep[k] = make_suggestions(this_base_content, this_head_content, v, keep)
    return keep

def init_diff(base_file, head_file, diff_file, init_dict):
    print("Init diff in {}".format(_get_printname(diff_file)))
    with open(base_file, 'r', encoding='utf8') as base_fh:
        base_content = json.load(base_fh)
    with open(head_file, 'r', encoding='utf8') as head_fh:
        head_content = json.load(head_fh)
    #print(init_dict)
    suggestions_content = make_suggestions(base_content, head_content, init_dict, {})
    with open(diff_file, 'w', encoding='utf8') as result_fh:
        json.dump(suggestions_content, result_fh, indent=4, ensure_ascii=False)
    #print(suggestions)
    # remove empty keys?
    # TODO: remove reading files from functions
    return True


def keep_diff(base_file, head_file, diff_file):
    # create the difference between the head file and the base file and write it to diff file

    def _diff_content_f(base_content, k, v):
        if k not in base_content:
            return False
        return base_content[k] != v

    def _branch_func(new_dict):
        # only append non-empty dicts
        return len(new_dict) > 0

    print(" - writing diff to {}".format(_get_printname(diff_file)))
    with open(base_file, 'r', encoding='utf8') as base_fh:
        base_content = json.load(base_fh)
    with open(head_file, 'r', encoding='utf8') as head_fh:
        head_content = json.load(head_fh)
    diffed_content = filter_dict(base_content, head_content, {}, _branch_func, _diff_content_f, False)
    with open(diff_file, 'w', encoding='utf8') as result_fh:
        json.dump(diffed_content, result_fh, indent=4, ensure_ascii=False)
    return True


def _get_printname(filename):
    return os.path.relpath(filename, script_dir)


def merge_file(base_file, head_file, result_file):
    print(" - merging {} over {}".format(_get_printname(head_file), _get_printname(base_file)))

    def _merge_overwrite_f(base_content, k, v):
        return True

    def _branch_func(new_dict):
        # overwrite everything that is defined
        return True

    # requirements
    if not os.path.isfile(head_file):
        print("Warning: {} does not exist, copying {}".format(_get_printname(head_file), _get_printname(base_file)))
        head_file = base_file
    # open
    with open(base_file, 'r', encoding='utf8') as base_fh:
        base_content = json.load(base_fh)
    with open(head_file, 'r', encoding='utf8') as head_fh:
        head_content = json.load(head_fh)
    # merge the already existing base_content with the new head_content
    merged_content = merge_dict(base_content, head_content, base_content, _branch_func, _merge_overwrite_f)
    with open(result_file, 'w', encoding='utf8') as result_fh:
        json.dump(merged_content, result_fh, indent=4, ensure_ascii=False)
    return True


UPDATE_LANG_CODES = ['de', 'en']

LANG_CODES = [
    "ar",
    "cs",
    "da",
    "de",
    "en",
    "eo",
    "es",
    "fa",
    "fa_IR",
    "fr",
    "gu",
    "hi",
    "hr",
    "it",
    "ja",
    "lb",
    "mr",
    "nl",
    "pl",
    "pt",
    "pt_BR",
    "ro",
    "ru",
    "sv",
    "zh_Hans",
    "zh_Hant",
]


def main():

    if args.update_karrot:
        print("Updating karrot locales")
        this_url = "https://raw.githubusercontent.com/yunity/karrot-frontend/master/src/locales/{}"
        out_dir = karrot_dir
        for lang_code in LANG_CODES:
            get_file(lang_code, this_url, out_dir)

    if args.update_project:
        print("Updating project locales")
        raise NotImplementedError

    if args.init_diff:
        print("Initing diffs (based on weblate/locale-en.json)")
        master_dict = os.path.join(weblate_dir, 'locale-en.json')
        # remove all leafs from init_dict

        def _keep_dict(this_dict):
            return this_dict

        def _empty_leaf(base_content, k, v):
            return ""

        with open(master_dict, 'r', encoding='utf8') as init_fh:
            init_content = json.load(init_fh)

        init_dict = rewrite_dict(init_content, {}, _keep_dict, _empty_leaf)
        #print(init_dict)
        #raise NotImplementedError

        for base_file in glob.glob(os.path.join(karrot_dir, 'locale-*.json')):
            # print(" - base file {}".format(base_file))
            file_name = os.path.basename(base_file)
            diff_file = os.path.join(weblate_dir, file_name)
            head_file = os.path.join(weblate_dir, file_name)
            # TODO: should i use head_file or diff_file here for head_file???
            # … probably diff_file, because it contains the latest translations, … ?

            # TODO: english overwrites if the key is not in head file nor in diff file
            init_diff(base_file, head_file, diff_file, init_dict)
        raise NotImplementedError

    if args.edit_diff:
        print("Re-creating diffs")
        for base_file in glob.glob(os.path.join(karrot_dir, 'locale-*.json')):
            # print(" - base file {}".format(base_file))
            file_name = os.path.basename(base_file)
            diff_file = os.path.join(weblate_dir, file_name)
            # TODO: add option to merge diff file over head_file?
            # keep diff needs to run initially, also it's a nice overview of your changes
            head_file = os.path.join(project_dir, file_name)
            # create the difference between the base file and the head file
            keep_diff(base_file, head_file, diff_file)

    if args.merge_diff:
        print("Merging diff files into project dir (diff wins)")
    for base_file in glob.glob(os.path.join(karrot_dir, 'locale-*.json')):
        # print(" - base file {}".format(base_file))
        file_name = os.path.basename(base_file)
        diff_file = os.path.join(weblate_dir, file_name)
        result_file = os.path.join(project_dir, file_name)
        merge_file(base_file, diff_file, result_file)


if __name__ == "__main__":
    main()

