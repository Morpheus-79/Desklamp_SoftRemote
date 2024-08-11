# Software remote control (mainly) for lamps using the HackRF
This is a software remote written in Python for controlling RF controllable lamps using the HackRF One. It's kind of an overkill using this kind of transceiver. But i already had it laying around... so it seemed like beeing the obvious hardware to me. Plus: the code is easy to modify for usage with other RF transmitters, since i couldn't figure out the transmission via *hackrf.dll* and therefore had to rely on using the *hackrf_transfer.exe* from the *HackRF-Tools* package. That's why i've included the [latest February build of the *HackRF-Tools* from 'Great Scott Gadgets'](https://github.com/greatscottgadgets/hackrf/releases/tag/v2024.02.1) in my repository.

## Features
This Python code creates a software representation of the remote for the Vatato Edge Light / M031 LED Desk Lamp:

![Vatato Edge Light](README/Vatato.jpg)

It has all the features of its hardware remote, including 'Pairing' the remote with a new lamp (which on the hardware remote is achieved by pressing the top two buttons simultaneously) and 'Soft Regulation' (achievable on the hardware remote by pressing dark/bright/cold/warm buttons for a longer time).

## Usage
By default this software remote starts minimized as a SysTray icon:

![SysTray-Icon](README/Systray.png)

A double click on the icon maximizes the GUI for the remote. With a right click on the remote you'll get a context menu:

![GUI](README/Remote.png)

... where you can switch 'Soft Regulation' on/off (which is saved inside the *settings.ini* and remembered on the next start), pair the remote with a new lamp or close the software.

A double click onto the remote minimizes it back to a SysTray icon.
