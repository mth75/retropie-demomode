#!/usr/bin/python3

import glob
import random
import select
import os
import subprocess
import re
import signal
import threading
import sys
import time
import logging

logging.basicConfig(filename='/var/tmp/rungames.log',level=logging.INFO)
game_exclusions = [ '.*/genesis/.*', '.*/mame-advmame/.*', '.*/pc/pcdata/.*', '.*/vectrex/overlays/.*', '.*/*/*.srm', '.*/nes/*.state', '.*/snes/*.state']
INACTIVITY_TIMEOUT = 60

def filter_games(gamename) :
	for rule in game_exclusions:
		if re.match(rule, gamename) != None : return False
	return True

gamelist = list(filter(filter_games, glob.glob('/home/pi/RetroPie/roms/*/*')))

def getRandomGame() :
	global gamelist
	random.shuffle(gamelist)
	logging.info('Random game selected: ' + gamelist[0])
	return gamelist[0]

def inputAvailable(fds, timeout, exitPipeFd) :
	global current_game
	#logging.info('Checking for input on: ' + str(fds) + ', exitFd= '+str(exitPipeFd))
	(rd, wr, sp) = select.select(fds, [], [], timeout)
	#logging.debug('Select reported read available on: ' + str(rd))
	result = rd != []
	while (rd != []):
		rd[0].read(1)
		if rd[0] == exitPipeFd:
			logging.warning('Dead child received in main loop (inputAvailable)')
			result = False
		(rd, wr, sp) = select.select(fds, [], [], 0)
	#logging.info('inputAvailable = ' + str(result))
	return result

fds = [open(fn, 'rb') for fn in glob.glob('/dev/input/event*')]

def killprocs(pid):
	try:
		os.kill(pid, signal.SIGTERM)
	except:
		pass

def killgame(pid):
	subp = subprocess.Popen('pstree '+str(pid)+' -p -a -l | cut -d, -f2 | cut -d\' \' -f1', stdout=subprocess.PIPE, shell=True)
	result = subp.communicate()[0].decode('utf8').split('\n')
	list(map(lambda procid : killprocs(int(procid)), [v for v in result if v != '']))

proc = 0

def popenAndCall(onExit, *popenArgs, **popenKWArgs):
    """
    Runs a subprocess.Popen, and then calls the function onExit when the
    subprocess completes.

    Use it exactly the way you'd normally use subprocess.Popen, except include a
    callable to execute as the first argument. onExit is a callable object, and
    *popenArgs and **popenKWArgs are simply passed up to subprocess.Popen.
    """

    def runInThread(onExit, popenArgs, popenKWArgs):
        global proc
        proc = subprocess.Popen(*popenArgs, **popenKWArgs)
        onExit(proc.wait())
        return

    thread = threading.Thread(target=runInThread,
                              args=(onExit, popenArgs, popenKWArgs))
    thread.start()

    return thread

def on_exit(code):
	global game_start_time
	global exitPipeWrite
	logging.info('onExit received at '+str(time.time()))
	if (code == 0):
		if (time.time() - game_start_time > 10):
			logging.info('Game exited by user after 10sec. Exiting.')
			os._exit(0)
		else:
			logging.info('Game exited before 10sec. Assumed dead. Signaling to main thread')
			exitPipeWrite.write('a')
			logging.info('Signaled')
	else:
		logging.info('Game exited with nonzero result. Assumed dead. Signaling to main thread')
		exitPipeWrite.write('b')
		logging.info('Signaled')

def purgueFd(fd) :
	(rd, wr, sp) = select.select([fd], [], [], 0)
	result = rd != []
	while (rd != []):
			rd[0].read(1)
			(rd, wr, sp) = select.select([fd], [], [], 0)

def clearScreen() :
	os.system('clear')

exitPipeRead, exitPipeWrite = os.pipe()
exitPipeRead, exitPipeWrite = os.fdopen(exitPipeRead,'rb'), os.fdopen(exitPipeWrite,'w')
fds.append(exitPipeRead)

logging.info('exitPipeRead: ' + str(exitPipeRead))

os.system('alias dialog=:')

while 1 :
	purgueFd(exitPipeRead)
	clearScreen()
	gamefile = getRandomGame()
	current_game = gamefile
	emulator = re.search('.*/([^/]+)/[^/]+', gamefile).group(1)
	cmd = '/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ "' + emulator + '" "'+gamefile+'"'
	game_start_time = time.time()
	logging.info('Starting game at '+str(game_start_time)+': '+cmd)
	popenAndCall(on_exit, cmd, stdin=0, stdout=1, stderr=2, shell=True)#, preexec_fn=os.setsid)

	timeOutTime = INACTIVITY_TIMEOUT
	while (inputAvailable(fds, timeOutTime, exitPipeRead)):
		pass

	logging.info('Killing game at '+str(time.time()))
	killgame(proc.pid)
	time.sleep(5)