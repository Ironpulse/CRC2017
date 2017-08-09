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