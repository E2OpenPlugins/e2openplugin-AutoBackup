##################################
##################################
# Configuration GUI
from . import _
import plugin
import os
import enigma
from Components.config import config, configfile, getConfigListEntry, ConfigSelection
from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Tools.FuzzyDate import FuzzyTime
from Screens.Standby import getReasons
from Tools.BoundFunction import boundFunction

FRIENDLY = {
	"/media/hdd": _("Harddisk"),
	"/media/usb": _("USB"),
	"/media/cf": _("CF"),
	"/media/mmc1": _("SD"),
	}
def getLocationChoices():
	result = []
	for line in open('/proc/mounts', 'r'):
		items = line.split()
		if items[1].startswith('/media'):
			desc = FRIENDLY.get(items[1], items[1])
			if items[0].startswith('//'):
				desc += ' (*)'
			result.append((items[1], desc))
		elif items[1] == '/' and items[0].startswith('/dev/'):
			# Box that has a rootfs mounted from a device
			desc = _("root")
			# On a 7025, that'd be the harddisk or CF
			if items[0].startswith('/dev/hdc'):
				desc = _("CF")
			elif items[0].startswith('/dev/hda'):
				desc = _("Harddisk")
			result.append((items[1], desc))
	return result

def getStandardFiles():
	return [os.path.normpath(n.strip()) for n in open('/usr/lib/enigma2/python/Plugins/Extensions/AutoBackup/backup.cfg', 'r')]

def getSelectedFiles():
	result = getStandardFiles()
	try:
		result += [os.path.normpath(n.strip()) for n in open('/etc/backup.cfg', 'r')]
	except:
		# ignore missing user cfg file
		pass
	return result

def saveSelectedFiles(files):
	standard = getStandardFiles()
	try:
		f = open('/etc/backup.cfg', 'w')
		for fn in files:
			fn = os.path.normpath(fn)
			if fn not in standard:
				f.write(fn + '\n')
		f.close()
	except Exception, ex:
		print "[AutoBackup] Failed to write /etc/backup.cfg", ex

class Config(ConfigListScreen,Screen):
	skin = """
<screen position="center,center" size="560,400" title="AutoBackup Configuration" >
	<ePixmap name="red"    position="0,0"   zPosition="2" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
	<ePixmap name="green"  position="140,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
	<ePixmap name="yellow" position="280,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
	<ePixmap name="blue"   position="420,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />

	<widget name="key_red" position="0,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
	<widget name="key_green" position="140,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
	<widget name="key_yellow" position="280,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
	<widget name="key_blue" position="420,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="background" shadowOffset="-2,-2" />

	<widget name="config" position="10,40" size="540,200" scrollbarMode="showOnDemand" />

	<widget name="statusbar" position="10,250" size="470,20" font="Regular;18" />
	<widget name="status" position="10,280" size="540,130" font="Console;14" />

	<ePixmap alphatest="on" pixmap="skin_default/icons/clock.png" position="480,383" size="14,14" zPosition="3"/>
	<widget font="Regular;18" halign="left" position="505,380" render="Label" size="55,20" source="global.CurrentTime" transparent="1" valign="center" zPosition="3">
		<convert type="ClockToText">Default</convert>
	</widget>
</screen>"""

	def __init__(self, session, args=0):
		self.session = session
		self.skinName = ["Config_AutoBackup", "Config"]
		self.setup_title = _("AutoBackup Configuration")
		Screen.__init__(self, session)
		cfg = config.plugins.autobackup
		choices=getLocationChoices()
		if choices:
			currentwhere = cfg.where.value
			defaultchoice = choices[0][0]
			for k,v in choices:
				if k == currentwhere:
					defaultchoice = k
					break
		else:
			defaultchoice = ""
			choices = [("", _("Nowhere"))]
		self.cfgwhere = ConfigSelection(default=defaultchoice, choices=choices)
		configList = [
			getConfigListEntry(_("Backup location"), self.cfgwhere),
			getConfigListEntry(_("Daily automatic backup"), cfg.enabled),
			getConfigListEntry(_("Automatic start time"), cfg.wakeup),
			getConfigListEntry (_("Create Autoinstall"), cfg.autoinstall),
			getConfigListEntry (_("EPG cache backup"), cfg.epgcache),
			getConfigListEntry (_("Save previous backup"), cfg.prevbackup),
			]
		ConfigListScreen.__init__(self, configList, session=session, on_change=self.changedEntry)
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("OK"))
		self["key_yellow"] = Button(_("Manual"))
		self["key_blue"] = Button(_("Options/Restore"))
		self["statusbar"] = Label()
		self["status"] = ScrollLabel('', showscrollbar=False)
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
		{
			"red": self.cancel,
			"green": self.save,
			"yellow": self.dobackup,
			"blue": self.menu,
			"save": self.save,
			"cancel": self.cancel,
			"ok": self.save,
			"menu": self.menu,
		}, -2)
		self.onChangedEntry = []
		self.data = ''
		self.container = enigma.eConsoleAppContainer()
		self.container.appClosed.append(self.appClosed)
		self.container.dataAvail.append(self.dataAvail)
		self.cfgwhere.addNotifier(self.changedWhere)
		self.onClose.append(self.__onClose)
		self.setTitle(_("AutoBackup Configuration"))

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]
	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())
	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

	def changedWhere(self, cfg):
		if not cfg.value:
			self["status"].setText(_("No suitable media found, insert USB stick, flash card or harddisk."))
		else:
			config.plugins.autobackup.where.value = cfg.value
			path = os.path.join(cfg.value, 'backup')
			try:
				if os.path.isfile(os.path.join(path, ".timestamp")) and os.path.isfile(os.path.join(path, "PLi-AutoBackup.tar.gz")):
					st = os.stat(os.path.join(path, ".timestamp"))
					self["status"].setText(_("Last backup date") + ": " + " ".join(FuzzyTime(st.st_mtime, inPast=True)))
				else:
					self["status"].setText(_("No backup present"))
			except Exception, ex:
				print "Failed to stat %s: %s" % (path, ex)
				self["status"].setText(_("No backup present"))

	def __onClose(self):
		self.cfgwhere.notifiers.remove(self.changedWhere)

	def save(self):
		config.plugins.autobackup.where.value = self.cfgwhere.value
		config.plugins.autobackup.where.save()
		self.saveAll()
		self.close(True,self.session)

	def cancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close(False,self.session)

	def menu(self):
		lst = [
			(_("Select files to backup"), self.selectFiles),
			(_("Run a backup now"), self.dobackup),
			(_("Backup EPG cache"), self.doepgcachebackup),
			(_("Run autoinstall"), self.doautoinstall),
			(_("Remove autoinstall list"), self.doremoveautoinstall),
			(_("Restore"), self.dorestore),
		]
		self.session.openWithCallback(self.menuDone, ChoiceBox, list=lst)

	def menuDone(self, result):
		if not result or not result[1]:
			return
		result[1]()

	def selectFiles(self):
		self.session.open(BackupSelection)

	def showOutput(self):
		self["status"].setText(self.data)

	def dobackup(self):
		if not self.cfgwhere.value:
			return
		self.saveAll()
		# Write config file before creating the backup so we have it all
		configfile.save()
		if config.plugins.autobackup.epgcache.value:
			self.doepgcachebackup()
		self.data = ''
		self.showOutput()
		self["statusbar"].setText(_('Running...'))
		cmd = plugin.backupCommand()
		if self.container.execute(cmd):
			print "[AutoBackup] failed to execute"
			self.showOutput()

	def dorestore(self):
		backupList = []
		foundBackupLocations = [media for media in os.listdir("/media/") if os.path.isdir(os.path.join("/media/", media))]
		for backupMedia in foundBackupLocations:
			path = "/media/%s/backup/" % backupMedia
			if os.path.isfile(path + "PLi-AutoBackup.tar.gz") and os.path.isfile(path + ".timestamp"):
				try:
					st = os.stat(os.path.join(path, ".timestamp"))
					backupList.append(("/media/%s " % backupMedia + _("from: ") + " ".join(FuzzyTime(st.st_mtime, inPast=True)), "/media/%s" % backupMedia, st.st_mtime))
				except Exception, ex:
					print "Failed to stat %s: %s" % (path, ex)

		if not backupList:
			self.session.open(MessageBox, _("No settings backups found"), type=MessageBox.TYPE_ERROR, timeout=10)
			return
		backupList.sort(key=lambda b: b[2], reverse=True)
		self.session.openWithCallback(self.dorestorenow_reason, MessageBox, _("Choose settings backup which should be restored.\nDo you really want to restore these settings and restart?"), list=backupList)

	def dorestorenow_reason(self, path):
		if not path:
			return
		reason = getReasons(self.session)
		if reason:
			text = reason + "\n" + _("Do you want to restore your settings?")
			self.session.openWithCallback(boundFunction(self.dorestorenow, path), MessageBox, text, simple=True)
		else:
			self.dorestorenow(path)

	def dorestorenow(self, path, answer=True):
		if not path or not answer:
			return
		self.data = ''
		self.showOutput()
		self["statusbar"].setText(_('Running...'))
		cmd = '/etc/init.d/settings-restore.sh ' + path + ' ; killall -9 enigma2'
		if self.container.execute(cmd):
			print "[AutoBackup] failed to execute"
			self.showOutput()

	def doautoinstall(self):
		backupList = []
		foundBackupLocations = [media for media in os.listdir("/media/") if os.path.isdir(os.path.join("/media/", media))]
		for backupMedia in foundBackupLocations:
			path = "/media/%s/backup/" % backupMedia
			if os.path.isfile(path + "autoinstall") and os.path.isfile(path + ".timestamp"):
				try:
					st = os.stat(os.path.join(path, ".timestamp"))
					backupList.append(("/media/%s " % backupMedia + _("from: ") + " ".join(FuzzyTime(st.st_mtime, inPast=True)), "/media/%s" % backupMedia, st.st_mtime))
				except Exception, ex:
					print "Failed to stat %s: %s" % (path, ex)

		if not backupList:
			self.session.open(MessageBox, _("No autoinstall list found"), type=MessageBox.TYPE_ERROR, timeout=10)
			return
		backupList.sort(key=lambda b: b[2], reverse=True)
		self.session.openWithCallback(self.doautoinstallnow, MessageBox, _("Choose a backup.\nThis will reinstall all plugins from your backup.\nDo you really want to reinstall?"), list=backupList)

	def doautoinstallnow(self, path):
		if not path:
			return
		self.data = ''
		self.showOutput()
		self["statusbar"].setText(_('Running...'))
		cmd = 'opkg update && while read f o; do opkg install $o $f; done < ' + path + '/backup/autoinstall'
		if self.container.execute(cmd):
			print "[AutoInstall] failed to execute"
			self.showOutput()

	def doremoveautoinstall(self):
		backupList = []
		foundBackupLocations = [media for media in os.listdir("/media/") if os.path.isdir(os.path.join("/media/", media))]
		for backupMedia in foundBackupLocations:
			path = "/media/%s/backup/" % backupMedia
			if os.path.isfile(path + "autoinstall") and os.path.isfile(path + ".timestamp"):
				try:
					st = os.stat(os.path.join(path, ".timestamp"))
					backupList.append(("/media/%s " % backupMedia + _("from: ") + " ".join(FuzzyTime(st.st_mtime, inPast=True)), "/media/%s" % backupMedia, st.st_mtime))
				except Exception, ex:
					print "Failed to stat %s: %s" % (path, ex)

		if not backupList:
			self.session.open(MessageBox, _("No autoinstall list found"), type=MessageBox.TYPE_ERROR, timeout=10)
			return
		backupList.sort(key=lambda b: b[2], reverse=True)
		self.session.openWithCallback(self.doremoveautoinstallnow, MessageBox, _("Choose a backup.\nThis will delete autoinstall list.\nDo you really want to continue?"), list=backupList)

	def doremoveautoinstallnow(self, path):
		if not path:
			return
		path = os.path.join(path, 'backup', "autoinstall")
		try:
			os.unlink(path)
		except:
			pass
		try:
			macaddr = open('/sys/class/net/eth0/address').read().strip().replace(':','')
			os.unlink(path + macaddr)
		except:
			pass

	def doepgcachebackup(self):
		enigma.eEPGCache.getInstance().save()

	def appClosed(self, retval):
		print "[AutoBackup] done:", retval
		if retval:
			txt = _("Failed")
		else:
			txt = _("Done")
		self.showOutput()
		self.data = ''
		self["statusbar"].setText(txt)
		self.changedWhere(self.cfgwhere)

	def dataAvail(self, s):
		print "[AutoBackup]", s.strip()
		self["status"].appendText(s)

class BackupSelection(Screen):
	skin = """
		<screen position="center,center" size="560,400" title="Select files/folders to backup">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget name="checkList" position="5,50" size="550,350" transparent="1" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["BackupSelection_AutoBackup", "BackupSelection"]
		from Components.Sources.StaticText import StaticText
		from Components.FileList import MultiFileSelectList
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText()
		selectedFiles = getSelectedFiles()
		defaultDir = '/'
		inhibitDirs = ["/bin", "/boot", "/dev", "/autofs", "/lib", "/proc", "/sbin", "/sys", "/hdd", "/tmp", "/mnt", "/media"]
		self.filelist = MultiFileSelectList(selectedFiles, defaultDir, inhibitDirs=inhibitDirs )
		self["checkList"] = self.filelist
		self["actions"] = ActionMap(["DirectionActions", "OkCancelActions", "ShortcutActions"],
		{
			"cancel": self.exit,
			"red": self.exit,
			"yellow": self.changeSelectionState,
			"green": self.saveSelection,
			"ok": self.okClicked,
			"left": self.filelist.pageUp,
			"right": self.filelist.pageDown,
			"down": self.filelist.down,
			"up": self.filelist.up
		}, -1)
		if not self.selectionChanged in self.filelist.onSelectionChanged:
			self.filelist.onSelectionChanged.append(self.selectionChanged)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		idx = 0
		self["checkList"].moveToIndex(idx)
		self.setWindowTitle()
		self.selectionChanged()

	def setWindowTitle(self):
		self.setTitle(_("Select files/folders to backup"))

	def selectionChanged(self):
		current = self["checkList"].getCurrent()[0]
		if len(current) > 2:
			if current[2] is True:
				self["key_yellow"].setText(_("Deselect"))
			else:
				self["key_yellow"].setText(_("Select"))

	def changeSelectionState(self):
		self["checkList"].changeSelectionState()

	def saveSelection(self):
		saveSelectedFiles(self["checkList"].getSelectedList())
		self.close(None)

	def exit(self):
		self.close(None)

	def okClicked(self):
		if self.filelist.canDescent():
			self.filelist.descent()

