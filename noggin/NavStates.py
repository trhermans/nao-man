""" States for finding our way on the field """

from .util import MyMath
import NavConstants as constants
from .players import ChaseBallConstants
from .playbook.PBConstants import GOALIE
from math import fabs, cos, sin, radians

DEBUG = False
# States for the standard spin - walk - spin go to
def spinToWalkHeading(nav):
    """
    Spin to the heading needed to walk to a specific point
    """
    targetH = MyMath.getTargetHeading(nav.brain.my, nav.destX, nav.destY)
    headingDiff = fabs(nav.brain.my.h - targetH)
    newSpinDir = MyMath.getSpinDir(nav.brain.my.h, targetH)

    if nav.firstFrame():
        nav.changeSpinDirCounter = 0
        nav.stopSpinToWalkCount = 0
        nav.curSpinDir = newSpinDir

    if newSpinDir != nav.curSpinDir:
        nav.changeSpinDirCounter += 1
    else:
        nav.changeSpinDirCounter = 0

    if nav.changeSpinDirCounter >  constants.CHANGE_SPIN_DIR_THRESH:
        nav.curSpinDir = newSpinDir
        nav.changeSpinDirCounter = 0
        if DEBUG: nav.printf("Switching spin directions my.h " +
                             str(nav.brain.my.h)+
                             " and my target h: " + str(targetH))

    if nav.atHeadingGoTo(targetH):
        nav.stopSpinToWalkCount += 1
    else :
        nav.stopSpinToWalkCount -= 1
        nav.stopSpinToWalkCount = max(0, nav.stopSpinToWalkCount)

    if nav.stopSpinToWalkCount > constants.GOTO_SURE_THRESH:
        return nav.goLater('walkStraightToPoint')
    if nav.atDestinationCloser():
        return nav.goLater('spinToFinalHeading')

    sTheta = nav.curSpinDir * constants.GOTO_SPIN_SPEED * \
        nav.getRotScale(headingDiff)

    if sTheta != nav.walkTheta:
        nav.setSpeed(0, 0, sTheta)

    return nav.stay()

def walkStraightToPoint(nav):
    """
    State to walk forward w/some turning
    until localization thinks we are close to the point
    Stops if we get there
    If we no longer are heading towards it change to the spin state.
    """
    if nav.firstFrame():
        nav.walkToPointCount = 0
        nav.walkToPointSpinCount = 0

    if nav.atDestinationCloser():
        nav.walkToPointCount += 1
    else :
        nav.walkToPointCount = 0

    if nav.walkToPointCount > constants.GOTO_SURE_THRESH:
        return nav.goLater('spinToFinalHeading')

    my = nav.brain.my
    targetH = MyMath.getTargetHeading(my, nav.destX, nav.destY)

    if nav.notAtHeading(targetH):
        nav.walkToPointSpinCount += 1
    else :
        nav.walkToPointSpinCount = 0

    if nav.walkToPointSpinCount > constants.GOTO_SURE_THRESH:
        return nav.goLater('spinToWalkHeading')

    bearing = MyMath.getRelativeBearing(my.x, my.y, my.h, nav.destX,nav.destY)
    distToDest = MyMath.dist(my.x, my.y, nav.destX, nav.destY)
    if distToDest < ChaseBallConstants.APPROACH_WITH_GAIN_DIST:
        gain = constants.GOTO_FORWARD_GAIN * MyMath.dist(my.x, my.y,
                                                         nav.destX, nav.destY)
    else :
        gain = 1.0

    sTheta = MyMath.clip(MyMath.sign(bearing) *
                         constants.GOTO_STRAIGHT_SPIN_SPEED *
                         nav.getRotScale(bearing),
                         -constants.GOTO_STRAIGHT_SPIN_SPEED,
                         constants.GOTO_STRAIGHT_SPIN_SPEED )

    if fabs(sTheta) < constants.MIN_SPIN_MAGNITUDE_WALK:
        sTheta = 0

    sX = MyMath.clip(constants.GOTO_FORWARD_SPEED*gain,
                     constants.WALK_TO_MIN_X_SPEED,
                     constants.WALK_TO_MAX_X_SPEED)

    nav.setSpeed(sX, 0, sTheta)
    return nav.stay()

def spinToFinalHeading(nav):
    """
    Spins until we are facing the final desired heading
    Stops when at heading
    """
    if nav.firstFrame():
        nav.stopSpinToWalkCount = 0

    targetH = nav.destH

    headingDiff = nav.brain.my.h - targetH
    if DEBUG:
        nav.printf("Need to spin to %g, heading diff is %g,heading uncert is %g"
                   % (targetH, headingDiff, nav.brain.my.uncertH))
    spinDir = MyMath.getSpinDir(nav.brain.my.h, targetH)

    spin = spinDir*constants.GOTO_SPIN_SPEED*nav.getRotScale(headingDiff)

    if nav.atHeading(targetH):
        nav.stopSpinToWalkCount += 1
    else:
        nav.stopSpinToWalkCount = 0

    if nav.stopSpinToWalkCount > constants.CHANGE_SPIN_DIR_THRESH:
        if nav.movingOrtho:
            return nav.goLater('orthoWalkToPoint')
        return nav.goLater('stop')

    nav.setSpeed(0, 0, spin)
    return nav.stay()

def orthoWalkToPoint(nav):
    """
    State to walk forward until localization thinks we are close to the point
    Stops if we get there
    If we no longer are heading towards it change to the spin state
    """
    my = nav.brain.my
    bearing = MyMath.getRelativeBearing(my.x, my.y, my.h, nav.destX,nav.destY)
    absBearing = fabs(bearing)
    if DEBUG:
        nav.printf('bearing: %g  absBearing: %g  my.x: %g   my.y: %g  my.h: %g'%
                   (bearing, absBearing, my.x, my.y, my.h))
    if DEBUG: nav.printf((' nav.destX: ', nav.destX,
               ' nav.destY: ', nav.destY, ' nav.destH: ', nav.destH))

    if absBearing <= 45:
        return nav.goNow('orthoForward')
    elif absBearing <= 135:
        if bearing < 0:
            return nav.goNow('orthoRightStrafe')
        else:
            return nav.goNow('orthoLeftStrafe')
    elif absBearing <= 180:
            return nav.goNow('orthoBackward')

    return nav.stay()

def orthoForward(nav):

    if nav.firstFrame():
        nav.walkToPointCount = 0
        nav.walkToPointSpinCount = 0
        nav.switchOrthoCount = 0

    if nav.notAtHeading(nav.destH):
        nav.walkToPointSpinCount += 1
        if nav.walkToPointSpinCount > constants.GOTO_SURE_THRESH:
            return nav.goLater('spinToFinalHeading')

    if nav.atDestinationCloser():
        nav.walkToPointCount += 1
        if nav.walkToPointCount > constants.GOTO_SURE_THRESH:
            return nav.goLater('stop')

    nav.setSpeed(constants.GOTO_FORWARD_SPEED,0,0)
    my = nav.brain.my
    bearing = MyMath.getRelativeBearing(my.x, my.y, my.h, nav.destX,nav.destY)

    if -45 <= bearing <= 45:
        return nav.stay()

    nav.switchOrthoCount += 1
    if nav.switchOrthoCount > constants.GOTO_SURE_THRESH:
        return nav.goLater('orthoWalkToPoint')
    return nav.stay()

def orthoBackward(nav):
    if nav.firstFrame():
        nav.walkToPointCount = 0
        nav.walkToPointSpinCount = 0
        nav.switchOrthoCount = 0

    if nav.notAtHeading(nav.destH):
        nav.walkToPointSpinCount += 1
        if nav.walkToPointSpinCount > constants.GOTO_SURE_THRESH:
            return nav.goLater('spinToFinalHeading')

    if nav.atDestinationCloser():
        nav.walkToPointCount += 1
        if nav.walkToPointCount > constants.GOTO_SURE_THRESH:
            return nav.goLater('stop')

    nav.setSpeed(constants.GOTO_BACKWARD_SPEED,0,0)
    my = nav.brain.my
    bearing = MyMath.getRelativeBearing(my.x, my.y, my.h, nav.destX,nav.destY)

    if 135 <= bearing or -135 >= bearing:
        return nav.stay()

    nav.switchOrthoCount += 1
    if nav.switchOrthoCount > constants.GOTO_SURE_THRESH:
        return nav.goLater('orthoWalkToPoint')
    return nav.stay()

def orthoRightStrafe(nav):
    if nav.firstFrame():
        nav.walkToPointCount = 0
        nav.walkToPointSpinCount = 0
        nav.switchOrthoCount = 0

    if nav.notAtHeading(nav.destH):
        nav.walkToPointSpinCount += 1
        if nav.walkToPointSpinCount > constants.GOTO_SURE_THRESH:
            return nav.goLater('spinToFinalHeading')

    if nav.atDestinationCloser():
        nav.walkToPointCount += 1
        if nav.walkToPointCount > constants.GOTO_SURE_THRESH:
            return nav.goLater('stop')

    nav.setSpeed(0, -constants.GOTO_STRAFE_SPEED,0)
    my = nav.brain.my
    bearing = MyMath.getRelativeBearing(my.x, my.y, my.h, nav.destX,nav.destY)

    if -135 <= bearing <= -45:
        return nav.stay()

    nav.switchOrthoCount += 1
    if nav.switchOrthoCount > constants.GOTO_SURE_THRESH:
        return nav.goLater('orthoWalkToPoint')
    return nav.stay()

def orthoLeftStrafe(nav):
    if nav.firstFrame():
        nav.walkToPointCount = 0
        nav.walkToPointSpinCount = 0
        nav.switchOrthoCount = 0

    if nav.notAtHeading(nav.destH):
        nav.walkToPointSpinCount += 1
        if nav.walkToPointSpinCount > constants.GOTO_SURE_THRESH:
            return nav.goLater('spinToFinalHeading')

    if nav.atDestinationCloser():
        nav.walkToPointCount += 1
        if nav.walkToPointCount > constants.GOTO_SURE_THRESH:
            return nav.goLater('stop')

    nav.setSpeed(0, constants.GOTO_STRAFE_SPEED,0)
    my = nav.brain.my
    bearing = MyMath.getRelativeBearing(my.x, my.y, my.h, nav.destX,nav.destY)
    absBearing = abs(bearing)

    if 45 <= bearing <= 135:
        return nav.stay()

    nav.switchOrthoCount += 1
    if nav.switchOrthoCount > constants.GOTO_SURE_THRESH:
        return nav.goLater('orthoWalkToPoint')
    return nav.stay()

def omniWalkToPoint(nav):
    if nav.firstFrame():
        nav.walkToPointCount = 0
    if nav.brain.play.isRole(GOALIE):
        if nav.atDestinationGoalie() and nav.atHeading():
            return nav.goNow('stop')
    else:
        if nav.atDestinationCloser() and nav.atHeading():
            return nav.goNow('stop')

    my = nav.brain.my
    bearing = MyMath.getRelativeBearing(my.x, my.y, my.h, nav.destX, nav.destY)
    absBearing = abs(bearing)
    sX, sY, sTheta = 0.0, 0.0, 0.0

    distToDest = MyMath.dist(my.x, my.y, nav.destX, nav.destY)

    forwardGain = constants.OMNI_GOTO_X_GAIN * distToDest* \
        cos(radians(bearing))
    strafeGain = constants.OMNI_GOTO_Y_GAIN * distToDest* \
        sin(radians(bearing))
    spinGain = constants.GOTO_SPIN_GAIN

    sX = constants.OMNI_GOTO_FORWARD_SPEED * forwardGain
    sY = constants.OMNI_GOTO_STRAFE_SPEED  * strafeGain

    sX = MyMath.clip(sX,
                     constants.OMNI_MIN_X_SPEED,
                     constants.OMNI_MAX_X_SPEED)
    sY = MyMath.clip(sY,
                     constants.OMNI_MIN_Y_SPEED,
                     constants.OMNI_MAX_Y_SPEED,)

    if fabs(sY) < constants.OMNI_MIN_Y_MAGNITUDE:
        sY = 0
    if fabs(sX) < constants.OMNI_MIN_X_MAGNITUDE:
        sX = 0


    spinDir = MyMath.getSpinDir(my.h, nav.destH)
    sTheta = spinDir * fabs(my.h - nav.destH) * spinGain

    sTheta = MyMath.clip(sTheta,
                         constants.OMNI_MIN_SPIN_SPEED,
                         constants.OMNI_MAX_SPIN_SPEED)

    if fabs(sTheta) < constants.OMNI_MIN_SPIN_MAGNITUDE:
        sTheta = 0.0

    if nav.atDestinationCloser():
        sX = sY = 0.0
    if nav.atHeading():
        sTheta = 0.0

    if DEBUG: nav.printf("sX: %g  sY: %g  sTheta: %g" %
               (sX, sY, sTheta))
    nav.setSpeed(sX, sY, sTheta)
    return nav.stay()

# State to be used with standard setSpeed movement
def walking(nav):
    """
    State to be used when setSpeed is called
    """
    if nav.firstFrame() or nav.updatedTrajectory:
        nav.setSpeed(nav.walkX, nav.walkY, nav.walkTheta)
        nav.updatedTrajectory = False

    return nav.stay()
# State to use with the setSteps method
def stepping(nav):
    """
    We use this to go a specified number of steps.
    This is different from walking.
    """
    if nav.firstFrame():
        nav.step(nav.stepX, nav.stepY, nav.stepTheta, nav.numSteps)
    elif not nav.brain.motion.isWalkActive():
        return nav.goNow("stopped")
    return nav.stay()

### Stopping States ###
def stop(nav):
    """
    Wait until the walk is finished.
    """
    if nav.firstFrame():
        if nav.brain.motion.isWalkActive():
            nav.setSpeed(0,0,0)
    nav.walkX = nav.walkY = nav.walkTheta = 0


    if not nav.brain.motion.isWalkActive():
        return nav.goNow('stopped')

    return nav.stay()

def stopped(nav):
    nav.walkX = nav.walkY = nav.walkTheta = 0
    return nav.stay()

def orbitPoint(nav):
    if nav.firstFrame():
        nav.setSpeed(0,
                    nav.orbitDir*constants.ORBIT_STRAFE_SPEED,
                    nav.orbitDir*constants.ORBIT_SPIN_SPEED )
    return nav.stay()


def orbitPointThruAngle(nav):
    """
    Circles around a point in front of robot, for a certain angle
    """
    if fabs(nav.angleToOrbit) < constants.MIN_ORBIT_ANGLE:
        return nav.goNow('stop')
    if nav.firstFrame():
        if nav.angleToOrbit < 0:
            nav.orbitDir = constants.ORBIT_LEFT
        else:
            nav.orbitDir = constants.ORBIT_RIGHT

        if fabs(nav.angleToOrbit) <= constants.ORBIT_SMALL_ANGLE:
            sY = constants.ORBIT_STRAFE_SPEED * constants.ORBIT_SMALL_GAIN
            sT = constants.ORBIT_SPIN_SPEED * constants.ORBIT_SMALL_GAIN

        elif fabs(nav.angleToOrbit) <= constants.ORBIT_LARGE_ANGLE:
            sY = constants.ORBIT_STRAFE_SPEED * \
                constants.ORBIT_MID_GAIN
            sT = constants.ORBIT_SPIN_SPEED * \
                constants.ORBIT_MID_GAIN
        else :
            sY = constants.ORBIT_STRAFE_SPEED * \
                constants.ORBIT_LARGE_GAIN
            sT = constants.ORBIT_SPIN_SPEED * \
                constants.ORBIT_LARGE_GAIN

        nav.setSpeed(-0.5, nav.orbitDir*sY, nav.orbitDir*sT)

    #  (frames/second) / (degrees/second) * degrees
    framesToOrbit = fabs((constants.FRAME_RATE / nav.walkTheta) *
                         nav.angleToOrbit)
    if nav.counter >= framesToOrbit:
        return nav.goLater('stop')
    return nav.stay()
