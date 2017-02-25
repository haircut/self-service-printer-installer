#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
self-service-printer-installer

See the wiki! https://github.com/haircut/self-service-printer-installer/wiki
"""

import sys
import syslog
import os
import subprocess
import json
import argparse

__version__ = "0.1.5"

BRANDICON = "{config[gui][brand_icon]}" # pylint: disable=line-too-long
PRINTERICON = "{config[gui][printer_icon]}" # pylint: disable=line-too-long

# Path to JAMF binary
JAMF = "/usr/local/bin/jamf"
CDPATH = "{config[cocoaDialog][path]}" # pylint: disable=line-too-long


###############################################################################
# Queue Definitions
###############################################################################

json_definitions = \
"""
{queues}
"""

queue_definitions = json.loads(json_definitions)

###############################################################################
# Program Logic - Here be dragons!
###############################################################################


class Logger(object):
    """Super simple logging class"""
    @classmethod
    def log(self, message, log_level=syslog.LOG_ALERT):
        """Log to the syslog and stdout"""
        syslog.syslog(log_level, "PRINTMAPPER: " + message)
        print message


# Initialize Logger
Logger = Logger()


def parse_args():
    """Set up argument parser"""
    parser = argparse.ArgumentParser(
        description=("Maps or 'installs' a printer queue after displaying "
                     "a list of available printer queues to the user. "
                     "Can specify a preselected_queue as argument 4, a filter "
                     "key as argument 5, and a filter value as arugment 6.")
    )
    parser.add_argument("jamf_mount", type=str, nargs='?',
                        help="JAMF-passed target drive mount point")
    parser.add_argument("jamf_hostname", type=str, nargs='?',
                        help="JAMF-passed computer hostname")
    parser.add_argument("jamf_user", type=str, nargs='?',
                        help="JAMF-passed name of user running policy")
    parser.add_argument("preselected_queue", type=str, nargs='?',
                        help="DisplayName of an available queue to map "
                             "without prompting user for selection")
    parser.add_argument("filter_key", type=str, nargs='?',
                        help="Field name of an attribute which you would "
                             "like to filter the available queues base upon")
    parser.add_argument("filter_value", type=str, nargs='?',
                        help="Value to search the provided filter_key "
                             "attribute for")

    return parser


def show_message(message_text, heading="{config[gui][window_title]}"):
    """Displays a message to the user via cocoaDialog"""
    showit = subprocess.Popen([CDPATH,
                               'ok-msgbox',
                               '--title', "{config[gui][window_title]}",
                               '--text', heading,
                               '--informative-text', message_text,
                               '--icon-file', BRANDICON,
                               '--float', '--no-cancel'])
    message_return, error = showit.communicate()
    return True


def error_and_exit(no_cocoaDialog=False):
    """
    Display a generic error message (if cocoaDialog is installed) then quit
    the program.
    """
    if not no_cocoaDialog:
        show_message("{config[gui][messages][error_undefined]}", "Error") # pylint: disable=line-too-long
    Logger.log("An error occurred which requires exiting this program.")
    sys.exit(1)


def run_jamf_policy(trigger, quiet=False):
    """Runs a jamf policy given the provided trigger"""
    if not quiet:
        progress_bar = subprocess.Popen([CDPATH, 'progressbar',
                                         '--title', 'Please wait...',
                                         '--text', 'Installing software...',
                                         '--float', '--indeterminate'],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

    jamf_policy = subprocess.Popen([JAMF, 'policy', '-event', trigger],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

    policy_return, error = jamf_policy.communicate()

    if not quiet:
        progress_bar.terminate()

    if "No policies were found for the" in policy_return:
        Logger.log("Unable to run JAMF policy via trigger " + trigger)
        return False
    elif "Submitting log to" in policy_return:
        Logger.log("Successfully ran JAMF policy via trigger " + trigger)
        return True


def check_for_cocoadialog():
    """
    Checks for the existence of cocoaDialog at the specified path. If it's not
    there, install it via the specified policy trigger.
    """
    if not os.path.exists(CDPATH):
        return run_jamf_policy("{config[cocoaDialog][install_trigger]}", True)
    else:
        return True


def get_currently_mapped_queues():
    """Return a list of print queues currently mapped on the system"""
    try:
        Logger.log('Gathering list of currently mappped queues')
        lpstat_result = subprocess.check_output(['/usr/bin/lpstat', '-p'])
    except subprocess.CalledProcessError as e:
        Logger.log('No current print queues found')
        lpstat_result = None

    current_queues = []
    if lpstat_result:
        for line in lpstat_result.splitlines():
            current_queues.append(line.split()[1])

    return current_queues


def build_printer_queue_list(current_queues, filter_key, filter_value):
    """Builds a list of available print queues for GUI presentation"""
    display_list = []
    for queue, values in queue_definitions.items():

        valid_queue = False
        if not values['DisplayName'] in current_queues:
            # If the CUPSName field is present check for its value among
            # mapped queues
            if 'CUPSName' in values:
                if values['CUPSName'] not in current_queues:
                    valid_queue = True
            else:
                valid_queue = True


        if valid_queue:
            # Queue is available but not currently mapped
            if filter_key and values.get(filter_key):
                # Filter is applied, and the passed key exists in the queue
                # definitions, so check for match condition
                if filter_value in values[filter_key]:
                    # Match condition met, so add queue to list
                    display_list.append(values['DisplayName'])
                # Implicit else of condition not met, do not add queue to list
            elif not filter_key:
                # No filter applied, so just add the queue to the list
                display_list.append(values['DisplayName'])

    if len(display_list) >= 1:
        return sorted(display_list)
    else:
        Logger.log("No currently-unmapped queues are available")
        show_message("{config[gui][messages][error_no_queues_available]}") # pylint: disable=line-too-long
        quit()


def prompt_queue(list_of_queues):
    """Prompts the user to select a queue name"""
    Logger.log('Prompting user to select desired queue')
    queue_dialog = subprocess.Popen([CDPATH, 'dropdown', '--string-output',
                                     '--float', '--icon', 'gear',
                                     '--title', 'Select Print Queue',
                                     '--text', ('Choose a print queue to '
                                                'add to your computer:'),
                                     '--button1', 'Add',
                                     '--button2', 'Cancel',
                                     '--items'] + list_of_queues,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
    prompt_return, error = queue_dialog.communicate()
    if not prompt_return == "Cancel\n":
        selected_queue = prompt_return.splitlines()[1]
        Logger.log('User selected queue ' + selected_queue)
        return selected_queue
    else:
        Logger.log('User canceled queue selection')
        return False


def install_drivers(trigger):
    """Installs required drivers via JAMF policy given a trigger value"""
    Logger.log("Attempting to install drivers via policy trigger " + trigger)

    if not run_jamf_policy(trigger):
        return False
    else:
        return True


def search_for_driver(driver, trigger):
    """Searches the system for the appropriate driver and if not found,
       attempts to install it via JAMF policy"""
    if not os.path.exists(driver):
        Logger.log("The driver was not found at " + driver)
        if not install_drivers(trigger):
            show_message("{config[gui][messages][error_driver_failure]}") # pylint: disable=line-too-long
            Logger.log('Quitting program')
            quit()


def add_queue(queue):
    # Reference the queue dictionary by name
    q = queue_definitions[queue]

    # Determine whether we need to handle custom drivers
    # By convention, a driver path only appears in the queue dict if a custom
    # driver is required. Queues using the generic postscript driver have this
    # dict attribute set to "None" so we can test for truth
    if q['Driver']:
        Logger.log("Queue " + q['DisplayName'] + " requires a vendor driver")
        search_for_driver(q['Driver'], q['DriverTrigger'])
        q_driver = q['Driver']
    else:
        Logger.log(q['DisplayName'] + " uses a generic driver")
        # Specify the path to the default postscript drivers
        q_driver = "{config[default_driver]}" # pylint: disable=line-too-long

    # Common command
    cmd = ['/usr/sbin/lpadmin',
           '-p', q['DisplayName'],
           '-L', q['Location'],
           '-E',
           '-v', q['URI'],
           '-P', q_driver]

    # Determine Options
    if q['Options']:
        options = []
        for key, val in q['Options'].iteritems():
            options.append('-o')
            options.append(key + '=' + val)
        cmd = cmd + options

    mapq = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=False)
    try:
        map_return, error = mapq.communicate()
        Logger.log("Excuting command: " + ' '.join(cmd))
        Logger.log("Queue " + q['DisplayName'] + " successfully mapped")
        show_message(("{config[gui][messages][success_queue_added]}" # pylint: disable=line-too-long
                      % q['DisplayName']), "Success!")
        quit()
    except subprocess.CalledProcessError as e:
        Logger.log('There was a problem mapping the queue!')
        Logger.log('Attempted command: ' + ' '.join(cmd))
        show_message("{config[gui][messages][error_unable_map_queue]}")# pylint: disable=line-too-long
        quit()


def main():
    """Manage arguments and run workflow"""
    # Parse command line / JAMF-passed arguments
    parser = parse_args()
    # parse_known_args() works around potentially empty arguments passed by
    # a JAMF policy
    args = parser.parse_known_args()[0]

    # Build list of currently mapped queues on client
    currently_mapped_queues = get_currently_mapped_queues()
    # Build list of available queues excluding currently-mapped queues
    available_queues = build_printer_queue_list(currently_mapped_queues,
                                                args.filter_key,
                                                args.filter_value)

    # Determine if a pre-selected print queue was passed

    if args.preselected_queue:
        # Ensure pre-selected queue is actually available
        if args.preselected_queue in available_queues:
            selected_queue = args.preselected_queue
        else:
            show_message(("{config[gui][messages][error_preselected_queue]}")
                          % args.preselected_queue)
            error_and_exit()
    else:
        # Make sure cocoaDialog is installed
        if not check_for_cocoadialog():
            error_and_exit()

        # Prompt for a queue selection
        selected_queue = prompt_queue(available_queues)

    # Map the queue
    if selected_queue:
        add_queue(selected_queue)


if __name__ == '__main__':
    main()
