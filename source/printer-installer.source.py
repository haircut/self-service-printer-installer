#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import syslog
import os
import subprocess
import json

__version__ = "0.0.0"


###############################################################################
# Configuration
###############################################################################


# cocoaDialog Trigger
# A custom trigger used to install cocoaDialog via JAMF policy if not found
# on the client system. See docs for "Resolving cocoaDialog Dependency"
cocoaDialog_trigger = "InstallcocoaDialog"

# GUI - Window Titles
# The title for all GUI windows
gui_window_title = "Printer Installer"

# GUI - Undefined error message
# Shown when the installation process fails for unknown reasons
msg_undefined_error = ("An error occured; please contact your support team "
                       "for assistance.")


###############################################################################
# Configuration
###############################################################################


global CDPATH
CDPATH = ("/Applications/cocoaDialog.app/Contents/MacOS/cocoaDialog")

# Branding icon
BRANDICON = ("/System/Library/CoreServices/Certificate Assistant.app/Contents/"
             "Resources/AppIcon.icns")
# Printer icon
PRINTERICON = ("System/Library/CoreServices/AddPrinter.app/Contents/Resources/"
               "Printer.icns")

# Path to JAMF binary
global JAMF
JAMF = "/usr/local/bin/jamf"


###############################################################################
# Queue Definitions
###############################################################################

json_definitions = \
"""
{placeholder}
"""

queue_definitions = json.loads(json_definitions)

###############################################################################
# Program Logic - Here be dragons!
###############################################################################


class Logger(object):
    """Super simple logging class"""
    def log(self, message, log_level=syslog.LOG_ALERT):
        """Log to the syslog and stdout"""
        syslog.syslog(log_level, "PRINTMAPPER: " + message)
        print message


# Initialize Logger
Logger = Logger()


def parse_args(args):
    """
    Parses passed arguments and returns a their values as named variables if
    those arguments are provided.
    """

    preselected_queue = None
    filter_key = None
    filter_value = None

    if len(args) > 4:
        try:
            if args[4]:
                preselected_queue = args[4]
        except:
            pass
        try:
            if args[5]:
                filter_key = args[5]
        except:
            pass
        try:
            if args[6]:
                filter_value = args[6]
        except:
            pass

    return preselected_queue, filter_key, filter_value


def show_message(message_text, heading=gui_window_title):
    """Displays a message to the user via cocoaDialog"""
    showit = subprocess.Popen([CDPATH,
                               'ok-msgbox',
                               '--title', gui_window_title,
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
        show_message(msg_undefined_error, "Error")
    Logger.log("An error occurred which requires exiting this program.")
    exit()


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
        return run_jamf_policy(cocoaDialog_trigger, True)
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
        if not (values['DisplayName'] in current_queues or
                    values['CUPSName'] in current_queues):
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
        show_message("All available print queues are already mapped to this "
                     "computer. Please contact ITS if you need further "
                     "assistance.")
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
            show_message("A driver is required for full control of this "
                         "printer, but an error occurred when attempting to "
                         "install the software. Please contact ITS for "
                         "assistance.")
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
        q_driver = ("/System/Library/Frameworks/ApplicationServices.framework"
                    "/Versions/A/Frameworks/PrintCore.framework/Versions/A/"
                    "Resources/Generic.ppd")

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
        show_message("The printer queue '" + q['DisplayName'] + "' was "
                     "successfully added. You should now be able to send "
                     "jobs to this printer.", "Success!")
        quit()
    except subprocess.CalledProcessError as e:
        Logger.log('There was a problem mapping the queue!')
        Logger.log('Attempted command: ' + ' '.join(cmd))
        show_message("There was a problem mapping the printer queue – please "
                     "try again. If the problem persists, contact ITS for "
                     "further assistance.")
        quit()


def main():
    preselected_queue, filter_key, filter_value = parse_args(sys.argv)
    # Build list of currently mapped queues on client
    currently_mapped_queues = get_currently_mapped_queues()
    # Build list of available queues excluding currently-mapped queues
    available_queues = build_printer_queue_list(currently_mapped_queues,
                                                filter_key, filter_value)

    # Determine if a pre-selected print queue was passed

    if preselected_queue:
        # Ensure pre-selected queue is actually available
        if preselected_queue in available_queues:
            selected_queue = preselected_queue
        else:
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
