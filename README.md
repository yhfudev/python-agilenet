# AgileNet: Agile Configuration Wizard for Switches and OpenWRT Routers

In today's interconnected world, a reliable and secure home network is essential. However, configuring switches and routers to optimize network performance can be a complex and time-consuming task. That's where AgileNet comes in.

AgileNet is a powerful tool designed to provide convenient functions for configuring switches and routers in a home network environment. With a user-friendly interface and comprehensive features, it streamlines the setup process for various devices, including Cisco switches, HP/Aruba switches, Dell PowerConnect switches, and OpenWRT devices (including VLAN configurations with `swconfig` or DSA).

With AgileNet, you can effortlessly set up essential network features such as VLAN, firewall (OpenWRT), WiFi (OpenWRT), clock, and device name. These features enable you to customize your network to meet your specific needs, ensuring optimal performance and security.

Setting up your devices with AgileNet is a breeze. AgileNet simplifies the device setup process, making it incredibly easy. By utilizing a terminal console through UART/RS-323 or a software bridged port, you can effortlessly initiate the configuration process in just one simple step.

The configuration of AgileNet is highly flexible. It utilizes a JSON configuration file that allows you to define connection details, device settings, internal network zone configurations, and more. By providing these sections in the configuration file, AgileNet effectively processes and applies the desired setup for your devices.

AgileNet supports various types of connections, including serial port/UART, Qemu/KVM console, and serial port to TCP port. Whether you prefer direct communication with your devices using a serial port, running a router firmware within a virtual machine, or accessing a serial port through a TCP port, AgileNet has got you covered.

Whether you are a networking enthusiast or a home user seeking a hassle-free network configuration solution, AgileNet is the perfect companion for your devices. With its intuitive interface, comprehensive features, and ongoing updates, it simplifies the process of configuring switches and routers, empowering you to create a secure and efficient home network.

Don't let complex network configuration hold you back. Experience the power of AgileNet and unlock the full potential of your home network.

## Table of Contents
<!-- TOC depthFrom:2 -->
- [AgileNet: Agile Configuration Wizard for Switches and OpenWRT Routers](#agilenet-agile-configuration-wizard-for-switches-and-openwrt-routers)
  - [Table of Contents](#table-of-contents)
  - [License](#license)
  - [Device Compatibility Matrix and Firmware Testing](#device-compatibility-matrix-and-firmware-testing)
  - [Setup](#setup)
    - [Initialize a Python environment](#initialize-a-python-environment)
    - [Access UART](#access-uart)
  - [Configuration](#configuration)
    - [Connection](#connection)
      - [Serial port (UART, RS-232)](#serial-port-uart-rs-232)
      - [Qemu/KVM console](#qemukvm-console)
      - [Serial port to TCP port](#serial-port-to-tcp-port)
    - [Device Settings](#device-settings)
      - [Basic Settings](#basic-settings)
      - [Map the External Ports to Internal Switch Ports and Ethernet Interfaces](#map-the-external-ports-to-internal-switch-ports-and-ethernet-interfaces)
      - [Port and Its VLAN IDs](#port-and-its-vlan-ids)
    - [Internal Network Zones Settings](#internal-network-zones-settings)
    - [Others (OpenWRT)](#others-openwrt)
    - [Alternative DNS Server for the Network](#alternative-dns-server-for-the-network)
  - [Command Line](#command-line)
  - [Config File Examples](#config-file-examples)
    - [A Main Router Using an Asus RT-N56U Device](#a-main-router-using-an-asus-rt-n56u-device)
    - [Edge OpenWRT Device with an Asus RT-N56U](#edge-openwrt-device-with-an-asus-rt-n56u)
  - [Summary](#summary)
  - [References](#references)
<!-- /TOC -->

## License

The software is provided under the terms of the GNU General Public License Version 2.


## Device Compatibility Matrix and Firmware Testing

The purpose of our tool is to support two types of use cases or scenarios:

- Main Router: The main router is responsible for handling NAT, DHCP, and firewall functions for the network.

- Edge Router/Switch: The edge router expands the network's reach through the use of VLANs (Virtual Local Area Networks) and also functions as a WiFi Access Point (AP).

We can set up an OpenWRT router as the main router and use a combination of OpenWRT routers and switches from various brands as edge switches with VLANs to extend the sub-networks to different sites.

Please note that the latest version of OpenWrt has replaced the legacy "swconfig" with the Distributed Switch Architecture (DSA). This change requires testing the compatibility of VLAN configurations between different OpenWrt versions. The goal is to ensure that VLAN settings and functionality remain consistent and functional during the transition to the new version. By conducting these compatibility tests, we can identify and address any potential issues or discrepancies, guaranteeing a smooth and seamless VLAN configuration experience across various versions of OpenWrt.

Before releasing the version to the public, we conducted several configuration tests to validate the accuracy of the changes made by the tool.

The tested boards include:

- `x86` - KVM: The OpenWRT is running in an `x86_64` VM with four ethernet cards assigned to the VM and connected to physical cards via bridges. The following OpenWRT versions are used:
  - OpenWRT version 19: [Download VM 19.07.10](https://downloads.openwrt.org/releases/19.07.10/targets/x86/generic/openwrt-19.07.10-x86-generic-combined-ext4.img.gz)
  - OpenWRT version 21: (no DSA) [Download VM 21.02.7](https://downloads.openwrt.org/releases/21.02.7/targets/x86/generic/openwrt-21.02.7-x86-generic-generic-ext4-combined.img.gz)
  - OpenWRT version 22: (no DSA) [Download VM 22.03.5](https://downloads.openwrt.org/releases/22.03.5/targets/x86/generic/openwrt-22.03.5-x86-generic-generic-ext4-combined.img.gz)
  - OpenWRT version 23: (no DSA) [Download VM 23.05.2](https://downloads.openwrt.org/releases/23.05.2/targets/x86/generic/openwrt-23.05.2-x86-generic-generic-ext4-combined.img.gz)


- `ramips/rt3883`- Asus RT-N56U; CPU 500MHz, RAM 128MB, Flash 8MB:
  - OpenWRT version 19: [Download FW 19.07.10](https://archive.openwrt.org/releases/19.07.10/targets/ramips/rt3883/openwrt-19.07.10-ramips-rt3883-rt-n56u-squashfs-sysupgrade.bin)
  - OpenWRT version 21: (no DSA) [Download FW 21.02.7](https://downloads.openwrt.org/releases/21.02.7/targets/ramips/rt3883/openwrt-21.02.7-ramips-rt3883-asus_rt-n56u-squashfs-sysupgrade.bin)
  - OpenWRT version 22: (no DSA) [Download FW 22.03.5](https://downloads.openwrt.org/releases/22.03.5/targets/ramips/rt3883/openwrt-22.03.5-ramips-rt3883-asus_rt-n56u-squashfs-sysupgrade.bin)
  - OpenWRT version 23: (no DSA) [Download FW 23.05.2](https://downloads.openwrt.org/releases/23.05.2/targets/ramips/rt3883/openwrt-23.05.2-ramips-rt3883-asus_rt-n56u-squashfs-sysupgrade.bin)


- `ath79`: TP-Link Archer C6 v2 (US) / A6 v2 (US/TW), CPU Atheros QCA9563 @775MHz, RAM 128MiB, Flash 16MiB
  - OpenWRT version 19: NOT supported
  - OpenWRT version 21: (no DSA) [Download FW 21.02.7](https://downloads.openwrt.org/releases/21.02.7/targets/ath79/generic/openwrt-21.02.7-ath79-generic-tplink_archer-c6-v2-us-squashfs-sysupgrade.bin),
  - OpenWRT version 22: (no DSA) [Download FW 22.03.5](https://downloads.openwrt.org/releases/22.03.5/targets/ath79/generic/openwrt-22.03.5-ath79-generic-tplink_archer-c6-v2-us-squashfs-sysupgrade.bin)
  - OpenWRT version 23: (no DSA) [Download FW 23.05.2](https://downloads.openwrt.org/releases/23.05.2/targets/ath79/generic/openwrt-23.05.2-ath79-generic-tplink_archer-c6-v2-us-squashfs-sysupgrade.bin)


- `ar71xx`: TP-Link Archer C7 v2, Qualcomm Atheros QCA9558 @720 MHz, RAM 128 MB, Flash 16 MB; Max 8 WiFi APs/band
  - OpenWRT version 19: [Download FW 19.07.10](https://downloads.openwrt.org/releases/19.07.10/targets/ath79/generic/openwrt-19.07.10-ath79-generic-tplink_archer-c7-v2-squashfs-sysupgrade.bin)
  - OpenWRT version 21: (no DSA) [Download FW 21.02.7](https://downloads.openwrt.org/releases/21.02.7/targets/ath79/generic/openwrt-21.02.7-ath79-generic-tplink_archer-c7-v2-squashfs-sysupgrade.bin),
  - OpenWRT version 22: (no DSA) [Download FW 22.03.5](https://downloads.openwrt.org/releases/22.03.5/targets/ath79/generic/openwrt-22.03.5-ath79-generic-tplink_archer-c7-v2-squashfs-sysupgrade.bin)
  - OpenWRT version 23: (no DSA) [Download FW 23.05.2](https://downloads.openwrt.org/releases/23.05.2/targets/ath79/generic/openwrt-23.05.2-ath79-generic-tplink_archer-c7-v2-squashfs-sysupgrade.bin)


- `kirkwood`: Linksys EA4500, CPU 1.2 GHz, RAM 128MB, Flash 128MB
  - OpenWRT version 19 is NOT supported.
  - OpenWRT version 21 (with DSA): [Download FW 21.02.7](https://downloads.openwrt.org/releases/21.02.7/targets/kirkwood/generic/openwrt-21.02.7-kirkwood-linksys_ea4500-squashfs-sysupgrade.bin),
    - It is not possible to edit `bridge-vlan` for `br-lan`.
  - OpenWRT version 22 (with DSA): [Download FW 22.03.5](https://downloads.openwrt.org/releases/22.03.5/targets/kirkwood/generic/openwrt-22.03.5-kirkwood-linksys_ea4500-squashfs-sysupgrade.bin)
  - OpenWRT version 23 (with DSA): [Download FW 23.05.2](https://downloads.openwrt.org/releases/23.05.2/targets/kirkwood/generic/openwrt-23.05.2-kirkwood-linksys_ea4500-squashfs-sysupgrade.bin)
  - Notes: It's not possible to upgrade from OpenWRT version 21.02.7 to 22.03.5 using the Luci interface. Instead, you'll need to use the command line for the upgrade:
```bash
cd /tmp
wget -O factory.img https://downloads.openwrt.org/releases/22.03.5/targets/kirkwood/generic/openwrt-22.03.5-kirkwood-linksys_ea4500-squashfs-factory.bin
sysupgrade -F -n factory.img
```

- `ramips/mt7621`: Linksys EA7500 V2, CPU MediaTek MT7621AT 880MHz, RAM 256MB, Flash 128MB
  - OpenWRT version 19 is NOT supported.
  - OpenWRT version 21 (with DSA): [Download FW 21.02.7](https://downloads.openwrt.org/releases/21.02.7/targets/ramips/mt7621/openwrt-21.02.7-ramips-mt7621-linksys_ea7500-v2-squashfs-sysupgrade.bin)
    - It is not possible to edit `bridge-vlan` for `br-lan` for the OpenWrt version 21.02.3.
  - OpenWRT version 22 (with DSA): [Download FW 22.03.5](https://downloads.openwrt.org/releases/22.03.5/targets/ramips/mt7621/openwrt-22.03.5-ramips-mt7621-linksys_ea7500-v2-squashfs-sysupgrade.bin)
  - OpenWRT version 23 (with DSA): [Download FW 23.05.2](https://downloads.openwrt.org/releases/23.05.2/targets/ramips/mt7621/openwrt-23.05.2-ramips-mt7621-linksys_ea7500-v2-squashfs-sysupgrade.bin)
  - Notes: If the router gets too hot, you can find solutions: [here](https://www.qualityology.com/tech/resolve-overheating-issues-on-linksys-ea6300-ea6350-ea6400-ea6700-or-similar-routers/)


- `ramips/mt7621`: Ubiquiti UniFi 6 Lite, CPU MediaTek MT7621AT 880MHz, RAM 256MB, Flash 32MB; 4 WiFi APs/2G; AC AX, ch36,40,44,48 80MHz/5G
It has a single Ethernet port that serves two use cases: when the device acts as the main router, it can connect to the Internet; alternatively, when the device functions as an edge router to extend the network, it acts as a VLAN trunk bridge to the main router.
  - OpenWRT version 19: NOT supported
  - OpenWRT version 21: (with DSA) [Download FW 21.02.7](https://downloads.openwrt.org/releases/21.02.7/targets/ramips/mt7621/openwrt-21.02.7-ramips-mt7621-ubnt_unifi-6-lite-squashfs-sysupgrade.bin)
  - OpenWRT version 22: (with DSA) [Download FW 22.03.5](https://downloads.openwrt.org/releases/22.03.5/targets/ramips/mt7621/openwrt-22.03.5-ramips-mt7621-ubnt_unifi-6-lite-squashfs-sysupgrade.bin)
  - OpenWRT version 23: (with DSA) [Download FW 23.05.2](https://downloads.openwrt.org/releases/23.05.2/targets/ramips/mt7621/openwrt-23.05.2-ramips-mt7621-ubnt_unifi-6-lite-squashfs-sysupgrade.bin)


- `ramips/mt7621`: ZyXEL NWA50AX, CPU Mediatek MT7621, RAM 256MB, Flash 128MB
It has a single Ethernet port that serves two use cases: when the device acts as the main router, it can connect to the Internet; alternatively, when the device functions as an edge router to extend the network, it acts as a VLAN trunk bridge to the main router.
  - OpenWRT version 19: NOT supported
  - OpenWRT version 21: NOT supported
  - OpenWRT version 22: (with DSA) [Download FW 22.03.5](https://downloads.openwrt.org/releases/22.03.5/targets/ramips/mt7621/openwrt-22.03.5-ramips-mt7621-zyxel_nwa50ax-squashfs-ramboot-factory.bin)
  - OpenWRT version 23: (with DSA) [Download FW 23.05.2](https://downloads.openwrt.org/releases/23.05.2/targets/ramips/mt7621/openwrt-23.05.2-ramips-mt7621-zyxel_nwa50ax-squashfs-ramboot-factory.bin)


- `mediatek/filogic`: GL.iNet Beryl AX (GL-MT3000), MT7981B, RAM 512MB, Flash 256MB,
  - OpenWRT version 19: NOT supported
  - OpenWRT version 21: NOT supported
  - OpenWRT version 22: NOT supported
  - OpenWRT version 23: (with DSA) [Download FW 23.05.2](https://downloads.openwrt.org/releases/23.05.2/targets/mediatek/filogic/openwrt-23.05.2-mediatek-filogic-glinet_gl-mt3000-squashfs-sysupgrade.bin)



test matrix: (-- - not supported, Y - yes, N - not tested; X - test failed; DSA - test DSA)
| board \ openwrt | OpenWRT 19.07.10 | OpenWRT 21.02.7 | OpenWRT 22.03.5 | OpenWRT 23.05.2 |
|-----------------|------------------|-----------------|-----------------|-----------------|
x86: KVM | Y (1) | Y (1) | Y (1) | Y (1)
ramips/rt3883: Asus RT-N56U | Y | Y | Y | Y
ath79: TP-Link Archer C6 v2 (US) / A6 v2 (US/TW) | -- | Y | Y | Y
ar71xx: TP-Link Archer C7 v2 | Y | Y | Y | Y
kirkwood: Linksys EA4500 | -- | Y, DSA (2) | Y, DSA | Y, DSA
ramips/mt7621: Linksys EA7500 V2 | -- | Y, DSA (2) | Y, DSA | Y, DSA
ramips/mt7621: Ubiquiti UniFi 6 Lite | -- | Y,  DSA | Y, DSA | Y, DSA
ramips/mt7621: ZyXEL NWA50AX | -- | -- | Y, DSA | Y, DSA
mediatek/filogic: GL.iNet Beryl AX | -- | -- | -- | Y, DSA

Note:
If you try to use a sub-network managed by the edge router itself, instead of the main router, you will need to manually assign a bridge device to a LAN interface in the LUCI interface of the edge router. This step is necessary to enable internet connectivity for LAN clients connected to the edge router.

(1): No WiFi AP
(2): The old OpenWrt 21.02.3 has some issues with configuring the bridge using DSA. Therefore, it is recommended to upgrade to the latest version.


function test matrix:
| board \ router | main router | edge router |
|----------------|-------------|-------------|
VLAN  | Y | Y
VLAN w/ DSA | Y | Y
WiFi AP | Y | Y
assign an IP to a LAN interface | Y | Y
assign an IP to a WAN interface | Y | N (1)
assign an IP to a WAN interface w/ DSA | Y | N (1)

Note:
(1): WAN mixing with VLAN tagged and untagged (for DHCP) is not yet implemented. To connect the LAN to the WAN (NAT), a bridge device needs to be manually assigned to the LAN interface using LUCI.


## Setup

The AgileNet utilizes a terminal console to set up the devices, either through a direct connection to the UART/RS-323 or a software bridged port. It is crucial to ensure an uninterrupted connection between the software and the device, even during device reboots.

In the case of OpenWRT devices, connecting the WAN port to a network with internet access is essential if some required packages are not included in the flash image. This requirement is necessary for the installation of certain packages, such as `luci-ssl`, during the setup process. The installation of these packages is critical and can only be carried out when there is an active internet connection. Alternatively, you can also re-pack a customized ROM image by yourself, including all the necessary packages for your specific usage, and then flash it onto the device. This eliminates the need to connect to the internet for downloading packages during the device configuration using this tool.


### Initialize a Python environment

To initialize a Python environment and create a virtual environment, you can follow these steps:
- Open a terminal or command prompt. Run the following command to create a virtual environment named `venv`:
```bash
python3 -m virtualenv venv
```
- Activate the virtual environment by running the appropriate command based on your operating system:
  - For Unix/Linux/macOS:
```bash
source venv/bin/activate
```
  - For Windows:
```bash
venv\Scripts\activate
```
- Once the virtual environment is activated, you can install the required packages by running the following command:
```bash
pip install -r requirements.txt
```

These commands will create a virtual environment, activate it, and install the packages listed in the `requirements.txt` file. Make sure you have `virtualenv` package installed in your Python environment before running the above commands.


### Access UART

To grant the current user access to the `tty` group in order to access a USB UART dongle or other `tty` devices, you can follow these steps:

- Open a terminal or command prompt. Run the following command to add the current user to the `tty` group:
```bash
# get the device info
stat /dev/ttyUSB0

#sudo usermod -a -G tty $(whoami)
sudo usermod -a -G dialout $(whoami)

grep -Hrn dialout /etc/group

# re-login OR su - ${USER}
id -nG
```
- Log out of your current session and log back in.

After logging back in, you should now have the necessary access to the `tty` devices, including USB UART dongles.

Please note that the `sudo` command might prompt you to enter your password. Make sure you have administrative privileges on your system to execute this command.

## Configuration
In this section, we will explain how to set up a configuration file that can be used by the tool to process the setup for the OpenWRT device.

The tool for configuring a switch requires a JSON configuration file to set up a device. The JSON config file consists of several sections, including:

- Connection: This section specifies the connection details for the device. The connection supports several types of connections, including: Serial port/UART, Qemu/KVM console, and/or Serial port to TCP port.

- Device settings: This section includes the settings specific to the device, such as the device name, VLAN configurations, firewall rules, WiFi settings, and clock settings.

- Internal network zones settings: This section defines the configuration for the internal network zones, such as their names, IP ranges, and any specific settings or rules associated with each zone.

By providing these sections in the JSON configuration file, the tool can effectively process and apply the desired setup for the OpenWRT device.

### Connection

This section specifies the connection details for the device. The connection supports several types of connections, including:
- Serial port/UART: This allows direct communication with the device using a serial port or UART interface. It typically involves connecting to the device using a physical cable or adapter. The serial port can be either UART (3.3v) or RS-232 (12v). Most commercial products provide an RS-232 port for accessing the device's console. Many all-in-one home routers also have a UART inside the device.
- Qemu/KVM console: Running a router firmware within a virtual machine is achievable by utilizing the OpenWRT VM for x86. This allows users to access the device's console through the Qemu/KVM console by executing the `virsh console` command.
- Serial port to TCP port: A serial port can be accessed through a TCP port using a serial-to-TCP tool. This setup allows for remote access to the device's console over a network connection. An example of such a tool is the `socat` utility, which can create a bridge between a serial port and a TCP port.


#### Serial port (UART, RS-232)

In the JSON config file, when configuring the serial port (UART or RS-232), you can include the following properties:
- `serial`: This property represents the device file path to the UART port in a Linux system. It specifies the location of the serial port device, such as `/dev/ttyS0` or `/dev/ttyUSB0`, which can vary depending on the system configuration.
- `baud`: This property represents the baud rate of the UART. The baud rate determines the speed at which data is transmitted and received through the serial port. Common baud rate values include 9600, 115200, and others, depending on the specific requirements of the device being connected.

```json
{
  "serial": "/dev/ttyUSB0",
  "baud": 115200,
}
```

Please check/ensure that the serial port is correctly configured with the correct device file path and baud rate settings for your systems.

#### Qemu/KVM console

In the config file, you can include the following properties for configuring a virtual machine:

- `virsh_url`: This property represents the URL or connection string to the virtual machine host. It specifies the address or hostname of the host machine where the virtual machine is running. It could be in the form of `qemu:///system` for the local system or a specific IP address or hostname for remote hosts. For example, `qemu+ssh://user@192.168.1.111/system` indicates a remote host accessible via SSH.

- `virsh_name`: This property represents the unique identifier or name assigned to the virtual machine within the KVM server.

Please ensure that the configuration file establishes the connection to the virtual machine host and allows interaction with the desired virtual machine using the provided settings. For example, you can use the following command:
```bash
virsh -c "qemu+ssh://username@192.168.11.22/system" console virsh_name
```
Make sure to replace `username@192.168.11.22` with the appropriate SSH connection details and `virsh_name` with the actual name or identifier of the virtual machine.

```json
{
  "virsh_url": "qemu+ssh://username@192.168.11.22/system",
  "virsh_name": "openwrt-test",
}
```

If the virtual machine is running on the local host, the tool can directly connect to it without requiring a separate URL or connection string. In this case, you can specify the `virsh_name` property in the configuration file with the appropriate name or identifier of the virtual machine. The JSON configuration would look like this:
```json
{
  "virsh_name": "openwrt-test",
}
```

#### Serial port to TCP port

To bridge a UART port to a TCP port using `socat`, you can use the following command:
```bash
socat TCP-LISTEN:6000,fork,reuseaddr  FILE:/dev/ttyUSB0,b115200,raw,echo=0 &
```

To specify the desired TCP port number, replace `6000` with the desired port number in the following command. This command establishes a link between the UART device named `/dev/ttyUSB0` and the specified TCP port. By using the `raw` option, the data is transmitted without any interpretation, preserving its original format.

Once the bridge is established, you can access the UART port by connecting to the TCP port using a TCP client, such as `telnet` or a custom application.
```bash
telnet localhost 6000
```

Make sure to adjust the command parameters according to your specific use case and requirements.

To configure the JSON file with the settings for bridging a UART port to a TCP port, you can use the following JSON configuration:
```json
{
  "ipaddr": "localhost", "port": 6000,
}
```
In this configuration, `ipaddr` specifies the IP address or hostname where the UART-to-TCP bridge is running, and `port` indicates the TCP port number to which the UART port is bridged.

Ensure that the `ipaddr` and `port` values match the actual settings used when creating the UART-to-TCP bridge.


### Device Settings

There are some settings in the configuration file related to the hardware/firmware of the device, including:
- `driver`: This setting specifies the driver for the device. The supported driver types are:
  - `ciscoios`: This driver is used for Cisco Switch IOS terminal console interface.
  - `openwrtuci`: This driver is used for the OpenWRT `uci` command line interface via the serial port.
  - `arubacli`: This driver is used for the HP/Aruba terminal console interface.
  - `dellpc`: This driver is used for the Dell PowerConnect switch terminal console interface.

- `arg_is_gns3`: This setting indicates whether the device is running on a GNS3 virtual machine in KVM. It is set to `true` if the device is running in a GNS3 environment, and `false` otherwise.
- `arg_has_hw_switch`: This setting specifies whether the device has a hardware switch. It is set to `true` for devices that have a physical hardware switch component, such as some commercial switch products and certain home routers. If the device does not have a hardware switch, for example, an OpenWRT x86 VM, this setting would be set to `false`.
- `arg_port_map`: This setting defines the mapping between external port names and their corresponding OS device names and master device name(s).
- `arg_port_vlan` or alternative pairs `arg_port_list` and `arg_vlan_list`: These settings are used to define the VLAN assignments for the device's ports.
  - `arg_port_vlan` pairs a port name with its assigned VLAN ID.
  - Alternatively, you can use `arg_port_list` and `arg_vlan_list` together to specify the port names and VLAN IDs separately. Each port name in `arg_port_list` corresponds to the VLAN ID at the same index in `arg_vlan_list`.

These settings allow you to configure various aspects related to the device's hardware, environment, port mappings, and VLAN assignments.


#### Basic Settings
Here are the basic settings for an OpenWRT in a home router and an OpenWRT in a virtual machine:

For an OpenWRT in a home router:
```json
{
  "driver": "openwrtuci",
  "arg_is_gns3": false,
  "arg_has_hw_switch": true,
}
```

For an OpenWRT in a virtual machine:
```json
{
  "driver": "openwrtuci",
  "arg_is_gns3": true,
  "arg_has_hw_switch": false,
}
```

In the configuration for the OpenWRT in a home router, the `arg_is_gns3` property is set to `false` indicating that it is not running in a GNS3 environment. The `arg_has_hw_switch` property is set to `true` to indicate the presence of a hardware switch.

#### Map the External Ports to Internal Switch Ports and Ethernet Interfaces

For an OpenWRT in a home router, you can use the following JSON configuration to map the external ports to internal switch ports and Ethernet interfaces:

```json
{
  "arg_port_map": { // the external port names to internal switch port num
    // name: [ switch_port, device, ]
    "CPU": [ 8, "eth0" ],
    "WAN": [ 4, "eth0" ],
      "1": [ 3, "eth0" ],
      "2": [ 2, "eth0" ],
      "3": [ 1, "eth0" ],
      "4": [ 0, "eth0" ],
  },
}
```
In this configuration, for example the first line:
- `"CPU"` is mapped to switch port `8`, which represents the port number for the `swconfig` (switch) in OpenWRT.
- The device interface `"eth0"` is the master Ethernet interface associated with that switch port.



* OpenWRT router of x86 arch in KVM

For an OpenWRT router of x86 architecture in KVM with 4 virtual Ethernet ports for the local network and one Ethernet port for WAN, you can use the following JSON configuration:
```json
{
  "arg_port_map": { // the external port names to internal switch port num
    // name: [ switch_port, device, ]
    "CPU": [ null, null ],
    "WAN": [ "eth0", "eth0" ],
      "1": [ "eth1", "eth1" ],
      "2": [ "eth2", "eth2" ],
      "3": [ "eth3", "eth3" ],
      "4": [ "eth4", "eth4" ],
  },
}
```
Please note that the `null` value for `"CPU"` indicates that it does not have a specific switch port or device interface associated with it.

* Cisco 8-port switch

For a Cisco 8-port switch, you can use the following JSON configuration to map the external port names to the internal port numbers or names:
```json
{
  "arg_port_map": { // the external port names to internal port num/name
     "WAN": "G0/1",
    "LAN1": "F0/1",
    "LAN2": "F0/2",
    "LAN3": "F0/3",
    "LAN4": "F0/4",
    "LAN5": "F0/5",
    "LAN6": "F0/6",
    "LAN7": "F0/7",
    "LAN8": "F0/8",
  },
}
```
Adjust the port numbers or names according to your specific Cisco switch configuration.


#### Port and Its VLAN IDs

It's to assign the VLAN IDs to each of the ports, includes the trunk VLAN(tagged). The VLAN value range is from `1` to `4096`, the `0` is to present a tagged(trunk) VLAN.


To specify the VLAN IDs for each port in your JSON configuration, you can use the `arg_port_vlan` to map the port name to a assigned value(s) of VLAN.:
```json
{
  "arg_port_vlan": { // the external port names to VLAN
    // name: VLAN // VLAN 0: tagged, 1-4095 untagged, -1 off
    "CPU":  0, // CPU (eth1) for LAN
    "WAN":  2, // the physical port for WAN
      "1":  1, // the physical port for LAN1
      "2": 10, // the physical port for LAN2
      "3": 20, // the physical port for LAN3
      "4":  0, // the physical port for LAN4
  },
}
```
In this example, `"CPU"` is assigned VLAN ID `0`, `"WAN"` is assigned VLAN ID `2`, `"1"` is assigned VLAN ID `1`, `"2"` is assigned VLAN ID `10`, `"3"` is assigned VLAN ID 20, and `"4"` is assigned VLAN ID `0` (representing a tagged VLAN).

If you prefer an alternative approach, you can use separate arrays to define the port names and VLAN IDs. This can be achieved by using two lists to map the port names to their corresponding VLAN values.

Using separate arrays `arg_port_list` and `arg_vlan_list`:
```json
{
  "arg_port_list": [ "CPU", "WAN", "1", "2", "3", "4", ], // the ports need to be configured
  "arg_vlan_list": [     0,     2,   1,  10,  20,   0, ], // the vlan id for each port to be configured
}
```
In this case, `"CPU"` corresponds to VLAN ID `0`, `"WAN"` corresponds to VLAN ID `2`, `"1"` corresponds to VLAN ID `1`, `"2"` corresponds to VLAN ID `10`, `"3"` corresponds to VLAN ID `20`, and `"4"` corresponds to VLAN ID `0` (tagged VLAN).



### Internal Network Zones Settings

The following JSON configuration sets up various network zones and their corresponding configurations:
```json
{
  "arg_interface_config": { // the openwrt interface config
    // name: [vlan, ip/bit, wifi, wifi pw, [list of forward zone]],
    "office":   [  10, "192.168.101.0/24", "Office", "pw4offic", ["wan"]],
    "game":     [  20, "192.168.102.0/24", "Game",   "pw4game1", ["wan"]],
    "iotapp":   [  30, "192.168.103.0/24", "IoT",    "pw4iot#!", []],
    "surve":    [  40, "192.168.104.0/24", "", "", []],
    "guest":    [  50, "192.168.105.0/24", "Guest",  "myGuest!", ["wan"]],
  },
}
```
In this configuration, each network zone is defined by a unique name and specified with the following settings:

- vlan: VLAN ID for the zone
- ip/bit: IP address and subnet mask for the zone
- wifi: WiFi name (if applicable)
- wifi pw: WiFi password (if applicable)
- List of forward zones: Specifies the zones to which traffic can be forwarded from the current zone (e.g., "wan" for forwarding to the WAN zone).

For example, the `"office"` zone is configured with VLAN ID `10`, IP address range `"192.168.101.0/24"`, WiFi name `"Office"`, WiFi password `"pw4offic"`, and it allows forwarding to the `"wan"` zone.



### Others (OpenWRT)

There are additional configuration options supported by the JSON file:
- `arg_app_zone`: This option allows you to set the access service IP for a specific service. The following properties can be configured:
  - `zone_server`: The zone name to which the server belongs. This allows the server to be accessible from other zones.
  - `ip`: The IP address of the server that can be accessed from other zones.
  - `zones_from`: A list of zones from which clients can access the server.
  - `dest_port`: The specific ports on the server that are opened for external access.
- `dns_server`: This option enables you to set a DNS server for the network. The properties for this configuration include:
  - `zone_server`: The zone name to which the DNS server belongs. This allows the server to be accessible from other zones.
  - `ip`: The IP address of the DNS server that can be accessed from other zones.
  - `zones_from`: A list of zones from which clients can access the DNS server.
- `external_tftp`: This option allows you to specify the IP address of a TFTP server.
- `extra_packets`: This option is used to specify extra software packages that need to be installed.

```json
{
  "external_tftp": "192.168.101.21", // the IP of the external TFTP server
  "arg_app_zone": [
    {
      // some zones can access file server on zone office
      // ports:
      // 22/tcp   open  ssh
      // 80/tcp   open  http
      // 111/tcp  open  rpcbind
      // 139/tcp  open  netbios-ssn
      // 445/tcp  open  microsoft-ds
      // 2049/tcp open  nfs
      // 9091/tcp open  torrent web
      "name": "Samba server 1",
      "prefix": "fileserver_",
      "zone_server": "office",
      "ip": "192.168.101.22",
      "zones_from": ["office", "game", "guest"],
      // a blank sep ports list
      "dest_port": "22 69 80 443 111 137 138 139 445 9091 4711 59000-59499",
    },
    {
      // some zones can access printer on zone noinet
      // ports:
      //  515 -- LPD
      // 9100 -- raw
      // 3702 -- WSD Multicast Discovery
      //   80 -- HTTP
      //  161 -- SNMP
      "name": "Printer server 1",
      "prefix": "printserver_",
      "zone_server": "office",
      "ip": "192.168.101.23",
      "zones_from": ["office", "game", "guest"],
      // a blank sep ports list
      "dest_port": "515 631 9100 3702",
    }
  ],
  "extra_packets": [
    "bash", "diffutils",
    "block-mount",
    "conntrack", "owipcalc", "etherwake", "uuidgen", // for bash-powerautosave
    "tcpdump", "iperf3", "curl", // network tests
  ],
}
```


### Alternative DNS Server for the Network

To provide an alternative DNS server for the network, users may choose to set up a separate DNS server, such as a `pi-hole`, to act as a filtering DNS server for blocking ad domains.

The JSON configuration below demonstrates the setup:
```json
{
  // set up the server that it can be reached from rest of the network
  "arg_app_zone": [
    {
      // all of internet zones can access DNS on zone office
      // ports:
      //  53 -- DNS, tcp/udp
      "name": "DNS server, pi-hole",
      "prefix": "pihole_",
      "zone_server": "office",
      "ip": "192.168.101.24",
      "zones_from": [ "office", "game", "guest" ],
      // a blank sep ports list
      "dest_port": "53",
    }
  ],

  // setup the DNS server, in DHCP options of each zone
  "dns_server": [
    {
      "name": "DNS server, ip-hole",
      "prefix": "pihole_",
      "ip": "192.168.101.24",
      "zone_server": "office",
      "zones_from": [ "office", "game", "guest" ],
    },
  ],
}
```
In this configuration, the `"arg_app_zone"` section sets up the DNS server to be accessible from the rest of the network. The server is assigned the name "DNS server, pi-hole" with the prefix `"pihole_"` in the name of firewall policies. It is associated with the `"office"` zone and has the IP address `"192.168.101.24"`. It can be accessed by the `"office"`, `"game"`, and `"guest"` zones. The destination port is specified as `53`, which corresponds to DNS traffic.

The `"dns_server"` section sets up the DNS server for each zone using DHCP options. The server is named `"DNS server, pi-hole"` with the prefix `"pihole_"` in the firewall policies. It has the IP address `"192.168.101.24"` and is associated with the `"office"` zone. It can be accessed by the `"office"`, `"game"`, and `"guest"` zones.


## Command Line

To set up a router/switch using the `setnetequ.py` command with a JSON configuration file, you can run the following command in the terminal:
```bash
./setnetequ.py [Options] <Argument>
```

Options:
- `-l`, `--logfile`: Specifies the log file to be used.
- `-o`, `--outputfile`: Specifies the file to save the setup contents.
- `-j`, `--json`: Specifies the JSON config file for the setup.
- `-s`, `--noreset`: Skips the reset of the router to factory mode.
- `-t`, `--type`:  Sets the default device driver type.
- `-d`, `--debug`: Shows debug messages.
- `-v`, `--version`: Shows the version of the script.

Argument:
- `info`: Shows device information only.
- `reset`: Resets the device only.
- `layout`: Resets and sets up the device with the config file.


Example:
```bash
./setnetequ.py \
  -j config-openwrt-asus.json \
  -o output-uci-commands.txt \
  -l output-logs.txt \
  layout
```
In the above example, the setnetequ.py script is executed with the following options:
- JSON config file: `config-openwrt-asus.json`
- Output file for saving setup contents: `output-uci-commands.txt`
- Log file: `output-logs.txt`

The script will perform the setup according to the configuration specified in the JSON file and generate the `uci` commands, which will be saved in the `output-uci-commands.txt` file. Additionally, log messages will be logged in the `output-logs.txt` file. The `layout` argument indicates that the script should reset and set up the device based on the configuration file.


## Config File Examples

### A Main Router Using an Asus RT-N56U Device

In this example, a home network consists of five zones separated by VLANs:
- `office`: This is the main network zone for the home.
- `game`: This zone is dedicated to game consoles, TVs, and other gaming devices.
- `iotapp`: This zone is reserved for IoT devices.
- `surve`: This zone is specifically for surveillance cameras and is isolated from the internet and other network zones.
- `guest`: This zone is designated for guest devices.

Within the local network, there are several server hosts available:
- TFTP server at `192.168.101.21`;
- NAS/Samba server at `192.168.101.22`, which is accessible from the `office`, `game`, and `guest` zones;
- Printer server at `192.168.101.23`;

```json
{
  "serial": "/dev/ttyUSB0", "baud": 57600,
  //"ipaddr": "localhost", "port": 6000,
  //"virsh_name": "openwrt-test",
  //"virsh_url": "qemu+ssh://username@192.168.1.105/system", "virsh_name": "openwrt-test",

  //"admin_password": "abc123",

  "name": "OpenWrt Main Router on Asus RT-N56U",

  "arg_hostname": "main-ap-1", // the hostname of the device

  "arg_interface_config": { // the openwrt interface config
    // name: [vlan, ip/bit, wifi, wifi pw, [list of forward zone]],
    "office":   [  10, "192.168.101.0/24", "Office", "pw4offic", ["wan"]],
    "game":     [  20, "192.168.102.0/24", "Game",   "pw4game1", ["wan"]],
    "iotapp":   [  30, "192.168.103.0/24", "IoT",    "pw4iot#!", []],
    "surve":    [  40, "192.168.104.0/24", "", "", []],
    "guest":    [  50, "192.168.105.0/24", "Guest",  "myGuest!", ["wan"]],
  },

  "external_tftp": "192.168.101.21", // the IP of the external TFTP server
  "arg_app_zone": [
    {
      // some zones can access file server on zone office
      // ports:
      // 22/tcp   open  ssh
      // 80/tcp   open  http
      // 111/tcp  open  rpcbind
      // 139/tcp  open  netbios-ssn
      // 445/tcp  open  microsoft-ds
      // 2049/tcp open  nfs
      // 9091/tcp open  torrent web
      "name": "Samba server 1",
      "prefix": "fileserver_",
      "zone_server": "office",
      "ip": "192.168.101.22",
      "zones_from": ["office", "game", "guest"],
      // a blank sep ports list
      "dest_port": "22 69 80 443 111 137 138 139 445 9091 4711 59000-59499",
    },
    {
      // some zones can access printer on zone noinet
      // ports:
      //  515 -- LPD
      // 9100 -- raw
      // 3702 -- WSD Multicast Discovery
      //   80 -- HTTP
      //  161 -- SNMP
      "name": "Printer server 1",
      "prefix": "printserver_",
      "zone_server": "office",
      "ip": "192.168.101.23",
      "zones_from": ["office", "game", "guest"],
      // a blank sep ports list
      "dest_port": "515 631 9100 3702",
    }
  ],
  "extra_packets": [
    "bash", "diffutils",
    "block-mount",
    "conntrack", "owipcalc", "etherwake", "uuidgen", // for bash-powerautosave
    "tcpdump", "iperf3", "curl", // network tests
  ],

/** config for Asus RT-N56U
 * +--------+--------+--------+--------+--------+--------+
 * | ------ |  WAN   |   1    |   2    |   3    |   4    |
 * +--------+--------+--------+--------+--------+--------+
 * |  CPU   |  WAN   | LAN 4  | LAN 3  | LAN 2  | LAN 1  |
 * +--------+--------+--------+--------+--------+--------+
 * | port 8 | port 4 | port 3 | port 2 | port 1 | port 0 |
 * +--------+--------+--------+--------+--------+--------+
 */
  "driver": "openwrtuci",
  "arg_is_gns3": false,
  "arg_has_hw_switch": true,
  "arg_port_map": { // the external port names to internal switch port num
    // name: [ switch_port, device, ]
    "CPU": [ 8, "eth0" ],
    "WAN": [ 4, "eth0" ],
      "1": [ 3, "eth0" ],
      "2": [ 2, "eth0" ],
      "3": [ 1, "eth0" ],
      "4": [ 0, "eth0" ],
  },
  "arg_port_vlan": { // the external port names to VLAN
    // name: VLAN // VLAN 0: tagged, 1-4095 untagged, -1 off
    "CPU":  0, // CPU (eth1) for LAN
    "WAN":  2, // the physical port for WAN
      "1":  1, // the physical port for LAN1
      "2":  1, // the physical port for LAN2
      "3":  1, // the physical port for LAN3
      "4": 20, // the physical port for LAN4
  },
}
```

### Edge OpenWRT Device with an Asus RT-N56U

The purpose of the "Edge" OpenWRT device is to extend the network from the main router to a larger area using a cable-connected WiFi AP. The WiFi AP can also function as a wired managed switch if it has Ethernet ports (e.g., 4 ports for most all-in-one home routers).

Here, we will configure the OpenWRT device with a WAN port connected to the main router's trunk VLAN port via an Ethernet cable.

Please make the following changes to the base config file based on the above configuration:
```json
{
  ...

  "name": "OpenWrt WiFi AP on Asus RT-N56U",
  "arg_hostname": "edge-ap-2", // the hostname of the device
  "arg_interface_config": { // the openwrt interface config
    // name: [vlan, ip/bit, wifi, wifi pw, [list of forward zone]],
    "office":   [  10, "", "Office", "pw4offic", []],
    "game":     [  20, "", "Game",   "pw4game1", []],
    "iotapp":   [  30, "", "IoT",    "pw4iot#!", []],
    "guest":    [  50, "", "Guest",  "myGuest!", []],
  },
  "external_tftp": null,
  "arg_app_zone": null,

  "arg_port_vlan": { // the external port names to VLAN
    // name: VLAN // VLAN 0: tagged, 1-4095 untagged, -1 off
    "CPU":  0, // CPU (eth1) for LAN
    "WAN":  0, // the physical port for WAN
      "1":  10, // the physical port for LAN1
      "2":  20, // the physical port for LAN2
      "3":  30, // the physical port for LAN3
      "4":  40, // the physical port for LAN4
  },
  ...
}
```
In the changes made above, the WAN port is configured as a tagged VLAN port.

The edge WiFi AP acts as a bridge switch to the main router. In the configuration, the "forward zone" in `arg_interface_config` is left empty, as the main router will handle the forwarding. The IP address in the `arg_interface_config` is also set to empty, ensuring that the `setnetequ.py` command does not assign IP addresses. This allows network packets to be handled by the switch as VLAN packets.


## Summary

The AgileNet is designed to simplify the setup of OpenWRT routers as main routers or edge routers/WiFi APs in home networks. It also allows for the integration of switches from various brands as edge switches, providing a hassle-free configuration experience.

However, there are certain limitations at present, and that's where we welcome developers like you to contribute to the project. One such limitation is encountered when configuring an **edge** router using OpenWRT version `19.07.10` and below. In these versions, it is not possible to configure a LAN that functions as a NAT to connect to the internet due to certain reasons. On the other hand, for OpenWRT version `21.02` and above, the user can use the LUCI interface to manually change the WAN configuration to use a bridge interface (e.g., `br-lan.20`) so that the LAN can work in NAT mode. It is important to note that this limitation may be addressed and resolved in future versions of the AgileNet.

Overall, the AgileNet aims to streamline the setup of home networks, saving you time and effort.


## References

[OpenWRT DSA Mini-Tutorial](https://openwrt.org/docs/guide-user/network/dsa/dsa-mini-tutorial)


[PfsenseFauxapi](https://github.com/ndejong/pfsense_fauxapi_client_python.git)


[swconfig dev %q help](https://github.com/gstrauss/openwrt-luci/blob/master/modules/luci-mod-admin-full/luasrc/model/cbi/admin_network/vlan.lua)
