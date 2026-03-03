# span
customizable top-alternative system monitor panel for linux written in python

<img width="1403" height="810" alt="2026-03-03-130847_hyprshot" src="https://github.com/user-attachments/assets/2ff7a406-2ff0-485e-ad9a-8e1a94f94b1e" />

---

# Installation
## Arch Linux
span is available on the AUR (arch user repository). Simply run:
```
yay -S span
```
or, if you use paru,
```
paru -S span
```
## Fedora/CentOS/RHEL
span is available via the Fedora Copr repository:
```
sudo dnf copr enable 3xiondev/span
sudo dnf install span
```
if `dnf` for some reason downloads the wrong version (the one where I forgot to force dependency install), you must also run:
```
sudo dnf install lm_sensors wpctl
```
## Other Linux distributions
span, unfortunately, is only natively built for Arch and Fedora. for other distributions, there are globally supported Linux binaries provided on the Releases page. you'll need to install your system's release of the `lm_sensors` and `wpctl` packages.
# Usage
## General
once you've installed the package, simply run `span` and the panel will start. if your terminal is smaller than 41 rows by 157 columns, the panel will immediately crash and tell you to resize your terminal. this is an unavoidable consequence of terminal interfaces; as a result, span is NOT RESIZABLE (mostly). it is intended to be run fullscreen in its own workspace. technically, you can reduce your terminal font size to allow span more space with a smaller window, but this makes text difficult to read. standalone operation is still recommended.

once the panel is running, it will update at a frequency dependent on how fast your system is. typically, it will update every 1.5 to 2 seconds. the panel is completely noninteractive; span is intended to be wholly informative.

to gracefully exit the panel, press `q`. this prevents any query threads from being left open and mindlessly using processing power.
## Configuration
span is already highly configurable, and more configuration options are to be added in the next versions.

when running span for the first time, it will detect that there is no configuration file on the system and will create the default one in `~/.config/span/`. this file, `config.json`, contains all of the possible customization options currently available to the user. the file is organized into sections, and each setting type has its own syntax:
- boolean settings such as `color:transparency` are supplied the values "yes" or "no"
- custom name inputs such as `user:user-custom-name` accept any string as a value; keep in mind this string cannot be too long, otherwise the panel will crash due to spacing issues
- unit inputs such as `memory:size-unit` accept ONLY "GiB" as input; any other value, including "", will default to GB
- directory inputs such as `disk:base-dir` accept a directory path as input and will error out if supplied a non-path
- color inputs such as those in `colors` can ONLY accept EIGHT PRESET COLOR INPUTS: `RED`, `GREEN`, `BLUE`, `CYAN`, `MAGENTA`, `YELLOW`, `WHITE`, and `BLACK`. in the future, custom color support will be added. default color scheme is red and yellow
- format inputs such as `colors:field-name-weight` accept four preset text formats: `BOLD`, `ITALIC`, `NORMAL`, and `UNDERLINE`. other values will error out
- the special inputs `clock-time-format` and `network:force-iface-display` accept user-provided values; specifically, `clock-time-format` accepts `12h` as input and any other input will be interpreted as `24h` and `network:force-iface-display` accepts the name of an existing network interface. if the interface does not exist, it will error out. this is to be used if span cannot detect the interface that is currently in use. default is `wlp3s0` because that is my interface; set to `wlan0` or the name of your interface when you configure

***NOTE:*** the "layout" section of `config.json` is NOT USED. it is safe to ignore, however it will be utilized in future versions.

configuration field names are intentionally written in a self-explanatory way, therefore I do not feel the need to explain them here. figure it out (it's really not that hard) or, if you have some other problem, create a github issue.

configuration cannot be changed at runtime; span requires a restart to reload new changes.
# Contributing
if, for some reason, you'd like to contribute to this mess of code i've written, open a pull request AND an issue. usually, i will only notice if issues are opened, so it's much in your favor to open one with your pull.
# Theming examples
<img width="1403" height="810" alt="2026-03-03-130847_hyprshot" src="https://github.com/user-attachments/assets/ce8ceac5-b7b8-4e52-b057-055a458851a0" /> Default color scheme

<img width="1402" height="803" alt="2026-03-03-144217_hyprshot" src="https://github.com/user-attachments/assets/5fb377b6-2c46-4010-9456-410aa757564f" />
Green/blue

<img width="1401" height="794" alt="2026-03-03-144406_hyprshot" src="https://github.com/user-attachments/assets/a75a4ea6-554f-419b-ad79-30082bf204ee" />
Cyan/purple (magenta)

<img width="1390" height="778" alt="2026-03-03-144543_hyprshot" src="https://github.com/user-attachments/assets/6357864e-2f86-4f13-90bf-9acc7e4145ba" />
Default with black transparency
