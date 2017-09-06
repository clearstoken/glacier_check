# -*- coding: utf-8 -*-

"""Console script for glacier_check."""

import click

import os
import json

from glacier_check.glacier_check import (
        get_valid_files,
        load_inventory,
        dictify_inventory,
        update_local_inventory,
        check_missing_files,
        check_mismatched_files,
        generate_check_receipt,
        save_check_receipt,
        print_check_receipt,
        print_check_receipt_hints,
        LOCAL_INVENTORY_FILENAME,
        REMOTE_INVENTORY_FILENAME,
    )

@click.command()
@click.option(
        '--verbose/--silent',
        default=True,
        help="Will print check receipt to console."
    )
@click.option(
        '--deep/--no-deep',
        default=False,
        help="Will recalculate checksums for "
            "previously encountered local files."
    )
@click.argument('local_dir')
def main(deep, verbose, local_dir, args=None):
    """Console script for glacier_check."""

    if deep:
        os.remove(os.path.join(local_dir, LOCAL_INVENTORY_FILENAME))

    old_local_inventory = load_inventory(local_dir, LOCAL_INVENTORY_FILENAME)
    valid_filenames = get_valid_files(local_dir)
    local_inventory = update_local_inventory(
            local_dir,
            valid_filenames,
            old_local_inventory
        )
    with open(os.path.join(local_dir, LOCAL_INVENTORY_FILENAME), 'w') as outfile:
        json.dump(local_inventory, outfile)

    remote_inventory = load_inventory(local_dir, REMOTE_INVENTORY_FILENAME)

    missing_local_files = check_missing_files(local_inventory, remote_inventory)

    missing_remote_files = check_missing_files(remote_inventory, local_inventory)

    mismatched_files = check_mismatched_files(local_inventory, remote_inventory)

    check_receipt = generate_check_receipt(
            local_dir,
            missing_local_files,
            missing_remote_files,
            mismatched_files
        )

    save_check_receipt(local_dir, check_receipt)

    if verbose:
        print_check_receipt(check_receipt)
        print_check_receipt_hints(check_receipt)


if __name__ == "__main__":
    main()
