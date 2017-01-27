#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import sys
import json
import argparse

# TODO: Variabalize the paths here

output_json_file = open('output/printer-queues.json', 'w+')
input_python_template = open('source/printer-installer.source.py', 'r')
output_script = open('output/printer-installer.py', 'w+')

def build_argparser():
    """Creates the argument parser"""
    parser = argparse.ArgumentParser(
        description=("Takes an input CSV of printer queues and converts the "
                     "list to a JSON document, then injects the JSON into "
                     "the Python template.")
    )

    parser.add_argument("infile",
                        type=argparse.FileType("r"),
                        help="Path to input CSV file of printer queues")
    parser.add_argument("exclude",
                        nargs="?",
                        type=argparse.FileType("r"),
                        help="Path to optional exclusions file")

    args = parser.parse_args()
    return args.infile, args.exclude


def main():
    # Grab the passed arguments
    infile, exclude = build_argparser()

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
                opts = dict(item.split('=') for item in line['Options'].split(','))
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
    output_script.write(template.format(placeholder=json_data))
    output_script.close()

    print "Done."


if __name__ == '__main__':
    main()
