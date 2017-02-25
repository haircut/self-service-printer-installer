#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Self Service Printer Installer generator script

Assembles all the source files into a usable script
"""

import csv
import json
import argparse

def build_argparser():
    """Creates the argument parser"""
    parser = argparse.ArgumentParser(
        description=("Takes an input CSV of printer queues and converts the "
                     "list to a JSON document, then injects the JSON into "
                     "the Python template.")
    )
    parser.add_argument("config",
                        type=argparse.FileType("r"),
                        help="Path to JSON configuration file")
    parser.add_argument("infile",
                        type=argparse.FileType("r"),
                        help="Path to input CSV file of printer queues")
    parser.add_argument("exclude",
                        nargs="?",
                        type=argparse.FileType("r"),
                        help="Path to optional exclusions file")

    args = parser.parse_args()
    return args.config, args.infile, args.exclude


def main():
    """Main program"""
    # Grab the passed arguments
    config, infile, exclude = build_argparser()

    # Load the config
    cfg = json.loads(config.read())

    # Open file handles for needed i/o files
    output_json_file = open(cfg["generator"]["output_json_file"], 'w+')
    input_python_template = open(cfg["generator"]["input_python_template"], 'r')
    output_script = open(cfg["generator"]["output_script"], 'w+')

    # Split the exclusions, if they exist
    exclusions = []
    if exclude:
        exclusions = exclude.read().splitlines()

    # Process the CSV into a dictionary
    csv_data = csv.DictReader(infile)

    # Ensure required fields are present
    required_fields = ['DisplayName', 'URI', 'Driver', 'DriverTrigger',
                       'Location']
    present_fields = csv_data.fieldnames
    for required_field in required_fields:
        if required_field not in present_fields:
            print "Missing required CSV field: " + required_field
            quit()

    # Convert each row into a dictionary
    lines = {}
    for line in csv_data:
        if line['DisplayName'] not in exclusions:
            if line['Options']:
                opts = dict(item.split('=') for item in line['Options'].split(' '))
                line['Options'] = opts

            lines[line['DisplayName']] = line

    # Format the dictionary as JSON
    json_data = json.dumps(lines, sort_keys=False, indent=4,
                           separators=(',', ': '))

    # Write the JSON to file
    output_json_file.write(json_data)
    output_json_file.close()

    # Inject the JSON into the Python template
    template = input_python_template.read()
    output_script.write(template.format(queues=json_data, config=cfg))
    output_script.close()

    print "Done."


if __name__ == '__main__':
    main()
