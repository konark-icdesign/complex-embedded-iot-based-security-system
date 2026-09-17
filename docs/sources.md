# References

References used for the September 2026 prototype. Arduino board specifications and MathWorks system requirements were rechecked during the documentation review. Simulation measurements are stored separately in `results/`.

| Source | Used for |
|---|---|
| [MathWorks R2026a requirements](https://www.mathworks.com/support/requirements/matlab-system-requirements.html) | Windows 10 22H2 support, 8 GB minimum / 16 GB recommended RAM, SSD guidance |
| [MathWorks serialport reference](https://www.mathworks.com/help/matlab/ref/serialport.html) | Base MATLAB serial communication API |
| [HP t640 QuickSpecs](https://h20195.www2.hp.com/v2/GetDocument.aspx?docname=c06392258) | Ryzen R1505G, two cores / four threads; search-accessible manufacturer specification |
| [Arduino UNO R4 WiFi hardware](https://docs.arduino.cc/hardware/uno-r4-wifi) | RA4M1 resources and official board architecture |
| [Arduino UNO R4 WiFi datasheet](https://docs.arduino.cc/resources/datasheets/ABX00087-datasheet.pdf) | Voltage domains, memory and board details |
| [Arduino software](https://www.arduino.cc/en/software) | IDE download and UNO development tools |
| [Arduino CLI configuration](https://arduino.github.io/arduino-cli/1.5/configuration/) | Official proxy configuration used to install the board toolchain in the hosted environment |
| [Official Renesas core source](https://github.com/arduino/ArduinoCore-renesas) | Board core and WDT API; installed core 1.6.0 headers inspected locally |
| [Hi-Link manufacturer](https://www.hlktech.net/) | LD2410-class product family; exact purchased module manual still required for electrical integration |
| [ESC-50 official dataset](https://github.com/karolpiczak/ESC-50) | Real sound files, categories, predefined folds and licensing |
| [ESC paper DOI](https://doi.org/10.1145/2733373.2806390) | Dataset citation: K. J. Piczak, ACM Multimedia 2015 |
| [Python downloads](https://www.python.org/downloads/) | Official Python installer |
| [MathWorks setup action](https://github.com/matlab-actions/setup-matlab) and [command action](https://github.com/matlab-actions/run-command) | MATLAB R2026a execution in the public repository's GitHub workflow |

The implemented equations are listed in `dsp_maths.md`. Detection results come from the project experiments.

Online notebook support: [Google Colab FAQ](https://research.google.com/colaboratory/faq.html). Colab supports notebooks loaded from GitHub; hosted resources and session duration are limited. The provided notebook has not been executed on Colab.
