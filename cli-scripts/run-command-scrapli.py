import asyncio
from scrapli.driver.core import AsyncIOSXEDriver
import click
import getpass
from rich import print

from asyncio.exceptions import TimeoutError
from scrapli.exceptions import ScrapliAuthenticationFailed


async def get_command_device(device, command):
    conn = AsyncIOSXEDriver(**device)
    try:
        await conn.open()
    except TimeoutError:
        return device["host"], "Connection failed"
    except ScrapliAuthenticationFailed:
        return device["host"], "Connection failed. Timeout"

    print(f"Connection successful to {device['host']}")
    prompt_result = await conn.get_prompt()
    output = await conn.send_command(f"{command}")
    await conn.close()
    print(f"Executed command for {device['host']}")
    if len(output.result):
        return prompt_result, output.result
    else:
        return prompt_result, "empty response"


async def runner(DEVICES, COMMAND):
    coroutines = [get_command_device(device, COMMAND) for device in DEVICES]
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
    "--devices",
    "-d",
    default="devices.txt",
    help="simple text file with list of devices",
)
@click.option(
    "--command",
    "-c",
    default=" show version | inc uptime ",
    prompt="Enter command: ",
    help="a single command in quotes",
)
def main(devices, command):

    # get input
    username = input("Username: ")
    password = getpass.getpass("Password: ")

    with open(devices, "r") as f:
        output = f.readlines()
    devices = [device.strip() for device in output]
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
    asyncio.run(runner(devices_dict, command))


if __name__ == "__main__":
    main()
