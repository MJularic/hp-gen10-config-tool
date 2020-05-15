import json
import requests
from requests.auth import HTTPBasicAuth
from server import Server


# INPUT (disk configuration from config file [], disk configuration from server [])
# OUTPUT difference between config file and server config []
def diff_config_file_server_config(config_from_file, config_from_server):
    diff = []
    for cfg_from_file in config_from_file:
        match = False
        for cfg_from_server in config_from_server:
            if cfg_from_file == cfg_from_server:
                match = True
        if not match:
            diff.append(cfg_from_file)
        else:
            config_from_server.remove(cfg_from_file)
    return diff
#INPUT (diff of configuration from config file and server configuration [], unconfigured drives retrieved from server [])
#OUTPUT configuration to apply {}
def get_config_to_apply(diff_config, unconfigured_drives):
    config_to_apply = {"LogicalDrives": [], "DataGuard": "Disabled"}

    for dc in diff_config:
        disk_number = dc["disk_number"]
        disk_capacity = dc["disk_size_GB"]
        raid_type = dc["raid_type"]

        logical_drive = {"Raid": raid_type, "DataDrives": []}
        disks_to_remove = []

        for ud in unconfigured_drives:
            if disk_capacity == ud["disk_size_GB"]:
                disk_number = disk_number - 1
                logical_drive["DataDrives"].append(ud["location"])
                disks_to_remove.append(ud)
        if disk_number == 0:
            for disk_to_remove in disks_to_remove:
                unconfigured_drives.remove(disk_to_remove)
            config_to_apply["LogicalDrives"].append(logical_drive)
        else:
            return None
    return config_to_apply

#Main program start
server_config_file = "/home/stack/hp-gen10-config-tool/configuration/server-config.json"

with open(server_config_file) as server_config_json:
    server_config = json.load(server_config_json)

for s in server_config["servers"]:

    server = Server(s["name"], s["ilo_username"], s["ilo_password"], s["ilo_ip"])
    disk_config_from_cfg = s["disk_config"]

    # Checking that the ILO Web Server is reachable and that IP connectivity exists
    print("Checking connectivity to server {0}".format(server.name))
    if not server.is_alive():
        print("FAILED!")
        continue
    print("OK!\n")

    # Checking that the ILO credentials that were provided are valid
    print("Checking ilo_user and ilo_pass parameters that were provided for {0}".format(server.name))
    if not server.are_credentials_valid():
        print("INVALID!")
        continue
    print("OK!\n")

    # Checking if the server has the capability of having RAID arrays configured through ILO
    print("Checking disk configuration capability of {0}".format(server.name))
    if not server.is_capable_of_disk_configuration():
        print("INCAPABLE!")
        continue
    print("CAPABLE!\n")

    print("### TARGET DISK CONFIGURATION OF {0} ###\n{1}\n".format(server.name, disk_config_from_cfg))

    # Get all of the logical drives that are configured on the server.
    logical_drives = server.get_configured_logical_drives()
    print("### CURRENT DISK CONFIGURATION OF {0} ###\n{1}\n".format(server.name, logical_drives))

    # Get all of the unconfigured drives that are on the server.
    unconfigured_drives = server.get_unconfigured_drives()
    print("### LIST OF UNCONFIGURED DRIVES OF {0} ####\n{1}\n".format(server.name, unconfigured_drives))

    if len(logical_drives) == 0:
        #No configuration is in place 
        #Check if the  configuration is applicable
        #Configure drives
        continue

    # The number of RAID arrays in the configuration file matches the number of RAID arrays configured on the server
    # The config file should reflect the state on the server!!!
    if len(disk_config_from_cfg) == len(logical_drives):
        diff_config = diff_config_file_server_config(disk_config_from_cfg, list(logical_drives))

        # If the configuration matches the state on the server the configuration is in place!
        # If NOT then the configuration is invalid!
        if len(diff_config) == 0:
            print("### DISK CONFIURATION FOR {0} IS ALREADY IN PLACE ###".format(server.name))
        else:
            print("### CONFIGURATION FOR {0} IS INVALID. PLEASE CHECK THE CONFIGURATION FILE {1} ###".format(server.name, server_config_file))

    if len(disk_config_from_cfg) > len(logical_drives):
        #Check if logical drives is a subset of disk_configs_from_config_file 
        diff_config = diff_config_file_server_config(disk_config_from_cfg, list(logical_drives))

        if len(disk_config_from_cfg) - len(logical_drives) == len(diff_config):
            config_to_apply = get_config_to_apply(diff_config, list(unconfigured_drives))
            if not config_to_apply:
                print("### CONFIGURATION FOR {0} IS INVALID. IT IS NOT POSSIBLE TO ACHIEVE THE TARGET CONFIGURATION ON THIS SERVER ###".format(server.name))
            else:
                print("### THE FOLLOWING CONFIGURATION WILL BE APPLIED TO THE SERVER {0} ###\n{1}\n".format(server.name, config_to_apply))
                if server.configure_raid_arrays(config_to_apply):
                    print("### THE CONFIGURATION WAS SUCCESSFULLY APPLIED TO THE SERVER {0} ###\n".format(server.name))
                    print("### THE SERVER NEEDS TO BE REBOOTED ###")
                else:
                    print("### THE CONFIGURATION WAS NOT SUCCESSFULLY APPLIED TO THE SERVER {0} ###\n".format(server.name))
        else:
            print("### CONFIGURATION FOR {0} IS INVALID. PLEASE CHECK THE CONFIGURATION FILE {1} ###".format(server.name, server_config_file))

    if len(disk_config_from_cfg) < len(logical_drives):
        print("### CONFIGURATION FOR {0} IS INVALID. PLEASE CHECK THE CONFIGURATION FILE {1} ###".format(server.name, server_config_file))