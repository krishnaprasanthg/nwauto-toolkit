import asyncio
from scrapli.driver.core import (
    AsyncIOSXEDriver,
    AsyncNXOSDriver,
    AsyncJunosDriver,
    AsyncIOSXRDriver,
    AsyncEOSDriver,
)
import click
import getpass
from rich import print
from time import time
from math import floor
from os.path import isfile

from asyncio.exceptions import TimeoutError
from scrapli.exceptions import ScrapliAuthenticationFailed, ScrapliTimeout

DRIVER_MAP = {
    "ios": AsyncIOSXEDriver,
    "junos": AsyncJunosDriver,
    "eos": AsyncEOSDriver,
    "nxos": AsyncNXOSDriver,
    "iosxr": AsyncIOSXRDriver,
}


async def configure_device(device, cfg_file, os_type):

    conn = DRIVER_MAP[os_type](**device)
    try:
        await conn.open()
    except TimeoutError:
        return device["host"], "[red]Connection failed[/red]"
    except ScrapliAuthenticationFailed:
        return device["host"], "[red]Authentication failed. Check the credentials[/red]"
    except ScrapliTimeout:
        return (
            device["host"],
            "[red]Connection failed. Timeout. Verify if the OS_TYPE argument passed. [/red]",
        )

    print(f"Connection successful to {device['host']}")
    prompt_result = await conn.get_prompt()
    output = await conn.send_configs_from_file(file=cfg_file, stop_on_failed=True)
    if output.failed == True:
        print(
            f"[red]Failed to configure the device {device['host']}. Skipping write[/red]"
        )
    else:
        print(f"Configured the device {device['host']}")
        save_result = await conn.send_command(f"copy running-config startup-config")
        print(
            f"[yellow]Saving configuration for device: {device['host']} {save_result.result}[/yellow]"
        )
    await conn.close()
    if len(output.result):
        return prompt_result, output
    else:
        return prompt_result, "empty response"


async def runner(DEVICES, CFG_FILE, OS_TYPE):
    coroutines = [configure_device(device, CFG_FILE, OS_TYPE) for device in DEVICES]
    results = await asyncio.gather(*coroutines)
    for result in results:
        print("=" * 50)
        print(f"[green]>>>> device: [bold]{result[0]}[/bold][/green]")
        print("=" * 50)
        results = [
            res.channel_input
            if not res.failed
            else "[red]"
            + str(res.channel_input)
            + "\n"
            + str(res.raw_result)
            + "[/red]"
            for res in result[1]
        ]
        for res in results:
            print(res)
        print("-" * 50)


@click.command()
@click.option(
    "--device_list",
    help=".txt file with list of devices",
)
@click.option(
    "--config_file",
    help=".txt file with list of configuration commands",
)
@click.option(
    "--os_type",
    "-t",
    default="ios",
    help="choose from nxos, ios, junos, iosxr, eos. Default is ios",
)
@click.option(
    "--device",
    "-d",
    multiple=True,
    help="ip or dns of the device, chain it for multiple devices ",
)
def main(device_list, device, os_type, config_file):

    if not isfile(path=config_file):
        print("provide the config file. See HELP.. ")
        exit()
    devices = []
    if device_list:
        with open(device_list, "r") as f:
            output = f.readlines()
        devices = [device.strip() for device in output]
    else:
        if device:
            devices.extend(list(device))

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
                "transport": "asyncssh",
            }
            for device in devices
        ]
        start_time = time()
        asyncio.run(runner(devices_dict, config_file, os_type))

        end_time = time()
        time_taken = (end_time - start_time) / 60
        minutes = floor(time_taken)
        seconds = floor((time_taken % 1) * 60)
        print(
            f"[green]Time taken:[/green] [blue]{minutes:02d}:{seconds:02d} minutes[/blue]"
        )
    else:
        print("no device inputs passed!!! ")


if __name__ == "__main__":
    main()
