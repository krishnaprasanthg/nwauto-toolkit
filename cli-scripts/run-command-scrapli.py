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

from asyncio.exceptions import TimeoutError
from scrapli.exceptions import ScrapliAuthenticationFailed

DRIVER_MAP = {
    "ios": AsyncIOSXEDriver,
    "junos": AsyncJunosDriver,
    "eos": AsyncEOSDriver,
    "nxos": AsyncNXOSDriver,
    "iosxr": AsyncIOSXRDriver,
}


async def get_command_device(device, command, os_type):

    conn = DRIVER_MAP[os_type](**device)
    try:
        await conn.open()
    except TimeoutError:
        return device["host"], "[red]Connection failed[/red]"
    except ScrapliAuthenticationFailed:
        return device["host"], "[red]Connection failed. Timeout[/red]"

    print(f"Connection successful to {device['host']}")
    prompt_result = await conn.get_prompt()
    output = await conn.send_command(f"{command}")
    await conn.close()
    print(f"Executed command for {device['host']}")
    if len(output.result):
        return prompt_result, output.result
    else:
        return prompt_result, "empty response"


async def runner(DEVICES, COMMAND, OS_TYPE):
    coroutines = [get_command_device(device, COMMAND, OS_TYPE) for device in DEVICES]
    results = await asyncio.gather(*coroutines)
    for result in results:
        print("=" * 50)
        print(
            f"[green]>>>> device: [bold]{result[0]}[/bold][/green] - [yellow]{COMMAND}[/yellow]"
        )
        print("=" * 50)
        print(f"{result[1]}")
        print("-" * 50)


@click.command()
@click.option(
    "--device_list",
    help="simple text file with list of devices",
)
@click.option(
    "--os_type",
    "-t",
    default="ios",
    help="choose from nxos, ios, junos, iosxr, eos",
)
@click.option(
    "--device",
    "-d",
    multiple=True,
    help="ip or dns of the device, can pass multiple",
)
@click.argument(
    "command",
    default="show version | inc uptime ",
)
def main(device_list, device, os_type, command):

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
        asyncio.run(runner(devices_dict, command, os_type))

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
