__Author__      = "Shou Chaofan"

from config import *
import wpilib
from wpilib import RobotDrive
class MyRobot(wpilib.IterativeRobot):
    '''Main robot class'''
    
    def robotInit(self):
        wpilib.CameraServer.launch()
        self.lr_motor           = wpilib.Spark(frontLeftChannel)
        self.rr_motor           = wpilib.Spark(rearLeftChannel)
        self.lf_motor           = wpilib.Spark(frontRightChannel)
        self.rf_motor           = wpilib.Spark(rearRightChannel)
        self.robot_drive        = wpilib.RobotDrive(self.lr_motor, self.rr_motor,
                                             self.lf_motor, self.rf_motor)
        self.robot_drive .setExpiration(Expiration)
        self.robot_drive.setInvertedMotor(wpilib.RobotDrive.MotorType.kFrontLeft, lf_motor_inverse)
        self.robot_drive.setInvertedMotor(wpilib.RobotDrive.MotorType.kRearLeft, rf_motor_inverse)
        
        self.stick              = wpilib.Joystick(JoystickNum)
        self.motorClimbOn       = wpilib.Spark(ClimbMotor)
        self.solenoid1          = wpilib.DoubleSolenoid(Solenoid11Num,Solenoid12Num)
        self.solenoid2          = wpilib.DoubleSolenoid(Solenoid21Num,Solenoid22Num)
        self.solenoid3          = wpilib.DoubleSolenoid(Solenoid31Num,Solenoid32Num)
        self.a                  = 0
        self.b                  = 0
    def autonomousInit(self):
        '''Called only at the beginning of autonomous mode'''
        self.a = 0
        self.b = 0
        self.solenoid1.set(1)
        self.solenoid2.set(1)
        self.solenoid3.set(2)
        global timer
        timer = wpilib.Timer()
        timer.start()
    def autonomousPeriodic(self):
        #move 65 inches
        if timer.get() < 1.0: #1s
            pass
        elif timer.get() < 1.0 + Stage1 and timer.get() >= 1.0: #10s
            print(1)
            self.solenoid1.set(1)
            self.solenoid2.set(1)
            self.solenoid3.set(2)
            self.robot_drive.mecanumDrive_Cartesian(0,0.4,0,0);
        elif timer.get() < 1.0 + Stage1 + Stage2 and timer.get() >= 1.0 + Stage1: #16s
        #solenoid
            print(2)
            self.solenoid3.set(1)
            self.solenoid1.set(2)
            self.solenoid2.set(2)
            self.robot_drive.mecanumDrive_Cartesian(0,-0.4,0,0);
        else:
            if timer.get() < 1.0 + Stage1 + Stage2 + Stage3 and timer.get() >= 1.0 + Stage1 + Stage2:
                print(3)
                self.solenoid3.set(2)
                self.solenoid1.set(1)
                self.solenoid2.set(1)
                self.robot_drive.mecanumDrive_Cartesian(0,0,0,0);
                    
        
    def disabledInit(self):
        '''Called only at the beginning of disabled mode'''
        self.robot_drive.mecanumDrive_Cartesian(0,0,0,0);

        self.solenoid1.set(2)
        self.solenoid2.set(2)
        self.solenoid3.set(2)
        self.solenoid1.set(0)
        self.solenoid2.set(0)
        self.solenoid3.set(0)
    def disabledPeriodic(self):
        '''Called every 20ms in disabled mode'''
        pass

    def teleopInit(self):
        '''Called only at the beginning of teleoperated mode'''
        self.a = 0
        self.solenoid1.set(1)
        self.solenoid2.set(1)
        self.solenoid3.set(2)
    def teleopPeriodic(self):
        '''Called every 20ms in teleoperated mode'''
        
        # Move a motor with a Joystick
        try:
            self.robot_drive.setSafetyEnabled(True)
            if self.isOperatorControl() and self.isEnabled():
                if self.stick.getX() > pct or self.stick.getY() > pct or self.stick.getZ() > pct or self.stick.getX() < -pct or self.stick.getY() < -pct or self.stick.getZ() < -pct:
                    self.robot_drive.mecanumDrive_Cartesian(self.stick.getX(),
                                                            self.stick.getY(),
                                                            self.stick.getZ(), 0);

                if self.stick.getRawButton(7) == True: #climb
                    self.solenoid1.set(1)
                    self.solenoid2.set(1)
                if self.stick.getRawButton(8) == True: #climb
                    self.solenoid1.set(2)
                    self.solenoid2.set(2)

                if self.stick.getRawButton(9) == True:
                    self.sol = 1
                    self.solenoid3.set(self.sol)
                if self.stick.getRawButton(10) == True:
                    self.sol = 2
                    self.solenoid3.set(self.sol)

                


                if self.stick.getRawButton(11) == True: #climb
                    self.robot_drive.mecanumDrive_Cartesian(0, 0, 0, 0)#set other motor to 0
                    self.motorClimbOn.set(ClimbEff)#start climbing
                if self.stick.getRawButton(12) == True: #climb
                    self.robot_drive.mecanumDrive_Cartesian(0, 0, 0, 0)#set other motor to 0
                    self.motorClimbOn.set(0)#start climbing
                wpilib.Timer.delay(0.005)
        except:
            raise error
if __name__ == '__main__':
    wpilib.run(MyRobot)
