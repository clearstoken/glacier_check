# -*- coding: utf-8 -*-

"""Main module."""

import json
import pprint
import os
from tqdm import tqdm

from botocore.utils import calculate_tree_hash
from datetime import datetime

REMOTE_INVENTORY_FILENAME = 'remote-inventory.json'

LOCAL_INVENTORY_FILENAME = 'local-inventory.json'

CHECK_RECEIPT_FILENAME = 'check-receipt.json'

EXCLUDE_FILENAMES = [
        REMOTE_INVENTORY_FILENAME,
        LOCAL_INVENTORY_FILENAME,
        CHECK_RECEIPT_FILENAME
    ]

def get_valid_files(local_dir):
    """Return a list of filenames of files contained in the local directory."""
    res = [
            f for f in os.listdir(local_dir)
            if (
                    os.path.isfile(os.path.join(local_dir, f))
                    and f not in EXCLUDE_FILENAMES
                )
        ]

    return res

def load_inventory(local_dir, filename):
    """Load the inventory stored as a json file in the local directory.
    If the inventory json file is not present, an empty inventory is returned."""

    try:
        with open(os.path.join(local_dir, filename), 'r') as inv_file:
            data = json.load(inv_file)
    except (IOError, ValueError):
        data = {'ArchiveList': [] }

    return data

def dictify_inventory(inventory):
    return {
            entry['ArchiveDescription'] : entry['SHA256TreeHash']
            for entry in inventory['ArchiveList']
        }

def update_local_inventory(local_dir, local_filenames, old_local_inventory):
    """Update the local inventory stored as a json file in the local directory.
    The updated local inventory is returned."""

    archive_list = list()

    old_local_inventory_dict = dictify_inventory(old_local_inventory)

    for f in tqdm(local_filenames):
        if f in old_local_inventory_dict:
            checksum = old_local_inventory_dict[f]
        else:
            with open(os.path.join(local_dir, f), 'rb') as target_file:
                checksum = calculate_tree_hash(target_file)

        archive_list.append({
                "ArchiveDescription" : f,
                "CreationDate" : datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "SHA256TreeHash" : checksum
            })

    res = {"ArchiveList" : archive_list}

    return res

def check_missing_files(from_inventory, against_inventory):
    """Compare the from_inventory to the against_inventory to check for missing files in the from_inventory.
    Filenames missing from the from_inventory are returned in a list.
    If no missing files are found, an empty list is returned."""

    from_inventory_dict = dictify_inventory(from_inventory)
    against_inventory_dict = dictify_inventory(against_inventory)

    res = [
            k for k in against_inventory_dict.keys()
            if k not in from_inventory_dict
        ]

    return res

def check_mismatched_files(local_inventory, remote_inventory):
    """Compare checksums of files present in both inventories.
    Filenames with mismatched checksums are returned in a list.
    If no missing files are found, an empty list is returned."""

    local_inventory_dict = dictify_inventory(local_inventory)
    remote_inventory_dict = dictify_inventory(remote_inventory)

    intersect = local_inventory_dict.keys() & remote_inventory_dict.keys()

    res = [
            k for k in intersect
            if local_inventory_dict[k] != remote_inventory_dict[k]
        ]

    return res

def generate_check_receipt(
        local_dir,
        missing_local_files,
        missing_remote_files,
        mismatched_files
    ):
    """Generate a check_receipt that records the local_dir, missing_local_files, missing_remote_files, mismatched_files, and a timestamp."""
    res = {
            'local_dir' : os.path.abspath(local_dir),
            'missing_local_files' : missing_local_files,
            'missing_remote_files' : missing_remote_files,
            'mismatched_files' : mismatched_files,
            'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    return res

def save_check_receipt(local_dir, check_receipt):
    """Save the check_receipt to the local_dir as a json file."""

    with open(os.path.join(local_dir, CHECK_RECEIPT_FILENAME), 'w') as outfile:
        json.dump(check_receipt, outfile)

def print_check_receipt(check_receipt):
    """Print the generated check receipt to the console."""
    print(json.dumps(check_receipt, indent=2))

def print_check_receipt_hints(check_receipt):
    """If mismatched or missing files, provide hints describing what might be causing the problems (and how to fix them).
    Hints are printed to the console."""

    if (
            check_receipt['missing_local_files'] or
            check_receipt['missing_remote_files'] or
            check_receipt['mismatched_files']
        ):
        print("uh-oh... you have a problem! Here are some hints...")

    else:
        print("looks good!")

    if check_receipt['missing_local_files']:
        print("There is a file present in your remote inventory that is missing from your local directory. "
        "If you moved it or deleted it unintentionally, put it back. "
        "If you intentionally deleted it, delete the corresponding archive from glacier."
        )

    if check_receipt['missing_remote_files']:
        print("There is a file present in your local inventory that is missing from your remote directory. "
        "If you haven't sent the missing file to glacier yet, then upload it. "
        "If you have uploaded the file, then you need to get an updated remote inventory. "
        "If you are using an updated remote inventory, try uploading the file again. "
        "Make sure that you didn't accidentally upload the file to an incorrectly named archive."
        )

    if check_receipt['mismatched_files']:
        print("There is a checksum mismatch between a local file and a remote archive. "
        "Perhaps you uploaded files to an incorrectly named archive. "
        "Otherwise, your local data or your remote data is corrupted."
        )
