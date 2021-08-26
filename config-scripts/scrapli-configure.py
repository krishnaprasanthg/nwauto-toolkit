import concurrent.futures
import getpass
import sys
from math import floor
from os.path import isfile
from time import time

import click
from rich import print
from scrapli.driver.core import (
    EOSDriver,
    IOSXEDriver,
    IOSXRDriver,
    JunosDriver,
    NXOSDriver,
)

DRIVER_MAP = {
    "ios": IOSXEDriver,
    "eos": EOSDriver,
    "nxos": NXOSDriver,
    "iosxr": IOSXRDriver,
    "junos": JunosDriver,
}
SAVE_COMMAND = {
    "ios": "copy running-config startup-config",
    "eos": "copy running-config startup-config",
    "nxos": "copy running-config startup-config",
    "iosxr": "copy running-config startup-config",
    "junos": "commit",
}


def device_handler(device, os_type, config_list):
    success = False
    print(f"handling device {device['host']}")
    config_list.append("!")

    try:
        with DRIVER_MAP[os_type](**device) as conn:
            print(f"connected to device {device['host']}")
            response = conn.send_configs(configs=config_list, stop_on_failed=True)
            if not len(response) == len(config_list):
                success = False
                result = response[-1].channel_input + " - " + response[-1].result
            else:
                success = True
                # save config per device type
                conn.send_command(str(SAVE_COMMAND[os_type]))
                print(f"Saved configuration to {device['host']}")
                result = "Success"
    except Exception as e:
        result = e
        print(f"Error - {e}")
    return (device, success, result)


@click.command()
@click.option(
    "--device",
    "-d",
    multiple=True,
    help="ip or dns of the device, chain it for multiple devices ",
)
def main(device):
    config_file = click.prompt("Provide the configuration file", default="config.txt")
    devices = []
    if device:
        devices.extend(list(device))
    else:
        device_list = click.prompt(
            "Provide the file with list of devices", default="devices.txt"
        )
        if not isfile(path=device_list):
            print("provide the list of devices. See HELP.. ")
            sys.exit()
        with open(device_list, "r") as f:
            output = f.readlines()
            devices = [device.strip() for device in output]
    num_workers = click.prompt("Enter the number of workers", default=40)
    os_type = click.prompt(
        "Provide the device OS", type=click.Choice(DRIVER_MAP.keys()), default="ios"
    )

    if not isfile(path=config_file):
        print("provide the config file. See HELP.. ")
        sys.exit()

    config = []
    with open(config_file, "r") as f:
        output = f.readlines()
        config = [config_line.strip() for config_line in output]

    if len(devices):

        # get credentials
        username = input("Username: ")
        password = getpass.getpass("Password: ")

        devices_dict = [
            {
                "host": device,
                "auth_username": f"{username}",
                "auth_password": f"{password}",
                "auth_strict_key": False,
                "transport": "ssh2",
            }
            for device in devices
        ]
        start_time = time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            results = []
            processed = 0
            total = len(devices)

            print(f"Executing against {total} devices with {num_workers} workers.")

            futures = {
                executor.submit(device_handler, device, os_type, config)
                for device in devices_dict
            }

            # Wait for the futures to complete and give status updates
            try:
                for future in concurrent.futures.as_completed(futures):
                    processed += 1
                    percent = round((processed / total) * 100)
                    print(f"{processed} of {total} ({percent}%) devices processed.")
            except (SystemExit, KeyboardInterrupt) as e:
                if isinstance(e, KeyboardInterrupt):
                    print("===============================================")
                    print("         Keyboard interrupt detected           ")
                    print("                                               ")
                    print("        Cancelling remaining devices           ")
                    print("  Currently executing devices remain running   ")
                    print("===============================================")
                # Cancel remaining work
                for f in futures:
                    f.cancel()
                executor.shutdown(wait=False)
                # System exits will be raised again so the code calling this function
                # also exits
                if isinstance(e, SystemExit):
                    raise
            print("Collecting results")
            for f in futures:
                try:
                    results.append(f.result())
                except concurrent.futures.CancelledError:
                    print("Skipping cancelled device")
        end_time = time()
        time_taken = (end_time - start_time) / 60
        minutes = floor(time_taken)
        seconds = floor((time_taken % 1) * 60)
        print(
            f"[green]Time taken:[/green] [blue]{minutes:02d}:{seconds:02d} minutes[/blue]"
        )
        for result in results:
            device, success, result = result
            print(f"{device['host']} --> {success} -> {result}")
    else:
        print("no device inputs passed!!! ")


if __name__ == "__main__":
    main()
