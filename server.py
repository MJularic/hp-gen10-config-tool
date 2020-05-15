import requests
from requests.auth import HTTPBasicAuth
import json
requests.packages.urllib3.disable_warnings()

class Server:
    
    def __init__(self, name, ilo_username, ilo_password, ilo_ip):
        self.name = name
        self.ilo_username = ilo_username
        self.ilo_password = ilo_password
        self.ilo_ip = ilo_ip

    def is_alive(self):
        try:
            health_check_req = requests.get("https://{0}/redfish/v1/".format(self.ilo_ip), verify=False)
            if health_check_req.status_code == 200:
                return True
            else:
                return False
        except:
            return False

    def are_credentials_valid(self):
        try:
            user_pass_check_req = requests.get("https://{0}/redfish/v1/Systems/1".format(self.ilo_ip),
                                            auth=HTTPBasicAuth(self.ilo_username, self.ilo_password),
                                            verify=False)
            if user_pass_check_req.status_code == 401:
                return False
            else:
                return True            
        except:
            return False

    def is_capable_of_disk_configuration(self):
        get_server_RAID_capability = requests.get("https://{0}/redfish/v1/Systems/1".format(self.ilo_ip),
                                            auth=HTTPBasicAuth(self.ilo_username, self.ilo_password),
                                            verify=False)
        server_capabilities = get_server_RAID_capability.json()
        try:
            server_capabilities["Oem"]["Hpe"]["SmartStorageConfig"]
        except KeyError:
            return False
        return True

    def get_configured_logical_drives(self):
        logical_drives = []
        get_logical_drives_overview = requests.get("https://{0}/redfish/v1/Systems/1/SmartStorage/ArrayControllers/0/LogicalDrives".format(self.ilo_ip),
                                                auth=HTTPBasicAuth(self.ilo_username, self.ilo_password), verify=False)

        logical_drives_overview = get_logical_drives_overview.json()
        num_logical_drives = logical_drives_overview["Members@odata.count"]

        if num_logical_drives == 0:
            return logical_drives

        for logical_drive_url in logical_drives_overview["Members"]:
            ld = {"raid_type": None, "disk_number": None, "disk_size_GB": None}

            get_logical_drive = requests.get("https://{0}{1}".format(self.ilo_ip, logical_drive_url["@odata.id"]),
                                                auth=HTTPBasicAuth(self.ilo_username, self.ilo_password), verify=False)

            logical_drive = get_logical_drive.json()
            get_data_drives_overview = requests.get("https://{0}{1}".format(self.ilo_ip, logical_drive["Links"]["DataDrives"]["@odata.id"]),
                                                        auth=HTTPBasicAuth(self.ilo_username, self.ilo_password), verify=False)
            
            data_drives_overview = get_data_drives_overview.json()

            disk_size_GB_on_server = None

            for data_drive_url in data_drives_overview["Members"]:
                get_data_drive = requests.get("https://{0}{1}".format(self.ilo_ip, data_drive_url["@odata.id"]),
                                                auth=HTTPBasicAuth(self.ilo_username, self.ilo_password), verify=False)
                
                disk_size_GB_on_server = get_data_drive.json()["CapacityGB"]

            ld["raid_type"] = "Raid" + logical_drive["Raid"]
            ld["disk_number"] = data_drives_overview["Members@odata.count"]
            ld["disk_size_GB"] = disk_size_GB_on_server

            logical_drives.append(ld)
        return logical_drives

    def get_unconfigured_drives(self):
        unconfigured_drives = []

        get_unconfigured_drives_overview = requests.get("https://{0}/redfish/v1/Systems/1/SmartStorage/ArrayControllers/0/UnconfiguredDrives/".format(self.ilo_ip),
                                                auth=HTTPBasicAuth(self.ilo_username, self.ilo_password), verify=False)

        unconfigured_drives_overview = get_unconfigured_drives_overview.json()
        
        num_unconfigured_drives = unconfigured_drives_overview["Members@odata.count"]

        if num_unconfigured_drives == 0:
            return unconfigured_drives
        
        for unconfigured_drive_url in unconfigured_drives_overview["Members"]:
            ud = {"location": None, "disk_size_GB": None}

            get_unconfigured_drive = requests.get("https://{0}{1}".format(self.ilo_ip, unconfigured_drive_url["@odata.id"]),
                                                auth=HTTPBasicAuth(self.ilo_username, self.ilo_password), verify=False)

            unconfigured_drive = get_unconfigured_drive.json()
            ud["location"] = unconfigured_drive["Location"]
            ud["disk_size_GB"] = unconfigured_drive["CapacityGB"]
            unconfigured_drives.append(ud)
        return unconfigured_drives

    def configure_raid_arrays(self, configuration):
        try:
            headers = {'Content-type': 'application/json'}
            configure_raid_arrays = requests.put("https://{0}/redfish/v1/Systems/1/SmartStorageConfig/settings".format(self.ilo_ip), data=json.dumps(configuration),
            headers=headers, auth=HTTPBasicAuth(self.ilo_username, self.ilo_password), verify=False)
            
            if configure_raid_arrays.status_code == 200:
                print(configure_raid_arrays.json())
                return True
            else:
                return False
        except:
            return False