package io.github.robotpy.cscore;

import java.io.IOException;
import java.io.InputStream;
import java.lang.ProcessBuilder.Redirect;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;

import edu.wpi.first.wpilibj.DriverStation;

/**
 * Provides a way to launch an out of process Python robotpy-cscore based
 * camera service instance from a Java robot program.
 * 
 * You must have Python and python36-robotpy-cscore installed, or this
 * just simply won't work. Refer to the RobotPy documentation for details.
 * 
 * The python code should be a single file, and must compiled into your java
 * jar file. If your file was in the src directory as 'vision.py', you would
 * add this to the 'project' section of build.xml:
 */
// <!-- add vision.py to JAR file -->
// <target name="jar" depends="compile">
//   <echo>[athena-jar] Making jar ${dist.jar}.</echo>
//  <mkdir dir="${dist.dir}" />
//   <mkdir dir="${build.jars}" />
//
//  <echo>[athena-jar] Copying jars to ${build.jars}.</echo>
//  <copy todir="${build.jars}" flatten="true">
//    <path refid="classpath.path"/>
//  </copy>
//
//   <jar destfile="${dist.jar}" update="false">
//     <manifest>
//   	<attribute name="Main-Class" value="edu.wpi.first.wpilibj.RobotBase"/>
//   	<attribute name="Robot-Class" value="${robot.class}"/>
//   	<attribute name="Class-Path" value="."/>
//     </manifest>
//
//     <fileset dir="${build.dir}" includes="**/*.class"/>
//     <fileset file="${src.dir}/vision.py"/>
//
//   <zipgroupfileset dir="${build.jars}"/>
//  </jar>
// </target>
public class CameraServer {

	public static String visionPath = "/home/lvuser/vision.py";
	private static boolean isAlive = false;
	private static boolean launched = false;
	
	/**
	 * @return true if the vision process is (probably) alive
	 */
	public static boolean isAlive() {
		return isAlive;
	}
	
	/**
	 * Launches an embedded resource called "vision.py" which contains a
	 * "main" function.
	 */
	public static void startPythonVision() {
		startPythonVision("/vision.py", "main");
	}
	
	/**
	 * Call this function to launch a python vision program in an external
	 * process.
	 * 
	 * @param resource      The resource built into the jar (see above), such as /vision.py
	 * @param functionName  The name of the function to call
	 */
	public static void startPythonVision(String resource, String functionName) {
		// don't allow restart
		if (launched) {
			return;
		}
		
		launched = true;
		
		System.out.println("Launching python process from " + resource);

		try {
			// extract the resource and write it to vision.py
			InputStream is = CameraServer.class.getResourceAsStream(resource);
			if (is == null) {
				throw new IOException("Resource " + resource + " not found");
			}
			
			Files.copy(is, Paths.get(visionPath), StandardCopyOption.REPLACE_EXISTING);
			
			// launch the process
			ProcessBuilder pb = new ProcessBuilder();
			pb.command("/usr/local/bin/python3", "-m", "cscore", visionPath + ":" + functionName);
			
			// we open a pipe to it so that when the robot program exits, the child dies
			pb.redirectInput(Redirect.PIPE);
			
			// and let us see stdout/stderr
			pb.redirectOutput(Redirect.INHERIT);
			pb.redirectError(Redirect.INHERIT);
			
			final Process p = pb.start();
			isAlive = true;
			
			Thread t = new Thread(()-> {
				try {
					p.waitFor();
				} catch (InterruptedException e) {
					// empty
				}
				
				isAlive = false;
			});
			t.setDaemon(true);
			t.start();
			
		} catch (IOException e) {
			System.out.println("Error launching vision! "  + e.toString());
			//if (!DriverStation.getInstance().isFMSAttached()) {
			//	throw new RuntimeException("Error launching vision", e);
			//}
		}
	}
}
