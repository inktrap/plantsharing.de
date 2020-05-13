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
    help="init diff from weblate/locale-en.json keys and create weblate files from upstream",
)

parser.add_argument(
    "-m",
    "--merge-diff",
    action="store_true",
    default=False,
    dest="merge_diff",
    help="merge diff from weblate over upstream and (re-)create project files",
)


parser.add_argument(
    "-u",
    "--update-upstream",
    action="store_true",
    default=False,
    dest="update_karrot",
    help="pull new upstream locale versions from github",
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

upstream_url = "https://raw.githubusercontent.com/yunity/karrot-frontend/master/src/locales/{}"
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


# requirements
script_dir = os.path.dirname(os.path.realpath(__file__))
karrot_dir = os.path.join(script_dir, 'upstream')
weblate_dir = os.path.join(script_dir, 'translate')
project_dir = os.path.join(script_dir, 'project')

for this_dir in [karrot_dir, weblate_dir, project_dir]:
    if not os.path.isdir(this_dir):
        os.mkdir(this_dir)
    assert os.path.isdir(this_dir), "Please create {}".format(this_dir)


def _p(filename):
    # create a printable version of a filepath+name
    return os.path.relpath(filename, script_dir)


def get_file(lang_code, this_url, out_dir):
    file_name = "locale-{}.json".format(lang_code)
    print("Updating {}".format(_p(file_name)))
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


def merge_dict(base_content, head_content, keep, weblate_en, karrot_en, branch_func, leaf_func):
    for k,v in head_content.items():
        if isinstance(v, str):
            keep[k] = leaf_func(base_content, head_content, k, v, weblate_en, karrot_en)
        if isinstance(v, dict):
            if k in weblate_en:
                this_weblate_content = weblate_en[k]
            else:
                this_weblate_content = {}
            if k in karrot_en:
                this_karrot_content = karrot_en[k]
            else:
                this_karrot_content = {}
            new_dict = merge_dict(base_content[k], v, base_content[k], this_weblate_content, this_karrot_content, branch_func, leaf_func)
            # i am replacing values, I'll strip out empty dicts later on
            keep[k] = branch_func(new_dict)
    return keep


def make_suggestions(base_content, head_content, weblate_en, karrot_en, keep):
    # traverse the keys in weblate_en and check wether
    for k,v in weblate_en.items():
        if isinstance(v, str):
            if k in head_content:
                # a value exists in head_file (the diff), if yes, take it
                keep[k] = head_content[k]
            elif k in base_content and base_content[k] != karrot_en[k]:
                # if not, check if one exists in karrot's file that is different to karrot's english default
                # this will give us the french suggestion if it exists, but will use the project's locale if not
                keep[k] = base_content[k]
            else:
                # just keep the existing value from weblate_en
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
            keep[k] = make_suggestions(this_base_content, this_head_content, v, karrot_en[k], v)
    return keep


def create_diff(karrot_file, weblate_file, diff_file, weblate_en, karrot_en):
    print("Init diff in {}".format(_p(diff_file)))
    with open(karrot_file, 'r', encoding='utf8') as karrot_fh:
        karrot_content = json.load(karrot_fh)
    # if the diff doesn't exist yet, we are copying karrot's to make suggestions
    if not os.path.isfile(weblate_file):
        shutil.copyfile(karrot_file, weblate_file)
    with open(weblate_file, 'r', encoding='utf8') as weblate_fh:
        weblate_content = json.load(weblate_fh)
    suggestions_content = make_suggestions(karrot_content, weblate_content, weblate_en, karrot_en, {})
    with open(diff_file, 'w', encoding='utf8') as result_fh:
        json.dump(suggestions_content, result_fh, indent=4, ensure_ascii=False)
    return True


def init_diff():
    print("Running init …")

    karrot_filename = os.path.join(karrot_dir, 'locale-en.json')

    if not os.path.isfile(karrot_filename):
        print("Please pull new karrot locales with -u/--update-upstream")
        return True

    weblate_init_filename = os.path.join(weblate_dir, 'init.json')
    diff_filename = os.path.join(weblate_dir, 'locale-en.json')
    if not (os.path.isfile(weblate_init_filename) and os.path.isfile(diff_filename)):
        print("Copying {} to {}".format(_p(karrot_filename), _p(weblate_init_filename)))
        shutil.copyfile(karrot_filename, weblate_init_filename)
        print("Edit {} now and re-run init to generate the first diff".format(_p(weblate_init_filename)))
        return True

    if not os.path.isfile(diff_filename):
        print("Creating diff of {} and {}".format(_p(weblate_init_filename), _p(karrot_filename)))
        keep_diff(karrot_filename, weblate_init_filename, diff_filename)
        print("You might want to check {} now and re-run init".format(_p(diff_filename)))
        return True

    print("Initing diffs based on keys in {} and content locales in {}".format(_p(diff_filename), karrot_dir))

    with open(diff_filename, 'r', encoding='utf8') as weblate_fh:
        weblate_en = json.load(weblate_fh)
    with open(karrot_filename, 'r', encoding='utf8') as karrot_fh:
        karrot_en = json.load(karrot_fh)

    for base_file in glob.glob(os.path.join(karrot_dir, 'locale-*.json')):
        file_name = os.path.basename(base_file)
        diff_file = os.path.join(weblate_dir, file_name)
        head_file = os.path.join(weblate_dir, file_name)
        create_diff(base_file, head_file, diff_file, weblate_en, karrot_en)
    print("You can upload the diff files to your translation interface now.")


def keep_diff(base_file, head_file, diff_file):
    # create the difference between the head file and the base file and write it to diff file
    # this is useful if karrot updated it's translations

    def _diff_content_f(base_content, k, v):
        if k not in base_content:
            return False
        return base_content[k] != v

    def _branch_func(new_dict):
        # only append non-empty dicts
        return len(new_dict) > 0

    print("Writing diff to {}".format(_p(diff_file)))
    with open(base_file, 'r', encoding='utf8') as base_fh:
        base_content = json.load(base_fh)
    with open(head_file, 'r', encoding='utf8') as head_fh:
        head_content = json.load(head_fh)
    diffed_content = filter_dict(base_content, head_content, {}, _branch_func, _diff_content_f, False)
    with open(diff_file, 'w', encoding='utf8') as result_fh:
        json.dump(diffed_content, result_fh, indent=4, ensure_ascii=False)
    return True


def merge_file(karrot_file, weblate_file, result_file, weblate_en, karrot_en):
    print("Merging {} over {}".format(_p(weblate_file), _p(karrot_file)))

    def _merge_overwrite_f(karrot_file, weblate_file, k_weblate, v_weblate, weblate_en, karrot_en):
        # the text is equal to karrot's default english value
        if v_weblate == karrot_en[k_weblate]:
            # if there is an edited value for that key, return that value
            if k_weblate in weblate_en:
                return weblate_en[k_weblate]
            # if there is no edited value, return karrot's value
            else:
                return v_weblate
        # the value is equal to karrot's value but it is not english
        # (e.g. someone translated karrot's value to french, but not ours)
        elif v_weblate == karrot_file[k_weblate]:
            # this is always the case
            if v_weblate in weblate_en:
                # return our english default value
                return weblate_en[k_weblate]
            else:
                # return karrot's translation
                return karrot_file[k_weblate]
        # simply return the value if it just works
        return v_weblate

    def _branch_func(new_dict):
        # overwrite everything that is defined
        return new_dict

    # requirements
    if not os.path.isfile(weblate_file):
        print("Warning: {} does not exist, copying {}".format(_p(weblate_file), _p(karrot_file)))
        weblate_file = karrot_file
    # open
    with open(karrot_file, 'r', encoding='utf8') as karrot_fh:
        karrot_content = json.load(karrot_fh)
    with open(weblate_file, 'r', encoding='utf8') as weblate_fh:
        weblate_content = json.load(weblate_fh)
    # merge the already existing base_content with the new head_content
    merged_content = merge_dict(karrot_content, weblate_content, karrot_content, weblate_en, karrot_en, _branch_func, _merge_overwrite_f)
    with open(result_file, 'w', encoding='utf8') as result_fh:
        json.dump(merged_content, result_fh, indent=4, ensure_ascii=False)
    return True


def merge_diff():
    print("Merging locales cleverly from {} and {} into {}".format(_p(karrot_dir), _p(weblate_dir), _p(project_dir)))
    karrot_filename = os.path.join(karrot_dir, 'locale-en.json')
    with open(karrot_filename, 'r', encoding='utf8') as karrot_fh:
        karrot_en = json.load(karrot_fh)
    weblate_file = os.path.join(weblate_dir, 'locale-en.json')
    with open(weblate_file, 'r', encoding='utf8') as weblate_fh:
        weblate_en = json.load(weblate_fh)
    for karrot_file in glob.glob(os.path.join(karrot_dir, 'locale-*.json')):
        file_name = os.path.basename(karrot_file)
        weblate_file = os.path.join(weblate_dir, file_name)
        result_file = os.path.join(project_dir, file_name)
        merge_file(karrot_file, weblate_file, result_file, weblate_en, karrot_en)


def update_karrot():
    print("Updating karrot locales")
    this_url = upstream_url
    out_dir = karrot_dir
    for lang_code in LANG_CODES:
        get_file(lang_code, this_url, out_dir)
    return True


def main():

    if args.update_karrot:
        update_karrot()

    if args.update_project:
        print("Updating project locales")
        raise NotImplementedError

    if args.init_diff:
        init_diff()

    if args.merge_diff:
        merge_diff()


if __name__ == "__main__":
    main()

