#!/bin/sh
# Backup files to harddisk backup dir

AUTOINSTALL="no"

if [ -z "$1" ] ; then
	echo "usage: $0 [-a] /path/to/destination"
	exit 1
fi
if [ "$1" == "-a" ] ; then
	AUTOINSTALL="yes"
	shift
fi
BACKUPDIR="$1"
if [ -z "$BACKUPDIR" ] ; then
	echo "No destination, aborted"
	exit 1
fi
if [ ! -d "$BACKUPDIR" ] ; then
	echo "$BACKUPDIR is not a directory, aborted"
	exit 1
fi

BACKUPFILE=/usr/lib/enigma2/python/Plugins/Extensions/AutoBackup/backup.cfg
USER_BACKUPFILE=/etc/backup.cfg
USER_AUTOINSTALL=/etc/autoinstall
INSTALLED=/etc/installed
TEMP_INSTALLED=/tmp/installed
RESTORE_TEMP=/tmp/restore.cfg
MACADDR=`cat /sys/class/net/eth0/address | tr -d :`
[ -z "$MACADDR" ] && MACADDR=nomac

echo "Backup to $BACKUPDIR/backup/"
[ ! -d "$BACKUPDIR/backup" ] && mkdir -p "$BACKUPDIR/backup"

for bckfile in $BACKUPFILE $USER_BACKUPFILE ; do
    if [ -f $bckfile ] ; then
	while read file ; do
		[ -f $file -o -d $file ] && echo $file >> $RESTORE_TEMP
	done < $bckfile
    fi
done

cp -f /etc/passwd /tmp && echo /tmp/passwd >> $RESTORE_TEMP
[ -f /etc/shadow ] && cp -f /etc/shadow /tmp && echo /tmp/shadow >> $RESTORE_TEMP

[ -f /etc/fstab ] && \
    grep -E ' cifs | nfs | swap |^UUID=|^LABEL=' /etc/fstab | sort -fd | uniq > /tmp/fstab && \
    echo /tmp/fstab >> $RESTORE_TEMP

crontab -l > /tmp/crontab 2> /dev/null && echo /tmp/crontab >> $RESTORE_TEMP

tar -czf "$BACKUPDIR/backup/PLi-AutoBackup$MACADDR.tar.gz" --files-from=$RESTORE_TEMP 2> /dev/null
ln -f -s PLi-AutoBackup$MACADDR.tar.gz "$BACKUPDIR/backup/PLi-AutoBackup.tar.gz" || \
cp -p "$BACKUPDIR/backup/PLi-AutoBackup$MACADDR.tar.gz" "$BACKUPDIR/backup/PLi-AutoBackup.tar.gz"

if [ "$AUTOINSTALL" == "yes" -a -f $INSTALLED ] ; then
	echo "Generating $BACKUPDIR/backup/autoinstall$MACADDR"
	opkg list_installed | cut -d ' ' -f 1 > $TEMP_INSTALLED
	diff $INSTALLED $TEMP_INSTALLED | grep "^+" | grep -v "^+++ $TEMP_INSTALLED" | \
               sed 's/^+//' > "$BACKUPDIR/backup/autoinstall$MACADDR"
	if [ -f $USER_AUTOINSTALL ] ; then
		for plugin in `cat ${USER_AUTOINSTALL}`
		do
			pluginname=`echo $plugin | sed -e 's/_.*//' | sed -re 's/^.+\///'`
			mv "$BACKUPDIR/backup/autoinstall$MACADDR" "$BACKUPDIR/backup/au.$$"
			grep -v "$pluginname$" "$BACKUPDIR/backup/au.$$" > "$BACKUPDIR/backup/autoinstall$MACADDR"
		done
		cat $USER_AUTOINSTALL >> "$BACKUPDIR/backup/autoinstall$MACADDR"
	fi
	ln -f -s autoinstall$MACADDR "$BACKUPDIR/backup/autoinstall" || \
	cp -p "$BACKUPDIR/backup/autoinstall$MACADDR" "$BACKUPDIR/backup/autoinstall"
fi

touch "$BACKUPDIR/backup/.timestamp"
rm -f /tmp/restore.cfg
rm -f /tmp/crontab
rm -f /tmp/fstab
rm -f /tmp/passwd
rm -f /tmp/shadow
rm -f $TEMP_INSTALLED
rm -f "$BACKUPDIR/backup/au.$$"

exit 0
