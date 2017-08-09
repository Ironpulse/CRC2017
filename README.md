# CRC 2017
The code for Chinese Robotic Competition 2017

File structures
----

* auto_pseudo.py - Auto's pseudo code for teammates to understand
* Cam - Useless, make teammates think I worked a lot
* config.py - Config file for teammates to change variables
* physics.py - Useless, for simulation
* robot.py - The main code

Functions:
----
Auto:

```
Stages is setted in config.py

time < 1.0: (1.0s)
    solenoid1  1
    solenoid2  1
    solenoid3  2
    drive 0


time < 1.0 + Stage1 but time >= 1.0: (5s)
    solenoid1  1
    solenoid2  1
    solenoid3  2
    drive 0.4


time < 1.0 + Stage1 + Stage2 but time >= 1.0 + Stage
    solenoid3  1
    solenoid1  2
    solenoid2  2
    drive -0.4


time < 1.0 + Stage1 + Stage2 + Stage3 but time >= 1.0 + Stage1 + Stage2
    solenoid3  2
    solenoid1  1
    solenoid2  1
    drive 0
```
Teleop:
```
Drive! Drive! Drive!
```
